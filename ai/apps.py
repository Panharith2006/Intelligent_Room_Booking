"""
ai/apps.py

Django AppConfig for the AI/RAG system.
Allows management commands and signal handlers to work properly.
"""

from django.apps import AppConfig


class AiConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'ai'
    verbose_name = 'AI & RAG System'
