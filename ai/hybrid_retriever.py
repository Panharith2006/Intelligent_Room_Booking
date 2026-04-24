import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)


# =========================
# HYBRID RETRIEVER
# =========================

class HybridRetriever:
    """
    Hybrid Retriever = ChromaDB Vector Search + Keyword Search + DB-structured results.
    Compatible with AgenticRAG and SelfRAG interfaces.
    """

    def __init__(
        self,
        vector_store=None,
        keyword_index=None,      # reserved for BM25 index (future)
        database_client=None,    # reserved for Django ORM queries (future)
    ):
        self.vector_store = vector_store
        self.keyword_index = keyword_index
        self.database_client = database_client

    # =========================
    # MAIN RETRIEVE FUNCTION
    # =========================

    def retrieve(
        self,
        query: str,
        entities: Dict = None,
        intent=None,
        top_k: int = 5,
        use_query_routing: bool = True,
    ) -> List[Dict]:
        """
        Main retrieval entry point.
        Compatible with AgenticRAG and SelfRAG callers.
        """

        logger.info(f"HybridRetriever: retrieving for query='{query[:80]}'")

        entities = entities or {}

        # Resolve intent string
        if isinstance(intent, dict):
            primary_intent = intent.get("primary", "information")
        else:
            primary_intent = intent or "information"

        vector_results = self._vector_search(query, entities, primary_intent, top_k)
        keyword_results = self._keyword_search(query, top_k)

        combined = self._merge_results(vector_results, keyword_results)
        combined.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        return combined[:top_k]

    # =========================
    # VECTOR SEARCH (ChromaDB)
    # =========================

    def _vector_search(
        self,
        query: str,
        entities: Dict,
        intent: str,
        top_k: int,
    ) -> List[Dict]:
        """
        Search booking policies only from policy.md ingestion.
        """

        if not self.vector_store:
            return []

        try:
            # Search only booking_policies collection (from policy.md)
            raw = self.vector_store.search_policies(query, n_results=top_k)
            return self._normalize_chroma_results(raw, source="vector")

        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    # =========================
    # KEYWORD SEARCH
    # =========================

    def _keyword_search(self, query: str, top_k: int) -> List[Dict]:
        """
        Simple token-overlap keyword search over in-memory documents.
        Falls back gracefully if no documents are loaded.
        """

        if not hasattr(self, "_documents") or not self._documents:
            return []

        query_tokens = set(query.lower().split())

        scored = []

        for doc in self._documents:
            text = doc.get("text", "").lower()
            tokens = set(text.split())

            if not tokens:
                continue

            overlap = len(query_tokens & tokens)
            score = (overlap / len(query_tokens)) * 0.6 if query_tokens else 0.0

            if score > 0:
                doc_copy = doc.copy()
                doc_copy["score"] = score
                doc_copy["source"] = "keyword"
                scored.append(doc_copy)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    # =========================
    # MERGE RESULTS
    # =========================

    def _merge_results(
        self,
        vector_docs: List[Dict],
        keyword_docs: List[Dict],
    ) -> List[Dict]:
        """
        Deduplicate and merge vector + keyword results.
        Boosts score if doc appears in both.
        """

        merged = {}

        for doc in vector_docs:
            key = doc.get("text", "")[:100]
            merged[key] = doc

        for doc in keyword_docs:
            key = doc.get("text", "")[:100]

            if key in merged:
                merged[key]["score"] = merged[key].get("score", 0.0) + doc.get("score", 0.0)
                merged[key]["source"] = "hybrid"
            else:
                merged[key] = doc

        return list(merged.values())

    def _merge_chroma_results(self, result_a: Dict, result_b: Dict) -> Dict:
        """
        Merge two raw ChromaDB result dicts.
        """

        merged = {
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }

        for key in ["documents", "metadatas", "distances"]:
            a = result_a.get(key, [[]])[0] if result_a else []
            b = result_b.get(key, [[]])[0] if result_b else []
            merged[key] = [a + b]

        return merged

    # =========================
    # CHROMA RESULT NORMALIZER
    # =========================

    def _normalize_chroma_results(self, raw: Dict, source: str = "vector") -> List[Dict]:
        """
        Convert raw ChromaDB query results into standard doc dicts.
        """

        if not raw:
            return []

        documents = raw.get("documents", [[]])[0] or []
        metadatas = raw.get("metadatas", [[]])[0] or []
        distances = raw.get("distances", [[]])[0] or []

        results = []

        for i, text in enumerate(documents):
            distance = distances[i] if i < len(distances) else 1.0
            score = max(0.0, 1.0 - distance)   # cosine distance → similarity

            results.append({
                "text": text or "",
                "document": text or "",         # SelfRAG uses "document" key
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "score": score,
                "source": source,
            })

        return results

    # =========================
    # LOAD IN-MEMORY DOCUMENTS
    # =========================

    def load_documents(self, documents: List[Dict]):
        """
        Load documents for keyword search.
        Call this after ingestion if you want BM25-style fallback.
        """
        self._documents = documents
        logger.info(f"HybridRetriever: loaded {len(documents)} documents for keyword search")


# =========================
# MULTI-QUERY RETRIEVER
# =========================

class MultiQueryRetriever:
    """
    Runs multiple query variations through HybridRetriever,
    merges and deduplicates results.
    Compatible with AgenticRAG interface.
    """

    def __init__(self, retriever: HybridRetriever, num_queries: int = 3):
        self.retriever = retriever
        self.num_queries = num_queries

    def retrieve(
        self,
        query: str,
        query_variations: List[str] = None,
        entities: Dict = None,
        intent=None,
        top_k: int = 5,
    ) -> List[Dict]:
        """
        Retrieve using multiple query variations, merge and deduplicate.
        """

        entities = entities or {}
        queries = query_variations or [query]

        # Limit to num_queries
        queries = queries[:self.num_queries]

        logger.info(f"MultiQueryRetriever: running {len(queries)} query variations")

        all_docs: Dict[str, Dict] = {}

        for q in queries:
            try:
                docs = self.retriever.retrieve(
                    query=q,
                    entities=entities,
                    intent=intent,
                    top_k=top_k,
                )

                for doc in docs:
                    key = doc.get("text", "")[:120]

                    if key in all_docs:
                        # Boost score for docs appearing in multiple queries
                        all_docs[key]["score"] = all_docs[key].get("score", 0.0) + doc.get("score", 0.0) * 0.3
                        all_docs[key]["source"] = "multi_query"
                    else:
                        all_docs[key] = doc

            except Exception as e:
                logger.error(f"MultiQueryRetriever: query failed '{q[:60]}': {e}")

        merged = list(all_docs.values())
        merged.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        logger.info(f"MultiQueryRetriever: merged to {len(merged[:top_k])} unique docs")

        return merged[:top_k]