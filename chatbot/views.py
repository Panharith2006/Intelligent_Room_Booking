from django.http import JsonResponse
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings

from django.core.cache import cache
import uuid
import json
import logging
import re

from ai.deepseek_adapter import call_deepseek_async, call_deepseek, get_deepseek_metrics, DeepseekError
from ai.booking_automation import BookingAutomation
from booking.models import Room, Booking, BookingRule
from django.utils.html import strip_tags

logger = logging.getLogger(__name__)

# Booking automation instance
booking_automation = BookingAutomation(Room, Booking, BookingRule)


def _get_session_context(session_id: str) -> dict:
    try:
        ctx = cache.get(f'chat_session:{session_id}', {})
        return ctx if isinstance(ctx, dict) else {}
    except Exception:
        return {}


def _save_session_context(session_id: str, ctx: dict):
    try:
        cache.set(f'chat_session:{session_id}', ctx, timeout=60 * 60 * 24)
    except Exception:
        pass


def _clear_session_context(session_id: str):
    try:
        cache.delete(f'chat_session:{session_id}')
    except Exception:
        pass


async def _deepseek_parse_structured(ai_reply):
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


async def _deepseek_generate_reply(intent_data: dict, session_ctx: dict, user_message: str, session_id: str = '') -> str:
    deepseek_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
    deepseek_base = getattr(settings, 'DEEPSEEK_BASE_URL', None)
    if not deepseek_key or not deepseek_base:
        return "I'm here to help — tell me what you'd like to do (find rooms, book, or view bookings)."

    prompt = (
        "You are a helpful assistant for university room bookings. Given the extracted intent and slots and the current session context, produce a short friendly reply suitable to show to the user. Respond in plain text or JSON with key 'reply_text'.\n\n"
        f"Intent data: {json.dumps(intent_data)}\nSession context: {json.dumps(session_ctx)}\nOriginal message: {user_message}"
    )

    resp = await call_deepseek_async(prompt, api_key=deepseek_key, base_url=deepseek_base, session_id=session_id)
    parsed = await _deepseek_parse_structured(resp)
    if isinstance(parsed, dict):
        return parsed.get('reply_text') or parsed.get('text') or str(parsed)
    return str(resp)


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
        user_email = body.get('email', '')
        session_id = body.get('session_id') or str(uuid.uuid4())

        if not user_message:
            return JsonResponse({'error': 'Message is required', 'reply': 'Please provide a message.'}, status=400)

        # Handle inline slot updates
        update_slots = body.get('update_slots')
        if isinstance(update_slots, dict) and update_slots:
            session_ctx = _get_session_context(session_id)
            session_ctx.update({k: v for k, v in update_slots.items() if v})
            _save_session_context(session_id, session_ctx)
            intent = session_ctx.get('last_intent', 'book_room')
            intent_data = {'intent': intent}
            for slot in ('date', 'start_time', 'end_time', 'duration', 'capacity', 'room_number', 'room_name', 'building', 'purpose'):
                if session_ctx.get(slot):
                    intent_data[slot] = session_ctx.get(slot)

            followup = await _deepseek_generate_reply(intent_data, session_ctx, user_message, session_id)
            structured = {
                'reply_text': strip_tags(followup),
                'reply_html': None,
                'actions': [],
                'slots': {k: session_ctx.get(k) for k in ('date', 'start_time', 'end_time', 'capacity', 'room_number', 'building', 'purpose')},
                'slot_confidences': {k: 1.0 for k in ('date', 'start_time', 'end_time', 'capacity', 'room_number', 'building', 'purpose')},
                'session_id': session_id,
                'kernel': 'deepseek'
            }
            result = JsonResponse(structured)
            result['Access-Control-Allow-Origin'] = '*'
            return result

        # Check AI providers in priority order: Groq (free) → HuggingFace → Deepseek
        groq_key = getattr(settings, 'GROQ_API_KEY', None)
        groq_model = getattr(settings, 'GROQ_MODEL', None)
        
        hf_key = getattr(settings, 'HF_API_KEY', None)
        hf_model = getattr(settings, 'HF_MODEL', None)
        
        deepseek_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
        deepseek_base = getattr(settings, 'DEEPSEEK_BASE_URL', None)
        
        if not groq_key and not hf_key and (not deepseek_key or not deepseek_base):
            return JsonResponse({'error': 'ai_not_configured', 'reply': 'AI service is not configured.'}, status=503)

        # Prepare prompt for AI assistant
        ai_prompt = (
            "You are a room-booking assistant for a university. When possible, respond with a JSON object containing keys: intent (book_room, find_available, my_bookings, room_info, help, affirmative, negative), slots (object with date,start_time,end_time,duration,capacity,room_number,building,purpose), reply_text (short human reply), actions (optional array). If you cannot produce JSON, return plain helpful text.\n\n"
            f"User message: {user_message}"
        )

        try:
            # Use Groq if configured (preferred, free and fast)
            if groq_key:
                from ai.groq_adapter import call_groq_async, GroqError
                try:
                    ai_reply = await call_groq_async(ai_prompt, api_key=groq_key, model=groq_model, session_id=session_id)
                except GroqError as e:
                    logger.error(f"Groq error: {e}")
                    return JsonResponse({'error': 'ai_error', 'reply': f'AI service error: {str(e)}'}, status=503)
            # Fallback to Hugging Face if configured
            elif hf_key:
                from ai.hf_adapter import call_huggingface_async, HuggingFaceError
                try:
                    ai_reply = await call_huggingface_async(ai_prompt, api_key=hf_key, model=hf_model, session_id=session_id)
                except HuggingFaceError as e:
                    logger.error(f"HuggingFace error: {e}")
                    return JsonResponse({'error': 'ai_error', 'reply': f'AI service error: {str(e)}'}, status=503)
            # Final fallback to Deepseek
            else:
                ai_reply = await call_deepseek_async(ai_prompt, api_key=deepseek_key, base_url=deepseek_base, session_id=session_id)
            parsed = await _deepseek_parse_structured(ai_reply)

            if isinstance(parsed, dict):
                intent = parsed.get('intent') or parsed.get('intent_name') or 'unknown'
                slots = parsed.get('slots', {}) or {}
                reply_text = parsed.get('reply_text') or parsed.get('text') or parsed.get('message') or ''
                actions = parsed.get('actions', []) or []

                # Merge slots into session
                if slots:
                    session_ctx = _get_session_context(session_id)
                    session_ctx.update({k: v for k, v in slots.items() if v})
                    session_ctx['last_intent'] = intent or session_ctx.get('last_intent')
                    _save_session_context(session_id, session_ctx)

                # If booking intent and full info, prepare preview
                if intent and intent.lower() in ('book_room', 'booking', 'reserve') and slots.get('date') and slots.get('start_time') and slots.get('end_time'):
                    criteria = {
                        'date': slots.get('date'),
                        'start_time': slots.get('start_time'),
                        'end_time': slots.get('end_time'),
                        'capacity': slots.get('capacity'),
                        'building': slots.get('building'),
                        'purpose': slots.get('purpose'),
                        'raw_message': user_message,
                    }

                    rooms = await sync_to_async(booking_automation.find_best_rooms, thread_sensitive=False)(criteria, limit=1)
                    if rooms:
                        best = rooms[0]
                        room = best['room']
                        try:
                            cache.set(f'booking_preview:{session_id}', {'criteria': criteria, 'best_room_id': getattr(room, 'id', None)}, timeout=15 * 60)
                        except Exception:
                            pass

                        confirm_html = (
                            f"I found a room that matches your request:\n\n"
                            f"**{room.name} ({getattr(room, 'room_number', '')})**\n"
                            f"Date: {criteria['date']}\n"
                            f"Time: {criteria['start_time']} - {criteria['end_time']}\n"
                            f"Capacity: {criteria.get('capacity') or 'N/A'} people\n\n"
                            "<div style=\"margin-top:8px;\">"
                            "<button class=\"inline-quick-action\" data-action=\"confirm_booking\" style=\"padding:8px 12px;border-radius:6px;border:1px solid #667eea;background:#667eea;color:white;cursor:pointer;\">Confirm booking</button>"
                            "</div>"
                        )

                        structured = {
                            'reply_text': strip_tags(reply_text) if reply_text else strip_tags(confirm_html),
                            'reply_html': confirm_html,
                            'actions': [{'type': 'confirm_booking', 'label': 'Confirm booking'}],
                            'slots': slots,
                            'slot_confidences': {k: 1.0 for k in slots.keys()},
                            'session_id': session_id,
                            'kernel': 'deepseek'
                        }
                        result = JsonResponse(structured)
                        result['Access-Control-Allow-Origin'] = '*'
                        return result

                structured = {
                    'reply_text': strip_tags(reply_text) if reply_text else strip_tags(parsed.get('reply', '')),
                    'reply_html': parsed.get('reply_html') if parsed.get('reply_html') else None,
                    'actions': actions,
                    'slots': slots,
                    'slot_confidences': {k: 1.0 for k in slots.keys()},
                    'session_id': session_id,
                    'kernel': 'deepseek'
                }
                result = JsonResponse(structured)
                result['Access-Control-Allow-Origin'] = '*'
                return result

            # Fallback: treat Deepseek output as plain text
            result = JsonResponse({'reply_text': strip_tags(ai_reply), 'reply_html': None, 'actions': [], 'slots': {}, 'slot_confidences': {}, 'session_id': session_id, 'kernel': 'deepseek'})
            result['Access-Control-Allow-Origin'] = '*'
            return result

        except DeepseekError as de:
            logger.exception('Deepseek call failed: %s', de)
            # Degrade gracefully: return a friendly reply object so frontend can continue
            structured = {
                'reply_text': 'AI service is temporarily unavailable. Please try again later.',
                'reply_html': None,
                'actions': [],
                'slots': {},
                'slot_confidences': {},
                'session_id': session_id,
                'kernel': 'deepseek',
                'error': 'ai_unavailable',
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
async def confirm_booking(request):
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)

    session_id = body.get('session_id') or ''
    user_email = body.get('email', '')

    if not session_id:
        return JsonResponse({'error': 'session_id required'}, status=400)

    preview = cache.get(f'booking_preview:{session_id}')
    if not preview:
        return JsonResponse({'reply': 'No pending booking found to confirm.'}, status=400)

    criteria = preview.get('criteria', {})

    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = None
    try:
        is_auth = await sync_to_async(lambda: getattr(request, 'user', None).is_authenticated if getattr(request, 'user', None) else False)()
    except Exception:
        is_auth = False

    if is_auth and getattr(request, 'user', None):
        user = request.user
    elif user_email:
        try:
            user = await sync_to_async(User.objects.get, thread_sensitive=False)(email=user_email)
        except User.DoesNotExist:
            user = None

    if not user or not getattr(user, 'is_authenticated', False):
        return JsonResponse({'reply': 'Please sign in to confirm booking.'}, status=403)

    result = await sync_to_async(booking_automation.auto_book, thread_sensitive=False)(user, criteria)

    try:
        cache.delete(f'booking_preview:{session_id}')
    except Exception:
        pass

    reply_text = result.get('user_message') if isinstance(result, dict) else str(result)
    return JsonResponse({'reply': reply_text, 'result': result, 'session_id': session_id})


@csrf_exempt
def chat_endpoint(request):
    return async_to_sync(_chat_endpoint_async)(request)


@require_http_methods(['GET'])
def health_check(request):
    from .apps import get_chat_agent
    agent = get_chat_agent()
    status = {'status': 'healthy' if agent else 'degraded', 'agent_initialized': agent is not None, 'service': 'Django Chatbot (Deepseek-only)'}
    return JsonResponse(status)


@require_http_methods(["GET"])
def debug_deepseek(request):
    """Lightweight endpoint to verify Deepseek connectivity and adapter health.

    Returns adapter metrics and a short sample reply from Deepseek without exposing the API key.
    """
    deepseek_key = getattr(settings, 'DEEPSEEK_API_KEY', None)
    deepseek_base = getattr(settings, 'DEEPSEEK_BASE_URL', None)

    if not deepseek_key or not deepseek_base:
        return JsonResponse({'ok': False, 'error': 'deepseek_not_configured'}, status=503)

    prompt = "Health check: please reply with a short 'pong' or OK message."
    start = None
    try:
        import time
        start = time.time()
        # call sync function via async helper for safety
        resp = async_to_sync(call_deepseek_async)(prompt, api_key=deepseek_key, base_url=deepseek_base, timeout=10)
        latency_ms = int((time.time() - start) * 1000)
        metrics = get_deepseek_metrics()
        return JsonResponse({'ok': True, 'sample_reply': resp if isinstance(resp, str) else str(resp), 'latency_ms': latency_ms, 'metrics': metrics})
    except DeepseekError as de:
        logger.exception(f'Deepseek debug call failed: {de}')
        return JsonResponse({'ok': False, 'error': 'deepseek_error', 'detail': str(de)}, status=502)
    except Exception as e:
        logger.exception(f'Unexpected error in debug_deepseek: {e}')
        return JsonResponse({'ok': False, 'error': 'internal_error', 'detail': str(e)}, status=500)


@csrf_exempt
@require_http_methods(['POST'])
def clear_session(request):
    try:
        body = json.loads(request.body.decode('utf-8'))
        session_id = body.get('session_id', '')
        if not session_id:
            return JsonResponse({'success': False, 'message': 'session_id required'}, status=400)
        _clear_session_context(session_id)
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


@csrf_exempt
@require_http_methods(["POST"])
async def confirm_booking(request):
    """Confirm a pending booking preview stored in cache and perform auto-booking."""
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    session_id = body.get('session_id') or ''
    user_email = body.get('email', '')

    if not session_id:
        return JsonResponse({"error": "session_id required"}, status=400)

    preview = cache.get(f'booking_preview:{session_id}')
    if not preview:
        return JsonResponse({"reply": "No pending booking found to confirm."}, status=400)

    criteria = preview.get('criteria', {})

    # Resolve user
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = None
    try:
        is_auth = await sync_to_async(lambda: getattr(request, 'user', None).is_authenticated if getattr(request, 'user', None) else False)()
    except Exception:
        is_auth = False

    if is_auth and getattr(request, 'user', None):
        user = request.user
    elif user_email:
        try:
            user = await sync_to_async(User.objects.get, thread_sensitive=False)(email=user_email)
        except User.DoesNotExist:
            user = None

    if not user or not getattr(user, 'is_authenticated', False):
        return JsonResponse({"reply": "Please sign in to confirm booking."}, status=403)

    # Perform auto-booking
    result = await sync_to_async(booking_automation.auto_book, thread_sensitive=False)(user, criteria)

    # Clear preview
    try:
        cache.delete(f'booking_preview:{session_id}')
    except Exception:
        pass

    # Return user-friendly reply
    reply_text = result.get('user_message') if isinstance(result, dict) else str(result)
    return JsonResponse({"reply": reply_text, "result": result, "session_id": session_id})


def _get_session_context(session_id: str) -> dict:
    """Retrieve session dialog context from cache (or empty dict)."""
    try:
        ctx = cache.get(f'chat_session:{session_id}', {})
        if not isinstance(ctx, dict):
            ctx = {}
        return ctx
    except Exception:
        return {}


def _save_session_context(session_id: str, ctx: dict):
    """Persist session dialog context into cache (24h TTL)."""
    try:
        cache.set(f'chat_session:{session_id}', ctx, timeout=60 * 60 * 24)
    except Exception:
        pass


def _clear_session_context(session_id: str):
    try:
        cache.delete(f'chat_session:{session_id}')
    except Exception:
        pass


# Rule-based processing removed — Deepseek is the only supported path.


async def _handle_booking_intent(request, intent_data: dict, user_email: str, session_id: str) -> str:
    """
    Handle booking intent with intelligent automation
    """
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Get user (use sync_to_async when accessing ORM or request.user in async context)
    user = None
    try:
        is_auth = await sync_to_async(lambda: getattr(request, 'user', None).is_authenticated if getattr(request, 'user', None) else False)()
    except Exception:
        is_auth = False

    if user_email and is_auth:
        # request.user is available and authenticated
        user = request.user
    elif user_email:
        try:
            user = await sync_to_async(User.objects.get, thread_sensitive=False)(email=user_email)
        except User.DoesNotExist:
            user = None
    
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
            'building': intent_data.get('building'),
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
            cache.set(f'booking_preview:{session_id}', {
                'criteria': criteria,
                'best_room_id': getattr(room, 'id', None)
            }, timeout=15 * 60)  # 15 minutes
        except Exception:
            pass

        # Return a friendly confirmation prompt with an inline confirm button
        confirm_html = (
            f"I found a room that matches your request:\n\n"
            f"**{room.name} ({getattr(room, 'room_number', '')})**\n"
            f"Date: {criteria['date']}\n"
            f"Time: {criteria['start_time']} - {criteria['end_time']}\n"
            f"Capacity: {criteria.get('capacity') or 'N/A'} people\n\n"
            "<div style=\"margin-top:8px;\">"
            "<button class=\"inline-quick-action\" data-action=\"confirm_booking\" style=\"padding:8px 12px;border-radius:6px;border:1px solid #667eea;background:#667eea;color:white;cursor:pointer;\">Confirm booking</button>"
            "</div>"
        )

        return confirm_html
    else:
        # Generate helpful response with what's missing using Deepseek
        session_ctx = _get_session_context(session_id)
        return await _deepseek_generate_reply(intent_data, session_ctx, intent_data.get('raw_message', ''), session_id)


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
    return async_to_sync(_chat_endpoint_async)(request)


@require_http_methods(["GET"])
def health_check(request):
    """Health check endpoint"""
    agent = get_chat_agent()
    
    status = {
        "status": "healthy" if agent else "degraded",
        "agent_initialized": agent is not None,
        "service": "Django Chatbot (Deepseek-only)",
        "rule_kernel": {
            "available": False,
            "detail": "removed — using Deepseek only"
        }
    }
    return JsonResponse(status)


@csrf_exempt
@require_http_methods(["POST"])
def clear_session(request):
    """Clear chat history for a session (clears local cached dialog state)."""
    try:
        body = json.loads(request.body.decode('utf-8'))
        session_id = body.get('session_id', '')
        if not session_id:
            return JsonResponse({"success": False, "message": "session_id required"}, status=400)

        # Clear our local session cache
        _clear_session_context(session_id)

        # If there is an agent with a clear_chat_history hook, call it too (best-effort)
        agent = get_chat_agent()
        if agent is not None and hasattr(agent, 'clear_chat_history'):
            try:
                agent.clear_chat_history(session_id)
            except Exception:
                pass

        return JsonResponse({"success": True, "message": "Session cleared"})
    except Exception as e:
        logger.exception(f"Error clearing session: {e}")
        return JsonResponse({"error": str(e)}, status=500)
