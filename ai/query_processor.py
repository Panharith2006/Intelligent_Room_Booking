import logging
import json
import re
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class QueryProcessor:
    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    # =========================================================================
    # MAIN PIPELINE
    # =========================================================================

    def process_query(self, query: str, context: Dict = None) -> Dict:
        logger.info(f"Processing query: {query[:80]}")

        normalized = self._normalize(query)
        llm_output = self._llm_understand_query(normalized, context)

        intent = llm_output.get("intent", {})
        entities = llm_output.get("entities", {})
        routing = llm_output.get("routing", {})

        complexity = routing.get("complexity_score", 2.5)
        execution_plan = routing.get("execution_plan", {})
        routing_strategy = routing.get("routing_strategy", "FAST_HYBRID_RETRIEVAL")

        sub_queries = []
        if execution_plan.get("decompose_query", False):
            logger.info("LLM decided: decomposition enabled")
            sub_queries = llm_output.get("sub_queries", []) or self.decompose_query(normalized)

        expanded_queries = []
        if execution_plan.get("expand_query", False):
            logger.info("LLM decided: expansion enabled")
            expanded_queries = self.expand_query(normalized, entities)

        return {
            "original_query": query,
            "normalized_query": normalized,
            "intent": intent,
            "entities": entities,
            "sub_queries": sub_queries or None,
            "expanded_queries": expanded_queries or None,
            "complexity": complexity,
            "routing_strategy": routing_strategy,
            "execution_plan": execution_plan,
        }

    def _normalize(self, query: str) -> str:
        return query.lower().strip()

    # =========================================================================
    # LLM QUERY UNDERSTANDING
    # =========================================================================

    def _llm_understand_query(self, query: str, context: Dict = None) -> Dict:
        if not self.llm_client:
            logger.warning("LLM not available, using safe fallback output")
            return self._fallback_output()

        prompt = f"""You are a Query Understanding Agent for an Agentic RAG system.

STRICT RULES:
- Return ONLY valid JSON (no extra keys, no explanation, no markdown)
- No code blocks (no ```json or ```)
- No trailing commas
- Ensure ALL required fields are present

TASKS:
1. Identify intent
2. Extract structured entities with correct formats
3. Decide routing strategy
4. Estimate complexity (1.0-5.0)
5. Decide if decomposition or expansion is needed

INTENTS:
- booking: User wants to book a room or find available rooms
- information: Questions about policies, how-to guides, FAQs
- user_profile: Questions about user's own data (name, email, student_id, position, phone)
- user_history: Questions about user's bookings, history, statistics
- modification: User wants to modify an existing booking
- cancellation: User wants to cancel a booking
- availability: User checking room availability without booking

ROUTING STRATEGY:
- FAST_HYBRID_RETRIEVAL (simple queries, complexity < 2.5)
- MULTI_QUERY_RETRIEVAL (complex queries, complexity >= 2.5)

ENTITY FORMATS (use null for missing):
- date: YYYY-MM-DD
- start_time, end_time: HH:MM
- room_type: one of [classroom, lab, conference, auditorium, library, study, other]
- equipment: array of strings
- capacity, attendees: positive integers

REQUIRED RESPONSE FORMAT:
{{
  "intent": {{
    "primary": "booking|information|user_profile|user_history|modification|cancellation|availability",
    "confidence": 0.75
  }},
  "entities": {{
    "room_number": null,
    "room_type": null,
    "capacity": null,
    "attendees": null,
    "date": null,
    "start_time": null,
    "end_time": null,
    "purpose": null,
    "equipment": []
  }},
  "routing": {{
    "complexity_score": 3.2,
    "routing_strategy": "MULTI_QUERY_RETRIEVAL",
    "execution_plan": {{
      "decompose_query": false,
      "expand_query": true
    }},
    "reason": "brief explanation"
  }},
  "sub_queries": []
}}

Query: "{query}"

Return only JSON. No other text."""

        try:
            response = self.llm_client(prompt)
            response_text = response if isinstance(response, str) else str(response)

            data = self._safe_json_parse(response_text)
            data = self._normalize_schema(data)
            data = self._validate_entities(data)
            data = self._reason_constraints(data)

            if "routing" in data and "complexity_score" in data["routing"]:
                score = float(data["routing"]["complexity_score"])
                data["routing"]["complexity_score"] = max(1.0, min(score, 5.0))

            return data

        except Exception as e:
            logger.warning(f"LLM understanding failed (falling back): {e}")
            return self._fallback_output()

    # =========================================================================
    # QUERY DECOMPOSITION  (LLM-only, no regex fallback)
    # =========================================================================

    def decompose_query(self, query: str) -> List[str]:
        if not self.llm_client:
            logger.warning("Decomposition skipped: no LLM client available")
            return []

        prompt = f"""Analyze this query to detect multiple distinct intents.
Return sub-queries ONLY if the query contains multiple separate goals.

IMPORTANT DISTINCTION:
- Multiple CONSTRAINTS on the same goal → Do NOT decompose
  Example: "room with projector and WiFi for 20 people" = single booking intent
- Multiple distinct GOALS → DO decompose
  Example: "book room A2 and check cancellation policy" = 2 separate intents

Intents: booking, information, modification, cancellation, availability, user_profile, user_history

Query: "{query}"

Return JSON only:
{{
  "has_multiple_intents": true,
  "sub_queries": ["sub-query 1", "sub-query 2"],
  "reasoning": "brief explanation"
}}"""

        try:
            response = self.llm_client(prompt)
            data = self._safe_json_parse(
                response if isinstance(response, str) else str(response)
            )

            if data.get("has_multiple_intents", False):
                sub_queries = [q.strip() for q in data.get("sub_queries", []) if q.strip()]
                if len(sub_queries) > 1:
                    logger.info(f"Multi-intent detected: {len(sub_queries)} sub-queries")
                    return sub_queries

            logger.info("Single intent — no decomposition")
            return []

        except Exception as e:
            logger.warning(f"Decomposition failed: {e}")
            return []

    # =========================================================================
    # QUERY EXPANSION  (LLM-only, no synonym dict)
    # =========================================================================

    def expand_query(self, query: str, entities: Dict) -> List[str]:
       
        if not self.llm_client:
            logger.warning("Expansion skipped: no LLM client available")
            return [query]

        entity_context = json.dumps(
            {k: v for k, v in entities.items() if v}, ensure_ascii=False
        )

        prompt = f"""Generate 3 alternative phrasings of the following query that preserve \
its meaning and extracted entities. The rewrites will be used to improve document retrieval, \
so focus on lexical and syntactic variation — not changing the intent.

Original query: "{query}"
Extracted entities: {entity_context}

Return JSON only:
{{
  "expanded_queries": [
    "rewrite 1",
    "rewrite 2",
    "rewrite 3"
  ]
}}"""

        try:
            response = self.llm_client(prompt)
            data = self._safe_json_parse(
                response if isinstance(response, str) else str(response)
            )

            rewrites = [q.strip() for q in data.get("expanded_queries", []) if q.strip()]
            # Always keep the original as the first entry
            all_queries = [query] + [q for q in rewrites if q != query]
            logger.info(f"Expanded to {len(all_queries)} query variations")
            return all_queries[:5]

        except Exception as e:
            logger.warning(f"Expansion failed: {e}")
            return [query]

    # =========================================================================
    # FALLBACK
    # =========================================================================

    def _fallback_output(self) -> Dict:
        return {
            "intent": {"primary": "information", "confidence": 0.5},
            "entities": {},
            "routing": {
                "complexity_score": 2.5,
                "routing_strategy": "FAST_HYBRID_RETRIEVAL",
                "execution_plan": {"decompose_query": False, "expand_query": False},
                "reason": "fallback mode",
            },
            "sub_queries": [],
        }

    # =========================================================================
    # SAFE JSON PARSING
    # =========================================================================
    def _safe_json_parse(self, text: str) -> Dict:
        text = text.strip()
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)

        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            logger.error("No JSON object found in LLM response")
            raise ValueError("No JSON found")

        json_text = match.group()

        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode failed, attempting cleanup: {e}")
            json_text = re.sub(r",(\s*[}\]])", r"\1", json_text)
            return json.loads(json_text)

    # =========================================================================
    # SCHEMA NORMALIZATION
    # =========================================================================

    def _normalize_schema(self, data: Dict) -> Dict:
        if not isinstance(data, dict):
            return self._fallback_output()

        data.setdefault("intent", {})
        data.setdefault("entities", {})
        data.setdefault("routing", {})
        data.setdefault("sub_queries", [])

        if not isinstance(data["intent"], dict):
            data["intent"] = {}
        data["intent"].setdefault("primary", "information")
        data["intent"].setdefault("confidence", 0.5)

        if not isinstance(data["routing"], dict):
            data["routing"] = {}
        data["routing"].setdefault("complexity_score", 2.5)
        data["routing"].setdefault("routing_strategy", "FAST_HYBRID_RETRIEVAL")
        data["routing"].setdefault("execution_plan", {})

        if not isinstance(data["routing"]["execution_plan"], dict):
            data["routing"]["execution_plan"] = {}
        data["routing"]["execution_plan"].setdefault("decompose_query", False)
        data["routing"]["execution_plan"].setdefault("expand_query", False)

        if not isinstance(data["entities"], dict):
            data["entities"] = {}

        return data

    # =========================================================================
    # ENTITY VALIDATION
    # =========================================================================

    def _validate_entities(self, data: Dict) -> Dict:
        entities = data.get("entities", {})

        if entities.get("date"):
            try:
                datetime.strptime(str(entities["date"]), "%Y-%m-%d")
            except (ValueError, TypeError):
                entities["date"] = None

        for time_field in ["start_time", "end_time"]:
            if entities.get(time_field):
                try:
                    datetime.strptime(str(entities[time_field]), "%H:%M")
                except (ValueError, TypeError):
                    entities[time_field] = None

        if entities.get("room_type"):
            valid_types = ["classroom", "lab", "conference", "auditorium", "library", "study", "other"]
            if str(entities["room_type"]).lower() not in valid_types:
                entities["room_type"] = None

        for int_field in ["capacity", "attendees"]:
            if entities.get(int_field):
                try:
                    entities[int_field] = int(entities[int_field])
                except (ValueError, TypeError):
                    entities[int_field] = None

        data["entities"] = {k: v for k, v in entities.items() if v is not None}
        return data

    # =========================================================================
    # CONSTRAINT REASONING
    # =========================================================================
    def _reason_constraints(self, data: Dict) -> Dict:
        entities = data.get("entities", {})
        constraints = {
            "conflicts": [],
            "inferred": [],
            "missing_for_intent": [],
            "valid": True,
        }

        if "capacity" in entities and "attendees" in entities:
            if entities["attendees"] > entities["capacity"]:
                constraints["conflicts"].append(
                    f"Attendees ({entities['attendees']}) > Capacity ({entities['capacity']})"
                )
                constraints["valid"] = False

        if "start_time" in entities and "end_time" in entities:
            try:
                start = datetime.strptime(entities["start_time"], "%H:%M")
                end = datetime.strptime(entities["end_time"], "%H:%M")
                if start >= end:
                    constraints["conflicts"].append(
                        f"Invalid time range: {entities['start_time']} >= {entities['end_time']}"
                    )
                    constraints["valid"] = False
            except (ValueError, TypeError):
                pass

        if "attendees" in entities and "capacity" not in entities:
            entities["capacity"] = entities["attendees"]
            constraints["inferred"].append(
                f"Inferred capacity = attendees ({entities['attendees']})"
            )

        if (
            "capacity" in entities
            and "attendees" not in entities
            and data.get("intent", {}).get("primary") == "booking"
        ):
            entities["attendees"] = entities["capacity"]
            constraints["inferred"].append(
                f"Inferred attendees = capacity ({entities['capacity']}) for booking intent"
            )

        intent_primary = data.get("intent", {}).get("primary", "information")

        if intent_primary == "booking":
            if "date" not in entities:
                constraints["missing_for_intent"].append("date (required for booking)")
            if "start_time" not in entities or "end_time" not in entities:
                constraints["missing_for_intent"].append("time range (required for booking)")

        elif intent_primary == "availability":
            if "date" not in entities:
                constraints["missing_for_intent"].append("date (required for availability check)")

        elif intent_primary in ("modification", "cancellation"):
            if not entities:
                constraints["missing_for_intent"].append(
                    "booking details or ID (required for modification/cancellation)"
                )

        data.setdefault("routing", {})
        data["routing"]["constraint_reasoning"] = constraints
        data["routing"]["constraints_valid"] = constraints["valid"]

        logger.info(f"Constraint reasoning: {constraints}")
        return data

# =============================================================================
# FACTORY
# =============================================================================
def process_query(query: str, context: Dict = None, llm_client=None) -> Dict:
    return QueryProcessor(llm_client=llm_client).process_query(query, context)