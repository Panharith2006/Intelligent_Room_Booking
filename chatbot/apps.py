from django.apps import AppConfig
import logging
import importlib.util
import sys
from pathlib import Path
import os
import asyncio
import json


from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

# Global agent instance
_chat_agent = None


def get_chat_agent():
    return _chat_agent


def set_chat_agent(agent):
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
            # Initialize Semantic Kernel with Groq and room booking plugin
            logger.info("Initializing Semantic Kernel with Groq and Room Booking Plugin...")

            # Import models and Semantic Kernel components
            from booking.models import Room as RoomModel, Booking as BookingModel, BookingRule
            from ai.booking_automation import BookingAutomation
            from ai.kernel_config import get_kernel
            from ai.plugins import RoomBookingPlugin

            # BookingAutomation for room operations
            booking_automation = BookingAutomation(RoomModel, BookingModel, BookingRule)
            
            # Get Semantic Kernel instance
            kernel = get_kernel()
            
            # Add room booking plugin to kernel
            room_plugin = RoomBookingPlugin(RoomModel, BookingModel, booking_automation)
            kernel.add_plugin(room_plugin, plugin_name="RoomBooking")

            class _ChatAgent:
                def __init__(self, kernel_instance, automation, plugin_instance):
                    self.kernel = kernel_instance
                    self.automation = automation
                    self.plugin_instance = plugin_instance
                    self.histories = {}

                def _parse_relative_date(self, date_str: str) -> str:
                    """Convert relative dates to YYYY-MM-DD format."""
                    from datetime import datetime, timedelta
                    import re
                    
                    date_str_lower = date_str.lower().strip()
                    today = datetime.now().date()
                    
                    if date_str_lower == 'today':
                        return today.strftime('%Y-%m-%d')
                    elif date_str_lower == 'tomorrow':
                        return (today + timedelta(days=1)).strftime('%Y-%m-%d')
                    elif 'next monday' in date_str_lower or date_str_lower == 'monday':
                        days_ahead = 0 - today.weekday()
                        if days_ahead <= 0:
                            days_ahead += 7
                        return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                    elif 'next tuesday' in date_str_lower or date_str_lower == 'tuesday':
                        days_ahead = 1 - today.weekday()
                        if days_ahead <= 0:
                            days_ahead += 7
                        return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                    elif 'next wednesday' in date_str_lower or date_str_lower == 'wednesday':
                        days_ahead = 2 - today.weekday()
                        if days_ahead <= 0:
                            days_ahead += 7
                        return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                    elif 'next thursday' in date_str_lower or date_str_lower == 'thursday':
                        days_ahead = 3 - today.weekday()
                        if days_ahead <= 0:
                            days_ahead += 7
                        return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                    elif 'next friday' in date_str_lower or date_str_lower == 'friday':
                        days_ahead = 4 - today.weekday()
                        if days_ahead <= 0:
                            days_ahead += 7
                        return (today + timedelta(days=days_ahead)).strftime('%Y-%m-%d')
                    
                    # Try to parse as date string
                    try:
                        parsed = datetime.strptime(date_str, '%Y-%m-%d')
                        return parsed.strftime('%Y-%m-%d')
                    except:
                        pass
                    
                    return date_str  # Return as-is if can't parse

                async def chat_async(self, message: str, user_email: str = "", session_id: str = "default") -> dict:
                    """Chat using Semantic Kernel with plugin support and return structured response."""
                    from semantic_kernel.contents.chat_history import ChatHistory
                    from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
                    from datetime import datetime
                    import re
                    
                    try:
                        # Get or create chat history for session
                        if session_id not in self.histories:
                            self.histories[session_id] = ChatHistory()
                        
                        chat_history = self.histories[session_id]
                        
                        # Add system message if this is a new conversation
                        if len(chat_history.messages) == 0:
                            today_date = datetime.now().strftime('%Y-%m-%d')
                            system_prompt = (
                                f"You are a friendly AI assistant. Today is {today_date}.\n\n"
                                "Answer ALL questions naturally and conversationally.\n"
                                "- For general questions (math, greetings, etc.): Just answer directly\n"
                                "- For room booking requests: Use the available functions to check the database\n\n"
                                "Be helpful, friendly, and concise in your responses."
                            )
                            chat_history.add_system_message(system_prompt)
                        
                        # Add user message (simple format for better AI understanding)
                        chat_history.add_user_message(message)
                        
                        # Get chat service from kernel
                        chat_service = self.kernel.get_service()
                        
                        # Create execution settings
                        settings = PromptExecutionSettings(
                            max_tokens=800,
                            temperature=0.7,  # Higher for more natural responses
                            top_p=0.95
                        )
                        
                        # Detect if this is a room booking related query
                        message_lower = message.lower()
                        booking_keywords = [
                            'room', 'book', 'reserve', 'reservation', 'schedule', 
                            'available', 'capacity', 'meeting', 'lecture', 'classroom',
                            'conference', 'hall', 'venue', 'space', 'facility',
                            'tomorrow', 'today', 'next week', 'monday', 'tuesday',
                            'wednesday', 'thursday', 'friday', 'saturday', 'sunday'
                        ]
                        
                        # Check if message contains booking keywords and is long enough
                        is_booking_query = (
                            len(message.split()) > 2 and  # More than 2 words
                            any(keyword in message_lower for keyword in booking_keywords)
                        )
                        
                        # Only provide tools for booking-related queries
                        tools = self._get_plugin_tools() if is_booking_query else None
                        
                        # Initial AI call
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
                        
                        # Handle function calls
                        if response and len(response) > 0:
                            first_response = response[0]
                            
                            # Log the response for debugging
                            logger.info(f"AI Response received - content: {first_response.content[:100] if first_response.content else 'None'}")
                            
                            # Check if AI wants to call a function (only if items exist and have function calls)
                            has_function_calls = (
                                hasattr(first_response, 'items') and 
                                first_response.items and 
                                len(first_response.items) > 0 and
                                any(hasattr(item, 'name') for item in first_response.items)
                            )
                            
                            if has_function_calls:
                                logger.info(f"Function calls detected: {[item.name for item in first_response.items if hasattr(item, 'name')]}")
                                # Add assistant's message with tool calls to history
                                chat_history.add_assistant_message(first_response.content or '')
                                
                                # Execute the function calls
                                function_results = await self._handle_function_calls(first_response, user_email)
                                
                                # Add function results to chat history as tool responses
                                from semantic_kernel.contents.chat_message_content import ChatMessageContent
                                from semantic_kernel.contents.utils.author_role import AuthorRole
                                for func_result in function_results:
                                    # Create a tool/function response message
                                    tool_message = ChatMessageContent(
                                        role=AuthorRole.TOOL,
                                        content=func_result['result'],
                                        metadata={'name': func_result['name']}
                                    )
                                    chat_history.messages.append(tool_message)
                                
                                # Get final response from AI after function execution
                                final_response = await chat_service.get_chat_message_contents(
                                    chat_history=chat_history,
                                    settings=settings
                                )
                                
                                if final_response and len(final_response) > 0:
                                    reply = final_response[0].content if hasattr(final_response[0], 'content') else str(final_response[0])
                                    chat_history.add_assistant_message(reply)
                                    
                                    # Extract intent and slots from the conversation
                                    intent = self._extract_intent_from_message(message, reply)
                                    slots = self._extract_slots_from_context(message, function_results)
                                    
                                    return {
                                        'intent': intent,
                                        'slots': slots,
                                        'reply_text': reply,
                                        'message': reply,
                                        'function_results': function_results
                                    }
                            else:
                                # No function call, just a direct text response
                                reply = first_response.content if hasattr(first_response, 'content') else str(first_response)
                                
                                logger.info(f"Direct response (no function call): {reply[:100] if reply else 'empty'}")
                                
                                # Ensure reply is not empty
                                if not reply or reply.strip() == '':
                                    # Try to get any text from the response
                                    reply = "I understand. How can I help you today?"
                                
                                chat_history.add_assistant_message(reply)
                                
                                intent = self._extract_intent_from_message(message, reply)
                                slots = self._extract_slots_from_context(message, [])
                                
                                return {
                                    'intent': intent,
                                    'slots': slots,
                                    'reply_text': reply,
                                    'message': reply
                                }
                        
                        return {
                            'intent': 'general',
                            'slots': {},
                            'reply_text': "I'm here to help with room bookings. What would you like to do?",
                            'message': "I'm here to help with room bookings. What would you like to do?"
                        }
                            
                    except Exception as e:
                        logger.exception(f'Semantic Kernel chat failed: {e}')
                        return {
                            'intent': 'error',
                            'slots': {},
                            'reply_text': "I'm having trouble processing your request. Please try again.",
                            'message': "I'm having trouble processing your request. Please try again."
                        }

                def _get_plugin_tools(self) -> list:
                    """Convert Semantic Kernel plugins to OpenAI tools format for Groq."""
                    tools = []
                    
                    # Get RoomBooking plugin
                    if hasattr(self.kernel, 'plugins') and 'RoomBooking' in self.kernel.plugins:
                        plugin = self.kernel.plugins['RoomBooking']
                        
                        for func_name, func in plugin.functions.items():
                            # Extract function metadata
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
                            
                            # Extract parameters from function metadata
                            if hasattr(func, 'metadata') and hasattr(func.metadata, 'parameters'):
                                for param in func.metadata.parameters:
                                    param_name = param.name
                                    param_desc = param.description if hasattr(param, 'description') else ""
                                    param_required = param.is_required if hasattr(param, 'is_required') else False
                                    
                                    tool["function"]["parameters"]["properties"][param_name] = {
                                        "type": "string",
                                        "description": param_desc
                                    }
                                    
                                    if param_required:
                                        tool["function"]["parameters"]["required"].append(param_name)
                            
                            tools.append(tool)
                    
                    return tools
                
                async def _handle_function_calls(self, response, user_email: str) -> list:
                    """Execute function calls requested by the AI."""
                    function_results = []
                    
                    if not hasattr(response, 'items') or not response.items:
                        return function_results
                    
                    for item in response.items:
                        # Check if this is a FunctionCallContent
                        func_name = None
                        func_args = {}
                        
                        if hasattr(item, 'name'):  # Direct FunctionCallContent
                            func_name = item.name
                            func_args_str = item.arguments if hasattr(item, 'arguments') else '{}'
                            func_args = json.loads(func_args_str) if isinstance(func_args_str, str) else func_args_str
                        elif hasattr(item, 'function') and item.function:  # Nested function
                            func_name = item.function.name
                            func_args = json.loads(item.function.arguments) if isinstance(item.function.arguments, str) else item.function.arguments
                        
                        if not func_name:
                            continue
                        
                        # Add user_email to args if function needs it
                        if func_name in ['create_booking', 'list_user_bookings'] and 'user_email' not in func_args:
                            func_args['user_email'] = user_email
                        
                        try:
                            # Use the stored plugin instance directly
                            if hasattr(self, 'plugin_instance') and self.plugin_instance:
                                plugin_instance = self.plugin_instance
                                
                                # Call the actual plugin method directly
                                if hasattr(plugin_instance, func_name):
                                    method = getattr(plugin_instance, func_name)
                                    
                                    # Call method with arguments
                                    if asyncio.iscoroutinefunction(method):
                                        result = await method(**func_args)
                                    else:
                                        result = method(**func_args)
                                    
                                    function_results.append({
                                        'name': func_name,
                                        'arguments': func_args,
                                        'result': str(result)
                                    })
                                    
                                    logger.info(f"✓ Function {func_name} executed successfully")
                                else:
                                    logger.warning(f"Function {func_name} not found in plugin")
                                    function_results.append({
                                        'name': func_name,
                                        'arguments': func_args,
                                        'result': f"Error: Function {func_name} not found"
                                    })
                            else:
                                logger.error("Plugin instance not available")
                                function_results.append({
                                    'name': func_name,
                                    'arguments': func_args,
                                    'result': "Error: Plugin not initialized"
                                })
                        except Exception as e:
                            logger.exception(f"Error executing function {func_name}: {e}")
                            function_results.append({
                                'name': func_name,
                                'arguments': func_args,
                                'result': f"Error: {str(e)}"
                            })
                    
                    return function_results
                
                def _extract_intent_from_message(self, user_message: str, ai_reply: str) -> str:
                    """Extract intent from user message and AI reply."""
                    user_lower = user_message.lower()
                    
                    if any(word in user_lower for word in ['book', 'reserve', 'schedule']):
                        return 'book_room'
                    elif any(word in user_lower for word in ['find', 'search', 'available', 'show me']):
                        return 'find_rooms'
                    elif any(word in user_lower for word in ['my booking', 'my reservations', 'list']):
                        return 'list_bookings'
                    elif 'room' in user_lower and any(word in user_lower for word in ['info', 'detail', 'about']):
                        return 'room_info'
                    else:
                        return 'general'
                
                def _extract_slots_from_context(self, message: str, function_results: list) -> dict:
                    """Extract booking slots from message and function results."""
                    slots = {}
                    
                    # Extract from function arguments if available
                    for func_result in function_results:
                        if 'arguments' in func_result:
                            args = func_result['arguments']
                            if 'date' in args:
                                slots['date'] = args['date']
                            if 'start_time' in args:
                                slots['start_time'] = args['start_time']
                            if 'end_time' in args:
                                slots['end_time'] = args['end_time']
                            if 'capacity' in args:
                                slots['capacity'] = args['capacity']
                            if 'building' in args:
                                slots['building'] = args['building']
                            if 'purpose' in args:
                                slots['purpose'] = args['purpose']
                    
                    return slots
                
                def clear_chat_history(self, session_id: str) -> bool:
                    if session_id in self.histories:
                        del self.histories[session_id]
                        return True
                    return False

            _chat_agent = _ChatAgent(kernel, booking_automation, room_plugin)
            logger.info("✓ Chat agent initialized (Semantic Kernel + Groq + Room Plugin)")

        except Exception as e:
            logger.exception(f"Failed to initialize chat agent: {e}")
            logger.warning("Chatbot will operate in degraded mode")
            _chat_agent = None
