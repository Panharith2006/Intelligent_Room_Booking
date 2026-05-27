import logging
from django.core.cache import cache

logger = logging.getLogger(__name__)

# -----------------------------
# Session context
# -----------------------------
def get_session_context(session_id: str) -> dict:
	try:
		ctx = cache.get(f"chat_session:{session_id}", {})
		return ctx if isinstance(ctx, dict) else {}
	except Exception as e:
		logger.warning(f"Failed to get session context: {e}")
		return {}


def save_session_context(session_id: str, ctx: dict):
	try:
		if not isinstance(ctx, dict):
			logger.warning("Invalid session context type, expected dict")
			return

		cache.set(
			f"chat_session:{session_id}",
			ctx,
			timeout=60 * 60 * 24  # 24 hours
		)

	except Exception as e:
		logger.error(f"Failed to save session context: {e}")


def clear_session_context(session_id: str):
	try:
		cache.delete(f"chat_session:{session_id}")
	except Exception as e:
		logger.error(f"Failed to clear session context: {e}")


# -----------------------------
# Booking preview cache
# -----------------------------
def set_booking_preview(session_id: str, payload: dict, timeout: int = 15 * 60):
	try:
		if not isinstance(payload, dict):
			logger.warning("Invalid booking preview payload type")
			return

		cache.set(f"booking_preview:{session_id}", payload, timeout=timeout)

	except Exception as e:
		logger.error(f"Failed to set booking preview: {e}")


def get_booking_preview(session_id: str):
	try:
		preview = cache.get(f"booking_preview:{session_id}")
		return preview if isinstance(preview, dict) else None
	except Exception as e:
		logger.warning(f"Failed to get booking preview: {e}")
		return None


def clear_booking_preview(session_id: str):
	try:
		cache.delete(f"booking_preview:{session_id}")
	except Exception as e:
		logger.error(f"Failed to clear booking preview: {e}")