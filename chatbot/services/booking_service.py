"""
Booking-specific service helpers used by chat controller.
Safe async wrapper around booking automation layer.
"""

from asgiref.sync import sync_to_async


# -----------------------------
# Build booking criteria safely
# -----------------------------
def build_booking_criteria(entities: dict, user_message: str) -> dict:
	"""
	Convert extracted entities into booking criteria.
	Safe version using .get() to prevent KeyError.
	"""
	return {
		"date": entities.get("date"),
		"start_time": entities.get("start_time"),
		"end_time": entities.get("end_time"),
		"capacity": entities.get("capacity", 1),
		"building": entities.get("building"),
		"purpose": entities.get("purpose", "meeting"),
		"room_number": entities.get("room_number"),
		"raw_message": user_message,
	}


# -----------------------------
# Validation helper (important)
# -----------------------------
def is_valid_criteria(criteria: dict) -> bool:
	"""
	Check if minimum required fields exist.
	Prevents sending incomplete booking requests.
	"""
	return all([
		criteria.get("date"),
		criteria.get("start_time"),
		criteria.get("end_time"),
	])


# -----------------------------
# Find best rooms (async safe)
# -----------------------------
async def find_best_rooms(booking_automation, criteria: dict, limit: int = 3):
	"""
	Find best available rooms using booking automation system.
	Wrapped safely using sync_to_async.
	"""
	try:
		return await sync_to_async(
			booking_automation.find_best_rooms,
			thread_sensitive=True  # safer for DB / shared state
		)(criteria, limit=limit)

	except Exception as e:
		return {
			"success": False,
			"error": f"find_best_rooms_failed: {str(e)}",
			"rooms": []
		}


# -----------------------------
# Auto booking (async safe)
# -----------------------------
async def auto_book(booking_automation, user, criteria: dict):
	try:
		return await sync_to_async(
			booking_automation.auto_book,
			thread_sensitive=True
		)(user, criteria)

	except Exception as e:
		return {
			"success": False,
			"error": f"auto_book_failed: {str(e)}"
		}