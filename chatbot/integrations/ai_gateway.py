import logging

logger = logging.getLogger(__name__)

_agentic_rag = None
_booking_automation = None
_vector_store = None


def initialize_ai_systems(rag_system, booking_system, vector_store=None):
    global _agentic_rag, _booking_automation, _vector_store

    _agentic_rag = rag_system
    _booking_automation = booking_system
    _vector_store = vector_store

    logger.info("AI systems initialized successfully")

def get_rag_system():
    return _agentic_rag, _booking_automation

def get_vector_store():
    return _vector_store

def is_ready():
    return _agentic_rag is not None and _booking_automation is not None