"""
Test script to verify the chatbot can access the database through function calling.
Run this after starting Django to test the updated chatbot functionality.
"""

import os
import sys
import django
import asyncio
import json

# Setup Django
sys.path.insert(0, os.path.dirname(__file__))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'room_booking_system.settings')
django.setup()

from chatbot.apps import get_chat_agent


async def test_chatbot_database_access():
    """Test that the chatbot can query the database for room availability."""
    
    print("\n" + "="*70)
    print("Testing AI Chatbot Database Access")
    print("="*70 + "\n")
    
    agent = get_chat_agent()
    
    if agent is None:
        print("❌ Error: Chat agent not initialized!")
        print("Make sure GROQ_API_KEY is configured in your settings.")
        return
    
    print("✓ Chat agent initialized successfully\n")
    
    # Test cases
    test_messages = [
        {
            "message": "Find available rooms for tomorrow from 2pm to 4pm for 10 people",
            "description": "Search for available rooms"
        },
        {
            "message": "Show me information about room 101",
            "description": "Get room information"
        },
        {
            "message": "What rooms are available today at 3pm for 5 people?",
            "description": "Check real-time availability"
        }
    ]
    
    session_id = "test_session"
    
    for i, test in enumerate(test_messages, 1):
        print(f"\n{'─'*70}")
        print(f"Test {i}: {test['description']}")
        print(f"{'─'*70}")
        print(f"User: {test['message']}")
        print()
        
        try:
            # Call the chatbot
            response = await agent.chat_async(
                test['message'],
                user_email="test@example.com",
                session_id=session_id
            )
            
            print(f"Intent: {response.get('intent', 'unknown')}")
            print(f"Slots: {json.dumps(response.get('slots', {}), indent=2)}")
            
            # Check if functions were called
            if 'function_results' in response:
                print(f"\n✓ Functions Called:")
                for func in response['function_results']:
                    print(f"  - {func['name']}: {func['result'][:100]}...")
            
            print(f"\nAI Response:")
            print(f"  {response.get('reply_text', 'No response')}")
            
        except Exception as e:
            print(f"❌ Error: {str(e)}")
            import traceback
            traceback.print_exc()
    
    print("\n" + "="*70)
    print("Test Complete!")
    print("="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(test_chatbot_database_access())
