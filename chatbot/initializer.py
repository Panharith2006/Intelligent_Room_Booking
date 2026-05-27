# chatbot/initializer.py

import logging
import os
import sys

logger = logging.getLogger(__name__)


def create_chat_agent():

    logger.info("Creating ChatAgent...")
    
    try:
        # --- Heavy imports moved here (important) ---
        from django.conf import settings
        from booking.models import Room, Booking, BookingRule

        from ai.kernel_config import create_kernel_groq
        from ai.booking_automation import BookingAutomation
        from ai.plugins.room_booking_plugin import RoomBookingPlugin

        # --- Init AI components ---
        logger.info("Initializing booking automation...")
        booking_automation = BookingAutomation(Room, Booking, BookingRule)

        # ✅ Using Groq API (Cloud-based, fast, free)
        groq_api_key = os.getenv("GROQ_API_KEY")
        
        if not groq_api_key:
            raise ValueError(
                "GROQ_API_KEY environment variable not set!\n"
                "Get your API token at: https://console.groq.com/keys\n"
                "Set it in your .env file: GROQ_API_KEY=gsk_your_token_here"
            )
        
        logger.info(f"✅ Groq API Key found (first 20 chars): {groq_api_key[:20]}...")
        
        logger.info("Initializing Groq API...")
        try:
            groq_model = os.getenv("GROQ_MODEL") or getattr(settings, "GROQ_MODEL", "llama-3.1-8b-instant")
            logger.info(f"   Model: {groq_model}")
            
            logger.info("Creating Groq kernel...")
            kernel, llm_service = create_kernel_groq(model=groq_model, api_key=groq_api_key)
            logger.info("✅ Groq API kernel created successfully")
        except Exception as e:
            logger.error(f"❌ Failed to create Groq kernel: {e}")
            print(f"❌ Groq Error: {e}", file=sys.stderr)
            raise

        logger.info("Adding room booking plugin...")
        room_plugin = RoomBookingPlugin(Room, Booking, booking_automation)
        kernel.add_plugin(room_plugin, plugin_name="RoomBooking")
        logger.info("✅ Room plugin added")

        # --- Import your ChatAgent class safely ---
        logger.info("Importing ChatAgent...")
        from chatbot.agent import ChatAgent

        logger.info("Creating ChatAgent instance...")
        agent = ChatAgent(kernel, booking_automation, room_plugin, llm_client=llm_service)
        
        logger.info("✅ ChatAgent created successfully")
        print("✅ Chatbot Ready: Using Groq AI for intelligent responses!")
        return agent
        
    except Exception as e:
        logger.error(f"❌ ChatAgent creation failed: {e}")
        print(f"\n{'='*70}", file=sys.stderr)
        print(f"❌ CRITICAL: ChatAgent Initialization Failed", file=sys.stderr)
        print(f"{'='*70}", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        print(f"\nTroubleshooting steps:", file=sys.stderr)
        print(f"1. Check .env file exists in project root", file=sys.stderr)
        print(f"2. Verify GROQ_API_KEY is set (get from https://console.groq.com/keys)", file=sys.stderr)
        print(f"3. Verify API key is valid (starts with 'gsk_')", file=sys.stderr)
        print(f"4. Check internet connection", file=sys.stderr)
        print(f"5. Check Groq API status: https://status.groq.com/", file=sys.stderr)
        print(f"{'='*70}\n", file=sys.stderr)
        raise
