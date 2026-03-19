from django.apps import AppConfig
import logging
import asyncio
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Global agent instance
_chat_agent = None

def get_chat_agent():
    """Get the global chat agent instance."""
    return _chat_agent


def set_chat_agent(agent):
    """Set the global chat agent instance."""
    global _chat_agent
    _chat_agent = agent


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'
    verbose_name = 'AI Chatbot Assistant'

    def ready(self):
        global _chat_agent

        # Only initialize once (Django can call ready() multiple times)
        if _chat_agent is not None:
            return

        try:
            # Initialize Semantic Kernel with room booking plugin
            logger.info("Initializing AI Chatbot with Semantic Kernel...")

            # Import Django models
            from booking.models import Room as RoomModel, Booking as BookingModel, BookingRule
            from django.conf import settings

            # Import AI components from ai folder
            from ai.kernel_config import create_kernel_ollama
            from ai.booking_automation import BookingAutomation
            from ai.plugins.room_booking_plugin import RoomBookingPlugin

            # Initialize booking automation
            booking_automation = BookingAutomation(RoomModel, BookingModel, BookingRule)
            
            # Create Semantic Kernel with Ollama
            model_name = getattr(settings, 'OLLAMA_MODEL', 'gemma3:1b')
            logger.info(f"Creating kernel with Ollama model: {model_name}...")
            kernel = create_kernel_ollama(model=model_name)
            
            # Create and add room booking plugin to kernel
            room_plugin = RoomBookingPlugin(RoomModel, BookingModel, booking_automation)
            kernel.add_plugin(room_plugin, plugin_name="RoomBooking")
            logger.info("Room booking plugin added to kernel")

            # Create the chat agent
            class ChatAgent:
                def __init__(self, kernel_instance, automation, plugin_instance):
                    self.kernel = kernel_instance
                    self.automation = automation
                    self.plugin = plugin_instance
                    self.histories = {}
                    self.context_cache = {}
                    self.context_cache_time = None
                    
                def _load_knowledge_base(self) -> str:
                    """Load comprehensive knowledge base from markdown file."""
                    try:
                        import os
                        from django.conf import settings
                        
                        kb_path = os.path.join(settings.BASE_DIR, 'SYSTEM_KNOWLEDGE_BASE.md')
                        if os.path.exists(kb_path):
                            with open(kb_path, 'r', encoding='utf-8') as f:
                                kb_content = f.read()
                            logger.info(f"✓ Knowledge base loaded: {len(kb_content)} chars")
                            return kb_content
                        else:
                            logger.warning(f"Knowledge base not found at: {kb_path}")
                            return ""
                    except Exception as e:
                        logger.error(f"Failed to load knowledge base: {e}")
                        return ""
                
                def _load_database_context(self) -> dict:
                    """Synchronous DB loader used by both sync and async wrappers."""
                    # This function will be called inside a thread when used from async code
                    from datetime import datetime, timedelta

                    # Cache context for 5 minutes to improve performance
                    now = datetime.now()
                    if (self.context_cache_time and (now - self.context_cache_time).seconds < 300 and self.context_cache):
                        logger.debug("Using cached database context")
                        return self.context_cache

                    try:
                        logger.info("Loading ENHANCED database context (RAG) [sync]")

                        # 1. Load ALL available rooms from database (not just 20)
                        rooms = list(RoomModel.objects.filter(is_available=True).values(
                            'id', 'name', 'room_number', 'capacity', 'room_type',
                            'equipment', 'description'
                        ))  # Load ALL rooms for better understanding

                        # 2. Load booking rules
                        rule = BookingRule.objects.filter(is_active=True).first()

                        # 3. Get system statistics
                        total_rooms = RoomModel.objects.filter(is_available=True).count()
                        today = datetime.now().date()
                        total_bookings_today = BookingModel.objects.filter(
                            start_time__date=today,
                            status='confirmed'
                        ).count()

                        # 4. Build room types summary
                        room_types = list(RoomModel.objects.filter(is_available=True).values_list(
                            'room_type', flat=True
                        ).distinct())

                        # 5. Build comprehensive room index (room_number → room details mapping)
                        room_index = {
                            room['room_number']: {
                                'name': room['name'],
                                'capacity': room['capacity'],
                                'type': room.get('room_type', 'N/A'),
                                'equipment': room.get('equipment', 'N/A')
                            }
                            for room in rooms
                        }

                        context = {
                            'rooms': rooms,
                            'room_index': room_index,  # For quick validation
                            'total_rooms': total_rooms,
                            'total_bookings_today': total_bookings_today,
                            'room_types': list(room_types),
                            'booking_rules': {
                                'max_duration_hours': rule.max_duration_hours if rule else 4,
                                'max_advance_days': rule.max_advance_days if rule else 14,
                                'min_advance_hours': getattr(rule, 'min_advance_hours', 2),
                                'daily_booking_limit': getattr(rule, 'daily_booking_limit', 2),
                                'booking_start_time': rule.booking_start_time.strftime('%H:%M') if rule else '07:00',
                                'booking_end_time': rule.booking_end_time.strftime('%H:%M') if rule else '22:00'
                            }
                        }

                        # Cache the context
                        self.context_cache = context
                        self.context_cache_time = now

                        logger.info(f"✓ ENHANCED RAG Context loaded: {total_rooms} rooms (ALL), {total_bookings_today} bookings today")
                        return context

                    except Exception as e:
                        logger.error(f"Failed to load database context: {e}")
                        return {
                            'rooms': [],
                            'room_index': {},
                            'total_rooms': 0,
                            'total_bookings_today': 0,
                            'room_types': [],
                            'booking_rules': {}
                        }

                async def _load_database_context_async(self) -> dict:
                    """Async wrapper that runs DB loader in thread to avoid sync DB calls in async loop."""
                    from asgiref.sync import sync_to_async

                    # Call the synchronous loader in a thread
                    context = await sync_to_async(self._load_database_context)()
                    return context
                
                async def _retrieve_relevant_context(self, query: str) -> str:
                    """
                    Retrieve relevant context from vector store for the user query.
                    Uses semantic search to find relevant documents.
                    """
                    try:
                        from ai.vector_store import get_vector_store
                        from asgiref.sync import sync_to_async
                        
                        vector_store = get_vector_store()
                        
                        # Perform semantic searches in parallel (wrapped in sync_to_async)
                        knowledge_results = await sync_to_async(vector_store.search_knowledge)(query, n_results=3)
                        policy_results = await sync_to_async(vector_store.search_policies)(query, n_results=2)
                        
                        # Build context from results
                        context_parts = []
                        
                        if knowledge_results:
                            context_parts.append("📚 RELEVANT KNOWLEDGE:")
                            for i, result in enumerate(knowledge_results, 1):
                                source = result['metadata'].get('source_file', 'System')
                                context_parts.append(f"\n[Source {i}: {source}]")
                                context_parts.append(result['document'][:500])  # Limit length
                        
                        if policy_results:
                            context_parts.append("\n\n⚖️ RELEVANT POLICIES:")
                            for i, result in enumerate(policy_results, 1):
                                source = result['metadata'].get('source_file', 'System')
                                context_parts.append(f"\n[Policy {i}: {source}]")
                                context_parts.append(result['document'][:500])
                        
                        if context_parts:
                            retrieved_context = "\n".join(context_parts)
                            logger.info(f"✓ Retrieved {len(knowledge_results) + len(policy_results)} relevant chunks from vector store")
                            return retrieved_context
                        
                        return ""
                        
                    except Exception as e:
                        logger.warning(f"Vector store retrieval failed (non-critical): {e}")
                        return ""
                    
                async def _get_system_prompt(self, user_info: dict = None) -> str:
                    """Build ENHANCED system prompt with Knowledge Base + RAG (Retrieval-Augmented Generation)."""
                    today = datetime.now().strftime('%Y-%m-%d %A')
                    
                    # Load comprehensive knowledge base (one-time load at session start)
                    knowledge_base = self._load_knowledge_base()
                    
                    # RAG: Load real-time database context (async-safe)
                    try:
                        db_context = await self._load_database_context_async()
                    except Exception as e:
                        logger.error(f"Failed to load database context: {e}")
                        db_context = {
                            'rooms': [],
                            'room_index': {},
                            'total_rooms': 0,
                            'total_bookings_today': 0,
                            'room_types': [],
                            'booking_rules': {}
                        }
                    
                    # Build user context
                    user_context = ""
                    if user_info:
                        user_context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔐 AUTHENTICATED USER:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Name: {user_info.get('full_name', 'User')}
Email: {user_info.get('email', 'N/A')}
Student ID: {user_info.get('student_id', 'N/A')}

⚠️ CRITICAL: User is authenticated. Use email '{user_info.get('email', '')}' for ALL booking operations.
"""
                    
                    # Build COMPREHENSIVE room inventory (ALL rooms, not just 10)
                    room_inventory = ""
                    if db_context['rooms']:
                        room_inventory = "\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n📍 COMPLETE ROOM INVENTORY (Live from Database):\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                        
                        # Group rooms by type for better organization
                        rooms_by_type = {}
                        for room in db_context['rooms']:
                            room_type = room.get('room_type', 'other')
                            if room_type not in rooms_by_type:
                                rooms_by_type[room_type] = []
                            rooms_by_type[room_type].append(room)
                        
                        # Display all rooms organized by type
                        for room_type, rooms in sorted(rooms_by_type.items()):
                            room_inventory += f"\n[{room_type.upper()}]\n"
                            for room in rooms:
                                room_inventory += f"  • {room['name']} (Room #{room['room_number']}) - Capacity: {room['capacity']}\n"
                                if room.get('equipment'):
                                    equipment_short = room['equipment'][:60] + '...' if len(room['equipment']) > 60 else room['equipment']
                                    room_inventory += f"    Equipment: {equipment_short}\n"
                        
                        room_inventory += f"\nTotal: {db_context['total_rooms']} rooms available in system\n"
                        room_inventory += "⚠️ ONLY suggest rooms from this list. NEVER invent room numbers!\n"
                    
                    # Build rules context (RAG)
                    rules = db_context['booking_rules']
                    rules_context = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
⚖️ BOOKING RULES (Live from Database):
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Max Duration: {rules.get('max_duration_hours', 4)} hours per booking
• Advance Booking Window: Up to {rules.get('max_advance_days', 14)} days ahead
• Minimum Notice: {rules.get('min_advance_hours', 2)} hours before start
• Daily User Limit: {rules.get('daily_booking_limit', 2)} bookings per user
• Operating Hours: {rules.get('booking_start_time', '07:00')} - {rules.get('booking_end_time', '22:00')}
"""
                    
                    # Build comprehensive system prompt combining knowledge base + RAG
                    system_prompt = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎓 UNIVERSITY ROOM BOOKING SYSTEM
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
You are an AI assistant with REAL-TIME access to our university room booking database.

📅 CURRENT DATE: {today}

📊 LIVE SYSTEM STATUS:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
• Active Rooms: {db_context['total_rooms']}
• Bookings Today: {db_context['total_bookings_today']}
• Room Categories: {', '.join(db_context['room_types']) if db_context['room_types'] else 'N/A'}
{room_inventory}{rules_context}{user_context}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📚 COMPREHENSIVE KNOWLEDGE BASE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{knowledge_base}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎯 YOUR MISSION:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

1. **ACCURACY FIRST**: Only suggest rooms that EXIST in the inventory above
2. **DATABASE-DRIVEN**: ALWAYS call find_available_rooms() before suggesting
3. **NO HALLUCINATIONS**: Never invent room numbers, capacities, or equipment
4. **FOLLOW WORKFLOW**: Search → Present → Confirm → Book
5. **BE SPECIFIC**: Reference exact room names and numbers from search results

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🚨 CRITICAL ANTI-HALLUCINATION PROTOCOL:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚫 ABSOLUTELY FORBIDDEN:
❌ NEVER invent room numbers that are NOT in the inventory above
❌ NEVER mention rooms like "Room G", "Room H", "Room 999" if not in database
❌ NEVER claim availability for specific dates/times without calling find_available_rooms()

✅ ALLOWED:
✓ List rooms from the COMPLETE ROOM INVENTORY above (when user asks "what rooms do you have?")
✓ Reference room names, capacities, types from the inventory
✓ Show room details that are in the database

✅ MANDATORY FOR SPECIFIC AVAILABILITY CHECKS:
When user provides date/time/capacity (e.g., "I need a room for 30 people tomorrow at 2pm"):
1. MUST call find_available_rooms(date, start_time, end_time, capacity)
2. ONLY suggest rooms that function returns
3. If function returns empty → "No rooms available for that time"

✅ ALLOWED FOR GENERAL QUERIES:
When user asks general questions (e.g., "What rooms do you have?", "Show me available rooms"):
1. List rooms from the COMPLETE ROOM INVENTORY section above
2. Show room names, capacities, types, equipment from inventory
3. Make it clear these are all our rooms (not filtered by availability)
4. Suggest they provide date/time for specific availability check

EXAMPLES:

User: "What rooms do you have?"
✅ Good: "We have X rooms available. Here are some examples from our [ROOM_TYPE]..."
         (Lists actual rooms from inventory above)
❌ Bad: "We have Room 101, Room G, Room H..." (invented rooms not in inventory)

User: "I need a room for 30 people tomorrow at 2pm"
✅ Good: [Calls find_available_rooms()] → "I found Conference Room A (CR-101)..."
❌ Bad: "Room A2.3 is usually available" (didn't call function)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
💬 COMMUNICATION STYLE:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

✓ Friendly, conversational, efficient
✓ List rooms from inventory for general queries
✓ Call functions for specific availability checks
✓ Show capacity and equipment when relevant
✓ Be honest if no rooms match requirements
✓ When in doubt, reference the inventory above

Remember: You have TWO ways to provide room info:
1. General queries → List from COMPLETE ROOM INVENTORY (no function needed)
2. Specific availability → Call find_available_rooms() (function required)
"""
                    return system_prompt

                async def chat_async(self, message: str, user_email: str = "", user_id: int = None, session_id: str = "default", user_info: dict = None) -> dict:
                    """Process chat message asynchronously with RAG context."""
                    from semantic_kernel.contents.chat_history import ChatHistory
                    from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
                    
                    try:
                        # Get or create chat history for session
                        system_prompt = await self._get_system_prompt(user_info)
                        if session_id not in self.histories:
                            self.histories[session_id] = ChatHistory()
                            # Add system prompt with RAG context on first message
                            self.histories[session_id].add_system_message(system_prompt)
                            logger.info(f"New chat session created with RAG context: {session_id}")

                        chat_history = self.histories[session_id]

                        # Ensure the enhanced system prompt is present and up-to-date.
                        # Some sessions may have an old or generic system message; if so, refresh it.
                        try:
                            has_valid_system = False
                            for msg in list(chat_history.messages):
                                role = getattr(msg, 'role', None)
                                content = getattr(msg, 'content', '')
                                role_val = role.value if hasattr(role, 'value') else str(role)
                                if role_val == 'system' and isinstance(content, str):
                                    if 'UNIVERSITY ROOM BOOKING SYSTEM' in content or 'REAL-TIME access to our university room booking database' in content:
                                        has_valid_system = True
                                        break
                            if not has_valid_system:
                                # Prepend or add the new system prompt so the model has correct context
                                chat_history.add_system_message(system_prompt)
                                logger.info(f"Refreshed system prompt for session: {session_id}")
                        except Exception:
                            # If ChatHistory structure is unexpected, skip refresh but log
                            logger.debug("Could not inspect chat history for system prompt refresh")
                        
                        # Vector RAG: Retrieve relevant context from vector store
                        vector_context = await self._retrieve_relevant_context(message)
                        
                        # Enhance user message with vector context if available
                        enhanced_message = message
                        if vector_context:
                            enhanced_message = f"{message}\n\n[SYSTEM: Retrieved relevant context]\n{vector_context}"
                            logger.debug(f"Enhanced message with {len(vector_context)} chars of vector context")
                        
                        # Add user message (with vector context if available)
                        chat_history.add_user_message(enhanced_message)
                        
                        # Get chat service from kernel
                        chat_service = self.kernel.get_service()
                        
                        # Smart function detection - check if booking-related
                        message_lower = message.lower()
                        booking_keywords = [
                            'room', 'book', 'reserve', 'available', 'schedule', 
                            'meeting', 'lecture', 'capacity', 'tomorrow', 'today',
                            'find', 'search', 'show', 'list', 'my booking'
                        ]
                        
                        is_booking_query = any(kw in message_lower for kw in booking_keywords)
                        
                        # Anti-hallucination: Use lower temperature for booking queries (factual accuracy)
                        if is_booking_query:
                            settings = PromptExecutionSettings(
                                max_tokens=600,
                                temperature=0.2,  # Low temp for factual, deterministic responses
                                top_p=0.9
                            )
                            logger.debug("Using low-temperature settings for booking query (anti-hallucination)")
                        else:
                            settings = PromptExecutionSettings(
                                max_tokens=600,
                                temperature=0.7,  # Normal for conversational
                                top_p=0.95
                            )
                        
                        # Performance optimization: Only provide tools for booking queries
                        tools = None
                        if is_booking_query:
                            tools = self._get_plugin_tools()
                            logger.debug(f"Booking query detected, providing {len(tools)} tools")
                        
                        # Get AI response
                        if tools:
                            response = await chat_service.get_chat_message_contents(
                                chat_history=chat_history,
                                settings=settings,
                                tools=tools
                            )
                        else:
                            response = await chat_service.get_chat_message_contents(
                                chat_history=chat_history,
                                settings=settings
                            )
                        
                        # Handle response
                        if response and len(response) > 0:
                            first_response = response[0]
                            
                            # Check for function calls
                            has_function_calls = (
                                hasattr(first_response, 'items') and 
                                first_response.items and 
                                any(hasattr(item, 'name') for item in first_response.items)
                            )
                            
                            if has_function_calls:
                                # Execute functions
                                chat_history.add_assistant_message(first_response.content or '')
                                
                                function_results = await self._execute_functions(first_response, user_email, user_id)
                                
                                # Add function results to history
                                from semantic_kernel.contents.chat_message_content import ChatMessageContent
                                from semantic_kernel.contents.utils.author_role import AuthorRole
                                
                                for func_result in function_results:
                                    tool_message = ChatMessageContent(
                                        role=AuthorRole.TOOL,
                                        content=func_result['result'],
                                        metadata={'name': func_result['name']}
                                    )
                                    chat_history.messages.append(tool_message)
                                
                                # Get final response
                                final_response = await chat_service.get_chat_message_contents(
                                    chat_history=chat_history,
                                    settings=settings
                                )
                                
                                if final_response and len(final_response) > 0:
                                    reply = final_response[0].content if hasattr(final_response[0], 'content') else str(final_response[0])
                                    
                                    # Validate response for hallucinations (async)
                                    intent = self._extract_intent(message)
                                    validation = await self._validate_response(reply, intent)
                                    
                                    # ANTI-HALLUCINATION: Only block if rooms are NOT in database (actual hallucinations)
                                    if not validation['is_valid'] and validation['invalid_room_count'] > 0:
                                        logger.error(f"🚫 HALLUCINATION BLOCKED: {validation['warnings']}")
                                        # Don't add hallucinated response to history
                                        # Return safe fallback
                                        safe_reply = (
                                            "I need to search our database to provide accurate room information. "
                                            "Could you please provide:\n"
                                            "• Date you need the room\n"
                                            "• Start and end time\n"
                                            "• Number of people\n\n"
                                            "Then I can search for available rooms in our system."
                                        )
                                        chat_history.add_assistant_message(safe_reply)
                                        return {
                                            'intent': intent,
                                            'reply_text': safe_reply,
                                            'message': safe_reply,
                                            'function_results': function_results,
                                            'validation': validation,
                                            'hallucination_blocked': True
                                        }
                                    
                                    # Response is valid (rooms from RAG or function results)
                                    if validation['is_from_rag']:
                                        logger.info(f"✓ Response uses {validation['valid_room_count']} rooms from RAG context")
                                    
                                    # Valid response - add to history
                                    chat_history.add_assistant_message(reply)
                                    return {
                                        'intent': intent,
                                        'reply_text': reply,
                                        'message': reply,
                                        'function_results': function_results,
                                        'validation': validation
                                    }
                            else:
                                # Direct response (no function calls)
                                reply = first_response.content if hasattr(first_response, 'content') else str(first_response)
                                
                                if not reply or reply.strip() == '':
                                    reply = "I'm here to help with room bookings. What can I do for you?"
                                
                                # Validate response for hallucinations (async)
                                intent = self._extract_intent(message)
                                validation = await self._validate_response(reply, intent)
                                
                                # ANTI-HALLUCINATION: Only block actual hallucinations (invalid rooms)
                                # Allow listing rooms from RAG context even without function call
                                if not validation['is_valid'] and validation['invalid_room_count'] > 0:
                                    logger.error(f"🚫 HALLUCINATION BLOCKED (no function call): {validation['warnings']}")
                                    safe_reply = (
                                        "I need to search our database to give you accurate room information. "
                                        "Please provide the date, time, and capacity you need, and I'll "
                                        "search for available rooms."
                                    )
                                    chat_history.add_assistant_message(safe_reply)
                                    return {
                                        'intent': intent,
                                        'reply_text': safe_reply,
                                        'message': safe_reply,
                                        'validation': validation,
                                        'hallucination_blocked': True
                                    }
                                
                                # Response is valid (rooms from RAG context)
                                if validation['is_from_rag'] and intent in ['list_rooms', 'find_rooms']:
                                    logger.info(f"✓ Response lists {validation['valid_room_count']} rooms from RAG context")
                                
                                # Valid response or non-booking query
                                chat_history.add_assistant_message(reply)
                                return {
                                    'intent': intent,
                                    'reply_text': reply,
                                    'message': reply,
                                    'validation': validation
                                }
                        
                        return {
                            'intent': 'general',
                            'reply_text': "How can I assist you with room bookings today?",
                            'message': "How can I assist you with room bookings today?"
                        }
                            
                    except Exception as e:
                        logger.exception(f'Chat error: {e}')
                        return {
                            'intent': 'error',
                            'reply_text': "I'm having trouble processing your request. Please try again.",
                            'message': "I'm having trouble processing your request. Please try again."
                        }

                def _get_plugin_tools(self) -> list:
                    """Convert Semantic Kernel plugins to tools format."""
                    tools = []
                    
                    if hasattr(self.kernel, 'plugins') and 'RoomBooking' in self.kernel.plugins:
                        plugin = self.kernel.plugins['RoomBooking']
                        
                        for func_name, func in plugin.functions.items():
                            tool = {
                                "type": "function",
                                "function": {
                                    "name": func_name,
                                    "description": func.description if hasattr(func, 'description') else f"Call {func_name}",
                                    "parameters": {
                                        "type": "object",
                                        "properties": {},
                                        "required": []
                                    }
                                }
                            }
                            
                            # Extract parameters
                            if hasattr(func, 'metadata') and hasattr(func.metadata, 'parameters'):
                                for param in func.metadata.parameters:
                                    tool["function"]["parameters"]["properties"][param.name] = {
                                        "type": "string",
                                        "description": param.description if hasattr(param, 'description') else ""
                                    }
                                    
                                    if hasattr(param, 'is_required') and param.is_required:
                                        tool["function"]["parameters"]["required"].append(param.name)
                            
                            tools.append(tool)
                    
                    return tools

                async def _execute_functions(self, response, user_email: str, user_id: int = None) -> list:
                    """Execute function calls from AI response."""
                    function_results = []
                    
                    if not hasattr(response, 'items') or not response.items:
                        return function_results
                    
                    for item in response.items:
                        func_name = None
                        func_args = {}
                        
                        if hasattr(item, 'name'):
                            func_name = item.name
                            func_args_str = item.arguments if hasattr(item, 'arguments') else '{}'
                            func_args = json.loads(func_args_str) if isinstance(func_args_str, str) else func_args_str
                        elif hasattr(item, 'function') and item.function:
                            func_name = item.function.name
                            func_args = json.loads(item.function.arguments) if isinstance(item.function.arguments, str) else item.function.arguments
                        
                        if not func_name:
                            continue
                        
                        # Inject trusted identity for protected operations.
                        if func_name in ['create_booking', 'list_user_bookings']:
                            func_args.pop('user_email', None)
                            if 'user_id' not in func_args and user_id is not None:
                                func_args['user_id'] = str(user_id)
                        
                        try:
                            # Execute plugin method
                            if hasattr(self.plugin, func_name):
                                method = getattr(self.plugin, func_name)
                                
                                if asyncio.iscoroutinefunction(method):
                                    result = await method(**func_args)
                                else:
                                    result = method(**func_args)
                                
                                function_results.append({
                                    'name': func_name,
                                    'arguments': func_args,
                                    'result': str(result)
                                })
                                
                                logger.info(f"Executed function: {func_name}")
                            else:
                                logger.warning(f"Function {func_name} not found")
                                function_results.append({
                                    'name': func_name,
                                    'arguments': func_args,
                                    'result': f"Error: Function {func_name} not available"
                                })
                        except Exception as e:
                            logger.exception(f"Error executing {func_name}: {e}")
                            function_results.append({
                                'name': func_name,
                                'arguments': func_args,
                                'result': f"Error: {str(e)}"
                            })
                    
                    return function_results

                async def _validate_response(self, reply: str, intent: str = 'general') -> dict:
                    """Validate AI response for hallucinations - checks against database."""
                    import re
                    
                    warnings = []
                    is_valid = True
                    is_from_rag = False  # Track if rooms are from RAG context
                    
                    # Get current database context (async-safe)
                    try:
                        db_context = await self._load_database_context_async()
                    except Exception as e:
                        logger.error(f"Failed to load database context for validation: {e}")
                        db_context = {
                            'rooms': [],
                            'room_index': {},
                            'total_rooms': 0,
                            'total_bookings_today': 0,
                            'room_types': [],
                            'booking_rules': {}
                        }
                    room_index = db_context.get('room_index', {})
                    
                    # Pattern 1: Check for room number mentions (e.g., "A2.3", "B1.2", "Room 101")
                    room_patterns = [
                        r'[Rr]oom\s+#?([A-Z0-9]+\.?[A-Z0-9]*)',  # "Room A2.3" or "Room #A2.3"
                        r'\(#?([A-Z0-9]+\.?[A-Z0-9]*)\)',         # "(A2.3)" or "(#A2.3)"
                        r'#([A-Z0-9]+\.?[A-Z0-9]+)',              # "#A2.3"
                    ]
                    
                    mentioned_rooms = set()
                    for pattern in room_patterns:
                        matches = re.findall(pattern, reply)
                        mentioned_rooms.update(matches)
                    
                    # Check if mentioned rooms exist in database
                    valid_rooms = []
                    invalid_rooms = []
                    for room_num in mentioned_rooms:
                        if room_num in room_index:
                            valid_rooms.append(room_num)
                        else:
                            invalid_rooms.append(room_num)
                            warnings.append(f"⚠️ Room '{room_num}' mentioned but NOT in database")
                            is_valid = False
                            logger.warning(f"HALLUCINATION DETECTED: Room {room_num} doesn't exist!")
                    
                    # If ALL mentioned rooms are valid (in database), mark as from RAG
                    if mentioned_rooms and len(valid_rooms) == len(mentioned_rooms):
                        is_from_rag = True
                        logger.debug(f"✓ All {len(valid_rooms)} mentioned rooms found in database (RAG)")
                    
                    # Pattern 2: Check for generic room references without function calls
                    generic_room_phrases = [
                        'available room', 'any room', 'a room', 'some room',
                        'meeting room', 'conference room', 'classroom'
                    ]
                    
                    if any(phrase in reply.lower() for phrase in generic_room_phrases):
                        # Check if response contains specific room numbers
                        if not mentioned_rooms:
                            warnings.append("⚠️ Generic room reference without specific room number")
                            logger.warning("Generic room mention detected - should specify exact room")
                    
                    # Pattern 3: Check for capacity or equipment claims
                    if 'capacity' in reply.lower() or 'seats' in reply.lower() or 'people' in reply.lower():
                        capacity_mentioned = re.findall(r'(\d+)\s*(?:people|seats|capacity)', reply.lower())
                        if capacity_mentioned and mentioned_rooms:
                            for room_num in mentioned_rooms:
                                room_data = room_index.get(room_num, {})
                                actual_capacity = room_data.get('capacity', 0)
                                # Verify mentioned capacity matches database
                                for mentioned_cap in capacity_mentioned:
                                    if actual_capacity > 0 and int(mentioned_cap) != actual_capacity:
                                        warnings.append(f"⚠️ Capacity mismatch for room {room_num}: said {mentioned_cap}, actual {actual_capacity}")
                                        logger.warning(f"CAPACITY MISMATCH: Room {room_num} capacity is {actual_capacity}, not {mentioned_cap}")
                    
                    return {
                        'is_valid': is_valid,
                        'warnings': warnings,
                        'mentioned_rooms': list(mentioned_rooms),
                        'validated_rooms': {room: room_index.get(room) for room in mentioned_rooms if room in room_index},
                        'is_from_rag': is_from_rag,  # All rooms are from loaded database
                        'valid_room_count': len(valid_rooms),
                        'invalid_room_count': len(invalid_rooms)
                    }

                def _extract_intent(self, message: str) -> str:
                    """Extract intent from user message."""
                    message_lower = message.lower()
                    
                    # Check for specific booking intent (with date/time/capacity)
                    has_datetime = any(word in message_lower for word in ['tomorrow', 'today', 'monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'am', 'pm', ':00', 'o\'clock', 'date', 'time'])
                    has_capacity = any(word in message_lower for word in ['people', 'person', 'capacity', 'seats', 'attendees'])
                    
                    if any(word in message_lower for word in ['book', 'reserve', 'schedule']):
                        return 'book_room'
                    elif any(word in message_lower for word in ['my booking', 'my reservations', 'list']):
                        return 'list_bookings'
                    elif (has_datetime or has_capacity) and any(word in message_lower for word in ['need', 'want', 'find', 'available']):
                        return 'check_availability'  # Specific availability check
                    elif any(word in message_lower for word in ['what rooms', 'which rooms', 'show rooms', 'list rooms', 'all rooms', 'available rooms', 'have rooms']):
                        return 'list_rooms'  # General inventory query
                    elif any(word in message_lower for word in ['find', 'search', 'available', 'show']):
                        return 'find_rooms'
                    else:
                        return 'general'

                def clear_chat_history(self, session_id: str) -> bool:
                    """Clear chat history for a session."""
                    if session_id in self.histories:
                        del self.histories[session_id]
                        logger.info(f"Chat history cleared for session: {session_id}")
                        return True
                    return False
                
                def refresh_context_cache(self) -> bool:
                    """Force refresh of database context cache (for admin/testing)."""
                    try:
                        self.context_cache = {}
                        self.context_cache_time = None
                        # Run the synchronous loader directly (sync context)
                        self._load_database_context()
                        logger.info("Context cache refreshed successfully")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to refresh context cache: {e}")
                        return False

            # Initialize the chat agent
            _chat_agent = ChatAgent(kernel, booking_automation, room_plugin)
            logger.info("✓ AI Chatbot initialized successfully (Semantic Kernel + Ollama + Room Booking Plugin)")

        except Exception as e:
            logger.exception(f"Failed to initialize chatbot: {e}")
            logger.warning("Chatbot will operate in degraded mode")
            _chat_agent = None
