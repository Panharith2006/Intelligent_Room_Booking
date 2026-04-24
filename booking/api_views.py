# booking/api_views.py
"""
REST API views for AI chatbot integration
These endpoints allow the Semantic Kernel AI agent to interact with the booking system
"""

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, timedelta
import json

from .models import Room, Booking, BookingRule
from accounts.models import User


# University booking policy scope (must match web flow enforcement)
BOOKING_MIN_DURATION_HOURS = 1
BOOKING_MAX_DURATION_HOURS = 3
BOOKING_MIN_ADVANCE_HOURS = 1
BOOKING_MAX_ADVANCE_DAYS = 30
BOOKING_MAX_ACTIVE_PER_USER = 5
BOOKING_BUFFER_MINUTES = 5
CANCELLATION_NOTICE_HOURS = 3
LATE_CANCELLATIONS_PER_WARNING = 2


def check_consecutive_booking_limit(user, room, start_datetime, end_datetime):
    """Ensure same-user consecutive bookings in the same room stay within max duration."""
    buffer_delta = timedelta(minutes=BOOKING_BUFFER_MINUTES)
    day_start = start_datetime.replace(hour=0, minute=0, second=0, microsecond=0)
    day_end = start_datetime.replace(hour=23, minute=59, second=59, microsecond=999999)

    bookings = list(
        Booking.objects.filter(
            user=user,
            room=room,
            status='confirmed',
            start_time__gte=day_start,
            end_time__lte=day_end,
        ).order_by('start_time')
    )

    chain_start = start_datetime
    chain_end = end_datetime

    changed = True
    while changed:
        changed = False
        for existing in bookings:
            is_touching_before = abs((existing.end_time - chain_start).total_seconds()) <= buffer_delta.total_seconds()
            is_touching_after = abs((existing.start_time - chain_end).total_seconds()) <= buffer_delta.total_seconds()

            if is_touching_before or is_touching_after:
                new_start = min(chain_start, existing.start_time)
                new_end = max(chain_end, existing.end_time)
                if new_start != chain_start or new_end != chain_end:
                    chain_start, chain_end = new_start, new_end
                    changed = True

    consecutive_hours = (chain_end - chain_start).total_seconds() / 3600
    if consecutive_hours > BOOKING_MAX_DURATION_HOURS:
        return False, f'Consecutive bookings in the same room cannot exceed {BOOKING_MAX_DURATION_HOURS} hours total.'

    return True, ''


# ============================================
# Room API Endpoints
# ============================================

@csrf_exempt
@require_http_methods(["GET"])
def api_list_rooms(request):
    try:
        # Get filter parameters
        room_type = request.GET.get('room_type', None)
        capacity_min = request.GET.get('capacity_min', None)
        capacity_max = request.GET.get('capacity_max', None)
        available_only = request.GET.get('available_only', 'true').lower() == 'true'
        
        # Base query
        rooms = Room.objects.all()
        
        # Apply filters
        if available_only:
            rooms = rooms.filter(is_available=True, availability_status='available')
        
        if room_type:
            rooms = rooms.filter(room_type=room_type)
        
        if capacity_min:
            rooms = rooms.filter(capacity__gte=int(capacity_min))
        
        if capacity_max:
            rooms = rooms.filter(capacity__lte=int(capacity_max))
        
        # Serialize rooms
        rooms_data = []
        for room in rooms:
            rooms_data.append({
                'id': room.id,
                'name': room.name,
                'room_number': room.room_number,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'description': room.description,
                'equipment': room.equipment,
                'is_available': room.is_available,
                'availability_status': room.availability_status
            })
        
        return JsonResponse({
            'success': True,
            'count': len(rooms_data),
            'rooms': rooms_data
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def api_check_availability(request):
    try:
        # Get parameters
        room_id = request.GET.get('room_id')
        date_str = request.GET.get('date')  # Format: YYYY-MM-DD
        start_time_str = request.GET.get('start_time')  # Format: HH:MM
        end_time_str = request.GET.get('end_time')  # Format: HH:MM
        
        if not all([room_id, date_str, start_time_str, end_time_str]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required parameters: room_id, date, start_time, end_time'
            }, status=400)
        
        # Parse date and time
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Create datetime objects
        start_datetime = timezone.make_aware(datetime.combine(date, start_time))
        end_datetime = timezone.make_aware(datetime.combine(date, end_time))

        # Validate against booking time policy
        now = timezone.now()
        if start_datetime <= now + timedelta(hours=BOOKING_MIN_ADVANCE_HOURS):
            return JsonResponse({
                'success': False,
                'available': False,
                'error': f'Booking must be made at least {BOOKING_MIN_ADVANCE_HOURS} hour in advance'
            }, status=400)

        if start_datetime > now + timedelta(days=BOOKING_MAX_ADVANCE_DAYS):
            return JsonResponse({
                'success': False,
                'available': False,
                'error': f'Cannot book more than {BOOKING_MAX_ADVANCE_DAYS} days in advance'
            }, status=400)

        if start_datetime >= end_datetime:
            return JsonResponse({
                'success': False,
                'available': False,
                'error': 'End time must be after start time'
            }, status=400)

        duration_hours = (end_datetime - start_datetime).total_seconds() / 3600
        if duration_hours < BOOKING_MIN_DURATION_HOURS:
            return JsonResponse({
                'success': False,
                'available': False,
                'error': f'Minimum booking duration is {BOOKING_MIN_DURATION_HOURS} hour'
            }, status=400)

        if duration_hours > BOOKING_MAX_DURATION_HOURS:
            return JsonResponse({
                'success': False,
                'available': False,
                'error': f'Maximum booking duration is {BOOKING_MAX_DURATION_HOURS} hours'
            }, status=400)
        
        # Get room
        room = Room.objects.get(id=room_id)
        
        # Check if room is available
        is_available = room.is_available_at(start_datetime, end_datetime)
        
        # Get conflicting bookings if not available
        conflicts = []
        if not is_available:
            conflicting_bookings = Booking.objects.filter(
                room=room,
                start_time__lt=end_datetime,
                end_time__gt=start_datetime,
                status='confirmed'
            )
            
            for booking in conflicting_bookings:
                conflicts.append({
                    'booking_id': booking.id,
                    'user': booking.user.get_full_name(),
                    'start_time': booking.start_time.strftime('%Y-%m-%d %H:%M'),
                    'end_time': booking.end_time.strftime('%Y-%m-%d %H:%M'),
                    'purpose': booking.purpose
                })
        
        return JsonResponse({
            'success': True,
            'available': is_available,
            'room': {
                'id': room.id,
                'name': room.name,
                'room_number': room.room_number,
                'capacity': room.capacity
            },
            'requested_time': {
                'start': start_datetime.strftime('%Y-%m-%d %H:%M'),
                'end': end_datetime.strftime('%Y-%m-%d %H:%M')
            },
            'conflicts': conflicts
        })
    
    except Room.DoesNotExist:
        return JsonResponse({
            'success': False,
            'error': 'Room not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================
# Booking API Endpoints
# ============================================

@csrf_exempt
@require_http_methods(["POST"])
def api_create_booking(request):
    try:
        # Parse JSON body
        data = json.loads(request.body)
        
        # Get required fields
        user_email = data.get('user_email')
        room_id = data.get('room_id')
        date_str = data.get('date')
        start_time_str = data.get('start_time')
        end_time_str = data.get('end_time')
        purpose = data.get('purpose')
        attendees = data.get('attendees', 1)
        notes = data.get('notes', '')
        
        # Validate required fields
        if not all([user_email, room_id, date_str, start_time_str, end_time_str, purpose]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields: user_email, room_id, date, start_time, end_time, purpose'
            }, status=400)
        
        # Get user
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'User with email {user_email} not found'
            }, status=404)
        
        # Get room
        try:
            room = Room.objects.get(id=room_id)
        except Room.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Room with ID {room_id} not found'
            }, status=404)
        
        # Parse date and time
        date = datetime.strptime(date_str, '%Y-%m-%d').date()
        start_time = datetime.strptime(start_time_str, '%H:%M').time()
        end_time = datetime.strptime(end_time_str, '%H:%M').time()
        
        # Create datetime objects
        start_datetime = timezone.make_aware(datetime.combine(date, start_time))
        end_datetime = timezone.make_aware(datetime.combine(date, end_time))
        
        # Validate booking time
        now = timezone.now()
        if start_datetime < now:
            return JsonResponse({
                'success': False,
                'error': 'Cannot book rooms in the past'
            }, status=400)
        
        if start_datetime >= end_datetime:
            return JsonResponse({
                'success': False,
                'error': 'End time must be after start time'
            }, status=400)
        
        # Check duration limits
        duration = end_datetime - start_datetime
        duration_hours = duration.total_seconds() / 3600
        if duration_hours < BOOKING_MIN_DURATION_HOURS:
            return JsonResponse({
                'success': False,
                'error': f'Minimum booking duration is {BOOKING_MIN_DURATION_HOURS} hour'
            }, status=400)
        
        if duration_hours > BOOKING_MAX_DURATION_HOURS:
            return JsonResponse({
                'success': False,
                'error': f'Maximum booking duration is {BOOKING_MAX_DURATION_HOURS} hours'
            }, status=400)
        
        # Check advance booking limits
        advance_days = (start_datetime - now).days
        if advance_days > BOOKING_MAX_ADVANCE_DAYS:
            return JsonResponse({
                'success': False,
                'error': f'Cannot book more than {BOOKING_MAX_ADVANCE_DAYS} days in advance'
            }, status=400)
        
        advance_hours = (start_datetime - now).total_seconds() / 3600
        if advance_hours < BOOKING_MIN_ADVANCE_HOURS:
            return JsonResponse({
                'success': False,
                'error': f'Must book at least {BOOKING_MIN_ADVANCE_HOURS} hour in advance'
            }, status=400)
        
        # Check capacity
        if attendees > room.capacity:
            return JsonResponse({
                'success': False,
                'error': f'Number of attendees ({attendees}) exceeds room capacity ({room.capacity})'
            }, status=400)

        # Check room admin availability status
        if not room.is_available or getattr(room, 'availability_status', 'available') != 'available':
            return JsonResponse({
                'success': False,
                'error': 'Room is currently unavailable based on admin settings'
            }, status=400)

        # Users cannot hold multiple rooms in the same time slot
        overlapping_user_bookings = Booking.objects.filter(
            user=user,
            status='confirmed',
            start_time__lt=end_datetime,
            end_time__gt=start_datetime,
        )
        if overlapping_user_bookings.exists():
            return JsonResponse({
                'success': False,
                'error': 'You already have a booking during this time slot. Multiple rooms at the same time are not allowed.'
            }, status=400)

        # Users can have at most 5 active bookings at any time
        active_bookings_count = Booking.objects.filter(
            user=user,
            status='confirmed',
            end_time__gt=now,
        ).count()
        if active_bookings_count >= BOOKING_MAX_ACTIVE_PER_USER:
            return JsonResponse({
                'success': False,
                'error': (
                    f'You already have {BOOKING_MAX_ACTIVE_PER_USER} active bookings. '
                    'Complete or cancel one booking before making a new one.'
                )
            }, status=400)

        # Consecutive same-room bookings must remain within max duration
        can_book_consecutively, consecutive_error = check_consecutive_booking_limit(
            user, room, start_datetime, end_datetime
        )
        if not can_book_consecutively:
            return JsonResponse({
                'success': False,
                'error': consecutive_error
            }, status=400)
        
        # Check room availability
        if not room.is_available_at(start_datetime, end_datetime):
            return JsonResponse({
                'success': False,
                'error': 'Room is not available at the requested time. Please choose a different time slot.'
            }, status=400)
        
        # Create booking
        booking = Booking.objects.create(
            user=user,
            room=room,
            start_time=start_datetime,
            end_time=end_datetime,
            purpose=purpose,
            attendees=attendees,
            additional_notes=notes,
            status='confirmed'
        )
        
        return JsonResponse({
            'success': True,
            'message': 'Booking created successfully',
            'booking': {
                'id': booking.id,
                'room_name': room.name,
                'room_number': room.room_number,
                'start_time': booking.start_time.strftime('%Y-%m-%d %H:%M'),
                'end_time': booking.end_time.strftime('%Y-%m-%d %H:%M'),
                'duration_hours': booking.duration_hours,
                'purpose': booking.purpose,
                'attendees': booking.attendees,
                'status': booking.status,
                'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M')
            }
        }, status=201)
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def api_list_user_bookings(request):
    try:
        user_email = request.GET.get('user_email')
        status = request.GET.get('status', None)  # confirmed, cancelled, or None for all
        
        if not user_email:
            return JsonResponse({
                'success': False,
                'error': 'user_email parameter is required'
            }, status=400)
        
        # Get user
        try:
            user = User.objects.get(email=user_email)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'User with email {user_email} not found'
            }, status=404)
        
        # Get bookings
        bookings = Booking.objects.filter(user=user)
        
        if status:
            bookings = bookings.filter(status=status)
        
        # Separate upcoming and past bookings
        now = timezone.now()
        upcoming_bookings = bookings.filter(end_time__gte=now).order_by('start_time')
        past_bookings = bookings.filter(end_time__lt=now).order_by('-start_time')
        
        def serialize_booking(booking):
            return {
                'id': booking.id,
                'room_name': booking.room.name,
                'room_number': booking.room.room_number,
                'start_time': booking.start_time.strftime('%Y-%m-%d %H:%M'),
                'end_time': booking.end_time.strftime('%Y-%m-%d %H:%M'),
                'duration_hours': booking.duration_hours,
                'purpose': booking.purpose,
                'attendees': booking.attendees,
                'status': booking.status,
                'can_cancel': booking.can_cancel(),
                'created_at': booking.created_at.strftime('%Y-%m-%d %H:%M')
            }
        
        return JsonResponse({
            'success': True,
            'user': {
                'email': user.email,
                'name': user.get_full_name()
            },
            'upcoming_bookings': [serialize_booking(b) for b in upcoming_bookings],
            'past_bookings': [serialize_booking(b) for b in past_bookings],
            'total_count': bookings.count()
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["POST"])
def api_cancel_booking(request):
    try:
        data = json.loads(request.body)
        booking_id = data.get('booking_id')
        user_email = data.get('user_email')
        
        if not all([booking_id, user_email]):
            return JsonResponse({
                'success': False,
                'error': 'Missing required fields: booking_id, user_email'
            }, status=400)
        
        # Get booking
        try:
            booking = Booking.objects.get(id=booking_id)
        except Booking.DoesNotExist:
            return JsonResponse({
                'success': False,
                'error': f'Booking with ID {booking_id} not found'
            }, status=404)
        
        # Verify user owns the booking
        if booking.user.email != user_email:
            return JsonResponse({
                'success': False,
                'error': 'You can only cancel your own bookings'
            }, status=403)
        
        # Check if booking can be cancelled
        if not booking.can_cancel():
            return JsonResponse({
                'success': False,
                'error': 'This booking cannot be cancelled (either already cancelled or in the past)'
            }, status=400)
        
        # Cancellation policy: cancellation remains possible before start,
        # but late cancellation (within 3 hours) is recorded as a penalty.
        time_until_booking = booking.start_time - timezone.now()
        if time_until_booking.total_seconds() <= 0:
            return JsonResponse({
                'success': False,
                'error': 'This booking has already started or passed and cannot be cancelled'
            }, status=400)

        late_cancellation = time_until_booking < timedelta(hours=CANCELLATION_NOTICE_HOURS)
        warning_issued = False
        late_cancel_message = ''

        if late_cancellation:
            booking.user.late_cancellation_count = (booking.user.late_cancellation_count or 0) + 1
            if booking.user.late_cancellation_count % LATE_CANCELLATIONS_PER_WARNING == 0:
                booking.user.cancellation_warning_count = (booking.user.cancellation_warning_count or 0) + 1
                warning_issued = True

            booking.user.save(update_fields=['late_cancellation_count', 'cancellation_warning_count'])
            late_cancel_message = (
                f' Late cancellation recorded (less than {CANCELLATION_NOTICE_HOURS} hours notice). '
                f'Total late cancellations: {booking.user.late_cancellation_count}.'
            )
        
        # Cancel the booking
        booking.status = 'cancelled'
        booking.save()
        
        return JsonResponse({
            'success': True,
            'message': (
                'Booking cancelled successfully.'
                + late_cancel_message
                + (
                    f' Warning #{booking.user.cancellation_warning_count} issued '
                    f'(every {LATE_CANCELLATIONS_PER_WARNING} late cancellations).'
                    if warning_issued else ''
                )
            ),
            'booking': {
                'id': booking.id,
                'room_name': booking.room.name,
                'start_time': booking.start_time.strftime('%Y-%m-%d %H:%M'),
                'status': booking.status
            },
            'late_cancellation': late_cancellation,
            'warning_issued': warning_issued
        })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'success': False,
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


# ============================================
# Helper/Utility Endpoints
# ============================================

@csrf_exempt
@require_http_methods(["GET"])
def api_get_booking_rules(request):
    try:
        rule = BookingRule.objects.filter(is_active=True).first()
        
        if not rule:
            return JsonResponse({
                'success': True,
                'rules': {
                    'min_duration_hours': BOOKING_MIN_DURATION_HOURS,
                    'max_duration_hours': BOOKING_MAX_DURATION_HOURS,
                    'daily_booking_limit': 3,
                    'max_advance_days': BOOKING_MAX_ADVANCE_DAYS,
                    'min_advance_hours': BOOKING_MIN_ADVANCE_HOURS,
                    'min_cancel_hours': CANCELLATION_NOTICE_HOURS,
                    'booking_start_time': '07:00',
                    'booking_end_time': '20:30'
                }
            })
        
        return JsonResponse({
            'success': True,
            'rules': {
                'min_duration_hours': BOOKING_MIN_DURATION_HOURS,
                'max_duration_hours': rule.max_duration_hours,
                'daily_booking_limit': rule.daily_booking_limit,
                'weekly_booking_limit': rule.weekly_booking_limit,
                'max_advance_days': rule.max_advance_days,
                'min_advance_hours': rule.min_advance_hours,
                'min_cancel_hours': CANCELLATION_NOTICE_HOURS,
                'booking_start_time': rule.booking_start_time.strftime('%H:%M'),
                'booking_end_time': rule.booking_end_time.strftime('%H:%M')
            }
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)


@csrf_exempt
@require_http_methods(["GET"])
def api_search_rooms(request):
    try:
        query = request.GET.get('query', '').lower()
        
        if not query:
            return JsonResponse({
                'success': False,
                'error': 'query parameter is required'
            }, status=400)
        
        # Simple keyword-based search
        rooms = Room.objects.filter(is_available=True)
        
        # Search in name, room_number, description, equipment
        rooms = rooms.filter(
            Q(name__icontains=query) |
            Q(room_number__icontains=query) |
            Q(description__icontains=query) |
            Q(equipment__icontains=query) |
            Q(room_type__icontains=query)
        )
        
        # Serialize results
        rooms_data = []
        for room in rooms[:10]:  # Limit to top 10 results
            rooms_data.append({
                'id': room.id,
                'name': room.name,
                'room_number': room.room_number,
                'room_type': room.room_type,
                'capacity': room.capacity,
                'description': room.description,
                'equipment': room.equipment
            })
        
        return JsonResponse({
            'success': True,
            'query': query,
            'count': len(rooms_data),
            'rooms': rooms_data
        })
    
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
