import logging
from typing import Optional
from asgiref.sync import sync_to_async

from chatbot.apps import get_chat_agent
from chatbot.services.booking_service import build_booking_criteria, find_best_rooms, auto_book

logger = logging.getLogger(__name__)


# =========================
# USER PROFILE QUERIES
# =========================
async def handle_user_profile(user):
    
    # Wrap user authentication check
    try:
        is_authenticated = await sync_to_async(lambda: user.is_authenticated if user else False)()
    except Exception as e:
        logger.warning(f"Could not check user auth: {e}")
        is_authenticated = False
    
    if not is_authenticated:
        return {
            "success": False,
            "message": "User not authenticated"
        }

    try:
        # Wrap user property access
        user_data = await sync_to_async(lambda: {
            "first_name": user.first_name or "Unknown",
            "last_name": user.last_name or "Unknown",
            "email": user.email or "N/A",
            "student_id": getattr(user, 'student_id', None) or "N/A",
            "position": getattr(user, 'position', None) or "N/A",
            "phone": getattr(user, 'phone_number', None) or "N/A",
        })()

        profile_text = (
            f"Your profile:\n"
            f"Name: {user_data['first_name']} {user_data['last_name']}\n"
            f"Email: {user_data['email']}\n"
            f"Student/Lecturer ID: {user_data['student_id']}\n"
            f"Position: {user_data['position']}\n"
            f"Phone: {user_data['phone']}"
        )

        return {
            "success": True,
            "response_text": profile_text,
            "profile_data": user_data
        }

    except Exception as e:
        logger.exception(f"Profile query failed: {e}")
        return {
            "success": False,
            "message": f"Could not retrieve profile: {str(e)}"
        }


# =========================
# USER HISTORY QUERIES
# =========================
async def handle_user_history(user):
    
    # Wrap user authentication check
    try:
        is_authenticated = await sync_to_async(lambda: user.is_authenticated if user else False)()
    except Exception as e:
        logger.warning(f"Could not check user auth: {e}")
        is_authenticated = False
    
    if not is_authenticated:
        return {
            "success": False,
            "message": "User not authenticated"
        }

    try:
        from booking.models import Booking
        from django.utils import timezone
        from datetime import timedelta

        # Get user's bookings
        all_bookings = await sync_to_async(
            lambda: list(Booking.objects.filter(user=user).order_by('-start_time'))
        )()

        now = timezone.now()
        
        # Categorize bookings
        active_bookings = [b for b in all_bookings if b.start_time > now and b.status == 'confirmed']
        completed_bookings = [b for b in all_bookings if b.start_time <= now and b.status == 'confirmed']
        cancelled_bookings = [b for b in all_bookings if b.status in ['cancelled', 'rejected']]
        pending_bookings = [b for b in all_bookings if b.status == 'pending']

        # Build history text
        history_text = (
            f"Your booking statistics:\n"
            f"Active bookings: {len(active_bookings)}\n"
            f"Completed bookings: {len(completed_bookings)}\n"
            f"Cancelled bookings: {len(cancelled_bookings)}\n"
            f"Pending approval: {len(pending_bookings)}\n"
            f"Total bookings: {len(all_bookings)}\n"
        )

        # Add upcoming bookings preview (if any)
        if active_bookings:
            history_text += "\nUpcoming bookings (next 3):\n"
            for booking in active_bookings[:3]:
                room_name = booking.room.name if booking.room else "Unknown Room"
                start = booking.start_time.strftime("%Y-%m-%d %H:%M")
                end = booking.end_time.strftime("%H:%M")
                history_text += f"  • {room_name} on {start} - {end}\n"

        return {
            "success": True,
            "response_text": history_text,
            "history_data": {
                "active_count": len(active_bookings),
                "completed_count": len(completed_bookings),
                "cancelled_count": len(cancelled_bookings),
                "total_count": len(all_bookings),
                "upcoming_bookings": [
                    {
                        "room": b.room.name,
                        "date": b.start_time.strftime("%Y-%m-%d"),
                        "time": f"{b.start_time.strftime('%H:%M')} - {b.end_time.strftime('%H:%M')}"
                    }
                    for b in active_bookings[:5]
                ]
            }
        }

    except Exception as e:
        logger.exception(f"History query failed: {e}")
        return {
            "success": False,
            "message": f"Could not retrieve booking history: {str(e)}"
        }



async def handle_find_rooms(entities: dict, user_message: str, limit: int = 3):
    agent = get_chat_agent()

    criteria = build_booking_criteria(entities, user_message)

    # If ChatAgent with room_plugin exists, prefer plugin (it uses booking_automation internally)
    try:
        if agent and hasattr(agent, 'room_plugin') and agent.room_plugin:
            plugin = agent.room_plugin
            # plugin.find_available_rooms returns a human-readable string; we prefer booking_automation for structured data
            # So call booking_automation directly if available on plugin
            if hasattr(agent, 'booking_automation') and agent.booking_automation:
                rooms = await sync_to_async(agent.booking_automation.find_best_rooms)(criteria, limit=limit)
                return rooms

    except Exception as e:
        logger.exception('Plugin find_rooms failed, falling back to booking service: %s', e)

    # Fallback: use booking service helper
    result = await find_best_rooms(agent.booking_automation if agent else None, criteria, limit=limit)
    # find_best_rooms returns either list or error dict depending on implementation
    if isinstance(result, dict) and result.get('rooms') is not None:
        return result.get('rooms')
    return result


async def handle_prepare_booking(entities: dict, user_message: str):
	"""Prepare booking preview with structured entities for frontend rendering"""
	agent = get_chat_agent()
	criteria = build_booking_criteria(entities, user_message)

	# Validate criteria first
	from chatbot.services.booking_service import is_valid_criteria
	validation = is_valid_criteria(criteria)
	
	if not validation.get("valid"):
		return {
			'criteria': criteria,
			'best_room_id': None,
			'success': False,
			'message': f"❌ {validation.get('message', 'Invalid booking criteria')}",
			'preview': None,
			'actions': []
		}

	try:
		# Try plugin preview (prepare_booking) if available
		if agent and hasattr(agent, 'room_plugin') and agent.room_plugin:
			plugin = agent.room_plugin
			# Use booking_automation to get structured room data
			if hasattr(agent, 'booking_automation') and agent.booking_automation:
				rooms = await sync_to_async(agent.booking_automation.find_best_rooms)(criteria, limit=1)
				if rooms:
					best = rooms[0]
					room = best['room']
					
					# Return structured preview (no formatted text)
					preview = {
						'room': {
							'id': room.id,
							'name': room.name,
							'room_number': room.room_number,
							'capacity': room.capacity,
							'type': room.room_type,
							'equipment': best.get('equipment', []),
							'description': room.description,
						},
						'booking': {
							'date': criteria.get('date'),
							'start_time': criteria.get('start_time'),
							'end_time': criteria.get('end_time'),
							'attendees': criteria.get('capacity'),
							'purpose': criteria.get('purpose'),
						}
					}
					
					return {
						'criteria': criteria,
						'best_room_id': room.id,
						'best_room_name': room.name,
						'best_room_number': room.room_number,
						'best_room_capacity': room.capacity,
						'equipment': best.get('equipment', []),
						'success': True,
						'message': f"✅ Found room: {room.name}",
						'preview': preview,
						'actions': [
							{
								'type': 'confirm_booking',
								'label': 'Confirm Booking',
								'style': 'primary',
								'data': {'criteria': criteria, 'room_id': room.id}
							}
						]
					}
	except Exception as e:
		logger.exception('Plugin prepare_booking failed: %s', e)

	# Fallback: use booking service
	try:
		rooms = await find_best_rooms(agent.booking_automation if agent else None, criteria, limit=1)
		if isinstance(rooms, list) and rooms:
			best = rooms[0]
			room = best.get('room') if isinstance(best, dict) else best
			
			if room:
				preview = {
					'room': {
						'id': room.id,
						'name': room.name,
						'room_number': room.room_number,
						'capacity': room.capacity,
						'type': room.room_type if hasattr(room, 'room_type') else 'Unknown',
						'equipment': best.get('equipment', []) if isinstance(best, dict) else [],
						'description': room.description if hasattr(room, 'description') else '',
					},
					'booking': {
						'date': criteria.get('date'),
						'start_time': criteria.get('start_time'),
						'end_time': criteria.get('end_time'),
						'attendees': criteria.get('capacity'),
						'purpose': criteria.get('purpose'),
					}
				}
				
				return {
					'criteria': criteria,
					'best_room_id': room.id,
					'best_room_name': room.name,
					'best_room_number': room.room_number,
					'best_room_capacity': room.capacity,
					'equipment': best.get('equipment', []) if isinstance(best, dict) else [],
					'success': True,
					'message': f"✅ Found room: {room.name}",
					'preview': preview,
					'actions': [
						{
							'type': 'confirm_booking',
							'label': 'Confirm Booking',
							'style': 'primary',
							'data': {'criteria': criteria, 'room_id': room.id}
						}
					]
				}
	except Exception as e:
		logger.exception('Fallback prepare_booking failed: %s', e)

	return {
		'criteria': criteria,
		'best_room_id': None,
		'success': False,
		'message': '❌ No rooms available for this time. Try different time slot.',
		'preview': None,
		'actions': []
	}

async def handle_confirm_booking(user, criteria: dict):
	"""Execute booking after user confirmation with full validation"""
	agent = get_chat_agent()

	# Final validation before booking
	from chatbot.services.booking_service import is_valid_criteria
	validation = is_valid_criteria(criteria)
	
	if not validation.get("valid"):
		return {
			"success": False,
			"error": validation.get("message"),
			"user_message": f"❌ Booking validation failed: {validation.get('message')}"
		}

	if not user or not user.is_authenticated:
		return {
			"success": False,
			"error": "User not authenticated",
			"user_message": "❌ User authentication failed. Please log in."
		}

	try:
		if agent and hasattr(agent, 'booking_automation') and agent.booking_automation:
			result = await sync_to_async(agent.booking_automation.auto_book)(user, criteria)
			
			# Ensure response has user_message
			if result.get("success"):
				if "user_message" not in result:
					room = result.get("room", {})
					if isinstance(room, dict):
						room_obj = room.get("room")
					else:
						room_obj = room
					
					if room_obj:
						result["user_message"] = (
							f"✅ **BOOKING CONFIRMED!**\n\n"
							f"Room: {result.get('room_name', 'Unknown')}\n"
							f"Date: {result.get('date', 'Unknown')}\n"
							f"Time: {result.get('time', 'Unknown')}\n"
							f"Booking ID: {result.get('booking_id', 'N/A')}"
						)
			
			return result
	except Exception as e:
		logger.exception('Plugin auto_book failed: %s', e)

	# Fallback
	result = await auto_book(agent.booking_automation if agent else None, user, criteria)
	return result

# =========================
# AVAILABILITY QUERIES
# =========================
async def handle_availability_query(entities: dict, user_message: str):
    """
    Find ALL available rooms matching criteria (no limit, no scoring)
    Shows all rooms that are bookable at requested time
    """
    agent = get_chat_agent()
    criteria = build_booking_criteria(entities, user_message)

    try:
        if agent and hasattr(agent, 'booking_automation') and agent.booking_automation:
            # Return ALL available rooms (return_all=True)
            rooms = await sync_to_async(agent.booking_automation.find_best_rooms)(criteria, return_all=True)
            
            if rooms:
                return {
                    "success": True,
                    "rooms": rooms,
                    "count": len(rooms),
                    "response_text": f"Found {len(rooms)} available rooms for your search."
                }
            else:
                return {
                    "success": False,
                    "rooms": [],
                    "count": 0,
                    "response_text": "No available rooms found for your criteria. Try a different time slot."
                }
    except Exception as e:
        logger.exception(f"Availability query failed: {e}")
        return {
            "success": False,
            "rooms": [],
            "error": str(e),
            "response_text": "Could not search for available rooms."
        }


# =========================
# MODIFICATION QUERIES
# =========================
async def handle_modify_booking(user, entities: dict, session_ctx: dict):
    
    if not user or not user.is_authenticated:
        return {
            "success": False,
            "message": "Please log in to modify your booking."
        }

    try:
        from booking.models import Booking
        from django.utils import timezone
        
        # Get user's most recent active booking
        latest_booking = await sync_to_async(
            lambda: Booking.objects.filter(
                user=user, 
                status='confirmed',
                start_time__gt=timezone.now()
            ).order_by('start_time').first()
        )()
        
        if not latest_booking:
            return {
                "success": False,
                "message": "You have no active bookings to modify."
            }
        
        # Build new criteria from extracted entities
        new_date = entities.get("date")
        new_start_time = entities.get("start_time")
        new_end_time = entities.get("end_time")
        
        # If no new time specified, return error
        if not (new_date and new_start_time and new_end_time):
            return {
                "success": False,
                "message": "Please specify the new date and time for your booking modification."
            }
        
        # Create session preview for confirmation
        session_ctx["modification_preview"] = {
            "booking_id": latest_booking.id,
            "old_date": latest_booking.start_time.strftime("%Y-%m-%d"),
            "old_time": f"{latest_booking.start_time.strftime('%H:%M')} - {latest_booking.end_time.strftime('%H:%M')}",
            "new_date": new_date,
            "new_time": f"{new_start_time} - {new_end_time}",
            "room": latest_booking.room.name if latest_booking.room else "Unknown"
        }
        
        return {
            "success": True,
            "message": (
                f"Modify booking for {latest_booking.room.name}: "
                f"from {session_ctx['modification_preview']['old_date']} "
                f"{session_ctx['modification_preview']['old_time']} "
                f"to {new_date} {new_start_time}-{new_end_time}?"
            ),
            "actions": [{"type": "confirm_modification", "label": "Confirm Modification"}]
        }
    
    except Exception as e:
        logger.exception(f"Modification query failed: {e}")
        return {
            "success": False,
            "message": f"Could not process modification: {str(e)}"
        }


# =========================
# CANCELLATION QUERIES
# =========================
async def handle_cancel_booking(user, session_ctx: dict):
    """
    Handle 'cancellation' intent - cancel an existing booking.
    
    User says: "Cancel my booking for tomorrow"
    Result: Booking cancelled or preview for confirmation
    """
    if not user or not user.is_authenticated:
        return {
            "success": False,
            "message": "Please log in to cancel your booking."
        }

    try:
        from booking.models import Booking
        from django.utils import timezone
        
        # Get user's most recent active booking
        latest_booking = await sync_to_async(
            lambda: Booking.objects.filter(
                user=user,
                status='confirmed',
                start_time__gt=timezone.now()
            ).order_by('start_time').first()
        )()
        
        if not latest_booking:
            return {
                "success": False,
                "message": "You have no active bookings to cancel."
            }
        
        # Store cancellation preview in session for confirmation
        session_ctx["cancellation_preview"] = {
            "booking_id": latest_booking.id,
            "room": latest_booking.room.name if latest_booking.room else "Unknown",
            "date": latest_booking.start_time.strftime("%Y-%m-%d"),
            "time": f"{latest_booking.start_time.strftime('%H:%M')} - {latest_booking.end_time.strftime('%H:%M')}"
        }
        
        return {
            "success": True,
            "message": (
                f"Cancel booking for {session_ctx['cancellation_preview']['room']} "
                f"on {session_ctx['cancellation_preview']['date']} "
                f"{session_ctx['cancellation_preview']['time']}?"
            ),
            "actions": [{"type": "confirm_cancellation", "label": "Confirm Cancellation"}]
        }
    
    except Exception as e:
        logger.exception(f"Cancellation query failed: {e}")
        return {
            "success": False,
            "message": f"Could not process cancellation: {str(e)}"
        }
