"""
chatbot/agent.py

ChatAgent: Central orchestrator that wires together:
- Semantic Kernel (Ollama)
- AgenticRAG system
- BookingAutomation
- RoomBookingPlugin
- AI Gateway registration
"""

import logging
from typing import Dict, Optional

from chatbot.integrations.ai_gateway import initialize_ai_systems

logger = logging.getLogger(__name__)


class ChatAgent:
    """
    Top-level agent that owns all AI subsystems.
    Created once at Django startup via chatbot/initializer.py.
    Registered into ai_gateway for use by chat_controller.
    """

    def __init__(self, kernel, booking_automation, room_plugin):
        """
        Parameters
        ----------
        kernel              : Semantic Kernel instance (Ollama-backed)
        booking_automation  : BookingAutomation instance
        room_plugin         : RoomBookingPlugin instance
        """

        self.kernel = kernel
        self.booking_automation = booking_automation
        self.room_plugin = room_plugin

        # Build AgenticRAG and register into ai_gateway
        self._rag_system = self._build_rag_system()

        # Register into ai_gateway so chat_controller can access them
        initialize_ai_systems(
            rag_system=self._rag_system,
            booking_system=self.booking_automation,
        )

        logger.info("ChatAgent initialized and registered into AI gateway")

    # =========================
    # RAG SYSTEM BUILDER
    # =========================

    def _build_rag_system(self):
        """
        Build AgenticRAG with shared VectorStore and HybridRetriever.
        Keeps all heavy imports deferred (called from initializer.py already).
        """

        try:
            from ai.agentic_rag import AgenticRAG
            from ai.vector_store import get_vector_store

            vector_store = get_vector_store()
            llm_client = getattr(self.kernel, "llm_client", None)

            rag = AgenticRAG(
                vector_store=vector_store,
                llm_client=llm_client,   # Gemma-backed callable client from Ollama kernel
                enable_self_rag=True,
                enable_reranking=True,
                enable_multi_query=True,
            )

            logger.info("AgenticRAG built successfully")
            return rag

        except Exception as e:
            logger.exception(f"Failed to build AgenticRAG: {e}")
            return None

    # =========================
    # PROPERTIES (SAFE ACCESS)
    # =========================

    @property
    def rag_system(self):
        return self._rag_system

    @property
    def is_ready(self) -> bool:
        return self._rag_system is not None and self.booking_automation is not None

    # =========================
    # HEALTH CHECK
    # =========================

    def health(self) -> Dict:
        """
        Returns a status dict for the /health/ endpoint.
        """

        vector_stats = {}

        try:
            from ai.vector_store import get_vector_store
            vector_stats = get_vector_store().get_collection_stats()
        except Exception as e:
            logger.warning(f"Could not fetch vector store stats: {e}")

        return {
            "agent_ready": self.is_ready,
            "rag_initialized": self._rag_system is not None,
            "booking_initialized": self.booking_automation is not None,
            "kernel_initialized": self.kernel is not None,
            "vector_store_stats": vector_stats,
        }

    # =========================
    # DIRECT QUERY (OPTIONAL)
    # =========================

    def process_query(
        self,
        query: str,
        context: Optional[Dict] = None,
        top_k: int = 5,
        use_self_rag: bool = True,
    ) -> Dict:
        """
        Optional direct query interface.
        chat_controller uses rag_system.process_query() directly,
        but this wrapper is useful for testing and management commands.
        """

        if not self._rag_system:
            return {
                "response_text": "RAG system not initialized.",
                "entities": {},
                "intent": {},
                "reflection_scores": {},
            }

        return self._rag_system.process_query(
            query=query,
            context=context or {},
            top_k=top_k,
            use_self_rag=use_self_rag,
        )