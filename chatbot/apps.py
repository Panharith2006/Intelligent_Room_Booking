# chatbot/apps.py

from django.apps import AppConfig
import logging
import sys

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
            logger.info("ChatAgent already initialized, skipping...")
            return

        try:
            logger.info("🤖 Initializing Chatbot...")

            # Import ONLY what is needed for bootstrap
            from chatbot.initializer import create_chat_agent

            _chat_agent = create_chat_agent()

            logger.info("✅ Chatbot initialized successfully")
            
            # Print to console for immediate visibility
            print("ChatAgent Ready: AI chatbot is initialized and ready to use!")

        except Exception as e:
            logger.error(f"❌ Chatbot initialization failed!")
            logger.error(f"   Error: {e}")
            logger.exception("Full traceback:")
            
            # Print to console AND stderr for visibility
            print(f"❌ ChatAgent Failed: {e}", file=sys.stderr)
            print(f"   Ensure HuggingFace API key is set in .env", file=sys.stderr)
            print(f"   Set: HF_API_KEY=hf_your_token_here or HUGGINGFACE_API_KEY=hf_...", file=sys.stderr)
            
            # IMPORTANT: Allow app to start without AI system
            # Users will see helpful error messages when trying to use chat
            _chat_agent = None
            
            import traceback
            print(f"\n{'='*60}", file=sys.stderr)
            print("FULL ERROR DETAILS:", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            print(f"{'='*60}\n", file=sys.stderr)