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


# ============================================
# Room API Endpoints
# ============================================

@csrf_exempt
@require_http_methods(["GET"])
def api_list_rooms(request):
    """
    List all available rooms with optional filters
    GET /api/rooms/?room_type=lab&capacity_min=10&capacity_max=50
    """
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
    """
    Check room availability for a specific date and time range
    GET /api/rooms/availability/?room_id=1&date=2025-11-20&start_time=09:00&end_time=11:00
    """
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
    """
    Create a new booking via AI chatbot
    POST /api/bookings/create/
    Body: {
        "user_email": "student@example.com",
        "room_id": 1,
        "date": "2025-11-20",
        "start_time": "09:00",
        "end_time": "11:00",
        "purpose": "Team meeting",
        "attendees": 5,
        "notes": "Optional notes"
    }
    """
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
        if duration < timedelta(minutes=30):
            return JsonResponse({
                'success': False,
                'error': 'Minimum booking duration is 30 minutes'
            }, status=400)
        
        if duration > timedelta(hours=8):
            return JsonResponse({
                'success': False,
                'error': 'Maximum booking duration is 8 hours'
            }, status=400)
        
        # Check advance booking limits
        advance_days = (start_datetime - now).days
        if advance_days > 14:
            return JsonResponse({
                'success': False,
                'error': 'Cannot book more than 14 days in advance'
            }, status=400)
        
        advance_hours = (start_datetime - now).total_seconds() / 3600
        if advance_hours < 1:
            return JsonResponse({
                'success': False,
                'error': 'Must book at least 1 hour in advance'
            }, status=400)
        
        # Check capacity
        if attendees > room.capacity:
            return JsonResponse({
                'success': False,
                'error': f'Number of attendees ({attendees}) exceeds room capacity ({room.capacity})'
            }, status=400)
        
        # Check room availability
        if not room.is_available_at(start_datetime, end_datetime):
            return JsonResponse({
                'success': False,
                'error': 'Room is not available at the requested time. Please choose a different time slot.'
            }, status=400)
        
        # Check daily booking limit
        today_bookings = Booking.objects.filter(
            user=user,
            start_time__date=date,
            status='confirmed'
        ).count()
        
        if today_bookings >= 3:
            return JsonResponse({
                'success': False,
                'error': 'You have reached the daily booking limit (3 bookings per day)'
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
    """
    List bookings for a specific user
    GET /api/bookings/?user_email=student@example.com&status=confirmed
    """
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
    """
    Cancel a booking
    POST /api/bookings/cancel/
    Body: {
        "booking_id": 123,
        "user_email": "student@example.com"
    }
    """
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
        
        # Check cancellation time limit (2 hours before)
        time_until_booking = booking.start_time - timezone.now()
        if time_until_booking < timedelta(hours=2):
            return JsonResponse({
                'success': False,
                'error': 'Bookings can only be cancelled at least 2 hours before the start time'
            }, status=400)
        
        # Cancel the booking
        booking.status = 'cancelled'
        booking.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Booking cancelled successfully',
            'booking': {
                'id': booking.id,
                'room_name': booking.room.name,
                'start_time': booking.start_time.strftime('%Y-%m-%d %H:%M'),
                'status': booking.status
            }
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
    """
    Get current booking rules
    GET /api/rules/
    """
    try:
        rule = BookingRule.objects.filter(is_active=True).first()
        
        if not rule:
            return JsonResponse({
                'success': True,
                'rules': {
                    'max_duration_hours': 8,
                    'daily_booking_limit': 3,
                    'max_advance_days': 14,
                    'min_advance_hours': 1,
                    'min_cancel_hours': 2,
                    'booking_start_time': '07:00',
                    'booking_end_time': '20:30'
                }
            })
        
        return JsonResponse({
            'success': True,
            'rules': {
                'max_duration_hours': rule.max_duration_hours,
                'daily_booking_limit': rule.daily_booking_limit,
                'weekly_booking_limit': rule.weekly_booking_limit,
                'max_advance_days': rule.max_advance_days,
                'min_advance_hours': rule.min_advance_hours,
                'min_cancel_hours': rule.min_cancel_hours,
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
    """
    Natural language search for rooms
    GET /api/rooms/search/?query=lab+for+20+people
    """
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
