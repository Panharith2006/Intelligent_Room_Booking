"""Lightweight BookingAutomation shim used by the chatbot during development.

This module provides a minimal implementation of the interface expected
by the chatbot (used in `chatbot/apps.py` and `chatbot/views.py`) so the
chat agent can be initialized without requiring a full external service.

It intentionally keeps behavior conservative: `find_best_rooms` returns
available rooms ordered by capacity match and `auto_book` returns a
friendly failure message to avoid creating bookings unexpectedly in dev.
Replace or extend this with your production booking automation as needed.
"""
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


class BookingAutomation:
    def __init__(self, RoomModel, BookingModel=None, BookingRuleModel=None):
        self.Room = RoomModel
        self.Booking = BookingModel
        self.BookingRule = BookingRuleModel

    def find_best_rooms(self, criteria: Dict[str, Any], limit: int = 3) -> List[Dict[str, Any]]:
        """Return a small list of candidate rooms matching basic criteria.

        Each item is a dict with at least the key `room` containing a Room
        instance. This is intentionally simple: it filters by `is_available`
        and `capacity` (if provided) and returns up to `limit` rooms.
        """
        qs = self.Room.objects.filter(is_available=True)
        try:
            cap = criteria.get('capacity')
            if cap:
                # allow numeric strings
                try:
                    cap_int = int(cap)
                    qs = qs.filter(capacity__gte=cap_int)
                except Exception:
                    pass
        except Exception:
            pass

        qs = qs.order_by('capacity')
        results = []
        for room in qs[:limit]:
            results.append({'room': room, 'score': 1.0})
        return results

    def auto_book(self, user, criteria: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to perform an automatic booking.

        The development shim does not create persistent bookings. It
        returns a structured response the chatbot expects. Replace this
        with real creation logic when ready.
        """
        try:
            # Basic validation
            date = criteria.get('date')
            start = criteria.get('start_time')
            end = criteria.get('end_time')
            if not (date and start and end):
                return {'success': False, 'user_message': 'Missing date or time information for booking.'}

            # If a specific room id was provided, try to resolve it for messaging
            room_id = criteria.get('best_room_id') or criteria.get('room_id')
            room_name = None
            if room_id:
                try:
                    room = self.Room.objects.filter(id=room_id).first()
                    if room:
                        room_name = getattr(room, 'name', str(room))
                except Exception:
                    room_name = None

            msg_room = f' for {room_name}' if room_name else ''
            return {
                'success': False,
                'user_message': f'Auto-booking is disabled in this development instance{msg_room}. Please confirm manually via the UI.'
            }
        except Exception as e:
            logger.exception('auto_book failed: %s', e)
            return {'success': False, 'user_message': 'Failed to perform auto-booking.'}
"""
Advanced Booking Automation Engine
Handles automated room booking with intelligent scheduling and conflict resolution
"""

from datetime import datetime, timedelta, time as dt_time
from django.utils import timezone
from django.db.models import Case, When, IntegerField
from typing import Dict, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BookingAutomation:
    
    def __init__(self, room_model, booking_model, booking_rule_model=None):
        self.Room = room_model
        self.Booking = booking_model
        self.BookingRule = booking_rule_model
    
    def find_best_rooms(self, criteria: dict, limit: int = 5) -> List[Dict]:
        date = criteria.get('date')
        start_time = criteria.get('start_time')
        end_time = criteria.get('end_time')
        capacity = criteria.get('capacity', 1)
        room_number = criteria.get('room_number')
        purpose = criteria.get('purpose')
        
        # Get base queryset
        rooms = self.Room.objects.filter(is_available=True)
        
        if room_number:
            rooms = rooms.filter(room_number__iexact=room_number)
        
        # Capacity filter (rooms that can accommodate the required capacity)
        if capacity:
            rooms = rooms.filter(capacity__gte=capacity)
        
        # Room type preference based on purpose
        if purpose:
            type_mapping = {
                'meeting': 'meeting',
                'lecture': 'lecture',
                'conference': 'conference',
                'workshop': 'training',
                'exam': 'exam'
            }
            room_type = type_mapping.get(purpose)
            if room_type:
                    # Prefer matching type but don't exclude others: annotate match flag then order
                    try:
                        rooms = rooms.annotate(
                            _match_type=Case(
                                When(room_type__iexact=room_type, then=1),
                                default=0,
                                output_field=IntegerField()
                            )
                        ).order_by('-_match_type', 'capacity')
                    except Exception:
                        # Fallback to simple ordering if annotation fails
                        rooms = rooms.order_by('capacity')
        
        # Check availability if date/time provided
        available_rooms = []
        
        for room in rooms[:20]:  # Check top 20 candidates
            score, availability = self._score_room(room, criteria)

            if availability['is_available']:
                # Safely access optional fields that may not exist on older models
                building = getattr(room, 'building_name', None) or getattr(room, 'building', None)
                available_rooms.append({
                    'room': room,
                    'score': score,
                    'capacity': getattr(room, 'capacity', None),
                    'name': getattr(room, 'name', None),
                    'room_number': getattr(room, 'room_number', None),
                    'building': building,
                    'availability': availability,
                    'features': self._get_room_features(room)
                })
        
        # Sort by score (descending)
        available_rooms.sort(key=lambda x: x['score'], reverse=True)
        
        return available_rooms[:limit]
    
    def _score_room(self, room, criteria: dict) -> Tuple[float, Dict]:
        """
        Score room based on how well it matches criteria
        
        Returns:
            (score, availability_info)
        """
        score = 0.0
        availability = {'is_available': True, 'conflicts': []}
        
        date = criteria.get('date')
        start_time = criteria.get('start_time')
        end_time = criteria.get('end_time')
        capacity = criteria.get('capacity', 1)
        
        # Check time-based availability
        if date and start_time and end_time:
            conflicts = self._check_conflicts(room, date, start_time, end_time)
            if conflicts:
                availability['is_available'] = False
                availability['conflicts'] = conflicts
                return 0.0, availability  # Not available
            else:
                score += 50  # Big bonus for being available
        
        # Capacity scoring (prefer optimal size)
        if capacity:
            if room.capacity >= capacity:
                # Score based on how close to optimal
                excess = room.capacity - capacity
                if excess == 0:
                    score += 30  # Perfect match
                elif excess <= 5:
                    score += 25  # Slightly over
                elif excess <= 10:
                    score += 20
                else:
                    score += 15 - min(excess * 0.5, 10)  # Penalty for too large
            else:
                # Room too small - not suitable
                availability['is_available'] = False
                return 0.0, availability
        
        # Building preference
        if criteria.get('building'):
            room_building = getattr(room, 'building_name', None) or getattr(room, 'building', None)
            if room_building and room_building.upper() == criteria['building'].upper():
                score += 20
        
        # Room type preference
        if criteria.get('purpose'):
            type_mapping = {
                'meeting': 'meeting',
                'lecture': 'lecture',
                'conference': 'conference',
                'workshop': 'training',
            }
            preferred_type = type_mapping.get(criteria['purpose'])
            if preferred_type and room.room_type == preferred_type:
                score += 15
        
        # Equipment/features bonus
        if hasattr(room, 'has_projector') and room.has_projector:
            score += 5
        if hasattr(room, 'has_whiteboard') and room.has_whiteboard:
            score += 3
        if hasattr(room, 'has_computer') and room.has_computer:
            score += 4
        
        return score, availability
    
    def _check_conflicts(self, room, date: str, start_time: str, end_time: str) -> List[Dict]:
        """
        Check for booking conflicts
        
        Returns:
            List of conflicting bookings
        """
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
        except:
            return []
        
        # Get bookings for this room on this date
        bookings = self.Booking.objects.filter(
            room=room,
            start_time__date=date_obj,
            status__in=['confirmed']
        )
        
        conflicts = []
        
        for booking in bookings:
            # Check time overlap
            if self._times_overlap(
                start_time, end_time,
                booking.start_time.strftime('%H:%M'),
                booking.end_time.strftime('%H:%M')
            ):
                conflicts.append({
                    'booking_id': booking.id,
                    'start': booking.start_time.strftime('%H:%M'),
                    'end': booking.end_time.strftime('%H:%M'),
                    'user': booking.user.get_full_name() if hasattr(booking.user, 'get_full_name') else str(booking.user)
                })
        
        return conflicts
    
    def _times_overlap(self, start1: str, end1: str, start2: str, end2: str) -> bool:
        """
        Check if two time ranges overlap
        """
        try:
            s1 = datetime.strptime(start1, '%H:%M')
            e1 = datetime.strptime(end1, '%H:%M')
            s2 = datetime.strptime(start2, '%H:%M')
            e2 = datetime.strptime(end2, '%H:%M')
            
            return s1 < e2 and e1 > s2
        except:
            return False
    
    def _get_room_features(self, room) -> List[str]:
        """
        Get list of room features/equipment
        """
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
            if hasattr(room, attr) and getattr(room, attr):
                features.append(label)
        
        return features
    
    def suggest_alternative_times(self, room, date: str, preferred_start: str, 
                                  duration_hours: float = 1.0) -> List[Dict]:
        """
        Suggest alternative time slots when preferred time is unavailable
        
        Args:
            room: Room object
            date: Date string (YYYY-MM-DD)
            preferred_start: Preferred start time (HH:MM)
            duration_hours: Duration in hours
            
        Returns:
            List of available time slots
        """
        try:
            date_obj = datetime.strptime(date, '%Y-%m-%d').date()
            pref_time = datetime.strptime(preferred_start, '%H:%M').time()
        except Exception:
            return []

        # Get all bookings for this room on this date (use start_time__date)
        bookings = list(self.Booking.objects.filter(
            room=room,
            start_time__date=date_obj,
            status__in=['confirmed']
        ).order_by('start_time'))

        # Define working hours (8 AM to 6 PM) as timezone-aware datetimes on the date
        work_start_dt = timezone.make_aware(datetime.combine(date_obj, dt_time(8, 0)))
        work_end_dt = timezone.make_aware(datetime.combine(date_obj, dt_time(18, 0)))

        # Build occupied time slots using booking datetimes (they are timezone-aware)
        occupied = []
        for booking in bookings:
            occupied.append({
                'start': booking.start_time,
                'end': booking.end_time
            })

        # Find free slots
        free_slots = []
        current = work_start_dt
        duration = timedelta(hours=duration_hours)

        while current + duration <= work_end_dt:
            slot_start = current
            slot_end = current + duration

            # Check if this slot conflicts with any booking
            is_free = True
            for occupied_slot in occupied:
                if slot_start < occupied_slot['end'] and slot_end > occupied_slot['start']:
                    is_free = False
                    # Jump to end of this booking
                    current = occupied_slot['end']
                    break

            if is_free:
                free_slots.append({
                    'start': slot_start.strftime('%H:%M'),
                    'end': slot_end.strftime('%H:%M'),
                    'duration': duration_hours
                })
                current += timedelta(minutes=30)  # 30-minute intervals
            else:
                # continue loop with updated current
                continue

        # Sort by proximity to preferred time
        pref_minutes = pref_time.hour * 60 + pref_time.minute

        for slot in free_slots:
            slot_time = datetime.strptime(slot['start'], '%H:%M').time()
            slot_minutes = slot_time.hour * 60 + slot_time.minute
            slot['proximity_score'] = abs(pref_minutes - slot_minutes)

        free_slots.sort(key=lambda x: x['proximity_score'])

        return free_slots[:5]  # Return top 5 closest alternatives
    
    def _check_booking_rules(self, user, start_dt: datetime, end_dt: datetime) -> Tuple[bool, str]:
        """
        Check if booking complies with active booking rules
        
        Returns:
            (is_valid, error_message)
        """
        if not self.BookingRule:
            return True, ""
        
        # Get active booking rule
        try:
            rule = self.BookingRule.objects.filter(is_active=True).first()
            if not rule:
                return True, ""  # No rules configured
        except Exception:
            return True, ""  # No rules table
        
        # Check duration limit
        duration_hours = (end_dt - start_dt).total_seconds() / 3600
        if duration_hours > rule.max_duration_hours:
            return False, f"Maximum booking duration is {rule.max_duration_hours} hours. Your booking is {duration_hours:.1f} hours."
        
        # Check advance booking limit
        from django.utils import timezone
        advance_days = (start_dt.date() - timezone.now().date()).days
        if advance_days > rule.max_advance_days:
            return False, f"Bookings can only be made up to {rule.max_advance_days} days in advance."
        
        # Check minimum advance time
        time_until_booking = (start_dt - timezone.now()).total_seconds() / 3600
        if time_until_booking < rule.min_advance_hours:
            return False, f"Bookings must be made at least {rule.min_advance_hours} hours in advance."
        
        # Check daily booking limit
        today_bookings = self.Booking.objects.filter(
            user=user,
            start_time__date=start_dt.date(),
            status='confirmed'
        ).count()
        
        if today_bookings >= rule.daily_booking_limit:
            return False, f"You've reached the daily booking limit of {rule.daily_booking_limit} bookings for {start_dt.strftime('%B %d, %Y')}."
        
        # Check weekly booking limit
        from datetime import timedelta
        week_start = start_dt.date() - timedelta(days=start_dt.weekday())
        week_end = week_start + timedelta(days=6)
        
        weekly_bookings = self.Booking.objects.filter(
            user=user,
            start_time__date__range=[week_start, week_end],
            status='confirmed'
        ).count()
        
        if weekly_bookings >= rule.weekly_booking_limit:
            return False, f"You've reached the weekly booking limit of {rule.weekly_booking_limit} bookings."
        
        # Check booking time window
        if start_dt.time() < rule.booking_start_time:
            return False, f"Bookings can only start from {rule.booking_start_time.strftime('%I:%M %p')} onwards."
        
        if end_dt.time() > rule.booking_end_time:
            return False, f"Bookings must end by {rule.booking_end_time.strftime('%I:%M %p')}."
        
        return True, ""
    
    def _log_booking_action(self, user, action: str, details: dict):
        """
        Log booking actions for audit trail
        """
        try:
            logger.info(
                f"Booking Action: {action} | User: {user.email if hasattr(user, 'email') else user} | "
                f"Details: {details}"
            )
        except Exception as e:
            logger.warning(f"Failed to log booking action: {e}")
    
    def auto_book(self, user, criteria: dict) -> Dict:
        """
        Automatically book the best available room based on criteria
        
        Args:
            user: Django user object
            criteria: Booking criteria dict
            
        Returns:
            Result dict with booking info or error
        """
        # Find best room
        best_rooms = self.find_best_rooms(criteria, limit=1)

        if not best_rooms:
            return {
                'success': False,
                'error': 'No available rooms found matching your criteria',
                'suggestions': self._generate_suggestions(criteria)
            }

        best_match = best_rooms[0]
        room = best_match['room']

        # Validate required fields
        required = ['date', 'start_time', 'end_time']
        missing = [f for f in required if not criteria.get(f)]

        if missing:
            return {
                'success': False,
                'error': f'Missing required information: {", ".join(missing)}',
                'best_room': best_match,
                'needs_input': missing
            }

        # Parse and combine date + times into timezone-aware datetimes expected by Booking model
        try:
            # date is YYYY-MM-DD, times are HH:MM
            date_obj = datetime.strptime(criteria['date'], '%Y-%m-%d').date()
            start_time_obj = datetime.strptime(criteria['start_time'], '%H:%M')
            end_time_obj = datetime.strptime(criteria['end_time'], '%H:%M')

            # Combine date and time into full datetimes
            start_dt = datetime.combine(date_obj, start_time_obj.time())
            end_dt = datetime.combine(date_obj, end_time_obj.time())

            # If end is before start, assume it crosses midnight -> add one day
            if end_dt <= start_dt:
                end_dt = end_dt + timedelta(days=1)
            
            # Make datetimes timezone-aware using Django timezone
            try:
                if timezone.is_naive(start_dt):
                    start_dt = timezone.make_aware(start_dt)
                if timezone.is_naive(end_dt):
                    end_dt = timezone.make_aware(end_dt)
            except Exception:
                # If timezone utilities are not available or make_aware fails, continue with naive
                pass
        except Exception as e:
            logger.error(f"Auto-booking: invalid date/time format: {e}")
            self._log_booking_action(user, 'FAILED_PARSE', {'error': str(e), 'criteria': criteria})
            return {
                'success': False,
                'error': 'Invalid date or time format. Please use YYYY-MM-DD for date and HH:MM for times.',
                'user_message': 'I couldn\'t understand the date or time format. Please try again with a format like "tomorrow at 2pm" or "Dec 15 from 14:00 to 15:00".'
            }

        # Check booking rules (daily/weekly limits, duration, advance time)
        rules_valid, rules_error = self._check_booking_rules(user, start_dt, end_dt)
        if not rules_valid:
            self._log_booking_action(user, 'RULE_VIOLATION', {
                'rule_error': rules_error,
                'criteria': criteria
            })
            return {
                'success': False,
                'error': rules_error,
                'user_message': f"{rules_error}\n\nPlease adjust your booking request or contact support if you need assistance.",
                'rule_violation': True
            }

        # Check for conflicts explicitly before creating booking
        conflicts = self._check_conflicts(room, criteria['date'], criteria['start_time'], criteria['end_time'])
        if conflicts:
            # Get alternative time suggestions
            alternatives = self.suggest_alternative_times(room, criteria['date'], criteria['start_time'])
            
            # Try to find other available rooms
            other_rooms = self.find_best_rooms(criteria, limit=3)
            other_available = [r for r in other_rooms if r['room'].id != room.id]
            
            self._log_booking_action(user, 'CONFLICT_DETECTED', {
                'room': str(room),
                'conflicts': len(conflicts),
                'alternatives_found': len(alternatives)
            })
            
            error_msg = f"{room.name} ({room.room_number}) is not available at that time."
            suggestions = []
            
            if alternatives:
                suggestions.append(f"\n**Alternative times for {room.name}:**")
                for i, alt in enumerate(alternatives[:3], 1):
                    suggestions.append(f"  {i}. {alt['start']} - {alt['end']}")
            
            if other_available:
                suggestions.append(f"\n**Other available rooms:**")
                for i, r in enumerate(other_available[:2], 1):
                    room_info = r['room']
                    suggestions.append(
                        f"  {i}. {room_info.name} ({room_info.room_number}) - Capacity: {room_info.capacity}"
                    )
            
            user_message = error_msg
            if suggestions:
                user_message += "\n" + "\n".join(suggestions)
                user_message += "\n\nWould you like to book one of these alternatives?"
            else:
                user_message += "\n\nPlease try a different date or time."
            
            return {
                'success': False,
                'error': 'Room not available',
                'user_message': user_message,
                'conflicts': conflicts,
                'alternatives': alternatives,
                'other_rooms': other_available,
                'best_room': best_match
            }

        # Create booking (map fields to Booking model)
        try:
            booking = self.Booking.objects.create(
                user=user,
                room=room,
                start_time=start_dt,
                end_time=end_dt,
                purpose=criteria.get('purpose', 'meeting'),
                attendees=criteria.get('capacity', 1),
                additional_notes=f"Auto-booked via chatbot. {criteria.get('raw_message', '')}"
            )
            
            # Log successful booking
            self._log_booking_action(user, 'AUTO_BOOKED', {
                'booking_id': booking.id,
                'room': str(room),
                'date': criteria['date'],
                'time': f"{criteria['start_time']} - {criteria['end_time']}",
                'capacity': criteria.get('capacity', 1)
            })

            return {
                'success': True,
                'booking': booking,
                'room': best_match,
                'message': f'Successfully booked {getattr(room, "name", str(room))} ({getattr(room, "room_number", "")})',
                'user_message': (
                    f"✅ **Booking Confirmed!**\n\n"
                    f"**Room:** {room.name} ({room.room_number})\n"
                    f"**Date:** {booking.start_time.strftime('%B %d, %Y')}\n"
                    f"**Time:** {booking.start_time.strftime('%I:%M %p')} - {booking.end_time.strftime('%I:%M %p')}\n"
                    f"**Capacity:** {best_match['capacity']} people\n\n"
                    f"Your booking has been created! You can view it in your dashboard."
                )
            }

        except Exception as e:
            logger.exception(f"Auto-booking failed: {str(e)}")
            self._log_booking_action(user, 'CREATE_FAILED', {
                'error': str(e),
                'room': str(room),
                'criteria': criteria
            })
            return {
                'success': False,
                'error': f'Booking failed: {str(e)}',
                'user_message': f"Sorry, I couldn't complete your booking due to a technical issue: {str(e)}\n\nPlease try again or contact support.",
                'best_room': best_match
            }
    
    def _generate_suggestions(self, criteria: dict) -> List[str]:
        """
        Generate helpful suggestions when no rooms are available
        """
        suggestions = []
        
        if criteria.get('capacity'):
            suggestions.append(f"Try searching for rooms with capacity {criteria['capacity'] + 10}+ to see more options")
        
        if criteria.get('date') and criteria.get('start_time'):
            suggestions.append("Consider alternative time slots")
            # Could add actual alternative times here
        
        if criteria.get('building'):
            suggestions.append(f"Check rooms in other buildings besides {criteria['building']}")
        
        suggestions.append("Browse all available rooms to see current options")
        
        return suggestions
