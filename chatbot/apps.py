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
            # Initialize Semantic Kernel with Deepseek and room booking plugin
            logger.info("Initializing Semantic Kernel with Deepseek and Room Booking Plugin...")

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
                def __init__(self, kernel_instance, automation):
                    self.kernel = kernel_instance
                    self.automation = automation
                    self.histories = {}

                async def chat_async(self, message: str, user_email: str = "", session_id: str = "default") -> str:
                    """Chat using Semantic Kernel with plugin support."""
                    from semantic_kernel.contents.chat_history import ChatHistory
                    from semantic_kernel.connectors.ai.prompt_execution_settings import PromptExecutionSettings
                    
                    try:
                        # Get or create chat history for session
                        if session_id not in self.histories:
                            self.histories[session_id] = ChatHistory()
                        
                        chat_history = self.histories[session_id]
                        
                        # Add system message if this is a new conversation
                        if len(chat_history.messages) == 0:
                            system_prompt = (
                                "You are a helpful room booking assistant. You can help users:\n"
                                "- Find available rooms (use find_available_rooms function)\n"
                                "- Get room information (use get_room_info function)\n"
                                "- Prepare bookings for confirmation (use prepare_booking function)\n"
                                "- List user bookings (use list_user_bookings function)\n\n"
                                "Always provide clear, friendly responses. When creating bookings, "
                                "prepare them for user confirmation first."
                            )
                            chat_history.add_system_message(system_prompt)
                        
                        # Add user message
                        chat_history.add_user_message(message)
                        
                        # Get chat service
                        chat_service = self.kernel.get_service()
                        
                        # Create execution settings
                        settings = PromptExecutionSettings(
                            max_tokens=512,
                            temperature=0.3,
                            top_p=0.95
                        )
                        
                        # Get response from Deepseek via Semantic Kernel
                        response = await chat_service.get_chat_message_contents(
                            chat_history=chat_history,
                            settings=settings
                        )
                        
                        # Extract and return response text
                        if response and len(response) > 0:
                            reply = response[0].content if hasattr(response[0], 'content') else str(response[0])
                            
                            # Add assistant response to history
                            chat_history.add_assistant_message(reply)
                            
                            return reply
                        else:
                            return "I'm here to help with room bookings. What would you like to do?"
                            
                    except Exception as e:
                        logger.exception(f'Semantic Kernel chat failed: {e}')
                        return "I'm having trouble processing your request. Please try again or contact support."

                def clear_chat_history(self, session_id: str) -> bool:
                    if session_id in self.histories:
                        del self.histories[session_id]
                        return True
                    return False

            _chat_agent = _ChatAgent(kernel, booking_automation)
            logger.info("✓ Chat agent initialized (Semantic Kernel + Deepseek + Room Plugin)")

        except Exception as e:
            logger.exception(f"Failed to initialize chat agent: {e}")
            logger.warning("Chatbot will operate in degraded mode")
            _chat_agent = None
