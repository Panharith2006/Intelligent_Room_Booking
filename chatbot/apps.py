# chatbot/apps.py

from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

_chat_agent = None


def get_chat_agent():
    return _chat_agent


def set_chat_agent(agent):
    global _chat_agent
    _chat_agent = agent


class ChatbotConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'chatbot'
    verbose_name = 'AI Chatbot Assistant'

    def ready(self):
        global _chat_agent

        # Prevent multiple initialization
        if _chat_agent is not None:
            return

        try:
            logger.info("Initializing Chatbot...")

            # Import ONLY what is needed for bootstrap
            from chatbot.initializer import create_chat_agent

            _chat_agent = create_chat_agent()

            logger.info("Chatbot initialized successfully")

        except Exception as e:
            logger.exception(f"Chatbot initialization failed: {e}")
            _chat_agent = None