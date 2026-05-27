import logging
from typing import List, Dict, Optional
from collections import defaultdict
import math

logger = logging.getLogger(__name__)

# Reciprocal weight applied to a document's score each additional query variation
# it appears in.  Keeps multi-query boosting bounded (e.g. 3 queries → +0.6 max).
_MULTI_QUERY_BOOST = 0.3

# Keyword score ceiling: raw Jaccard-style overlap is scaled to [0, 0.6] so that
# keyword hits never outrank strong vector hits (which sit in [0, 1]).
_KEYWORD_SCORE_CEILING = 0.6


# =============================================================================
# HYBRID RETRIEVER
# =============================================================================
class HybridRetriever:
    def __init__(
        self,
        vector_store=None,
        keyword_index=None,      # reserved for BM25 index (future)
        database_client=None,    # reserved for Django ORM queries (future)
    ):
        self.vector_store = vector_store
        self.keyword_index = keyword_index
        self.database_client = database_client
        
        # Initialize keyword index as None
        self._documents = None
        self._doc_term_freq = None
        self._doc_lengths = None
        self._idf_scores = None
        self._vocabulary = None
        
        # Lazy-load documents from vector store if available
        self._documents_loaded = False

    # ── Public API ────────────────────────────────────────────────────────────
    def retrieve(
        self,
        query: str,
        entities: Dict = None,
        intent=None,
        top_k: int = 5,
        use_query_routing: bool = True,
    ) -> List[Dict]:

        logger.info(f"HybridRetriever: retrieving for query='{query[:80]}'")

        entities = entities or {}

        vector_results = self._vector_search(query, top_k)
        keyword_results = self._keyword_search(query, top_k)

        combined = self._merge_results(vector_results, keyword_results)
        combined.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        return combined[:top_k]

    def load_documents(self, documents: List[Dict]):
        """Load documents into the in-memory keyword index and build TF-IDF statistics."""
        self._documents = documents
        self._build_keyword_index(documents)
        self._documents_loaded = True
        logger.info(f"HybridRetriever: loaded {len(documents)} documents for keyword search")

    def _lazy_load_documents(self):
        """Lazy-load documents from vector store if not already loaded."""
        if self._documents_loaded or not self.vector_store:
            return
        
        try:
            # Try to load from multiple collections
            documents = []
            for collection_name in ["knowledge_base", "booking_policies", "rooms_info"]:
                docs = self.vector_store.get_all_documents(collection_name)
                documents.extend(docs)
            
            if documents:
                self.load_documents(documents)
                logger.info(f"Lazy-loaded {len(documents)} documents from vector store")
            else:
                logger.warning("No documents found in vector store for keyword indexing")
                self._documents_loaded = True  # Mark as attempted even if empty
        except Exception as e:
            logger.error(f"Failed to lazy-load documents: {e}")
            self._documents_loaded = True  # Mark as attempted to avoid repeated failures

    def _build_keyword_index(self, documents: List[Dict]):
        """Build TF-IDF index from documents for better keyword search."""
        self._doc_term_freq = []  # Term frequency per document
        self._doc_lengths = []     # Document lengths (in tokens)
        self._idf_scores = {}      # IDF scores for each term
        self._vocabulary = set()   # All unique terms
        
        if not documents:
            return
        
        # First pass: collect all terms and compute document frequencies
        term_doc_count = defaultdict(int)
        doc_tokens_list = []
        
        for doc in documents:
            text = doc.get("text", "").lower()
            tokens = self._tokenize(text)
            doc_tokens_list.append(tokens)
            self._doc_lengths.append(len(tokens))
            
            unique_terms = set(tokens)
            for term in unique_terms:
                term_doc_count[term] += 1
            self._vocabulary.update(unique_terms)
        
        # Second pass: compute IDF scores
        num_docs = len(documents)
        for term in self._vocabulary:
            doc_freq = term_doc_count[term]
            # IDF = log(N / df)
            idf = math.log(num_docs / max(1, doc_freq))
            self._idf_scores[term] = idf
        
        # Third pass: compute term frequencies per document
        for tokens in doc_tokens_list:
            term_freq = defaultdict(int)
            for token in tokens:
                term_freq[token] += 1
            self._doc_term_freq.append(dict(term_freq))
        
        logger.debug(f"Built keyword index: {len(self._vocabulary)} unique terms, "
                    f"{len(self._idf_scores)} IDF scores")

    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization: lowercase and split by whitespace."""
        return [t for t in text.lower().split() if t.strip()]

    # ── Vector search (ChromaDB) ──────────────────────────────────────────────
    def _vector_search(self, query: str, top_k: int) -> List[Dict]:
        if not self.vector_store:
            return []

        try:
            raw = self.vector_store.search_policies(query, n_results=top_k)
            return self._normalize_chroma_results(raw, source="vector")
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            return []

    # ── Keyword search ────────────────────────────────────────────────────────
    def _keyword_search(self, query: str, top_k: int) -> List[Dict]:
        """Search documents using TF-IDF scoring."""
        # Lazy-load documents if not already loaded
        self._lazy_load_documents()
        
        documents = getattr(self, "_documents", None)
        if not documents:
            return []

        query_tokens = self._tokenize(query)
        if not query_tokens:
            return []

        # If index not built yet, fall back to simple search
        if not hasattr(self, "_doc_term_freq") or self._doc_term_freq is None:
            return self._simple_keyword_search(query, top_k)

        scored_docs = []
        
        for doc_idx, doc in enumerate(documents):
            if doc_idx >= len(self._doc_term_freq):
                continue
                
            term_freq = self._doc_term_freq[doc_idx]
            doc_length = self._doc_lengths[doc_idx] if doc_idx < len(self._doc_lengths) else 1
            
            # Compute TF-IDF score for this document
            score = 0.0
            for token in query_tokens:
                tf = term_freq.get(token, 0)
                idf = self._idf_scores.get(token, 0.0)
                
                # TF-IDF with length normalization
                if doc_length > 0:
                    tfidf = (tf / doc_length) * idf
                    score += tfidf
            
            if score > 0:
                # Normalize score to [0, _KEYWORD_SCORE_CEILING]
                normalized_score = min(score / max(1.0, len(query_tokens)), _KEYWORD_SCORE_CEILING)
                
                doc_copy = doc.copy()
                doc_copy["score"] = normalized_score
                doc_copy["source"] = "keyword"
                scored_docs.append(doc_copy)
        
        scored_docs.sort(key=lambda x: x["score"], reverse=True)
        return scored_docs[:top_k]

    def _simple_keyword_search(self, query: str, top_k: int) -> List[Dict]:
        """Fallback simple keyword search using token overlap (Jaccard similarity)."""
        documents = getattr(self, "_documents", None)
        if not documents:
            return []

        query_tokens = set(self._tokenize(query))
        if not query_tokens:
            return []

        scored = []
        for doc in documents:
            text = doc.get("text", "")
            doc_tokens = set(self._tokenize(text))
            if not doc_tokens:
                continue

            overlap = len(query_tokens & doc_tokens)
            if overlap == 0:
                continue

            # Jaccard similarity: intersection / union
            union_size = len(query_tokens | doc_tokens)
            jaccard = overlap / union_size if union_size > 0 else 0.0
            
            # Scale to [0, _KEYWORD_SCORE_CEILING]
            score = jaccard * _KEYWORD_SCORE_CEILING

            doc_copy = doc.copy()
            doc_copy["score"] = score
            doc_copy["source"] = "keyword"
            scored.append(doc_copy)

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:top_k]

    # ── Merge ─────────────────────────────────────────────────────────────────
    def _merge_results(
        self,
        vector_docs: List[Dict],
        keyword_docs: List[Dict],
    ) -> List[Dict]:
       
        merged: Dict[str, Dict] = {}

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

    # ── ChromaDB normalizer ───────────────────────────────────────────────────
    def _normalize_chroma_results(self, raw: Dict, source: str = "vector") -> List[Dict]:
       
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
                "document": text or "",         # SelfRAG compatibility alias
                "metadata": metadatas[i] if i < len(metadatas) else {},
                "score": score,
                "source": source,
            })

        return results


# =============================================================================
# MULTI-QUERY RETRIEVER
# =============================================================================
class MultiQueryRetriever:
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

        entities = entities or {}
        queries = (query_variations or [query])[:self.num_queries]

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
                        # Docs appearing in multiple query variations are likely
                        # more relevant; apply a bounded boost per extra hit.
                        all_docs[key]["score"] = (
                            all_docs[key].get("score", 0.0)
                            + doc.get("score", 0.0) * _MULTI_QUERY_BOOST
                        )
                        all_docs[key]["source"] = "multi_query"
                    else:
                        all_docs[key] = doc

            except Exception as e:
                logger.error(f"MultiQueryRetriever: query failed '{q[:60]}': {e}")

        merged = sorted(all_docs.values(), key=lambda x: x.get("score", 0.0), reverse=True)

        logger.info(f"MultiQueryRetriever: merged to {len(merged[:top_k])} unique docs")

        return merged[:top_k]