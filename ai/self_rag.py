import logging
from typing import Dict, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class ReflectionType(Enum):
    RELEVANCE = "relevance"
    SUPPORT = "support"
    UTILITY = "utility"
    COMPLETENESS = "completeness"


class SelfRAG:
    """
    Production-ready Self-RAG system with reflection and self-correction.
    """

    def __init__(self, retriever, llm_client=None, thresholds: Dict[str, float] = None):

        self.retriever = retriever
        self.llm_client = llm_client

        self.thresholds = thresholds or {
            "relevance": 0.6,
            "support": 0.7,
            "utility": 0.6,
            "completeness": 0.7,
        }

        logger.info("Self-RAG initialized")

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
    ) -> Dict:

        iteration = 0
        refined_query = query
        last_result = {}

        while iteration < max_iterations:

            retrieved_docs = self.retriever.retrieve(
                query=refined_query,
                entities=entities,
                intent=intent,
                top_k=5,
            )

            relevance = self._check_relevance(query, retrieved_docs)

            if relevance < self.thresholds["relevance"]:
                refined_query = self._refine_query(query, entities, intent)
                iteration += 1
                continue

            response = self._generate_response(
                query=query,
                retrieved_docs=retrieved_docs,
                entities=entities,
                intent=intent,
                context=context,
            )

            support = self._check_support(response, retrieved_docs)
            utility = self._check_utility(query, response, intent, entities)
            completeness = self._check_completeness(response)

            scores = {
                "relevance": relevance,
                "support": support,
                "utility": utility,
                "completeness": completeness,
                "overall": (relevance + support + utility + completeness) / 4,
            }

            last_result = {
                "response": response,
                "retrieved_docs": retrieved_docs,
                "reflection_scores": scores,
                "iterations": iteration + 1,
                "success": all(
                    [
                        relevance >= self.thresholds["relevance"],
                        support >= self.thresholds["support"],
                        utility >= self.thresholds["utility"],
                        completeness >= self.thresholds["completeness"],
                    ]
                ),
            }

            if last_result["success"]:
                return last_result

            iteration += 1
            refined_query = self._refine_query(query, entities, intent)

        return last_result

    # =========================
    # REFLECTION FUNCTIONS
    # =========================

    def _check_relevance(self, query: str, docs: List[Dict]) -> float:
        if not docs:
            return 0.0

        scores = [d.get("score", 0.5) for d in docs]
        return sum(scores) / len(scores)

    def _check_support(self, response: str, docs: List[Dict]) -> float:
        if not response or not docs:
            return 0.0

        text = " ".join(
            d.get("document") or d.get("text", "") for d in docs
        ).lower()

        words = response.lower().split()
        matches = sum(1 for w in words if w in text)

        return min(matches / max(len(words), 1), 1.0)

    def _check_utility(self, query, response, intent, entities) -> float:
        if not response:
            return 0.0

        score = 0.5
        r = response.lower()

        if intent == "booking" or (isinstance(intent, dict) and intent.get("primary") == "booking"):
            if any(k in r for k in ["room", "available", "book"]):
                score += 0.3

        if len(response.split()) > 10:
            score += 0.2

        return min(score, 1.0)

    def _check_completeness(self, response: str) -> float:
        if not response:
            return 0.0

        keywords = ["room", "time", "capacity", "available", "building"]
        found = sum(1 for k in keywords if k in response.lower())

        return found / len(keywords)

    # =========================
    # QUERY REFINEMENT
    # =========================

    def _refine_query(self, query, entities, intent):
        refined = query

        if entities:
            if entities.get("capacity"):
                refined += f" {entities['capacity']} people"
            if entities.get("building"):
                refined += f" building {entities['building']}"

        if isinstance(intent, dict):
            intent = intent.get("primary")

        if intent == "booking":
            refined += " available rooms book reserve"

        return refined

    # =========================
    # RESPONSE GENERATION
    # =========================

    def _generate_response(self, query, retrieved_docs, entities, intent, context):

        if not retrieved_docs:
            return "No relevant information found."

        top = retrieved_docs[0]
        doc = top.get("document") or top.get("text", "")

        if isinstance(intent, dict):
            intent = intent.get("primary")

        if intent == "booking":
            return f"I found relevant booking information:\n{doc[:300]}"

        return doc[:300]