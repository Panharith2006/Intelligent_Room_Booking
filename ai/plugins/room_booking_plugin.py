import logging
from typing import Annotated
from semantic_kernel.functions import kernel_function
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class RoomBookingPlugin:
    def __init__(self, room_model, booking_model, booking_automation):
        self.Room = room_model
        self.Booking = booking_model
        self.booking_automation = booking_automation

    # -----------------------------
    # 1. FIND AVAILABLE ROOMS
    # -----------------------------
    @kernel_function(
        name="find_available_rooms",
        description="Search available rooms. Always call this BEFORE booking."
    )
    async def find_available_rooms(
        self,
        date: Annotated[str, "YYYY-MM-DD"],
        start_time: Annotated[str, "HH:MM"],
        end_time: Annotated[str, "HH:MM"],
        capacity: Annotated[str, "Minimum capacity"] = "1",
    ) -> str:
        try:
            # Validate input
            if not all([date, start_time, end_time]):
                return "❌ Missing required parameters: date, start_time, end_time (format: YYYY-MM-DD, HH:MM)"
            
            criteria = {
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "capacity": int(capacity) if capacity else 1,
            }

            # Validate date/time format
            from datetime import datetime
            try:
                datetime.strptime(date, "%Y-%m-%d")
                datetime.strptime(start_time, "%H:%M")
                datetime.strptime(end_time, "%H:%M")
            except ValueError as ve:
                return f"❌ Invalid date/time format: {str(ve)}"

            rooms = await sync_to_async(self.booking_automation.find_best_rooms)(
                criteria, limit=5
            )

            if not rooms:
                return "❌ No available rooms found. Try different time or capacity."

            result = f"📌 Found {len(rooms)} available room(s):\n\n"

            for i, room_data in enumerate(rooms[:3], 1):
                room = room_data["room"]
                score = room_data.get("score", 0)
                result += f"{i}. **{room.name}** ({room.room_number})\n"
                result += f"   Capacity: {room.capacity} | Score: {score:.0f}\n"
                result += f"   Type: {room.get_room_type_display() if hasattr(room, 'get_room_type_display') else room.room_type}\n"
                result += f"   Equipment: {', '.join(room_data.get('equipment', ['None']))}\n\n"

            return result

        except Exception as e:
            logger.exception(f"Error finding rooms: {e}")
            return f"❌ Error searching for rooms: {str(e)}"

    # -----------------------------
    # 2. ROOM INFO
    # -----------------------------
    @kernel_function(
        name="get_room_info",
        description="Get detailed info of a room by room_number"
    )
    async def get_room_info(
        self,
        room_number: Annotated[str, "Room number"]
    ) -> str:
        try:
            room = await sync_to_async(
                self.Room.objects.filter(room_number__iexact=room_number).first
            )()

            if not room:
                return f"Room {room_number} not found."

            info = f"{room.name} ({room.room_number})\n"
            info += f"Capacity: {room.capacity}\n"
            info += f"Status: {'Available' if room.is_available else 'Unavailable'}\n"

            if hasattr(room, "room_type") and room.room_type:
                info += f"Type: {room.get_room_type_display()}\n"

            equipment = await sync_to_async(
                self.booking_automation._get_room_equipment
            )(room)

            if equipment:
                info += f"Equipment: {', '.join(equipment)}\n"

            return info

        except Exception as e:
            logger.exception(f"Error getting room info: {e}")
            return "Error retrieving room info."

    # -----------------------------
    # 3. PREPARE BOOKING (SAFE STEP)
    # -----------------------------
    @kernel_function(
        name="prepare_booking",
        description="Prepare booking preview. DO NOT create booking yet - return preview only."
    )
    async def prepare_booking(
        self,
        date: Annotated[str, "YYYY-MM-DD"],
        start_time: Annotated[str, "HH:MM"],
        end_time: Annotated[str, "HH:MM"],
        capacity: Annotated[str, "People"] = "1",
        purpose: Annotated[str, "Purpose"] = "meeting",
    ) -> str:
        try:
            # Validate all required fields
            if not all([date, start_time, end_time]):
                return "❌ Missing required booking information: date, start_time, end_time"

            from datetime import datetime
            try:
                datetime.strptime(date, "%Y-%m-%d")
                datetime.strptime(start_time, "%H:%M")
                datetime.strptime(end_time, "%H:%M")
            except ValueError as ve:
                return f"❌ Invalid date/time format: {str(ve)}"

            criteria = {
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "capacity": int(capacity) if capacity else 1,
                "purpose": purpose,
            }

            # Find best available room without booking
            rooms = await sync_to_async(self.booking_automation.find_best_rooms)(
                criteria, limit=1
            )

            if not rooms:
                return f"❌ No rooms available for {date} {start_time}-{end_time}. Try different time."

            best_room = rooms[0]["room"]
            equipment = rooms[0].get("equipment", [])
            capacity_match = best_room.capacity >= int(capacity)

            preview = (
                f"✅ **BOOKING PREVIEW** (Review before confirming)\n\n"
                f"**Room Details:**\n"
                f"  • Name: {best_room.name}\n"
                f"  • Number: {best_room.room_number}\n"
                f"  • Capacity: {best_room.capacity} people\n"
                f"  • Type: {best_room.get_room_type_display() if hasattr(best_room, 'get_room_type_display') else best_room.room_type}\n\n"
                f"**Booking Details:**\n"
                f"  • Date: {date}\n"
                f"  • Time: {start_time} - {end_time}\n"
                f"  • Attendees: {capacity}\n"
                f"  • Purpose: {purpose}\n\n"
                f"**Equipment:** {', '.join(equipment) if equipment else 'None specified'}\n\n"
                f"👉 **Click 'Confirm Booking' to proceed**"
            )

            return preview

        except Exception as e:
            logger.exception(f"Error preparing booking: {e}")
            return f"❌ Error preparing booking: {str(e)}"

    # -----------------------------
    # 4. CREATE BOOKING (VALIDATED)
    # -----------------------------
    @kernel_function(
        name="create_booking",
        description="Execute booking ONLY after user confirmation. Requires all validated details."
    )
    async def create_booking(
        self,
        user_id: Annotated[str, "Authenticated user ID"],
        date: Annotated[str, "YYYY-MM-DD"],
        start_time: Annotated[str, "HH:MM"],
        end_time: Annotated[str, "HH:MM"],
        capacity: Annotated[str, "People"] = "1",
        purpose: Annotated[str, "Purpose"] = "meeting",
    ) -> str:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            # Validate all required parameters
            if not all([user_id, date, start_time, end_time]):
                return "❌ Missing required booking data: user_id, date, start_time, end_time"

            # Validate date/time format
            from datetime import datetime
            try:
                datetime.strptime(date, "%Y-%m-%d")
                datetime.strptime(start_time, "%H:%M")
                datetime.strptime(end_time, "%H:%M")
            except ValueError as ve:
                return f"❌ Invalid date/time format: {str(ve)}"

            # Get user
            try:
                user = await sync_to_async(User.objects.filter(id=int(user_id)).first)()
            except (ValueError, TypeError):
                return "❌ Invalid user ID format."

            if not user:
                return "❌ User not found. Please log in again."

            # Build criteria
            criteria = {
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "capacity": int(capacity) if capacity else 1,
                "purpose": purpose,
            }

            # STEP 1: VALIDATE CRITERIA
            validation = await sync_to_async(
                self.booking_automation.validate_booking
            )(criteria)

            if not validation.get("valid"):
                msg = validation.get("message", "Booking failed validation.")
                return f"❌ Validation Error: {msg}"

            # STEP 2: ATTEMPT BOOKING
            result = await sync_to_async(
                self.booking_automation.auto_book
            )(user, criteria)

            # Return appropriate response based on result
            if result.get("success"):
                return (
                    f"✅ **BOOKING CONFIRMED**\n\n"
                    f"Room: {result.get('room_name', 'Unknown')} ({result.get('room_number', 'N/A')})\n"
                    f"Date: {result.get('date', date)}\n"
                    f"Time: {result.get('time', f'{start_time}-{end_time}')}\n"
                    f"Booking ID: {result.get('booking_id', 'N/A')}\n\n"
                    f"{result.get('user_message', 'Booking successful!')}"
                )
            else:
                error_msg = result.get("user_message", result.get("error", "Booking failed."))
                return f"❌ {error_msg}"

        except Exception as e:
            logger.exception(f"Error creating booking: {e}")
            return f"❌ Unexpected error during booking: {str(e)}"

    # -----------------------------
    # 5. LIST USER BOOKINGS
    # -----------------------------
    @kernel_function(
        name="list_user_bookings",
        description="List user's confirmed bookings"
    )
    async def list_user_bookings(
        self,
        user_id: Annotated[str, "Authenticated user ID"]
    ) -> str:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            if not user_id:
                return "❌ Authentication required. Please provide user ID."

            try:
                user = await sync_to_async(User.objects.filter(id=int(user_id)).first)()
            except (ValueError, TypeError):
                return "❌ Invalid user ID format."

            if not user:
                return "❌ User not found."

            bookings = await sync_to_async(lambda: list(
                self.Booking.objects.filter(
                    user=user,
                    status="confirmed"
                ).select_related("room").order_by("-start_time")[:5]
            ))()

            if not bookings:
                return "📭 You have no confirmed bookings."

            result = f"📋 **Your Bookings** ({len(bookings)} confirmed):\n\n"

            for i, b in enumerate(bookings, 1):
                start_str = b.start_time.strftime("%Y-%m-%d %H:%M")
                end_str = b.end_time.strftime("%H:%M")
                result += (
                    f"{i}. {b.room.name} ({b.room.room_number})\n"
                    f"   Date: {start_str} - {end_str}\n"
                    f"   Purpose: {b.purpose}\n"
                    f"   Attendees: {b.attendees}\n\n"
                )

            return result

        except Exception as e:
            logger.exception(f"Error listing bookings: {e}")
            return f"❌ Error retrieving bookings: {str(e)}"
