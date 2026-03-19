"""
Integrated Chatbot Views with Advanced RAG
Professional implementation combining AgenticRAG with booking automation
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
from asgiref.sync import async_to_sync, sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.utils.html import strip_tags

import uuid
import json
import logging

# Advanced RAG Components
from ai.agentic_rag import AgenticRAG
from ai.vector_store import VectorStore
from ai.booking_automation import BookingAutomation
from booking.models import Room, Booking, BookingRule

logger = logging.getLogger(__name__)

# Initialize components (done once in apps.py, accessed here)
_agentic_rag = None
_booking_automation = None


def set_rag_system(rag, booking_auto):
    """Set global RAG system instances."""
    global _agentic_rag, _booking_automation
    _agentic_rag = rag
    _booking_automation = booking_auto


def get_rag_system():
    """Get RAG system instances."""
    return _agentic_rag, _booking_automation


# Session management
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


@csrf_exempt
async def chat_endpoint(request):
    """
    Main chat endpoint using Advanced RAG.
    
    Process Flow:
    1. Query Processing (intent, entities)
    2. Hybrid Retrieval (semantic + keyword + structured)
    3. Re-ranking (cross-encoder)
    4. Self-RAG (reflection & verification)
    5. Response Generation
    6. Booking Integration (if booking intent)
    """
    if request.method == 'OPTIONS':
        response = JsonResponse({'status': 'ok'})
        response['Access-Control-Allow-Origin'] = '*'
        response['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
        response['Access-Control-Allow-Headers'] = 'Content-Type'
        return response

    try:
        # Parse request
        body = json.loads(request.body.decode('utf-8'))
        user_message = body.get('message', '').strip()
        user_email = body.get('email', '')
        session_id = body.get('session_id') or str(uuid.uuid4())
        
        # Get session context
        session_ctx = _get_session_context(session_id)
        
        # Get authenticated user info
        user_info = await _get_user_info_async(request)
        if user_info:
            user_email = user_info['email']
        
        # Handle inline slot updates
        update_slots = body.get('update_slots')
        if isinstance(update_slots, dict) and update_slots:
            session_ctx.update({k: v for k, v in update_slots.items() if v})
            _save_session_context(session_id, session_ctx)
            
            return JsonResponse({
                'reply_text': 'Information updated. How can I help you with booking?',
                'reply_html': None,
                'actions': [],
                'slots': session_ctx,
                'session_id': session_id,
                'rag_mode': 'advanced'
            })
        
        # Empty message handling
        if not user_message:
            return JsonResponse({
                'reply_text': 'How can I help you with room booking?',
                'reply_html': None,
                'actions': [],
                'slots': session_ctx,
                'session_id': session_id,
                'rag_mode': 'advanced'
            })
        
        # Get RAG system
        rag_system, booking_automation = get_rag_system()
        
        if not rag_system:
            # Fallback to basic response
            logger.error("RAG system not initialized")
            return JsonResponse({
                'error': 'rag_not_initialized',
                'reply_text': 'Chat system is initializing. Please try again in a moment.',
                'session_id': session_id
            }, status=503)
        
        try:
            # ===== ADVANCED RAG PROCESSING =====
            logger.info(f"Processing with Advanced RAG: {user_message[:100]}")
            
            rag_result = rag_system.process_query(
                query=user_message,
                context=session_ctx,
                user_info=user_info,
                top_k=5,
                use_self_rag=True  # Enable self-reflection
            )
            
            # Extract results
            response_text = rag_result['response_text']
            entities = rag_result['entities']
            intent = rag_result['intent']
            retrieved_docs = rag_result['retrieved_docs']
            reflection_scores = rag_result.get('reflection_scores', {})
            
            logger.info(f"RAG Result - Intent: {intent}, Entities: {entities}")
            logger.info(f"Reflection Scores: {reflection_scores}")
            
            # Update session with extracted entities
            if entities:
                session_ctx.update(entities)
                _save_session_context(session_id, session_ctx)
            
            # ===== BOOKING INTEGRATION =====
            # If booking intent with complete info, find rooms
            primary_intent = intent.get('primary') if isinstance(intent, dict) else intent
            
            if primary_intent == 'booking' and all(k in entities for k in ['date', 'start_time', 'end_time']):
                # Build booking criteria
                criteria = {
                    'date': entities['date'],
                    'start_time': entities['start_time'],
                    'end_time': entities['end_time'],
                    'capacity': entities.get('capacity', 1),
                    'building': entities.get('building'),
                    'purpose': entities.get('purpose', 'meeting'),
                    'room_number': entities.get('room_number'),
                    'raw_message': user_message
                }
                
                # Find available rooms
                rooms = await sync_to_async(
                    booking_automation.find_best_rooms,
                    thread_sensitive=False
                )(criteria, limit=3)
                
                if rooms:
                    # Cache for confirmation
                    best_room = rooms[0]['room']
                    try:
                        cache.set(f'booking_preview:{session_id}', {
                            'criteria': criteria,
                            'best_room_id': best_room.id
                        }, timeout=15 * 60)
                    except Exception as e:
                        logger.error(f"Failed to cache booking preview: {e}")
                    
                    # Build rich response with room options
                    response_html = _build_room_selection_html(rooms, criteria)
                    response_text = strip_tags(response_html)
                    
                    actions = [{'type': 'confirm_booking', 'label': 'Confirm Booking'}]
                else:
                    # No rooms available
                    response_text = "I couldn't find any available rooms for that time. Please try a different date or time."
                    response_html = None
                    actions = []
            
            else:
                # Non-booking or incomplete booking info
                response_html = None
                actions = []
            
            # Prepare response
            structured = {
                'reply_text': response_text,
                'reply_html': response_html,
                'actions': actions,
                'slots': entities,
                'intent': primary_intent,
                'confidence': reflection_scores.get('overall', 0.8) if reflection_scores else 0.8,
                'session_id': session_id,
                'rag_mode': 'advanced',
                'metadata': {
                    'processing_time': rag_result.get('processing_time', 0),
                    'num_documents': len(retrieved_docs),
                    'complexity': rag_result.get('complexity', 1),
                    'reflection_scores': reflection_scores
                }
            }
            
            result = JsonResponse(structured)
            result['Access-Control-Allow-Origin'] = '*'
            return result
            
        except Exception as e:
            logger.exception(f"RAG processing failed: {e}")
            # Fallback response
            return JsonResponse({
                'reply_text': 'I encountered an issue processing your request. Please try rephrasing your question.',
                'reply_html': None,
                'actions': [],
                'slots': session_ctx,
                'session_id': session_id,
                'error': 'rag_processing_error'
            })
    
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON in request body',
            'reply_text': "Sorry, I couldn't understand that request."
        }, status=400)
    
    except Exception as e:
        logger.exception(f'Error in chat endpoint: {e}')
        return JsonResponse({
            'error': f'Internal error: {str(e)}',
            'reply_text': 'Sorry, something went wrong. Please try again.'
        }, status=500)


@csrf_exempt
async def confirm_booking(request):
    """Confirm and create booking after user confirmation."""
    try:
        body = json.loads(request.body.decode('utf-8'))
    except Exception:
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    
    session_id = body.get('session_id', '')
    user_email = body.get('email', '')
    
    if not session_id:
        return JsonResponse({'error': 'session_id required'}, status=400)
    
    # Get cached booking preview
    preview = cache.get(f'booking_preview:{session_id}')
    if not preview:
        return JsonResponse({
            'reply_text': 'No pending booking found to confirm.'
        }, status=400)
    
    criteria = preview.get('criteria', {})
    
    # Get user
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user = await _get_authenticated_user_async(request, user_email, User)
    
    if not user or not getattr(user, 'is_authenticated', False):
        return JsonResponse({
            'reply_text': 'Please sign in to confirm booking.'
        }, status=403)
    
    # Create booking
    _, booking_automation = get_rag_system()
    result = await sync_to_async(
        booking_automation.auto_book,
        thread_sensitive=False
    )(user, criteria)
    
    # Clear cache
    try:
        cache.delete(f'booking_preview:{session_id}')
    except Exception:
        pass
    
    reply_text = result.get('user_message') if isinstance(result, dict) else str(result)
    
    return JsonResponse({
        'reply_text': reply_text,
        'result': result,
        'session_id': session_id
    })


# Helper functions
async def _get_user_info_async(request):
    """Get authenticated user info (async-safe)."""
    try:
        def get_user_info_sync():
            if not hasattr(request, 'user'):
                return None
            
            user = request.user
            if not user.is_authenticated:
                return None
            
            return {
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
        
        return await sync_to_async(get_user_info_sync, thread_sensitive=True)()
    except Exception as e:
        logger.warning(f"Failed to get user info: {e}")
        return None


async def _get_authenticated_user_async(request, user_email, User):
    """Get authenticated user from request or email."""
    # Try request user first
    try:
        def get_request_user():
            if not hasattr(request, 'user'):
                return None
            if not request.user.is_authenticated:
                return None
            return request.user
        
        user = await sync_to_async(get_request_user, thread_sensitive=True)()
        if user:
            return user
    except Exception as e:
        logger.warning(f"Failed to get request user: {e}")
    
    # Try email
    if user_email:
        try:
            return await sync_to_async(
                User.objects.get,
                thread_sensitive=False
            )(email=user_email)
        except User.DoesNotExist:
            pass
    
    return None


def _build_room_selection_html(rooms: list, criteria: dict) -> str:
    """Build HTML for room selection with booking preview."""
    best_room = rooms[0]['room']
    
    html = f"""
    <div style='background: linear-gradient(135deg, #e0f2fe 0%, #bae6fd 100%); 
                padding: 20px; border-radius: 12px; margin: 15px 0;'>
        <strong style='color: #0369a1; font-size: 18px; display: block; margin-bottom: 15px;'>
            ✅ Perfect! I found available rooms for you:
        </strong>
    """
    
    for i, room_data in enumerate(rooms, 1):
        room = room_data['room']
        score = room_data['score']
        
        # Highlight best match
        border_style = "border: 3px solid #10b981;" if i == 1 else "border: 1px solid #93c5fd;"
        
        html += f"""
        <div style='background: white; padding: 15px; border-radius: 8px; 
                    margin: 10px 0; {border_style}'>
            <div style='display: flex; justify-content: space-between; align-items: center;'>
                <div>
                    <strong style='color: #0369a1; font-size: 16px;'>{room.name}</strong>
                    <span style='color: #059669; font-weight: bold; margin-left: 10px;'>
                        {'⭐ BEST MATCH' if i == 1 else ''}
                    </span>
                    <br>
                    <span style='color: #075985;'>Room: {room.room_number}</span>
                    <br>
                    <span style='color: #075985;'>👥 Capacity: {room.capacity} people</span>
                    <br>
                    <span style='color: #075985;'>📍 Building: {getattr(room, 'building_name', None) or getattr(room, 'building', 'N/A')}</span>
                    <br>
                    <span style='color: #6b7280; font-size: 12px;'>Match Score: {score:.0f}/100</span>
                </div>
            </div>
        </div>
        """
    
    html += f"""
    </div>
    <div style='background: #dcfce7; padding: 15px; border-radius: 8px; 
                border-left: 4px solid #10b981; margin: 15px 0;'>
        <strong style='color: #15803d;'>📅 Booking Summary:</strong><br>
        <span style='color: #166534;'>Date: {criteria['date']}</span><br>
        <span style='color: #166534;'>Time: {criteria['start_time']} - {criteria['end_time']}</span><br>
        <span style='color: #166534;'>Capacity: {criteria.get('capacity', 1)} people</span>
    </div>
    <div style='text-align: center; margin-top: 20px;'>
        <button class='inline-quick-action' data-action='confirm_booking' type='button'
                style='padding: 14px 40px; border-radius: 12px; border: none;
                       background: linear-gradient(135deg, #10b981 0%, #059669 100%);
                       color: white; cursor: pointer; font-weight: 600; font-size: 16px;
                       transition: all 0.3s; box-shadow: 0 4px 6px rgba(16, 185, 129, 0.3);'>
            ✓ Confirm Booking
        </button>
    </div>
    """
    
    return html


# Sync wrapper for compatibility
@csrf_exempt
def chat_endpoint_sync(request):
    """Sync wrapper for chat_endpoint."""
    return async_to_sync(chat_endpoint)(request)


@csrf_exempt
def confirm_booking_sync(request):
    """Sync wrapper for confirm_booking."""
    return async_to_sync(confirm_booking)(request)
