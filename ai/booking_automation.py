import logging
from typing import Dict, List, Tuple
from datetime import datetime, timedelta, time as dt_time
from django.utils import timezone

logger = logging.getLogger(__name__)


class BookingAutomation:
    """
    Booking engine for AI chatbot (room recommendation + auto booking)
    """

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
    def find_best_rooms(self, criteria: dict, limit: int = 5) -> List[Dict]:

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

        for room in rooms[:20]:
            score, availability = self._score_room(room, criteria)

            if availability["is_available"]:
                available_rooms.append({
                    "room": room,
                    "score": score,
                    "capacity": room.capacity,
                    "name": room.name,
                    "room_number": room.room_number,
                    "building": getattr(room, "building_name", None) or getattr(room, "building", None),
                    "availability": availability,
                    "features": self._get_room_features(room)
                })

        available_rooms.sort(key=lambda x: x["score"], reverse=True)
        return available_rooms[:limit]

    # =========================================================
    # ROOM SCORING
    # =========================================================
    def _score_room(self, room, criteria: dict) -> Tuple[float, Dict]:

        score = 0.0
        availability = {"is_available": True, "conflicts": []}

        date = criteria.get("date")
        start_time = criteria.get("start_time")
        end_time = criteria.get("end_time")

        capacity = criteria.get("capacity", 1)
        if isinstance(capacity, str):
            try:
                capacity = int(capacity)
            except:
                capacity = 1

        # conflict check
        if date and start_time and end_time:
            conflicts = self._check_conflicts(room, date, start_time, end_time)

            if conflicts:
                availability["is_available"] = False
                availability["conflicts"] = conflicts
                return 0.0, availability

            score += 50

        # capacity score
        if room.capacity >= capacity:
            excess = room.capacity - capacity

            if excess == 0:
                score += 30
            elif excess <= 5:
                score += 25
            elif excess <= 10:
                score += 20
            else:
                score += max(0, 15 - min(excess * 0.5, 10))
        else:
            availability["is_available"] = False
            return 0.0, availability

        # building match
        if criteria.get("building"):
            room_building = getattr(room, "building_name", None) or getattr(room, "building", None)

            if room_building and room_building.upper() == criteria["building"].upper():
                score += 20

        # purpose match
        if criteria.get("purpose"):
            type_mapping = {
                "meeting": "meeting",
                "lecture": "lecture",
                "conference": "conference",
                "workshop": "workshop",
                "lab": "lab",
            }

            preferred = type_mapping.get(criteria["purpose"])

            if preferred and room.room_type == preferred:
                score += 15

        # features
        if getattr(room, "has_projector", False):
            score += 5
        if getattr(room, "has_whiteboard", False):
            score += 3
        if getattr(room, "has_computer", False):
            score += 4

        return score, availability

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
    # FEATURES
    # =========================================================
    def _get_room_features(self, room) -> List[str]:

        features = []

        mapping = [
            ("has_projector", "Projector"),
            ("has_whiteboard", "Whiteboard"),
            ("has_computer", "Computer"),
            ("has_audio", "Audio System"),
            ("has_video", "Video Conferencing"),
            ("has_ac", "Air Conditioning"),
        ]

        for attr, label in mapping:
            if getattr(room, attr, False):
                features.append(label)

        return features

    # =========================================================
    # AUTO BOOKING
    # =========================================================
    def auto_book(self, user, criteria: dict) -> Dict:

        # IMPORTANT FIX: validation first
        validation = self.validate_booking(criteria)
        if not validation["valid"]:
            return {
                "success": False,
                "error": validation["message"]
            }

        best_rooms = self.find_best_rooms(criteria, limit=1)

        if not best_rooms:
            return {
                "success": False,
                "error": "No available rooms",
            }

        best = best_rooms[0]
        room = best["room"]

        try:
            date_obj = datetime.strptime(criteria["date"], "%Y-%m-%d").date()

            start_time = datetime.strptime(criteria["start_time"], "%H:%M")
            end_time = datetime.strptime(criteria["end_time"], "%H:%M")

            start_dt = timezone.make_aware(datetime.combine(date_obj, start_time.time()))
            end_dt = timezone.make_aware(datetime.combine(date_obj, end_time.time()))

            if end_dt <= start_dt:
                end_dt += timedelta(days=1)

        except Exception as e:
            return {
                "success": False,
                "error": "Invalid date/time format"
            }

        # conflict check
        conflicts = self._check_conflicts(
            room,
            criteria["date"],
            criteria["start_time"],
            criteria["end_time"]
        )

        if conflicts:
            return {
                "success": False,
                "error": "Room not available",
                "conflicts": conflicts
            }

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
            "room": best,
            "message": f"Booking confirmed: {room.name} ({room.room_number})"
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