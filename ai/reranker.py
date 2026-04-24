# Cross-Encoder Re-Ranker for RAG System (Production Ready)

import logging
from typing import List, Dict, Tuple, Optional
import numpy as np
from functools import lru_cache

logger = logging.getLogger(__name__)


# =========================
# MODEL LOADING (SAFE)
# =========================

@lru_cache(maxsize=1)
def get_cross_encoder(model_name: str):
    """
    Singleton model loader to prevent reloading in every request.
    """
    from sentence_transformers import CrossEncoder
    return CrossEncoder(model_name)


# =========================
# DOCUMENT NORMALIZATION
# =========================

def normalize_doc(doc: Dict) -> Dict:
    """
    Standardize document format from different retrievers (Chroma, FAISS, etc.)
    """
    return {
        "text": doc.get("text") or doc.get("document", ""),
        "score": doc.get("score", 0.0) or (1 - doc.get("distance", 0.0)),
        "metadata": doc.get("metadata", {})
    }


# =========================
# CROSS-ENCODER RERANKER
# =========================

class DocumentReRanker:

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self.enabled = False
        self._load_model()

    def _load_model(self):
        try:
            self.model = get_cross_encoder(self.model_name)
            self.enabled = True
            logger.info(f"Cross-encoder loaded: {self.model_name}")
        except Exception as e:
            self.enabled = False
            logger.warning(f"Cross-encoder disabled: {e}")

    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: Optional[int] = None,
        score_field: str = "score",
        text_field: str = "text"
    ) -> List[Dict]:

        if not self.enabled or not documents:
            return documents or []

        try:
            normalized_docs = [normalize_doc(d) for d in documents]

            pairs = [
                [query, doc.get(text_field, "")]
                for doc in normalized_docs
            ]

            scores = self.model.predict(pairs)

            reranked = []
            for doc, score in zip(normalized_docs, scores):
                doc_copy = doc.copy()
                doc_copy["original_score"] = doc_copy.get(score_field, 0.0)
                doc_copy[score_field] = float(score)
                doc_copy["reranked"] = True
                reranked.append(doc_copy)

            reranked.sort(key=lambda x: x[score_field], reverse=True)

            if top_k:
                reranked = reranked[:top_k]

            if reranked:
                logger.debug(f"Top rerank score: {reranked[0][score_field]:.4f}")

            return reranked

        except Exception as e:
            logger.error(f"Rerank failed: {e}")
            return documents


# =========================
# HYBRID RERANKER
# =========================

class HybridReRanker:

    def __init__(self, cross_encoder_model: str = None):
        self.cross_encoder = DocumentReRanker(
            cross_encoder_model or "cross-encoder/ms-marco-MiniLM-L-6-v2"
        )

        # Can be moved to Django settings in production
        self.weights = {
            "cross_encoder": 0.5,
            "retrieval_score": 0.2,
            "metadata": 0.15,
            "overlap": 0.15
        }

    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: Optional[int] = None,
        text_field: str = "text"
    ) -> List[Dict]:

        if not documents:
            return []

        docs = self.cross_encoder.rerank(query, documents, top_k=None, text_field=text_field)

        for doc in docs:
            metadata_score = self._metadata_score(doc)
            overlap_score = self._overlap_score(query, doc.get(text_field, ""))

            doc["metadata_score"] = metadata_score
            doc["overlap_score"] = overlap_score

            doc["hybrid_score"] = (
                self.weights["cross_encoder"] * doc.get("score", 0.0) +
                self.weights["retrieval_score"] * doc.get("original_score", 0.0) +
                self.weights["metadata"] * metadata_score +
                self.weights["overlap"] * overlap_score
            )

        docs.sort(key=lambda x: x["hybrid_score"], reverse=True)

        if top_k:
            docs = docs[:top_k]

        if docs:
            logger.debug(f"Top hybrid score: {docs[0]['hybrid_score']:.4f}")

        return docs

    def _metadata_score(self, doc: Dict) -> float:
        meta = doc.get("metadata", {})
        score = 0.5

        if meta.get("timestamp") or meta.get("date"):
            score += 0.2

        source = str(meta.get("source", "")).lower()
        if any(k in source for k in ["policy", "guide", "official"]):
            score += 0.2

        doc_type = str(meta.get("type", "")).lower()
        if doc_type in ["policy", "rule"]:
            score += 0.15
        elif doc_type in ["guide", "manual"]:
            score += 0.1

        return min(score, 1.0)

    def _overlap_score(self, query: str, document: str) -> float:
        if not document:
            return 0.0

        try:
            q_tokens = set(query.lower().split())
            d_tokens = set(document.lower().split())

            stop_words = {
                "the", "a", "an", "is", "are", "was", "were",
                "in", "on", "at", "to", "for"
            }

            q_tokens -= stop_words
            d_tokens -= stop_words

            if not q_tokens or not d_tokens:
                return 0.0

            return len(q_tokens & d_tokens) / len(q_tokens | d_tokens)

        except Exception:
            return 0.0


# =========================
# MMR RERANKER (SAFE VERSION)
# =========================

class MMRReRanker:

    def __init__(self, lambda_param: float = 0.7):
        self.lambda_param = lambda_param

    def rerank(
        self,
        documents: List[Dict],
        top_k: int,
        score_field: str = "score"
    ) -> List[Dict]:

        if not documents or top_k <= 0:
            return []

        docs = documents.copy()
        docs.sort(key=lambda x: x.get(score_field, 0.0), reverse=True)

        selected = [docs.pop(0)]

        while len(selected) < top_k and docs:
            best_doc = None
            best_score = -1

            for doc in docs:
                relevance = doc.get(score_field, 0.0)

                diversity_penalty = max(
                    [
                        self._simple_similarity(doc, sel)
                        for sel in selected
                    ] or [0.0]
                )

                mmr = self.lambda_param * relevance - (1 - self.lambda_param) * diversity_penalty

                if mmr > best_score:
                    best_score = mmr
                    best_doc = doc

            if best_doc:
                selected.append(best_doc)
                docs.remove(best_doc)

        return selected

    def _simple_similarity(self, d1: Dict, d2: Dict) -> float:
        t1 = set(d1.get("text", "").lower().split())
        t2 = set(d2.get("text", "").lower().split())

        if not t1 or not t2:
            return 0.0

        return len(t1 & t2) / len(t1 | t2)


# =========================
# FACTORY FUNCTION
# =========================

def rerank_documents(query: str, documents: List[Dict], top_k: int = 5, method: str = "cross_encoder"):
    if method == "cross_encoder":
        return DocumentReRanker().rerank(query, documents, top_k)

    if method == "hybrid":
        return HybridReRanker().rerank(query, documents, top_k)

    if method == "mmr":
        return MMRReRanker().rerank(documents, top_k)

    return documents[:top_k]