from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings

from django.core.cache import cache
import uuid
import json
import logging
import re

# Using local Ollama model (gemma3:1b) via Semantic Kernel
# No API models required - fully local and private
from ai.booking_automation import BookingAutomation
from booking.models import Room, Booking, BookingRule
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

# Booking automation instance
booking_automation = BookingAutomation(Room, Booking, BookingRule)


def _get_session_payload(session_id: str) -> dict:
    """Return owner-bound session payload with backward compatibility."""
    try:
        payload = cache.get(f'chat_session:{session_id}', {})
        if not isinstance(payload, dict):
            return {'owner_user_id': None, 'context': {}}

        # Backward compatibility for legacy payloads that stored context directly.
        if 'context' not in payload:
            return {'owner_user_id': None, 'context': payload}

        context = payload.get('context')
        if not isinstance(context, dict):
            context = {}

        return {
            'owner_user_id': payload.get('owner_user_id'),
            'context': context,
        }
    except Exception:
        return {'owner_user_id': None, 'context': {}}


def _get_session_context(session_id: str) -> dict:
    return _get_session_payload(session_id).get('context', {})


def _save_session_context(session_id: str, ctx: dict, owner_user_id: int = None):
    try:
        payload = _get_session_payload(session_id)
        existing_owner = payload.get('owner_user_id')
        resolved_owner = existing_owner if existing_owner is not None else owner_user_id
        cache.set(
            f'chat_session:{session_id}',
            {'owner_user_id': resolved_owner, 'context': ctx},
            timeout=60 * 60 * 24,
        )
    except Exception:
        pass


def _clear_session_context(session_id: str, owner_user_id: int = None) -> bool:
    try:
        if owner_user_id is not None:
            payload = _get_session_payload(session_id)
            existing_owner = payload.get('owner_user_id')
            if existing_owner is not None and existing_owner != owner_user_id:
                return False
        cache.delete(f'chat_session:{session_id}')
        return True
    except Exception:
        return False


async def _ai_parse_structured(ai_reply):
    """Parse AI reply to extract structured JSON data."""
    if isinstance(ai_reply, dict):
        return ai_reply
    if not isinstance(ai_reply, str):
        return None
    try:
        return json.loads(ai_reply)
    except Exception:
        # Attempt to extract JSON substring
        m = re.search(r'\{.*\}', ai_reply, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


@csrf_exempt
async def _chat_endpoint_async(request):
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    try:
        body = json.loads(request.body.decode('utf-8'))
        user_message = body.get('message', '').strip()
        session_id = body.get('session_id') or str(uuid.uuid4())
        
        # Get authenticated user info (async-safe)
        user_info = None
        try:
            # Use sync_to_async to safely check auth status
            def get_user_info_sync():
                if not hasattr(request, 'user'):
                    return None
                
                user = request.user
                if not user.is_authenticated:
                    return None
                
                return {
                    'id': user.id,
                    'email': user.email,
                    'full_name': user.get_full_name() or f"{user.first_name} {user.last_name}".strip() or user.username,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username,
                    'student_id': getattr(user, 'student_id', 'N/A'),
                    'department': getattr(user, 'department', 'N/A'),
                    'faculty': getattr(user, 'faculty', 'N/A'),
                    'phone': getattr(user, 'phone_number', 'N/A'),
                }
            
            user_info = await sync_to_async(get_user_info_sync, thread_sensitive=True)()
        except Exception as e:
            logger.warning(f"Failed to get user info: {e}")
            user_info = None

        # Require authenticated user for chat operations.
        if not user_info:
            return JsonResponse({'error': 'Authentication required.'}, status=403)

        user_id = user_info['id']
        user_email = user_info['email']

        # Verify chat session ownership before using cached context.
        session_payload = _get_session_payload(session_id)
        owner_user_id = session_payload.get('owner_user_id')
        if owner_user_id is not None and owner_user_id != user_id:
            return JsonResponse({'error': 'Forbidden: session ownership mismatch.'}, status=403)
        if owner_user_id is None:
            if session_payload.get('context'):
                return JsonResponse({'error': 'Forbidden: unbound legacy session. Start a new session.'}, status=403)
            _save_session_context(session_id, session_payload.get('context', {}), owner_user_id=user_id)

        # Handle inline slot updates
        update_slots = body.get('update_slots')
        if isinstance(update_slots, dict) and update_slots:
            session_ctx = session_payload.get('context', {})
            session_ctx.update({k: v for k, v in update_slots.items() if v})
            _save_session_context(session_id, session_ctx, owner_user_id=user_id)
            
            # Return confirmation message
            structured = {
                'reply_text': 'Information updated. How can I help you with booking?',
                'reply_html': None,
                'actions': [],
                'slots': {k: session_ctx.get(k) for k in ('date', 'start_time', 'end_time', 'capacity', 'room_number', 'building', 'purpose')},
                'slot_confidences': {k: 1.0 for k in ('date', 'start_time', 'end_time', 'capacity', 'room_number', 'building', 'purpose')},
                'session_id': session_id,
                'kernel': 'local'
            }
            result = JsonResponse(structured)
            result['Access-Control-Allow-Origin'] = '*'
            return result

        # If message is empty, return a friendly prompt
        if not user_message:
            return JsonResponse({
                'reply_text': 'How can I help you with room booking?',
                'reply_html': None,
                'actions': [],
                'slots': {},
                'slot_confidences': {},
                'session_id': session_id,
                'kernel': 'local'
            })

        # Check if local Ollama is running (optional check)
        # Ollama connection will be tested when agent makes the call
        # If Ollama is not running, the error will be caught in the main try/except

        try:
            # Use Semantic Kernel agent
            from chatbot.apps import get_chat_agent
            agent = get_chat_agent()
            
            if agent is None:
                return JsonResponse({'error': 'agent_not_initialized', 'reply': 'Chat agent is not initialized.'}, status=503)
            
            # Call agent's chat method with user info - now returns dict
            ai_reply = await agent.chat_async(
                user_message,
                user_email=user_email,
                user_id=user_id,
                session_id=session_id,
                user_info=user_info,
            )
            
            # ai_reply is already a dict from the updated agent
            if isinstance(ai_reply, dict):
                intent = ai_reply.get('intent', 'unknown')
                slots = ai_reply.get('slots', {})
                reply_text = ai_reply.get('reply_text', '') or ai_reply.get('message', '')
                actions = ai_reply.get('actions', [])
                
                # Log the AI response for debugging
                logger.info(f"AI Reply - intent: {intent}, reply_text: {reply_text[:100] if reply_text else 'empty'}")
                
                # If no reply text, provide a default response
                if not reply_text or reply_text.strip() == '':
                    reply_text = "I'm here to help! You can ask me questions or request room bookings."

                # Merge slots into session
                if slots:
                    session_ctx = _get_session_context(session_id)
                    session_ctx.update({k: v for k, v in slots.items() if v})
                    session_ctx['last_intent'] = intent
                    _save_session_context(session_id, session_ctx, owner_user_id=user_id)

                # If booking intent and full info, prepare preview
                if intent and intent.lower() in ('book_room', 'booking', 'reserve'):
                    if slots.get('date') and slots.get('start_time') and slots.get('end_time'):
                        criteria = {
                            'date': slots.get('date'),
                            'start_time': slots.get('start_time'),
                            'end_time': slots.get('end_time'),
                            'capacity': slots.get('capacity', 1),
                            'building': slots.get('building'),
                            'purpose': slots.get('purpose', 'meeting'),
                            'raw_message': user_message,
                        }

                        rooms = await sync_to_async(booking_automation.find_best_rooms, thread_sensitive=False)(criteria, limit=1)
                        if rooms:
                            best = rooms[0]
                            room = best['room']
                            try:
                                cache.set(f'booking_preview:{session_id}', {
                                    'owner_user_id': user_id,
                                    'criteria': criteria, 
                                    'best_room_id': getattr(room, 'id', None)
                                }, timeout=15 * 60)
                            except Exception:
                                pass

                            confirm_html = (
                                f"✅ <strong>Perfect! I found a room for you:</strong><br><br>"
                                f"<div style='background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%); padding: 15px; border-radius: 10px; margin: 10px 0;'>"
                                f"<strong style='color: #0369a1; font-size: 16px;'>{room.name}</strong><br>"
                                f"<span style='color: #075985;'>Room: {getattr(room, 'room_number', '')}</span><br>"
                                f"<span style='color: #075985;'>📅 Date: {criteria['date']}</span><br>"
                                f"<span style='color: #075985;'>🕒 Time: {criteria['start_time']} - {criteria['end_time']}</span><br>"
                                f"<span style='color: #075985;'>👥 Capacity: {criteria.get('capacity', 1)} people</span>"
                                f"</div>"
                                f"<div style='margin-top: 15px; padding: 10px; background: #fef3c7; border-radius: 8px; border-left: 4px solid #f59e0b;'>"
                                f"<strong style='color: #92400e;'>Ready to confirm?</strong><br>"
                                f"<span style='color: #78350f; font-size: 13px;'>Click the button below to complete your booking</span>"
                                f"</div>"
                                "<div style=\"margin-top:15px; text-align: center;\">"
                                "<button class=\"inline-quick-action\" data-action=\"confirm_booking\" type=\"button\" "
                                "style=\"padding:12px 30px;border-radius:10px;border:none;background:linear-gradient(135deg, #10b981 0%, #059669 100%);color:white;cursor:pointer;font-weight:600;font-size:15px;transition:all 0.3s;box-shadow: 0 4px 6px rgba(16, 185, 129, 0.3);\">"
                                "✓ Confirm Booking</button>"
                                "</div>"
                            )

                            structured = {
                                'reply_text': strip_tags(confirm_html),
                                'reply_html': confirm_html,
                                'actions': [{'type': 'confirm_booking', 'label': 'Confirm booking'}],
                                'slots': slots,
                                'slot_confidences': {k: 1.0 for k in slots.keys()},
                                'session_id': session_id,
                                'kernel': 'local'
                            }
                            result = JsonResponse(structured)
                            result['Access-Control-Allow-Origin'] = '*'
                            return result
                        else:
                            # No rooms available
                            reply_text = "I couldn't find any available rooms for that time. Please try a different date or time."

                # Return standard response
                structured = {
                    'reply_text': strip_tags(reply_text),
                    'reply_html': ai_reply.get('reply_html'),
                    'actions': actions,
                    'slots': slots,
                    'slot_confidences': {k: 1.0 for k in slots.keys()},
                    'session_id': session_id,
                    'kernel': 'local'
                }
                result = JsonResponse(structured)
                result['Access-Control-Allow-Origin'] = '*'
                return result
            
            # Fallback: treat AI output as plain text
            result = JsonResponse({
                'reply_text': strip_tags(str(ai_reply)), 
                'reply_html': None, 
                'actions': [], 
                'slots': {}, 
                'slot_confidences': {}, 
                'session_id': session_id, 
                'kernel': 'local'
            })
            result['Access-Control-Allow-Origin'] = '*'
            return result

       
        
        except Exception as e:
            logger.exception(f'Error in chat endpoint: {e}')
            structured = {
                'reply_text': 'AI service is temporarily unavailable. Please try again later.',
                'reply_html': None,
                'actions': [],
                'slots': {},
                'slot_confidences': {},
                'session_id': session_id,
                'kernel': 'local',
                'error': 'ai_error',
            }
            result = JsonResponse(structured, status=200)
            result['Access-Control-Allow-Origin'] = '*'
            return result

    except json.JSONDecodeError:
        return JsonResponse({'error': 'Invalid JSON in request body', 'reply': "Sorry, I couldn't understand that request."}, status=400)
    except Exception as e:
        logger.exception(f'Error in chat endpoint: {e}')
        return JsonResponse({'error': f'Internal error: {str(e)}', 'reply': 'Sorry, something went wrong. Please try again.'}, status=500)


@csrf_exempt
async def _confirm_booking_async(request):
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    session_id = body.get('session_id') or ''

    if not session_id:
        return JsonResponse({'error': 'session_id required'}, status=400)

    preview = cache.get(f'booking_preview:{session_id}')
    if not preview:
        return JsonResponse({'reply': 'No pending booking found to confirm.'}, status=400)

    if not isinstance(preview, dict):
        return JsonResponse({'reply': 'Invalid booking preview.'}, status=400)

    owner_user_id = preview.get('owner_user_id')

    criteria = preview.get('criteria', {})

    # Require authenticated request.user for booking confirmation.
    try:
        def get_request_user():
            if not hasattr(request, 'user'):
                return None
            if not request.user.is_authenticated:
                return None
            return request.user

        user = await sync_to_async(get_request_user, thread_sensitive=True)()
    except Exception as e:
        logger.warning(f"Failed to get request user: {e}")
        user = None

    if not user or not getattr(user, 'is_authenticated', False):
        return JsonResponse({'reply': 'Please sign in to confirm booking.'}, status=403)

    if owner_user_id is None:
        return JsonResponse({'error': 'Forbidden: unbound booking preview. Please regenerate preview.'}, status=403)

    if owner_user_id != user.id:
        return JsonResponse({'error': 'Forbidden: booking preview ownership mismatch.'}, status=403)

    result = await sync_to_async(booking_automation.auto_book, thread_sensitive=False)(user, criteria)

    try:
        cache.delete(f'booking_preview:{session_id}')
    except Exception:
        pass

    reply_text = result.get('user_message') if isinstance(result, dict) else str(result)
    return JsonResponse({'reply': reply_text, 'result': result, 'session_id': session_id})

# Sync wrapper for compatibility
@csrf_exempt
def confirm_booking(request):
    """Sync wrapper for the async confirm_booking endpoint."""
    return async_to_sync(_confirm_booking_async)(request)


@require_http_methods(['GET'])
def health_check(request):
    from .apps import get_chat_agent
    from django.conf import settings
    agent = get_chat_agent()
    model_name = getattr(settings, 'OLLAMA_MODEL', 'gemma3:1b')
    status = {
        'status': 'healthy' if agent else 'degraded',
        'agent_initialized': agent is not None,
        'service': 'Django Chatbot (Local Ollama + Semantic Kernel)',
        'model': model_name
    }
    return JsonResponse(status)


@csrf_exempt
@require_http_methods(['POST'])
def clear_session(request):
    try:
        body = json.loads(request.body.decode('utf-8'))
        session_id = body.get('session_id', '')
        if not session_id:
            return JsonResponse({'success': False, 'message': 'session_id required'}, status=400)

        if not getattr(request, 'user', None) or not request.user.is_authenticated:
            return JsonResponse({'success': False, 'message': 'Authentication required'}, status=403)

        if not _clear_session_context(session_id, owner_user_id=request.user.id):
            return JsonResponse({'success': False, 'message': 'Forbidden: session ownership mismatch'}, status=403)

        from .apps import get_chat_agent
        agent = get_chat_agent()
        if agent is not None and hasattr(agent, 'clear_chat_history'):
            try:
                agent.clear_chat_history(session_id)
            except Exception:
                pass
        return JsonResponse({'success': True, 'message': 'Session cleared'})
    except Exception as e:
        logger.exception(f'Error clearing session: {e}')
        return JsonResponse({'error': str(e)}, status=500)


# Rule-based processing removed — Deepseek is the only supported path.

async def _handle_booking_intent(request, intent_data: dict, user_email: str, session_id: str) -> str:
    """
    Handle booking intent with intelligent automation
    """
    # Get user (use sync_to_async when accessing ORM or request.user in async context)
    user = None
    try:
        is_auth = await sync_to_async(lambda: getattr(request, 'user', None).is_authenticated if getattr(request, 'user', None) else False)()
    except Exception:
        is_auth = False

    if is_auth:
        # request.user is available and authenticated
        user = request.user
    
    if not user or not user.is_authenticated:
        return ("I'd love to help you book a room!\n\n"
                "However, you need to be logged in to make a booking.\n\n"
                "Please sign in and try again.")
    
    # Check if we have enough info to auto-book
    has_date = intent_data.get('date') is not None
    has_time = intent_data.get('start_time') is not None
    has_end = intent_data.get('end_time') is not None
    
    if has_date and has_time and has_end:
        # Prepare a booking preview and ask user to confirm instead of auto-booking immediately
        criteria = {
            'date': intent_data.get('date'),
            'start_time': intent_data.get('start_time'),
            'end_time': intent_data.get('end_time'),
            'capacity': intent_data.get('capacity'),
            'purpose': intent_data.get('purpose'),
            'raw_message': intent_data.get('raw_message', '')
        }

        # Find best matching room for preview
        rooms = await sync_to_async(booking_automation.find_best_rooms, thread_sensitive=False)(criteria, limit=1)
        if not rooms:
            return "I couldn't find any available rooms for that time. Try a different time or reduce capacity."

        best = rooms[0]
        room = best['room']

        # Save preview to cache so confirmation endpoint can complete the booking
        try:
            owner_user_id = await sync_to_async(lambda: request.user.id if hasattr(request, 'user') and request.user.is_authenticated else None, thread_sensitive=True)()
            cache.set(f'booking_preview:{session_id}', {
                'owner_user_id': owner_user_id,
                'criteria': criteria,
                'best_room_id': getattr(room, 'id', None)
            }, timeout=15 * 60)  # 15 minutes
        except Exception:
            pass

        # Return a friendly confirmation prompt with an inline confirm button
        confirm_html = (
            f"I found a room that matches your request:<br><br>"
            f"<strong>{room.name} ({getattr(room, 'room_number', '')})</strong><br>"
            f"Date: {criteria['date']}<br>"
            f"Time: {criteria['start_time']} - {criteria['end_time']}<br>"
            f"Capacity: {criteria.get('capacity') or 'N/A'} people<br><br>"
            "<div style=\"margin-top:12px;\">"
            "<button class=\"inline-quick-action\" data-action=\"confirm_booking\" type=\"button\" "
            "style=\"padding:10px 20px;border-radius:8px;border:none;background:linear-gradient(135deg, #10b981 0%, #059669 100%);color:white;cursor:pointer;font-weight:600;font-size:14px;transition:all 0.2s;\">"
            "✓ Confirm Booking</button>"
            "</div>"
        )

        return confirm_html
    else:
        # Generate helpful response about missing information
        missing_fields = []
        if not has_date:
            missing_fields.append('date')
        if not has_time:
            missing_fields.append('start time')
        if not has_end:
            missing_fields.append('end time')
        
        return f"To book a room, I need: {', '.join(missing_fields)}. Could you provide that information?"


async def _handle_find_rooms_intent(request, intent_data: dict) -> str:
    """
    Handle find available rooms intent
    """
    criteria = {
        'date': intent_data.get('date'),
        'start_time': intent_data.get('start_time'),
        'end_time': intent_data.get('end_time'),
        'capacity': intent_data.get('capacity'),
        'building': intent_data.get('building'),
        'purpose': intent_data.get('purpose')
    }
    
    # Find best matching rooms (run ORM in thread)
    rooms = await sync_to_async(booking_automation.find_best_rooms, thread_sensitive=False)(criteria, limit=5)
    
    if not rooms:
        return (
            "I couldn't find any available rooms matching your criteria. 😕\n\n"
            "**Try:**\n"
            "• Adjusting the date or time\n"
            "• Reducing capacity requirements\n"
            "• Checking other buildings\n\n"
            "Or browse all rooms in the booking page!"
        )
    
    response = f"**Found {len(rooms)} available room(s)!** 🎯\n\n"
    
    for i, room_data in enumerate(rooms[:3], 1):
        room = room_data['room']
        features = room_data.get('features', [])
        
        response += f"**{i}. {room.name} ({room.room_number})**\n"
        response += f"   • Capacity: {room.capacity} people\n"
        
        if room.building_name:
            response += f"   • Building: {room.building_name}\n"
        
        if features:
            response += f"   • Features: {', '.join(features)}\n"
        
        response += "\n"
    
    if len(rooms) > 3:
        response += f"...and {len(rooms) - 3} more room(s)\n\n"
    
    response += "Would you like to book one of these rooms? Just let me know which one!"
    
    return response


async def _handle_room_info(room_number: str) -> str:
    """
    Get information about a specific room
    """
    try:
        # Use sync_to_async for ORM query
        room = await sync_to_async(lambda: Room.objects.filter(room_number__iexact=room_number).first(), thread_sensitive=False)()
        
        if not room:
            return f"Sorry, I couldn't find Room {room_number}. 🤔\n\nPlease check the room number and try again."
        
        response = f"**{room.name} ({room.room_number})** 🏢\n\n"
        response += f"**Capacity:** {room.capacity} people\n"
        
        if room.building_name:
            response += f"**Building:** {room.building_name}\n"
        
        if hasattr(room, 'room_type') and room.room_type:
            response += f"**Type:** {room.room_type.title()}\n"
        
        response += f"**Status:** {'Available ✅' if room.is_available else 'Unavailable ❌'}\n"
        
        # Add features if available
        automation = BookingAutomation(Room, Booking)
        features = automation._get_room_features(room)
        
        if features:
            response += f"\n**Features:**\n"
            for feature in features:
                response += f"• {feature}\n"
        
        if room.is_available:
            response += "\n💡 Ready to book this room? Just tell me the date and time!"
        
        return response
        
    except Exception as e:
        logger.error(f"Error getting room info: {e}")
        return f"Sorry, I had trouble getting information for Room {room_number}."


# Sync wrapper for compatibility with sync servers (runserver)
@csrf_exempt
def chat_endpoint(request):
    """Sync wrapper for the async chat endpoint."""
    return async_to_sync(_chat_endpoint_async)(request)


def chatbot_index(request):
    """Render the standalone chatbot test page."""
    from datetime import datetime
    
    # Get system statistics
    total_rooms = Room.objects.count()
    available_rooms = Room.objects.filter(is_available=True).count()
    total_bookings = Booking.objects.count()
    
    context = {
        'total_rooms': total_rooms,
        'available_rooms': available_rooms,
        'total_bookings': total_bookings,
        'page_title': 'Room Booking Chatbot',
    }
    
    return render(request, 'chatbot/index.html', context)
