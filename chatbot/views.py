from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)

from chatbot.controllers.chat_controller import (
    chatbot_index,
    health_check,
    clear_session,
    chat_endpoint,
    confirm_booking,
)


# -----------------------------
# Chat Endpoint - Handles Both GET and POST
# -----------------------------

@csrf_exempt
def chat_page_get(request):
    """
    Chat endpoint that handles both GET and POST.
    - GET: Redirect to chatbot UI (/)
    - POST: Process chat message through async endpoint
    """
    if request.method == "GET":
        # Redirect GET requests to the main chatbot UI
        return redirect('chatbot:index')
    
    elif request.method == "POST":
        # Handle POST: process chat message
        try:
            return async_to_sync(chat_endpoint)(request)
        except Exception as e:
            logger.error(f"Chat endpoint error: {e}", exc_info=True)
            return JsonResponse({
                'error': str(e),
                'message': 'Chat endpoint error'
            }, status=500)
    
    else:
        # Other methods not allowed
        return JsonResponse({
            'error': 'Method not allowed',
            'message': 'Only GET and POST are supported'
        }, status=405)


# Alias for backward compatibility
@csrf_exempt
@require_http_methods(["POST"])
def chat_endpoint_sync(request):
    """
    Sync wrapper for async chat endpoint.
    Needed because Django views are sync by default.
    Only accepts POST requests with message payload.
    """
    try:
        return async_to_sync(chat_endpoint)(request)
    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        return JsonResponse({
            'error': str(e),
            'message': 'Chat endpoint error'
        }, status=500)


# ----------------------------
# Booking Confirmation
# ----------------------------

@csrf_exempt
@require_http_methods(["POST"])
def confirm_booking_sync(request):
    """
    Sync wrapper for async booking confirmation endpoint.
    Only accepts POST requests.
    """
    try:
        return async_to_sync(confirm_booking)(request)
    except Exception as e:
        logger.error(f"Booking confirmation error: {e}", exc_info=True)
        return JsonResponse({
            'error': str(e),
            'message': 'Booking confirmation error'
        }, status=500)