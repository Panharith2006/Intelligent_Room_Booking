from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    # UI / entry page (main chatbot interface)
    path('', views.index_view, name='index'),

    # Core chat endpoint - GET redirects to UI, POST processes messages
    path('chat/', views.chat_page_get, name='chat'),

    # System health check (AI + DB + kernel status)
    path('health/', views.health_view, name='health'),

    # Clear conversation session
    path('clear/', views.clear_view, name='clear_session'),

    # Booking confirmation endpoint (final step of workflow)
    path('confirm_booking/', views.confirm_booking_view, name='confirm_booking'),
]