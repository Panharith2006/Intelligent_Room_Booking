import logging
from typing import Annotated
from semantic_kernel.functions import kernel_function
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)


class RoomBookingPlugin:
    def __init__(self, room_model, booking_model, booking_automation):
        """Initialize plugin with Django models and automation."""
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
            criteria = {
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "capacity": int(capacity) if capacity else 1,
            }

            rooms = await sync_to_async(self.booking_automation.find_best_rooms)(
                criteria, limit=5
            )

            if not rooms:
                return "No available rooms found. Try different time or capacity."

            result = f"Found {len(rooms)} room(s):\n\n"

            for i, room_data in enumerate(rooms[:3], 1):
                room = room_data["room"]
                result += f"{i}. {room.name} ({room.room_number})\n"
                result += f"   Capacity: {room.capacity}\n"
                result += f"   Type: {room.get_room_type_display()}\n"
                result += f"   Use room_number: {room.room_number} when booking\n\n"

            return result

        except Exception as e:
            logger.exception(f"Error finding rooms: {e}")
            return "Error searching for rooms."

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

            features = await sync_to_async(
                self.booking_automation._get_room_features
            )(room)

            if features:
                info += f"Features: {', '.join(features)}\n"

            return info

        except Exception as e:
            logger.exception(f"Error getting room info: {e}")
            return "Error retrieving room info."

    # -----------------------------
    # 3. PREPARE BOOKING (SAFE STEP)
    # -----------------------------
    @kernel_function(
        name="prepare_booking",
        description="Prepare booking preview. DO NOT create booking yet."
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
            if not all([date, start_time, end_time]):
                return "Missing required booking information."

            criteria = {
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "capacity": int(capacity) if capacity else 1,
                "purpose": purpose,
            }

            rooms = await sync_to_async(self.booking_automation.find_best_rooms)(
                criteria, limit=1
            )

            if not rooms:
                return "No rooms available for this time."

            best_room = rooms[0]["room"]

            preview = (
                f"Booking Preview:\n\n"
                f"Room: {best_room.name} ({best_room.room_number})\n"
                f"Room_ID: {best_room.id}\n"
                f"Date: {date}\n"
                f"Time: {start_time} - {end_time}\n"
                f"Capacity: {capacity}\n"
                f"Purpose: {purpose}\n\n"
                f"Please type 'confirm' to complete booking."
            )

            return preview

        except Exception as e:
            logger.exception(f"Error preparing booking: {e}")
            return "Error preparing booking."

    # -----------------------------
    # 4. CREATE BOOKING (VALIDATED)
    # -----------------------------
    @kernel_function(
        name="create_booking",
        description="Execute booking ONLY after user confirmation."
    )
    async def create_booking(
        self,
        user_email: Annotated[str, "User email"],
        date: Annotated[str, "YYYY-MM-DD"],
        start_time: Annotated[str, "HH:MM"],
        end_time: Annotated[str, "HH:MM"],
        capacity: Annotated[str, "People"] = "1",
        purpose: Annotated[str, "Purpose"] = "meeting",
    ) -> str:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            if not all([user_email, date, start_time, end_time]):
                return "Missing required booking data."

            user = await sync_to_async(
                User.objects.filter(email=user_email).first
            )()

            if not user:
                return "User not found. Please login."

            criteria = {
                "date": date,
                "start_time": start_time,
                "end_time": end_time,
                "capacity": int(capacity) if capacity else 1,
                "purpose": purpose,
            }

            # ✅ RULES ENGINE VALIDATION (CRITICAL)
            validation = await sync_to_async(
                self.booking_automation.validate_booking
            )(criteria)

            if not validation.get("valid"):
                return validation.get("message", "Booking failed validation.")

            # ✅ EXECUTION
            result = await sync_to_async(
                self.booking_automation.auto_book
            )(user, criteria)

            if result.get("success"):
                return result.get("user_message", "Booking successful.")
            else:
                return result.get("error", "Booking failed.")

        except Exception as e:
            logger.exception(f"Error creating booking: {e}")
            return "Error creating booking."

    # -----------------------------
    # 5. LIST USER BOOKINGS
    # -----------------------------
    @kernel_function(
        name="list_user_bookings",
        description="List user's confirmed bookings"
    )
    async def list_user_bookings(
        self,
        user_email: Annotated[str, "User email"]
    ) -> str:
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()

            user = await sync_to_async(
                User.objects.filter(email=user_email).first
            )()

            if not user:
                return "User not found."

            bookings = await sync_to_async(lambda: list(
                self.Booking.objects.filter(
                    user=user,
                    status="confirmed"
                ).select_related("room").order_by("-start_time")[:5]
            ))()

            if not bookings:
                return "No bookings found."

            result = f"Your bookings ({len(bookings)}):\n\n"

            for i, b in enumerate(bookings, 1):
                result += f"{i}. {b.room.name} ({b.room.room_number})\n"
                result += f"   Date: {b.start_time.strftime('%Y-%m-%d')}\n"
                result += f"   Time: {b.start_time.strftime('%H:%M')} - {b.end_time.strftime('%H:%M')}\n\n"

            return result

        except Exception as e:
            logger.exception(f"Error listing bookings: {e}")
            return "Error retrieving bookings."
