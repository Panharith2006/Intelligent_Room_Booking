import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

# Import RAG components
from ai.query_processor import QueryProcessor
from ai.hybrid_retriever import HybridRetriever, MultiQueryRetriever
from ai.reranker import HybridReRanker, DocumentReRanker
from ai.vector_store import VectorStore

logger = logging.getLogger(__name__)

# System prompt that governs how the LLM generates from retrieved context.
# The LLM reasons over what it was given — no hard-coded intent branches.
GENERATION_SYSTEM_PROMPT = """You are a helpful assistant for a room booking system.
You are given:
  - A user query
  - Structured metadata about the user's intent and extracted entities
  - A set of retrieved documents (both semantic and structured/real-time data)

Your job is to synthesise a clear, accurate response **grounded solely in the retrieved documents**.

Guidelines:
- If structured room data is present (source: "structured"), lead with those facts.
- If any required booking detail (date, time, capacity) is missing from the entities, ask only for what is missing — do not ask for things already provided.
- If no documents are relevant, say so clearly and ask the user to rephrase or provide more detail.
- Never fabricate room numbers, availability, or equipment.
- Keep the response concise and actionable."""


class AgenticRAG:

    def __init__(
        self,
        vector_store: VectorStore = None,
        llm_client=None,
        enable_reranking: bool = True,
        enable_multi_query: bool = True
    ):
        self.vector_store = vector_store or VectorStore()
        self.llm_client = llm_client

        self.enable_reranking = enable_reranking
        self.enable_multi_query = enable_multi_query

        logger.info("Initializing Agentic RAG components...")
        logger.info(f"  Input Model (QueryProcessor): {type(llm_client).__name__ if llm_client else 'None'}")

        self.query_processor = QueryProcessor(llm_client)

        self.retriever = HybridRetriever(
            vector_store=self.vector_store,
            keyword_index=None,
            database_client=None
        )

        if self.enable_multi_query:
            self.multi_query_retriever = MultiQueryRetriever(self.retriever, num_queries=3)

        if self.enable_reranking:
            try:
                self.reranker = HybridReRanker()
                logger.info("  Re-ranking enabled")
            except Exception as e:
                logger.warning(f"Re-ranking initialization failed: {e}")
                self.enable_reranking = False

        logger.info(
            f"  Agentic RAG initialized "
            f"(Re-ranking: {self.enable_reranking}, Multi-Query: {self.enable_multi_query})"
        )

    def process_query(
        self,
        query: str,
        context: Dict = None,
        conversation_history: List[Dict] = None,
        user_info: Dict = None,
        top_k: int = 5,
    ) -> Dict:

        logger.info("=" * 80)
        logger.info(f"Processing query: {query}")
        logger.info("=" * 80)

        start_time = datetime.now()

        # ── Step 1: Query Understanding ───────────────────────────────────────
        logger.info("Step 1: Query Processing...")
        processed_query = self.query_processor.process_query(query, context)

        intent = processed_query["intent"]
        entities = processed_query["entities"]
        expanded_queries = processed_query["expanded_queries"]
        complexity = processed_query["complexity"]

        logger.info(f"  Intent: {intent.get('primary') if isinstance(intent, dict) else intent}")
        logger.info(f"  Entities: {entities}")
        logger.info(f"  Complexity: {complexity}/5")

        # ── Step 2: Retrieval ─────────────────────────────────────────────────
        logger.info("Step 2: Retrieval...")

        use_multi_query = self.enable_multi_query and complexity >= 3

        if use_multi_query:
            logger.info(f"  Using multi-query retrieval ({len(expanded_queries)} variations)")
            retrieved_docs = self.multi_query_retriever.retrieve(
                query=query,
                query_variations=expanded_queries,
                entities=entities,
                intent=intent,
                top_k=top_k * 2,
            )
        else:
            logger.info("  Using standard hybrid retrieval")
            retrieved_docs = self.retriever.retrieve(
                query=query,
                entities=entities,
                intent=intent,
                top_k=top_k * 2,
                use_query_routing=True,
            )

        logger.info(f"  Retrieved {len(retrieved_docs)} documents")

        # ── Step 3: Re-Ranking ────────────────────────────────────────────────
        if self.enable_reranking and retrieved_docs:
            logger.info("Step 3: Re-ranking...")
            retrieved_docs = self.reranker.rerank(
                query=query,
                documents=retrieved_docs,
                top_k=top_k,
            )
            logger.info(f"  Re-ranked to top {len(retrieved_docs)} documents")
        else:
            retrieved_docs = retrieved_docs[:top_k]

        # ── Step 4: Context Compression ───────────────────────────────────────
        compressed_docs = self._compress_context(retrieved_docs, query, entities)

        # ── Step 5: LLM-Grounded Generation ──────────────────────────────────
        logger.info("Step 5: LLM-grounded response generation...")
        response_text = self._generate_response(
            query=query,
            retrieved_docs=compressed_docs,
            entities=entities,
            intent=intent,
            context=context,
            conversation_history=conversation_history,
        )

        processing_time = (datetime.now() - start_time).total_seconds()

        result = {
            "response_text": response_text,
            "retrieved_docs": [
                {
                    "text": doc.get("text", "")[:200],
                    "score": doc.get("score", 0.0),
                    "source": doc.get("source", "unknown"),
                    "metadata": doc.get("metadata", {}),
                }
                for doc in compressed_docs
            ],
            "entities": entities,
            "intent": intent,
            "complexity": complexity,
            "processing_time": processing_time,
            "metadata": {
                "num_retrieved": len(retrieved_docs),
                "num_re_ranked": len(compressed_docs) if self.enable_reranking else 0,
                "used_multi_query": use_multi_query,
                "query_variations": expanded_queries if use_multi_query else [query],
            },
        }

        logger.info(f"Processing complete in {processing_time:.2f}s")
        logger.info("=" * 80)

        return result

    # ── Context Compression ───────────────────────────────────────────────────

    def _compress_context(
        self,
        documents: List[Dict],
        query: str,
        entities: Dict,
    ) -> List[Dict]:
        """Deduplicate and trim documents before passing to the LLM."""
        if not documents:
            return []

        compressed = []
        seen_texts: set = set()

        for doc in documents:
            text = doc.get("text", "")

            text_hash = hash(text[:100])
            if text_hash in seen_texts:
                continue
            seen_texts.add(text_hash)

            if len(text) > 1000:
                query_terms = set(query.lower().split())
                sentences = text.split(".")
                relevant = [
                    s for s in sentences
                    if query_terms & set(s.lower().split())
                ]
                text = ". ".join(relevant[:3]) + "." if relevant else text[:500]

            doc_copy = doc.copy()
            doc_copy["text"] = text
            compressed.append(doc_copy)

        return compressed

    # ── LLM-Grounded Generation ───────────────────────────────────────────────
    def _generate_response(
        self,
        query: str,
        retrieved_docs: List[Dict],
        entities: Dict,
        intent: Dict,
        context: Dict,
        conversation_history: List[Dict] = None,
    ) -> str:
       
        if not self.llm_client:
            logger.warning("No LLM client configured — returning fallback response.")
            return self._fallback_no_llm(retrieved_docs)

        user_prompt = self._build_generation_prompt(
            query=query,
            retrieved_docs=retrieved_docs,
            entities=entities,
            intent=intent,
            context=context,
        )

        messages = []

        # Inject conversation history so the model has full turn context
        if conversation_history:
            for turn in conversation_history:
                role = turn.get("role", "user")
                content = turn.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": user_prompt})

        try:
            response_text = self.llm_client.generate(
                system=GENERATION_SYSTEM_PROMPT,
                messages=messages,
            )
            return response_text
        except Exception as e:
            logger.error(f"LLM generation failed: {e}", exc_info=True)
            return self._fallback_no_llm(retrieved_docs)

    def _build_generation_prompt(
        self,
        query: str,
        retrieved_docs: List[Dict],
        entities: Dict,
        intent: Dict,
        context: Dict,
    ) -> str:
        
        # Serialise retrieved documents
        docs_block = ""
        if retrieved_docs:
            doc_lines = []
            for i, doc in enumerate(retrieved_docs, 1):
                source = doc.get("source", "unknown")
                score = doc.get("score", 0.0)
                text = doc.get("text", "").strip()
                metadata = doc.get("metadata", {})

                header = f"[Doc {i}] source={source} score={score:.3f}"
                if metadata:
                    # Flatten key metadata fields for the model to reason over
                    meta_str = ", ".join(
                        f"{k}={v}" for k, v in metadata.items()
                        if k in (
                            "room_number", "capacity", "room_type",
                            "equipment", "available", "floor",
                        )
                    )
                    if meta_str:
                        header += f" | {meta_str}"
                doc_lines.append(f"{header}\n{text}")
            docs_block = "\n\n".join(doc_lines)
        else:
            docs_block = "(no documents retrieved)"

        # Serialise entities compactly (skip empty values)
        entity_items = {k: v for k, v in entities.items() if v}
        entities_str = json.dumps(entity_items, ensure_ascii=False) if entity_items else "{}"

        intent_str = (
            intent.get("primary", "unknown")
            if isinstance(intent, dict)
            else str(intent)
        )

        extra_context = ""
        if context:
            extra_context = f"\n\nAdditional context: {json.dumps(context, ensure_ascii=False)}"

        return (
            f"User query: {query}\n\n"
            f"Detected intent: {intent_str}\n"
            f"Extracted entities: {entities_str}"
            f"{extra_context}\n\n"
            f"Retrieved documents:\n{docs_block}\n\n"
            f"Please generate a helpful, grounded response."
        )

    # ── Fallbacks ─────────────────────────────────────────────────────────────
    def _fallback_no_llm(self, retrieved_docs: List[Dict]) -> str:
        if not retrieved_docs:
            return (
                "I couldn't find relevant information for your query. "
                "Could you rephrase or provide more details?"
            )
        snippets = [doc.get("text", "").strip() for doc in retrieved_docs[:3] if doc.get("text")]
        return "Based on the available information:\n\n" + "\n\n".join(snippets)

    # ── Utility ───────────────────────────────────────────────────────────────

    def get_conversation_summary(self, conversation_history: List[Dict]) -> str:
        if not conversation_history:
            return ""

        summary_parts = []
        for turn in conversation_history[-3:]:
            role = turn.get("role", "user")
            content = turn.get("content", "")
            if role == "user":
                summary_parts.append(f"User asked: {content[:100]}")
            else:
                summary_parts.append(f"Assistant: {content[:100]}")

        return " | ".join(summary_parts)


# ── Convenience function ──────────────────────────────────────────────────────
def process_with_agentic_rag(
    query: str,
    vector_store: VectorStore = None,
    context: Dict = None,
    user_info: Dict = None,
    top_k: int = 5,
) -> Dict:
    rag = AgenticRAG(vector_store=vector_store)
    return rag.process_query(
        query=query,
        context=context,
        user_info=user_info,
        top_k=top_k,
    )