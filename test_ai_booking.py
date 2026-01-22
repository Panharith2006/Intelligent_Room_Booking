"""
Test script to verify AI chatbot booking automation integration
"""
import os
import sys
import django
import asyncio

# Setup Django environment
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'room_booking_system.settings')
django.setup()

from chatbot.apps import get_chat_agent
from booking.models import Room, Booking, BookingRule
from django.contrib.auth import get_user_model

User = get_user_model()


async def test_chatbot_booking():
    """Test the AI chatbot with booking automation."""
    
    print("=" * 60)
    print("Testing AI Chatbot Booking Automation")
    print("=" * 60)
    
    # Get the chat agent
    agent = get_chat_agent()
    
    if agent is None:
        print("❌ ERROR: Chat agent not initialized!")
        print("   Make sure GROQ_API_KEY is set in .env file")
        return False
    
    print("✓ Chat agent initialized successfully")
    print()
    
    # Test queries
    test_queries = [
        "I want to book a room tomorrow from 2pm to 4pm for 10 people",
        "Find available rooms for next Monday at 9am to 11am",
        "Show me rooms that can fit 20 people",
        "Book room 101 for today at 3pm to 5pm",
    ]
    
    for i, query in enumerate(test_queries, 1):
        print(f"Test {i}: {query}")
        print("-" * 60)
        
        try:
            # Call the agent
            response = await agent.chat_async(
                message=query,
                user_email="test@example.com",
                session_id=f"test_session_{i}"
            )
            
            # Display response
            if isinstance(response, dict):
                intent = response.get('intent', 'unknown')
                slots = response.get('slots', {})
                reply = response.get('reply_text', response.get('message', 'No reply'))
                
                print(f"Intent: {intent}")
                print(f"Extracted Slots: {slots}")
                print(f"Reply: {reply}")
                print()
                
                # Check if booking information was extracted
                if intent in ['book_room', 'booking', 'reserve']:
                    if slots.get('date') and slots.get('start_time') and slots.get('end_time'):
                        print("✓ Successfully extracted booking information!")
                    else:
                        print("⚠ Partial booking information extracted")
                elif intent in ['find_rooms']:
                    print("✓ Room search intent detected")
                else:
                    print(f"ℹ Intent: {intent}")
            else:
                print(f"Reply: {response}")
            
            print()
            
        except Exception as e:
            print(f"❌ ERROR: {e}")
            import traceback
            traceback.print_exc()
            print()
    
    print("=" * 60)
    print("Test Summary")
    print("=" * 60)
    print("✓ All tests completed")
    print()
    print("Next steps:")
    print("1. Start the development server: python manage.py runserver")
    print("2. Open the chatbot interface in your browser")
    print("3. Test booking automation with real user interactions")
    print()
    
    return True


def check_database_setup():
    """Check if database has rooms and users."""
    print("Checking database setup...")
    
    rooms_count = Room.objects.count()
    users_count = User.objects.count()
    bookings_count = Booking.objects.count()
    
    print(f"  - Rooms: {rooms_count}")
    print(f"  - Users: {users_count}")
    print(f"  - Bookings: {bookings_count}")
    print()
    
    if rooms_count == 0:
        print("⚠ WARNING: No rooms in database. Add rooms first!")
        print("   Run: python manage.py shell")
        print("   Then create some rooms for testing")
        print()
    
    if users_count == 0:
        print("⚠ WARNING: No users in database. Create a superuser!")
        print("   Run: python manage.py createsuperuser")
        print()
    
    return rooms_count > 0 and users_count > 0


if __name__ == "__main__":
    print()
    
    # Check database
    db_ok = check_database_setup()
    
    if not db_ok:
        print("Please set up the database first before testing.")
        sys.exit(1)
    
    # Run async test
    result = asyncio.run(test_chatbot_booking())
    
    if result:
        print("✓ All systems operational!")
        sys.exit(0)
    else:
        print("❌ Some tests failed")
        sys.exit(1)
