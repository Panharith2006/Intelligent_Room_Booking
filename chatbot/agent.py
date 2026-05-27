import logging
from typing import Dict, Optional

from chatbot.integrations.ai_gateway import initialize_ai_systems

logger = logging.getLogger(__name__)

class ChatAgent:
    def __init__(self, kernel, booking_automation, room_plugin, llm_client=None):

        self.kernel = kernel
        self.booking_automation = booking_automation
        self.room_plugin = room_plugin

        # Build AgenticRAG and register into ai_gateway
        self._rag_system = self._build_rag_system(llm_client=llm_client)

        # Register into ai_gateway so chat_controller can access them
        initialize_ai_systems(
            rag_system=self._rag_system,
            booking_system=self.booking_automation,
        )
        logger.info("ChatAgent initialized and registered into AI gateway")

    # =========================
    # RAG SYSTEM BUILDER
    # =========================
    def _build_rag_system(self, llm_client=None):
        try:
            from ai.agentic_rag import AgenticRAG
            from ai.vector_store import get_vector_store

            vector_store = get_vector_store()
            rag = AgenticRAG(
                vector_store=vector_store,
                llm_client=llm_client,   # HuggingFace Inference API client from HuggingFace kernel
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
    ) -> Dict:

        if not self._rag_system:
            return {
                "response_text": "RAG system not initialized.",
                "entities": {},
                "intent": {},
            }

        return self._rag_system.process_query(
            query=query,
            context=context or {},
            top_k=top_k,
        )