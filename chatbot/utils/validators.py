"""
Validation helpers for chatbot HTTP payloads and booking logic.
Production-safe version (clean + strict + predictable).
"""

from typing import Any, Dict, Optional, Tuple
import json


# =========================
# JSON BODY PARSER
# =========================

def parse_json_body(request) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str], int]:
    """
    Safely parse JSON request body.

    Returns:
        (success, data, error_message, status_code)
    """
    try:
        raw = request.body.decode("utf-8") if request.body else "{}"
        data = json.loads(raw)

        if not isinstance(data, dict):
            return False, None, "JSON payload must be an object", 400

        return True, data, None, 200

    except json.JSONDecodeError:
        return False, None, "Invalid JSON", 400

    except Exception:
        return False, None, "Invalid request body", 400


# =========================
# REQUIRED STRING FIELD
# =========================

def require_string_field(
    payload: Dict[str, Any],
    field: str,
    *,
    allow_empty: bool = False,
) -> Tuple[bool, Optional[str], Optional[str], int]:
    """
    Validate required string field.

    Returns:
        (success, value, error_message, status_code)
    """
    value = payload.get(field)

    if value is None:
        return False, None, f"{field} is required", 400

    if not isinstance(value, str):
        return False, None, f"{field} must be a string", 400

    value = value.strip()

    if not allow_empty and not value:
        return False, None, f"{field} cannot be empty", 400

    return True, value, None, 200


# =========================
# OPTIONAL STRING FIELD
# =========================

def optional_string(payload: Dict[str, Any], field: str, default: str = "") -> str:
    """
    Safely extract optional string field.
    """
    value = payload.get(field, default)

    if isinstance(value, str):
        return value.strip()

    return default


# =========================
# SLOT VALIDATION
# =========================

def validate_update_slots(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Sanitize update_slots for safe session updates.
    Only allows primitive safe types.
    """
    slots = payload.get("update_slots")

    if not isinstance(slots, dict):
        return {}

    cleaned = {}

    for key, value in slots.items():
        if not isinstance(key, str):
            continue

        key = key.strip()
        if not key:
            continue

        # allow safe primitive values only
        if isinstance(value, (str, int, float, bool)):
            if value is not None and value != "":
                cleaned[key] = value

    return cleaned


# =========================
# BOOKING VALIDATION
# =========================

def validate_booking_entities(entities: Dict[str, Any]) -> bool:
    """
    Ensure required booking fields exist and are valid.
    Prevents invalid AI-generated booking requests.
    """
    if not isinstance(entities, dict):
        return False

    required_fields = ["date", "start_time", "end_time"]

    for field in required_fields:
        value = entities.get(field)

        if not isinstance(value, str):
            return False

        if not value.strip():
            return False

    return True