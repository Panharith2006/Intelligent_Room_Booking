import logging
from typing import List, Dict, Optional
from functools import lru_cache

logger = logging.getLogger(__name__)


# =============================================================================
# SHARED UTILITIES
# =============================================================================

def _jaccard(a: str, b: str) -> float:
    """Token-level Jaccard similarity with stopword removal."""
    _STOPWORDS = {
        "the", "a", "an", "is", "are", "was", "were",
        "in", "on", "at", "to", "for",
    }
    t1 = set(a.lower().split()) - _STOPWORDS
    t2 = set(b.lower().split()) - _STOPWORDS
    if not t1 or not t2:
        return 0.0
    return len(t1 & t2) / len(t1 | t2)


def normalize_doc(doc: Dict) -> Dict:
    """
    Normalise varied document shapes into a consistent format.

    Score precedence: explicit "score" field → distance inversion → 0.0.
    Uses `is None` so a legitimate score of 0.0 is not discarded.
    """
    raw_score = doc.get("score")
    if raw_score is None:
        distance = doc.get("distance")
        raw_score = (1.0 - distance) if distance is not None else 0.0

    return {
        "text": doc.get("text") or doc.get("document", ""),
        "score": float(raw_score),
        "metadata": doc.get("metadata", {}),
    }


# =============================================================================
# MODEL LOADING
# =============================================================================
@lru_cache(maxsize=4)
def _get_cross_encoder(model_name: str):
    """Load and cache a CrossEncoder by name. One instance per model name."""
    from sentence_transformers import CrossEncoder
    return CrossEncoder(model_name)


_DEFAULT_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"


# =============================================================================
# CROSS-ENCODER RERANKER
# =============================================================================

class DocumentReRanker:
    def __init__(self, model_name: str = _DEFAULT_MODEL):
        self.model_name = model_name
        self.model = None
        self.enabled = False
        self._load_model()

    def _load_model(self):
        try:
            self.model = _get_cross_encoder(self.model_name)
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
        text_field: str = "text",
    ) -> List[Dict]:

        if not self.enabled or not documents:
            return documents or []

        try:
            normalized = [normalize_doc(d) for d in documents]
            pairs = [[query, doc.get(text_field, "")] for doc in normalized]
            scores = self.model.predict(pairs)

            reranked = []
            for doc, score in zip(normalized, scores):
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


# =============================================================================
# HYBRID RERANKER
# =============================================================================
# cross_encoder: learned relevance from the cross-encoder model
# retrieval_score: original vector/keyword similarity from the retriever
# overlap: lightweight token overlap as a grounding signal
_DEFAULT_WEIGHTS = {
    "cross_encoder": 0.6,
    "retrieval_score": 0.25,
    "overlap": 0.15,
}


class HybridReRanker:
    def __init__(
        self,
        cross_encoder_model: str = None,
        weights: Dict[str, float] = None,
    ):
        self.cross_encoder = DocumentReRanker(cross_encoder_model or _DEFAULT_MODEL)
        self.weights = weights or _DEFAULT_WEIGHTS

    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: Optional[int] = None,
        text_field: str = "text",
    ) -> List[Dict]:

        if not documents:
            return []

        docs = self.cross_encoder.rerank(query, documents, top_k=None, text_field=text_field)

        for doc in docs:
            overlap_score = _jaccard(query, doc.get(text_field, ""))
            doc["overlap_score"] = overlap_score
            doc["hybrid_score"] = (
                self.weights["cross_encoder"] * doc.get("score", 0.0)
                + self.weights["retrieval_score"] * doc.get("original_score", 0.0)
                + self.weights["overlap"] * overlap_score
            )

        docs.sort(key=lambda x: x["hybrid_score"], reverse=True)

        if top_k:
            docs = docs[:top_k]

        if docs:
            logger.debug(f"Top hybrid score: {docs[0]['hybrid_score']:.4f}")

        return docs


# =============================================================================
# MMR RERANKER
# =============================================================================

class MMRReRanker:
    """
    Maximal Marginal Relevance: balances relevance against diversity.
    lambda_param=1.0 → pure relevance, 0.0 → pure diversity.
    """
    def __init__(self, lambda_param: float = 0.7):
        self.lambda_param = lambda_param

    def rerank(
        self,
        documents: List[Dict],
        top_k: int,
        score_field: str = "score",
    ) -> List[Dict]:

        if not documents or top_k <= 0:
            return []

        docs = sorted(documents, key=lambda x: x.get(score_field, 0.0), reverse=True)
        selected = [docs.pop(0)]

        while len(selected) < top_k and docs:
            best_doc, best_score = None, float("-inf")

            for doc in docs:
                relevance = doc.get(score_field, 0.0)
                diversity_penalty = max(
                    (_jaccard(doc.get("text", ""), sel.get("text", "")) for sel in selected),
                    default=0.0,
                )
                mmr = self.lambda_param * relevance - (1 - self.lambda_param) * diversity_penalty

                if mmr > best_score:
                    best_score = mmr
                    best_doc = doc

            if best_doc:
                selected.append(best_doc)
                docs.remove(best_doc)

        return selected


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

_cross_encoder_instance: Optional[DocumentReRanker] = None
_hybrid_instance: Optional[HybridReRanker] = None


def rerank_documents(
    query: str,
    documents: List[Dict],
    top_k: int = 5,
    method: str = "cross_encoder",
) -> List[Dict]:
    """
    Convenience wrapper. Uses module-level singletons so the CrossEncoder
    model is loaded once regardless of how many times this is called.
    """
    global _cross_encoder_instance, _hybrid_instance

    if method == "cross_encoder":
        if _cross_encoder_instance is None:
            _cross_encoder_instance = DocumentReRanker()
        return _cross_encoder_instance.rerank(query, documents, top_k)

    if method == "hybrid":
        if _hybrid_instance is None:
            _hybrid_instance = HybridReRanker()
        return _hybrid_instance.rerank(query, documents, top_k)

    if method == "mmr":
        return MMRReRanker().rerank(documents, top_k)

    return documents[:top_k]