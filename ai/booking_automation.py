import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta, time as dt_time
from django.utils import timezone

logger = logging.getLogger(__name__)


class BookingAutomation:
    def __init__(self, room_model, booking_model, booking_rule_model=None):
        self.Room = room_model
        self.Booking = booking_model
        self.BookingRule = booking_rule_model

    # =========================================================
    # VALIDATION
    # =========================================================
    def validate_booking(self, criteria: dict) -> Dict:
        try:
            required = ["date", "start_time", "end_time"]
            missing = [f for f in required if not criteria.get(f)]

            if missing:
                return {
                    "valid": False,
                    "message": f"Missing fields: {', '.join(missing)}"
                }

            datetime.strptime(criteria["date"], "%Y-%m-%d")
            datetime.strptime(criteria["start_time"], "%H:%M")
            datetime.strptime(criteria["end_time"], "%H:%M")

            return {"valid": True}

        except Exception as e:
            return {"valid": False, "message": f"Invalid input: {str(e)}"}

    # =========================================================
    # FIND ROOMS
    # =========================================================
    def find_best_rooms(self, criteria: dict, limit: int = None, return_all: bool = False) -> List[Dict]:
        
        rooms = self.Room.objects.filter(is_available=True)

        capacity = criteria.get("capacity", 1)
        if isinstance(capacity, str):
            try:
                capacity = int(capacity)
            except:
                capacity = 1

        room_number = criteria.get("room_number")

        if room_number:
            rooms = rooms.filter(room_number__iexact=room_number)

        if capacity:
            rooms = rooms.filter(capacity__gte=capacity)

        available_rooms = []

        for room in rooms:
            # Simple check: is room available at this time (no conflicts)?
            is_available = True
            conflicts = []
            
            date = criteria.get("date")
            start_time = criteria.get("start_time")
            end_time = criteria.get("end_time")

            if date and start_time and end_time:
                conflicts = self._check_conflicts(room, date, start_time, end_time)
                if conflicts:
                    is_available = False

            if is_available:
                available_rooms.append({
                    "room": room,
                    "capacity": room.capacity,
                    "name": room.name,
                    "room_number": room.room_number,
                    "room_type": room.room_type,
                    "availability": {"is_available": True, "conflicts": []},
                    "equipment": self._get_room_equipment(room)
                })

        # Sort by capacity (smallest suitable room first) - simpler than scoring
        available_rooms.sort(key=lambda x: x["capacity"])

        # Return all or limited
        if return_all:
            return available_rooms
        elif limit:
            return available_rooms[:limit]
        else:
            return available_rooms

    # =========================================================
    # CONFLICT CHECK
    # =========================================================
    def _check_conflicts(self, room, date: str, start_time: str, end_time: str) -> List[Dict]:

        try:
            date_obj = datetime.strptime(date, "%Y-%m-%d").date()
        except:
            return []

        bookings = self.Booking.objects.filter(
            room=room,
            start_time__date=date_obj,
            status__in=["confirmed"]
        )

        conflicts = []

        for booking in bookings:
            if self._times_overlap(
                start_time,
                end_time,
                booking.start_time.strftime("%H:%M"),
                booking.end_time.strftime("%H:%M")
            ):
                conflicts.append({
                    "booking_id": booking.id,
                    "start": booking.start_time.strftime("%H:%M"),
                    "end": booking.end_time.strftime("%H:%M"),
                    "user": str(booking.user),
                })

        return conflicts

    # =========================================================
    # TIME OVERLAP
    # =========================================================
    def _times_overlap(self, start1, end1, start2, end2) -> bool:
        try:
            s1 = datetime.strptime(start1, "%H:%M")
            e1 = datetime.strptime(end1, "%H:%M")
            s2 = datetime.strptime(start2, "%H:%M")
            e2 = datetime.strptime(end2, "%H:%M")

            return s1 < e2 and e1 > s2

        except:
            return False

    # =========================================================
    # EQUIPMENT PARSING
    # =========================================================
    def _parse_equipment(self, equipment_text: str) -> List[str]:
        if not equipment_text:
            return []
        
        # Split by comma or common separators
        items = [item.strip() for item in equipment_text.replace(',', ' ').split()]
        return [item for item in items if item]

    def _get_room_equipment(self, room) -> List[str]:
        return self._parse_equipment(room.equipment)

    # =========================================================
    # AUTO BOOKING
    # =========================================================
    def auto_book(self, user, criteria: dict) -> Dict:

        # STEP 1: VALIDATE BOOKING CRITERIA
        validation = self.validate_booking(criteria)
        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["message"],
                "user_message": f" Booking validation failed: {validation['message']}"
            }

        # STEP 2: FIND BEST ROOMS
        best_rooms = self.find_best_rooms(criteria, limit=1)

        if not best_rooms:
            return {
                "success": False,
                "error": "No available rooms",
                "user_message": "❌ No available rooms found for your criteria. Try a different time or capacity."
            }

        best = best_rooms[0]
        room = best["room"]

        # STEP 3: VALIDATE USER
        if not user or not hasattr(user, 'id'):
            return {
                "success": False,
                "error": "Invalid user",
                "user_message": "❌ User authentication failed. Please log in."
            }

        # STEP 4: PARSE DATE/TIME
        try:
            date_obj = datetime.strptime(criteria["date"], "%Y-%m-%d").date()
            start_time = datetime.strptime(criteria["start_time"], "%H:%M")
            end_time = datetime.strptime(criteria["end_time"], "%H:%M")

            start_dt = timezone.make_aware(datetime.combine(date_obj, start_time.time()))
            end_dt = timezone.make_aware(datetime.combine(date_obj, end_time.time()))

            # Handle same-day bookings that cross midnight
            if end_dt <= start_dt:
                end_dt += timedelta(days=1)

        except Exception as e:
            logger.error(f"Date/time parsing failed: {e}")
            return {
                "success": False,
                "error": "Invalid date/time format",
                "user_message": f"❌ Invalid date or time format: {str(e)}"
            }

        # STEP 5: FINAL CONFLICT CHECK (before creation)
        conflicts = self._check_conflicts(
            room,
            criteria["date"],
            criteria["start_time"],
            criteria["end_time"]
        )

        if conflicts:
            return {
                "success": False,
                "error": "Room not available - conflicts detected",
                "conflicts": conflicts,
                "user_message": f"❌ Room {room.name} is not available at that time due to existing bookings."
            }

        # STEP 6: CREATE BOOKING
        try:
            booking = self.Booking.objects.create(
                user=user,
                room=room,
                start_time=start_dt,
                end_time=end_dt,
                purpose=criteria.get("purpose", "meeting"),
                attendees=criteria.get("capacity", 1),
                additional_notes=criteria.get("raw_message", "")
            )

            return {
                "success": True,
                "booking": booking,
                "booking_id": booking.id,
                "room": best,
                "room_name": room.name,
                "room_number": room.room_number,
                "date": criteria["date"],
                "time": f"{criteria['start_time']} - {criteria['end_time']}",
                "user_message": f"✅ Booking confirmed: {room.name} ({room.room_number}) on {criteria['date']} from {criteria['start_time']} to {criteria['end_time']}"
            }
        except Exception as e:
            logger.exception(f"Booking creation failed: {e}")
            return {
                "success": False,
                "error": f"Booking creation failed: {str(e)}",
                "user_message": "❌ Failed to create booking. Please try again."
            }

    # =========================================================
    # SUGGESTIONS
    # =========================================================
    def _generate_suggestions(self, criteria: dict) -> List[str]:

        suggestions = []

        if criteria.get("capacity"):
            suggestions.append(f"Try rooms with capacity {criteria['capacity'] + 10}+")

        if criteria.get("date"):
            suggestions.append("Try different time slots")

        if criteria.get("building"):
            suggestions.append(f"Check other buildings besides {criteria['building']}")

        suggestions.append("Browse all available rooms")

        return suggestions