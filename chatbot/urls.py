"""
Chatbot URL Configuration
"""
from django.urls import path
from . import views

app_name = 'chatbot'

urlpatterns = [
    path('chat/', views.chat_endpoint, name='chat'),
    path('health/', views.health_check, name='health'),
    path('clear/', views.clear_session, name='clear_session'),
    # path('debug_deepseek/', views.debug_deepseek, name='debug_deepseek'),
    path('confirm_booking/', views.confirm_booking, name='confirm_booking'),
]
