import logging
import uuid

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from asgiref.sync import sync_to_async

from chatbot.integrations.ai_gateway import get_rag_system
from ai.health_monitor import get_health_monitor
from chatbot.services.response_service import build_chat_response
from chatbot.services.session_service import (
    clear_booking_preview,
    clear_session_context,
    get_booking_preview,
    get_session_context,
    save_session_context,
    set_booking_preview,
)
from chatbot.utils.validators import (
    optional_string,
    parse_json_body,
    require_string_field,
    validate_booking_entities,
)

logger = logging.getLogger(__name__)


# =========================
# BASIC ENDPOINTS
# =========================
@require_http_methods(["GET"])
def chatbot_index(request):
    return JsonResponse({
        "service": "chatbot",
        "status": "ok",
        "message": "Use /chatbot/chat/ for chat requests.",
    })


@require_http_methods(["GET"])
def health_check(request):
    rag_system, _ = get_rag_system()
    
    return JsonResponse({
        "status": "ok",
        "rag_initialized": rag_system is not None,
        "llm_provider": "groq"
    })


# =========================
# CLEAR SESSION
# =========================
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
def clear_session(request):
    if request.method == "OPTIONS":
        return JsonResponse({"status": "ok"})

    try:
        ok, body, err, status = parse_json_body(request)
        if not ok:
            return JsonResponse({"error": err}, status=status)

        ok, session_id, err, status = require_string_field(body, "session_id")
        if not ok:
            return JsonResponse({"error": err}, status=status)

        clear_session_context(session_id)
        clear_booking_preview(session_id)

        return JsonResponse({"status": "cleared", "session_id": session_id})

    except Exception as e:
        logger.exception(e)
        return JsonResponse({"error": "failed_to_clear_session"}, status=500)


# =========================
# CHAT ENDPOINT
# =========================
@csrf_exempt
@require_http_methods(["POST", "OPTIONS"])
async def chat_endpoint(request):

    if request.method == "OPTIONS":
        return JsonResponse({"status": "ok"})

    try:
        ok, body, err, status = parse_json_body(request)
        if not ok:
            return JsonResponse({"error": err, "reply_text": "Invalid request format."}, status=status)

        user_message = optional_string(body, "message")
        session_id = optional_string(body, "session_id") or str(uuid.uuid4())

        session_ctx = await sync_to_async(get_session_context)(session_id)

        if not user_message:
            return JsonResponse({
                "reply_text": "How can I help you with booking?",
                "session_id": session_id
            })

        # =========================
        # GET RAG SYSTEM (for query processing and routing)
        # =========================
        rag_system, booking_automation = get_rag_system()

        if not rag_system:
            logger.error(
                "❌ RAG System not initialized!\n"
                "   Possible causes:\n"
                "   1. Groq API key not set in .env (GROQ_API_KEY)\n"
                "   2. Failed to initialize ChatAgent during Django startup\n"
                "   3. Import error in chatbot or AI modules\n"
                "   Check server logs for full error details."
            )
            return JsonResponse({
                "error": "rag_not_initialized",
                "reply_text": "⚠️ AI system not ready. Check that Groq API key is set in .env file. Restart the server."
            }, status=503)

        # =========================
        # EARLY INTENT CLASSIFICATION (LLM only, decides routing)
        # For database queries, route directly to tools instead of running full RAG
        # =========================
        early_intent = await sync_to_async(rag_system.query_processor.process_query)(
            user_message, 
            session_ctx
        )
        
        primary_intent = early_intent.get("intent", {}).get("primary")
        entities = early_intent.get("entities", {})
        intent_confidence = early_intent.get("intent", {}).get("confidence", 0.5)
        
        logger.info(f"Intent classification: {primary_intent} (confidence: {intent_confidence})")

        # =========================
        # DATABASE QUERY SHORTCUT (No RAG for these intents)
        # =========================
        DATABASE_INTENTS = ["availability", "user_profile", "user_history", "booking", "modification", "cancellation"]
        
        if primary_intent in DATABASE_INTENTS and intent_confidence > 0.7:
            logger.info(f"✓ Routing to tool calling (bypassing RAG): {primary_intent}")
            
            # Import orchestrator handlers
            from chatbot.services.orchestrator import (
                handle_availability_query,
                handle_user_profile,
                handle_user_history,
                handle_modify_booking,
                handle_prepare_booking,
            )
            
            try:
                # Route to appropriate handler based on intent
                if primary_intent == "availability":
                    availability_result = await handle_availability_query(entities, user_message)
                    response_text = availability_result.get("response_text", "No rooms found.")
                    rooms_payload = [
                        {
                            "id": r['room'].id,
                            "name": r['room'].name,
                            "room_number": r['room'].room_number,
                            "capacity": r['room'].capacity,
                        }
                        for r in availability_result.get("rooms", [])
                    ] if availability_result.get("rooms") else None
                    
                    return JsonResponse({
                        "reply_text": response_text,
                        "session_id": session_id,
                        "data": rooms_payload,
                        "type": "tool_result",
                        "intent": primary_intent,
                    })
                
                elif primary_intent == "user_profile":
                    profile_result = await handle_user_profile(request.user)
                    response_text = profile_result.get("response_text", profile_result.get("message", "Could not get profile"))
                    
                    return JsonResponse({
                        "reply_text": response_text,
                        "session_id": session_id,
                        "type": "tool_result",
                        "intent": primary_intent,
                    })
                
                elif primary_intent == "user_history":
                    history_result = await handle_user_history(request.user)
                    response_text = history_result.get("response_text", history_result.get("message", "Could not get history"))
                    
                    return JsonResponse({
                        "reply_text": response_text,
                        "session_id": session_id,
                        "data": history_result.get("history_data"),
                        "type": "tool_result",
                        "intent": primary_intent,
                    })
                
                elif primary_intent == "booking":
                    booking_result = await handle_prepare_booking(entities, user_message)
                    success = booking_result.get("success", False)
                    message = booking_result.get("message", "Booking preparation failed")
                    preview = booking_result.get("preview")
                    actions = booking_result.get("actions", [])
                    
                    return JsonResponse({
                        "reply_text": message,
                        "session_id": session_id,
                        "data": preview,
                        "actions": actions,
                        "type": "tool_result",
                        "intent": primary_intent,
                        "success": success,
                    })
                
                elif primary_intent == "modification":
                    mod_result = await handle_modify_booking(request.user, entities, session_ctx)
                    response_text = mod_result.get("response_text", mod_result.get("message", "Modification failed"))
                    
                    return JsonResponse({
                        "reply_text": response_text,
                        "session_id": session_id,
                        "type": "tool_result",
                        "intent": primary_intent,
                    })
            
            except Exception as e:
                logger.exception(f"Tool calling failed for intent {primary_intent}: {e}")
                # Fall through to RAG as fallback

        # =========================
        # FULL RAG PROCESSING (For document/information queries or fallback)
        # =========================
        rag_result = await sync_to_async(rag_system.process_query)(
            query=user_message,
            context=session_ctx,
            top_k=5,
        )

        response_text = rag_result["response_text"]
        entities = rag_result["entities"]
        intent = rag_result["intent"]
        
        # Note: reflection_scores no longer computed during runtime
        # They are only calculated during offline evaluation phase
        reflection_scores = {}

        if entities:
            session_ctx.update(entities)
            await sync_to_async(save_session_context)(session_id, session_ctx)

        primary_intent = intent.get("primary") if isinstance(intent, dict) else intent

        response_html = None
        actions = []
        rooms_payload = None
        criteria = None

        # =========================
        # USER PROFILE QUERIES
        # =========================
        if primary_intent == "user_profile":
            from chatbot.services.orchestrator import handle_user_profile
            
            profile_result = await handle_user_profile(request.user)
            
            if profile_result.get("success"):
                response_text = profile_result.get("response_text", "Here is your profile information.")
            else:
                response_text = profile_result.get("message", "Could not retrieve your profile.")

        # =========================
        # USER HISTORY QUERIES
        # =========================
        elif primary_intent == "user_history":
            from chatbot.services.orchestrator import handle_user_history
            
            history_result = await handle_user_history(request.user)
            
            if history_result.get("success"):
                response_text = history_result.get("response_text", "Here is your booking history.")
            else:
                response_text = history_result.get("message", "Could not retrieve your booking history.")

        # =========================
        # BOOKING FLOW (Fallback for low-confidence booking intents detected by RAG)
        # =========================
        elif primary_intent == "booking" and validate_booking_entities(entities):
            # delegate to orchestrator which prefers plugin/kernel or booking automation
            from chatbot.services.orchestrator import handle_prepare_booking

            # Prepare booking preview with structured data
            booking_result = await handle_prepare_booking(entities, user_message)
            success = booking_result.get('success', False)
            message = booking_result.get('message', 'Booking preparation failed')
            preview = booking_result.get('preview')
            actions = booking_result.get('actions', [])
            criteria = booking_result.get('criteria')

            if success and preview:
                # Store booking preview in session for confirmation
                await sync_to_async(set_booking_preview)(session_id, {
                    "criteria": criteria,
                    "room_id": preview['room']['id'],
                    "room_name": preview['room']['name'],
                    "room_number": preview['room']['room_number'],
                    "room_capacity": preview['room']['capacity'],
                    "equipment": preview['room'].get('equipment', []),
                })

                response_text = message
                # Actions already include clickable button data
            else:
                response_text = message
                actions = []
                preview = None

        # =========================
        # AVAILABILITY QUERIES (Find rooms without booking)
        # =========================
        elif primary_intent == "availability":
            from chatbot.services.orchestrator import handle_availability_query

            availability_result = await handle_availability_query(entities, user_message)

            if availability_result.get("success") and availability_result.get("rooms"):
                rooms = availability_result.get("rooms")
                response_text = availability_result.get("response_text", f"Found {len(rooms)} available rooms.")
                
                # Build rooms payload
                rooms_payload = [
                    {
                        "id": r['room'].id,
                        "name": r['room'].name,
                        "room_number": r['room'].room_number,
                        "capacity": r['room'].capacity,
                        "available_until": r.get('available_until', 'End of day')
                    }
                    for r in rooms
                ]
                actions = [{"type": "book_room", "label": "Book a Room"}]
            else:
                response_text = availability_result.get("response_text", "No available rooms found.")

        # =========================
        # MODIFICATION QUERIES (Reschedule booking)
        # =========================
        elif primary_intent == "modification":
            from chatbot.services.orchestrator import handle_modify_booking

            mod_result = await handle_modify_booking(request.user, entities, session_ctx)

            if mod_result.get("success"):
                response_text = mod_result.get("message", "Modification request prepared.")
                actions = mod_result.get("actions", [])
                await sync_to_async(save_session_context)(session_id, session_ctx)
            else:
                response_text = mod_result.get("message", "Could not process modification request.")

        # =========================
        # CANCELLATION QUERIES
        # =========================
        elif primary_intent == "cancellation":
            from chatbot.services.orchestrator import handle_cancel_booking

            cancel_result = await handle_cancel_booking(request.user, session_ctx)

            if cancel_result.get("success"):
                response_text = cancel_result.get("message", "Cancellation request prepared.")
                actions = cancel_result.get("actions", [])
                await sync_to_async(save_session_context)(session_id, session_ctx)
            else:
                response_text = cancel_result.get("message", "Could not process cancellation request.")

        # =========================
        # RESPONSE
        # =========================
        structured = build_chat_response(
            response_text=response_text,
            response_html=response_html,
            actions=actions,
            entities=entities,
            primary_intent=primary_intent,
            reflection_scores=reflection_scores,
            session_id=session_id,
            rag_result=rag_result,
            retrieved_docs=rag_result.get("retrieved_docs", []),
        )

        # attach frontend-friendly data
        structured["rooms"] = rooms_payload
        structured["booking_criteria"] = criteria

        return JsonResponse(structured)

    except Exception as e:
        logger.exception(e)
        return JsonResponse({
            "error": "internal_error",
            "reply_text": "Something went wrong."
        }, status=500)


# =========================
# CONFIRM BOOKING
# =========================
@csrf_exempt
@require_http_methods(["POST"])
async def confirm_booking(request):
    from chatbot.services.orchestrator import handle_confirm_booking
    
    ok, body, err, status = parse_json_body(request)
    if not ok:
        return JsonResponse({"error": err}, status=status)

    ok, session_id, err, status = require_string_field(body, "session_id")
    if not ok:
        return JsonResponse({"error": err}, status=status)

    preview = await sync_to_async(get_booking_preview)(session_id)

    if not preview:
        return JsonResponse({"reply_text": "No booking found."}, status=400)

    criteria = preview["criteria"]

    # Use orchestrator to handle booking (prefers plugin/automation where available)
    result = await handle_confirm_booking(request.user, criteria)

    await sync_to_async(clear_booking_preview)(session_id)

    return JsonResponse({
        "reply_text": result.get("user_message", "Booking confirmed"),
        "result": result,
        "session_id": session_id
    })