import logging
from typing import Dict, List
from enum import Enum
import time

logger = logging.getLogger(__name__)


class ReflectionType(Enum):
    # Retrieval
    CONTEXT_RECALL = "context_recall"
    CONTEXT_PRECISION = "context_precision"

    # Generation
    FAITHFULNESS = "faithfulness"
    RELEVANCE = "relevance"
    COMPLETENESS = "completeness"

    # System
    ROUTING_ACCURACY = "routing_accuracy"
    LATENCY = "latency"
    ITERATION_EFFICIENCY = "iteration_efficiency"


class SelfRAG:
    """
    Self-Reflective Agentic RAG with LLM-based output evaluation.
    
    Uses a dedicated EVALUATION MODEL for quality metrics:
    - faithfulness: Is response grounded in documents?
    - relevance: Does response address query intent?
    - completeness: Does response cover all required info?
    
    This model may differ from the INPUT model used for query processing.
    """

    def __init__(self, retriever, llm_client=None, thresholds: Dict[str, float] = None):
        self.retriever = retriever
        # llm_client here is the EVALUATION model, used only for output evaluation
        self.llm_client = llm_client

        self.thresholds = thresholds or {
            "context_recall": 0.5,
            "context_precision": 0.6,
            "faithfulness": 0.6,
            "relevance": 0.5,
            "completeness": 0.6,
            "routing_accuracy": 0.7,
            "latency_ms": 1500,
        }

        self.pipeline_metrics = {
            "total_queries": 0,
            "successful_queries": 0,
            "total_iterations": 0,
            "total_latency_ms": 0,
        }

    # =========================
    # MAIN PIPELINE
    # =========================
    def generate_with_reflection(
        self,
        query: str,
        entities: Dict = None,
        intent: str = None,
        context: Dict = None,
        max_iterations: int = 3,
        relevant_doc_ids_in_corpus: List[str] = None,
    ) -> Dict:

        start_time = time.time()
        iteration = 0
        refined_query = query
        last_result = {}

        self.pipeline_metrics["total_queries"] += 1

        # Optional ground-truth relevant IDs for standard recall/precision formulas
        if relevant_doc_ids_in_corpus is None and isinstance(context, dict):
            relevant_doc_ids_in_corpus = context.get("relevant_doc_ids_in_corpus")

        while iteration < max_iterations:

            retrieved_docs = self.retriever.retrieve(
                query=refined_query,
                entities=entities,
                intent=intent,
                top_k=5,
            )

            # =========================
            # RETRIEVAL METRICS
            # =========================
            context_recall = self._compute_context_recall(
                retrieved_docs=retrieved_docs,
                relevant_doc_ids_in_corpus=relevant_doc_ids_in_corpus,
            )
            context_precision = self._compute_context_precision(
                retrieved_docs=retrieved_docs,
                relevant_doc_ids_in_corpus=relevant_doc_ids_in_corpus,
            )

            if context_recall < self.thresholds["context_recall"]:
                refined_query = self._refine_query(query, entities, intent)
                iteration += 1
                continue

            # =========================
            # GENERATION
            # =========================
            response = self._generate_response(
                query, retrieved_docs, entities, intent, context
            )

            # =========================
            # GENERATION METRICS
            # =========================
            faithfulness = self._compute_faithfulness(response, retrieved_docs)
            relevance = self._compute_relevance(query, response)
            completeness = self._compute_completeness(response, entities)

            # =========================
            # SYSTEM METRICS
            # =========================
            routing_accuracy = self._compute_routing_accuracy(intent)
            latency_ms = (time.time() - start_time) * 1000
            self.pipeline_metrics["total_latency_ms"] += latency_ms

            iteration_efficiency = 1.0 / (iteration + 1)

            # =========================
            # SCORES
            # =========================
            evaluation_scores = {
                "context_recall": context_recall,
                "context_precision": context_precision,
                "faithfulness": faithfulness,
                "relevance": relevance,
                "completeness": completeness,
                "routing_accuracy": routing_accuracy,
                "latency_ms": latency_ms,
                "iteration_efficiency": iteration_efficiency,

                "retrieval_quality": (context_recall + context_precision) / 2,
                "generation_quality": (faithfulness + relevance + completeness) / 3,
                "overall_quality": (
                    0.3 * (context_recall + context_precision) / 2 +
                    0.5 * (faithfulness + relevance + completeness) / 3 +
                    0.2 * (1.0 - min(latency_ms / 1500, 1.0))
                ),
            }

            success = (
                context_recall >= self.thresholds["context_recall"] and
                context_precision >= self.thresholds["context_precision"] and
                faithfulness >= self.thresholds["faithfulness"] and
                relevance >= self.thresholds["relevance"] and
                completeness >= self.thresholds["completeness"] and
                routing_accuracy >= self.thresholds["routing_accuracy"]
            )

            last_result = {
                "response": response,
                "retrieved_docs": retrieved_docs,
                "evaluation_scores": evaluation_scores,
                "iterations": iteration + 1,
                "success": success,
            }

            if success:
                self.pipeline_metrics["successful_queries"] += 1
                self.pipeline_metrics["total_iterations"] += iteration + 1
                return last_result

            iteration += 1
            refined_query = self._refine_query(query, entities, intent)

        self.pipeline_metrics["total_iterations"] += max_iterations
        return last_result

    # =========================
    # RETRIEVAL METRICS
    # =========================

    def _extract_doc_id(self, doc: Dict) -> str:
        """Extract a stable document identifier from a retrieved document."""
        if not isinstance(doc, dict):
            return ""

        for key in ("id", "doc_id", "document_id", "source_id", "pk", "uuid"):
            value = doc.get(key)
            if value is not None:
                return str(value)

        return ""

    def _compute_context_recall(
        self,
        retrieved_docs: List[Dict],
        relevant_doc_ids_in_corpus: List[str] = None,
    ) -> float:
        """Standard recall formula: |Retrieved ∩ Relevant| / |Relevant|.

        If `relevant_doc_ids_in_corpus` is not provided, fall back to a
        score-based proxy to preserve runtime behavior.
        """
        if not relevant_doc_ids_in_corpus:
            return self._compute_context_recall_proxy(retrieved_docs)

        relevant_set = {str(doc_id) for doc_id in relevant_doc_ids_in_corpus}
        if not relevant_set:
            return 0.0

        retrieved_set = {
            self._extract_doc_id(d)
            for d in (retrieved_docs or [])
            if self._extract_doc_id(d)
        }
        true_positives = len(retrieved_set.intersection(relevant_set))
        return true_positives / len(relevant_set)

    def _compute_context_recall_proxy(self, retrieved_docs: List[Dict]) -> float:
        """Proxy recall when no ground-truth labels are available.

        This is not strict corpus recall; it approximates recall quality using
        retriever score magnitude and strong-hit count.
        """
        if not retrieved_docs:
            return 0.0

        raw_scores = []
        for d in retrieved_docs:
            try:
                raw_scores.append(float(d.get("score", 0.0) or 0.0))
            except Exception:
                raw_scores.append(0.0)

        min_s, max_s = min(raw_scores), max(raw_scores)
        if max_s > 1.0 or min_s < 0.0 or max_s == min_s:
            if max_s == min_s:
                norm_scores = [0.0 for _ in raw_scores]
            else:
                norm_scores = [(s - min_s) / (max_s - min_s) for s in raw_scores]
        else:
            norm_scores = raw_scores

        avg_score = sum(norm_scores) / len(norm_scores)
        bonus_denom = float(min(5, len(norm_scores))) if norm_scores else 1.0
        high_count = sum(1 for s in norm_scores if s > 0.5)
        doc_count_bonus = min(high_count / bonus_denom, 0.2)
        return min(max(avg_score + doc_count_bonus, 0.0), 1.0)

    def _compute_context_precision(
        self,
        retrieved_docs: List[Dict],
        relevant_doc_ids_in_corpus: List[str] = None,
    ) -> float:
        """Standard precision formula: |Retrieved ∩ Relevant| / |Retrieved|.

        If `relevant_doc_ids_in_corpus` is not provided, fall back to a
        score-threshold proxy to preserve runtime behavior.
        """
        retrieved_set = {
            self._extract_doc_id(d)
            for d in (retrieved_docs or [])
            if self._extract_doc_id(d)
        }
        if not relevant_doc_ids_in_corpus:
            return self._compute_context_precision_proxy(retrieved_docs)

        if not retrieved_set:
            return 0.0

        relevant_set = {str(doc_id) for doc_id in relevant_doc_ids_in_corpus}
        if not relevant_set:
            return 0.0

        true_positives = len(retrieved_set.intersection(relevant_set))
        return true_positives / len(retrieved_set)

    def _compute_context_precision_proxy(self, retrieved_docs: List[Dict]) -> float:
        """Proxy precision when no ground-truth labels are available."""
        if not retrieved_docs:
            return 0.0

        relevant = sum(
            1 for d in retrieved_docs if float(d.get("score", 0.0) or 0.0) > 0.5
        )
        return relevant / len(retrieved_docs)

    # =========================
    # GENERATION METRICS
    # =========================

    def _compute_faithfulness(self, response: str, docs: List[Dict]) -> float:
        """Evaluate faithfulness using LLM: how grounded is response in documents."""
        if not self.llm_client or not docs:
            return 0.5

        if not response:
            return 0.0

        doc_context = "\n".join(
            d.get("document") or d.get("text", "") for d in docs
        )

        prompt = f"""Evaluate how well this response is grounded in the provided documents.
Score semantic faithfulness: are claims in the response supported by the documents?

Documents:
{doc_context}

Response:
{response}

Respond with ONLY a score from 0.0 to 1.0 where:
- 1.0 = completely grounded, no hallucination
- 0.5 = mix of supported and inferred claims
- 0.0 = completely hallucinated, no grounding"""

        try:
            result = self.llm_client(prompt)
            score = float(result.strip())
            return min(max(score, 0.0), 1.0)
        except Exception as e:
            logger.warning(f"Faithfulness evaluation failed: {e}")
            return 0.5

    def _compute_relevance(self, query: str, response: str) -> float:
        """Evaluate relevance using LLM: does response address the query intent."""
        if not self.llm_client:
            return 0.5

        if not response:
            return 0.0

        prompt = f"""Evaluate how relevant the response is to the user query.
Consider semantic alignment and whether the response addresses the user's intent.

Query:
{query}

Response:
{response}

Respond with ONLY a score from 0.0 to 1.0 where:
- 1.0 = perfectly relevant
- 0.5 = partially relevant with some off-topic content
- 0.0 = completely irrelevant"""

        try:
            result = self.llm_client(prompt)
            score = float(result.strip())
            return min(max(score, 0.0), 1.0)
        except Exception as e:
            logger.warning(f"Relevance evaluation failed: {e}")
            return 0.5

    def _compute_completeness(self, response: str, entities: Dict = None) -> float:
        """Evaluate completeness using LLM: does response cover all required information."""
        if not self.llm_client or not response:
            return 0.5

        if not entities:
            # Can't evaluate completeness without entities
            return 0.5

        entities_str = "\n".join(f"- {k}: {v}" for k, v in entities.items())

        prompt = f"""Evaluate how completely the response addresses the user's requirements.
Score whether all required information is present in the response.

Required information (entities):
{entities_str}

Response:
{response}

Respond with ONLY a score from 0.0 to 1.0 where:
- 1.0 = fully complete, all required info present
- 0.5 = partially complete, some info missing
- 0.0 = completely incomplete"""

        try:
            result = self.llm_client(prompt)
            score = float(result.strip())
            return min(max(score, 0.0), 1.0)
        except Exception as e:
            logger.warning(f"Completeness evaluation failed: {e}")
            return 0.5

    # =========================
    # SYSTEM METRICS
    # =========================

    def _compute_routing_accuracy(self, intent) -> float:
        if not intent:
            return 0.5

        return 1.0  # placeholder (replace with ground truth if available)

    def get_pipeline_metrics(self) -> Dict:
        if self.pipeline_metrics["total_queries"] == 0:
            return {}

        total = self.pipeline_metrics["total_queries"]

        return {
            "success_rate": self.pipeline_metrics["successful_queries"] / total,
            "avg_iterations": self.pipeline_metrics["total_iterations"] / total,
            "avg_latency_ms": self.pipeline_metrics["total_latency_ms"] / total,
            "iteration_efficiency": 1.0 / (
                self.pipeline_metrics["total_iterations"] / total
            ),
        }

    # =========================
    # QUERY REFINEMENT
    # =========================

    def _refine_query(self, query: str, entities: Dict = None, intent=None) -> str:
        refined = query

        if entities:
            for k, v in entities.items():
                refined += f" {v}"

        if intent:
            refined += f" {intent}"

        return refined

    # =========================
    # GENERATION
    # =========================

    def _generate_response(
        self,
        query: str,
        retrieved_docs: List[Dict],
        entities: Dict = None,
        intent=None,
        context: Dict = None,
    ) -> str:

        if not retrieved_docs:
            return "No relevant information found."

        doc_context = "\n".join(
            (d.get("document") or d.get("text", "")) for d in retrieved_docs[:3]
        )

        if self.llm_client:
            try:
                prompt = f"""
Answer the question using ONLY the provided documents.

Question:
{query}

Documents:
{doc_context}

Answer:
"""
                return self.llm_client(prompt)
            except Exception:
                pass

        return doc_context[:300]