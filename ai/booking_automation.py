import logging
from typing import Annotated, Dict, List, Tuple
from datetime import datetime, timedelta, time as dt_time
from semantic_kernel.functions import kernel_function
from asgiref.sync import sync_to_async
from django.utils import timezone

logger = logging.getLogger(__name__)

# =========================
# Booking Automation Class
# =========================
class BookingAutomation:
    def __init__(self, room_model, booking_model, booking_rule_model=None):
        self.Room = room_model
        self.Booking = booking_model
        self.BookingRule = booking_rule_model

    # -------------------------
    # Validate required fields
    # -------------------------
    def validate_booking(self, criteria: dict) -> Dict:
        try:
            required = ['date', 'start_time', 'end_time']
            missing = [f for f in required if not criteria.get(f)]
            if missing:
                return {"valid": False, "message": f"Missing fields: {', '.join(missing)}"}

            datetime.strptime(criteria['date'], '%Y-%m-%d')
            datetime.strptime(criteria['start_time'], '%H:%M')
            datetime.strptime(criteria['end_time'], '%H:%M')

            return {"valid": True}
        except Exception as e:
            return {"valid": False, "message": f"Invalid input: {str(e)}"}

    # -------------------------
    # Find best available rooms
    # -------------------------
    def find_best_rooms(self, criteria: dict, limit: int = 5) -> List[Dict]:
        date = criteria.get('date')
        start_time = criteria.get('start_time')
        end_time = criteria.get('end_time')
        capacity = criteria.get('capacity', 1)
        room_number = criteria.get('room_number')
        purpose = criteria.get('purpose')

        rooms = self.Room.objects.filter(is_available=True)
        if room_number:
            rooms = rooms.filter(room_number__iexact=room_number)
        if capacity:
            rooms = rooms.filter(capacity__gte=capacity)

        # Room type preference
        if purpose:
            type_mapping = {
                'meeting': 'meeting',
                'lecture': 'lecture',
                'conference': 'conference',
                'workshop': 'workshop',
                'lab': 'lab'
            }
            room_type = type_mapping.get(purpose)
            if room_type:
                from django.db.models import Case, When, IntegerField
                try:
                    rooms = rooms.annotate(
                        _match_type=Case(
                            When(room_type__iexact=room_type, then=1),
                            default=0,
                            output_field=IntegerField()
                        )
                    ).order_by('-_match_type', 'capacity')
                except Exception:
                    rooms = rooms.order_by('capacity')

        available_rooms = []
        for room in rooms[:20]:
            score, availability = self._score_room(room, criteria)
            if availability['is_available']:
                building_info = getattr(room, 'building_name', None) or getattr(room, 'building', None)
                available_rooms.append({
                    'room': room,
                    'score': score,
                    'capacity': getattr(room, 'capacity', None),
                    'name': getattr(room, 'name', None),
                    'room_number': getattr(room, 'room_number', None),
                    'building': building_info,
                    'availability': availability,
                    'features': self._get_room_features(room)
                })

        available_rooms.sort(key=lambda x: x['score'], reverse=True)
        return available_rooms[:limit]

    # -------------------------
    # Score a room based on criteria
    # -------------------------
    def _score_room(self, room, criteria: dict) -> Tuple[float, Dict]:
        score = 0.0
        availability = {'is_available': True, 'conflicts': []}

        date = criteria.get('date')
        start_time = criteria.get('start_time')
        end_time = criteria.get('end_time')
        capacity = criteria.get('capacity', 1)
        if isinstance(capacity, str):
            try: capacity = int(capacity)
            except: capacity = 1

        if date and start_time and end_time:
            conflicts = self._check_conflicts(room, date, start_time, end_time)
            if conflicts:
                availability['is_available'] = False
                availability['conflicts'] = conflicts
                return 0.0, availability
            else:
                score += 50

        # Capacity scoring
        if room.capacity >= capacity:
            excess = room.capacity - capacity
            if excess == 0: score += 30
            elif excess <= 5: score += 25
            elif excess <= 10: score += 20
            else: score += 15 - min(excess * 0.5, 10)
        else:
            availability['is_available'] = False
            return 0.0, availability

        # Building preference
        if criteria.get('building'):
            room_building = getattr(room, 'building_name', None) or getattr(room, 'building', None)
            if room_building and room_building.upper() == criteria['building'].upper():
                score += 20

        # Room type preference
        if criteria.get('purpose'):
            type_mapping = {'meeting': 'meeting','lecture':'lecture','conference':'conference','workshop':'training'}
            preferred_type = type_mapping.get(criteria['purpose'])
            if preferred_type and room.room_type == preferred_type:
                score += 15

        # Features
        if getattr(room, 'has_projector', False): score += 5
        if getattr(room, 'has_whiteboard', False): score += 3
        if getattr(room, 'has_computer', False): score += 4

        return score, availability

    # -------------------------
    # Check booking conflicts
    # -------------------------
    def _check_conflicts(self, room, date: str, start_time: str, end_time: str) -> List[Dict]:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except:
            return []

        bookings = self.Booking.objects.filter(
            room=room,
            start_time__date=date_obj,
            status__in=['confirmed']
        )

        conflicts = []
        for booking in bookings:
            if self._times_overlap(start_time, end_time,
                                   booking.start_time.strftime('%H:%M'),
                                   booking.end_time.strftime('%H:%M')):
                conflicts.append({
                    'booking_id': booking.id,
                    'start': booking.start_time.strftime('%H:%M'),
                    'end': booking.end_time.strftime('%H:%M'),
                    'user': getattr(booking.user, 'get_full_name', lambda: str(booking.user))()
                })
        return conflicts

    # -------------------------
    # Time overlap check
    # -------------------------
    def _times_overlap(self, start1: str, end1: str, start2: str, end2: str) -> bool:
        try:
            s1 = datetime.strptime(start1, '%H:%M')
            e1 = datetime.strptime(end1, '%H:%M')
            s2 = datetime.strptime(start2, '%H:%M')
            e2 = datetime.strptime(end2, '%H:%M')
            return s1 < e2 and e1 > s2
        except:
            return False

    # -------------------------
    # Room features list
    # -------------------------
    def _get_room_features(self, room) -> List[str]:
        features = []
        feature_attrs = [
            ('has_projector', 'Projector'),
            ('has_whiteboard', 'Whiteboard'),
            ('has_computer', 'Computer'),
            ('has_audio', 'Audio System'),
            ('has_video', 'Video Conferencing'),
            ('has_ac', 'Air Conditioning'),
        ]
        for attr, label in feature_attrs:
            if getattr(room, attr, False):
                features.append(label)
        return features

    # -------------------------
    # Suggest alternative times
    # -------------------------
    def suggest_alternative_times(self, room, date: str, preferred_start: str, duration_hours: float = 1.0) -> List[Dict]:
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            pref_time = datetime.strptime(preferred_start, '%H:%M').time()
        except Exception:
            return []

        bookings = list(self.Booking.objects.filter(
            room=room,
            start_time__date=date_obj,
            status__in=['confirmed']
        ).order_by('start_time'))

        work_start_dt = timezone.make_aware(datetime.combine(date_obj, dt_time(8, 0)))
        work_end_dt = timezone.make_aware(datetime.combine(date_obj, dt_time(18, 0)))
        occupied = [{'start': b.start_time, 'end': b.end_time} for b in bookings]

        free_slots = []
        current = work_start_dt
        duration = timedelta(hours=duration_hours)

        while current + duration <= work_end_dt:
            slot_start = current
            slot_end = current + duration
            is_free = True
            for o in occupied:
                if slot_start < o['end'] and slot_end > o['start']:
                    is_free = False
                    current = o['end']
                    break
            if is_free:
                free_slots.append({'start': slot_start.strftime('%H:%M'),'end': slot_end.strftime('%H:%M'),'duration':duration_hours})
                current += timedelta(minutes=30)
            else:
                continue

        pref_minutes = pref_time.hour*60 + pref_time.minute
        for slot in free_slots:
            slot_time = datetime.strptime(slot['start'],'%H:%M').time()
            slot_minutes = slot_time.hour*60 + slot_time.minute
            slot['proximity_score'] = abs(pref_minutes - slot_minutes)
        free_slots.sort(key=lambda x: x['proximity_score'])
        return free_slots[:5]

    # -------------------------
    # Auto booking
    # -------------------------
    def auto_book(self, user, criteria: dict) -> Dict:
        best_rooms = self.find_best_rooms(criteria, limit=1)
        if not best_rooms:
            return {'success': False,'error':'No available rooms','suggestions': self._generate_suggestions(criteria)}
        best_match = best_rooms[0]
        room = best_match['room']

        # Parse date/time
        try:
            date_obj = datetime.strptime(criteria['date'],'%Y-%m-%d').date()
            start_time_obj = datetime.strptime(criteria['start_time'],'%H:%M')
            end_time_obj = datetime.strptime(criteria['end_time'],'%H:%M')
            start_dt = timezone.make_aware(datetime.combine(date_obj,start_time_obj.time()))
            end_dt = timezone.make_aware(datetime.combine(date_obj,end_time_obj.time()))
            if end_dt <= start_dt: end_dt += timedelta(days=1)
        except Exception as e:
            logger.error(f"Auto-booking: invalid date/time: {e}")
            return {'success':False,'error':'Invalid date/time','user_message':'Invalid date/time format'}

        conflicts = self._check_conflicts(room, criteria['date'], criteria['start_time'], criteria['end_time'])
        if conflicts:
            alternatives = self.suggest_alternative_times(room, criteria['date'], criteria['start_time'])
            other_rooms = [r for r in self.find_best_rooms(criteria, limit=3) if r['room'].id != room.id]
            user_message = f"{room.name} ({room.room_number}) is not available at that time."
            if alternatives:
                user_message += "\n**Alternative times:**\n" + "\n".join([f"{a['start']} - {a['end']}" for a in alternatives[:3]])
            if other_rooms:
                user_message += "\n**Other rooms:**\n" + "\n".join([f"{r['room'].name} ({r['room'].room_number})" for r in other_rooms[:2]])
            return {'success':False,'error':'Room not available','user_message':user_message,'conflicts':conflicts}

        booking = self.Booking.objects.create(
            user=user,
            room=room,
            start_time=start_dt,
            end_time=end_dt,
            purpose=criteria.get('purpose','meeting'),
            attendees=criteria.get('capacity',1),
            additional_notes=f"Auto-booked via chatbot. {criteria.get('raw_message','')}"
        )

        return {'success':True,'booking':booking,'room':best_match,'user_message':f"✅ Booking confirmed: {room.name} ({room.room_number})"}

    # -------------------------
    # Suggestions if no rooms
    # -------------------------
    def _generate_suggestions(self, criteria: dict) -> List[str]:
        suggestions = []
        if criteria.get('capacity'): suggestions.append(f"Try rooms with capacity {criteria['capacity']+10}+")
        if criteria.get('date') and criteria.get('start_time'): suggestions.append("Consider alternative time slots")
        if criteria.get('building'): suggestions.append(f"Check rooms in other buildings besides {criteria['building']}")
        suggestions.append("Browse all available rooms")
        return suggestions

