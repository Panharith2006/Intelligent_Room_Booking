"""
Semantic Kernel plugin for room booking operations.
Provides native functions that can be called by the AI agent.
"""
import logging
from typing import Annotated
from datetime import datetime
from semantic_kernel.functions import kernel_function

logger = logging.getLogger(__name__)


class RoomBookingPlugin:
    """Plugin providing room booking functions to Semantic Kernel."""
    
    def __init__(self, room_model, booking_model, booking_automation):
        """Initialize plugin with Django models and automation."""
        self.Room = room_model
        self.Booking = booking_model
        self.booking_automation = booking_automation
    
    @kernel_function(
        name="find_available_rooms",
        description="Find available rooms matching the given criteria (date, time, capacity, building)"
    )
    def find_available_rooms(
        self,
        date: Annotated[str, "Date in YYYY-MM-DD format"],
        start_time: Annotated[str, "Start time in HH:MM format"],
        end_time: Annotated[str, "End time in HH:MM format"],
        capacity: Annotated[str, "Minimum capacity (number of people)"] = "1",
        building: Annotated[str, "Building name (optional)"] = "",
    ) -> str:
        """Find available rooms and return formatted results."""
        try:
            criteria = {
                'date': date,
                'start_time': start_time,
                'end_time': end_time,
                'capacity': int(capacity) if capacity else 1,
                'building': building if building else None
            }
            
            rooms = self.booking_automation.find_best_rooms(criteria, limit=5)
            
            if not rooms:
                return "No available rooms found matching your criteria. Try adjusting the date, time, or capacity."
            
            result = f"Found {len(rooms)} available room(s):\n\n"
            for i, room_data in enumerate(rooms[:3], 1):
                room = room_data['room']
                result += f"{i}. {room.name} ({room.room_number})\n"
                result += f"   Capacity: {room.capacity} people\n"
                if room.building_name:
                    result += f"   Building: {room.building_name}\n"
                result += "\n"
            
            return result
            
        except Exception as e:
            logger.exception(f"Error finding rooms: {e}")
            return f"Error searching for rooms: {str(e)}"
    
    @kernel_function(
        name="get_room_info",
        description="Get detailed information about a specific room by room number"
    )
    def get_room_info(
        self,
        room_number: Annotated[str, "Room number to look up"]
    ) -> str:
        """Get information about a specific room."""
        try:
            room = self.Room.objects.filter(room_number__iexact=room_number).first()
            
            if not room:
                return f"Room {room_number} not found. Please check the room number."
            
            info = f"**{room.name} ({room.room_number})**\n\n"
            info += f"Capacity: {room.capacity} people\n"
            
            if room.building_name:
                info += f"Building: {room.building_name}\n"
            
            if hasattr(room, 'room_type') and room.room_type:
                info += f"Type: {room.room_type.title()}\n"
            
            info += f"Status: {'Available' if room.is_available else 'Unavailable'}\n"
            
            # Add features
            features = self.booking_automation._get_room_features(room)
            if features:
                info += f"\nFeatures: {', '.join(features)}\n"
            
            return info
            
        except Exception as e:
            logger.exception(f"Error getting room info: {e}")
            return f"Error retrieving room information: {str(e)}"
    
    @kernel_function(
        name="prepare_booking",
        description="Prepare a booking preview for confirmation. Returns booking details that need user confirmation."
    )
    def prepare_booking(
        self,
        date: Annotated[str, "Date in YYYY-MM-DD format"],
        start_time: Annotated[str, "Start time in HH:MM format"],
        end_time: Annotated[str, "End time in HH:MM format"],
        capacity: Annotated[str, "Number of people"] = "1",
        purpose: Annotated[str, "Purpose of booking"] = "meeting",
    ) -> str:
        """Prepare booking details for user confirmation."""
        try:
            criteria = {
                'date': date,
                'start_time': start_time,
                'end_time': end_time,
                'capacity': int(capacity) if capacity else 1,
                'purpose': purpose
            }
            
            rooms = self.booking_automation.find_best_rooms(criteria, limit=1)
            
            if not rooms:
                return "No available rooms found for your requested time. Please try a different time or reduce capacity requirements."
            
            best_room = rooms[0]['room']
            
            preview = (
                f"Booking Preview:\n\n"
                f"Room: {best_room.name} ({best_room.room_number})\n"
                f"Date: {date}\n"
                f"Time: {start_time} - {end_time}\n"
                f"Capacity: {capacity} people\n"
                f"Purpose: {purpose}\n\n"
                f"To confirm this booking, please click the 'Confirm Booking' button."
            )
            
            return preview
            
        except Exception as e:
            logger.exception(f"Error preparing booking: {e}")
            return f"Error preparing booking: {str(e)}"
    
    @kernel_function(
        name="list_user_bookings",
        description="List all bookings for the current user"
    )
    def list_user_bookings(
        self,
        user_email: Annotated[str, "User's email address"]
    ) -> str:
        """List user's bookings."""
        try:
            from django.contrib.auth import get_user_model
            User = get_user_model()
            
            user = User.objects.filter(email=user_email).first()
            if not user:
                return "User not found. Please sign in to view your bookings."
            
            bookings = self.Booking.objects.filter(
                user=user,
                status='confirmed'
            ).order_by('-start_time')[:5]
            
            if not bookings:
                return "You have no confirmed bookings."
            
            result = f"Your bookings ({bookings.count()}):\n\n"
            for i, booking in enumerate(bookings, 1):
                result += f"{i}. {booking.room.name} ({booking.room.room_number})\n"
                result += f"   Date: {booking.start_time.strftime('%Y-%m-%d')}\n"
                result += f"   Time: {booking.start_time.strftime('%H:%M')} - {booking.end_time.strftime('%H:%M')}\n"
                result += "\n"
            
            return result
            
        except Exception as e:
            logger.exception(f"Error listing bookings: {e}")
            return f"Error retrieving bookings: {str(e)}"
