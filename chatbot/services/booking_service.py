import logging
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

# ====================================================================
# BUILD BOOKING CRITERIA SAFELY
# ====================================================================
def build_booking_criteria(entities: dict, user_message: str) -> dict:
	"""Build and validate booking criteria from extracted entities"""
	return {
		"date": entities.get("date"),
		"start_time": entities.get("start_time"),
		"end_time": entities.get("end_time"),
		"capacity": entities.get("capacity", 1),
		"building": entities.get("building"),
		"purpose": entities.get("purpose", "meeting"),
		"room_number": entities.get("room_number"),
		"equipment": entities.get("equipment"),
		"raw_message": user_message,
	}

# ====================================================================
# VALIDATION HELPER (CRITICAL FOR BOOKING FLOW)
# ====================================================================
def is_valid_criteria(criteria: dict) -> dict:
	"""Validate booking criteria and return detailed validation result"""
	result = {
		"valid": False,
		"missing_fields": [],
		"errors": [],
		"message": ""
	}
	
	# Check required fields
	required_fields = ["date", "start_time", "end_time"]
	missing = [f for f in required_fields if not criteria.get(f)]
	
	if missing:
		result["missing_fields"] = missing
		result["message"] = f"Missing required fields: {', '.join(missing)}"
		return result
	
	# Validate date/time format
	from datetime import datetime
	try:
		datetime.strptime(criteria["date"], "%Y-%m-%d")
		datetime.strptime(criteria["start_time"], "%H:%M")
		datetime.strptime(criteria["end_time"], "%H:%M")
	except ValueError as e:
		result["errors"].append(f"Invalid date/time format: {str(e)}")
		result["message"] = f"Invalid date/time format: {str(e)}"
		return result
	
	# Validate capacity
	try:
		capacity = int(criteria.get("capacity", 1))
		if capacity < 1:
			result["errors"].append("Capacity must be at least 1")
			result["message"] = "Invalid capacity: must be at least 1"
			return result
	except (ValueError, TypeError):
		result["errors"].append("Capacity must be a number")
		result["message"] = "Invalid capacity"
		return result
	
	result["valid"] = True
	result["message"] = "Criteria validation passed"
	return result

# ====================================================================
# FIND BEST ROOMS (ASYNC SAFE)
# ====================================================================
async def find_best_rooms(booking_automation, criteria: dict, limit: int = 3):
	"""Find best available rooms matching criteria"""
	try:
		if not booking_automation:
			return {
				"success": False,
				"error": "Booking automation not initialized",
				"rooms": []
			}
		
		# Validate criteria before search
		validation = is_valid_criteria(criteria)
		if not validation.get("valid"):
			return {
				"success": False,
				"error": validation.get("message", "Invalid booking criteria"),
				"rooms": []
			}
		
		rooms = await sync_to_async(
			booking_automation.find_best_rooms,
			thread_sensitive=True
		)(criteria, limit=limit)

		return {
			"success": True,
			"rooms": rooms,
			"count": len(rooms) if rooms else 0
		}

	except Exception as e:
		logger.exception(f"find_best_rooms failed: {e}")
		return {
			"success": False,
			"error": f"Error searching for rooms: {str(e)}",
			"rooms": []
		}

# ====================================================================
# AUTO BOOKING (ASYNC SAFE)
# ====================================================================
async def auto_book(booking_automation, user, criteria: dict):
	"""Execute automated booking with full validation"""
	try:
		if not booking_automation:
			return {
				"success": False,
				"error": "Booking automation not initialized",
				"user_message": "❌ Booking system not available"
			}
		
		if not user:
			return {
				"success": False,
				"error": "User not provided",
				"user_message": "❌ User authentication failed"
			}
		
		# Validate criteria
		validation = is_valid_criteria(criteria)
		if not validation.get("valid"):
			return {
				"success": False,
				"error": validation.get("message"),
				"user_message": f"❌ {validation.get('message', 'Booking validation failed')}"
			}
		
		# Execute booking
		result = await sync_to_async(
			booking_automation.auto_book,
			thread_sensitive=True
		)(user, criteria)

		return result

	except Exception as e:
		logger.exception(f"auto_book failed: {e}")
		return {
			"success": False,
			"error": f"Booking error: {str(e)}",
			"user_message": "❌ An error occurred during booking"
		}