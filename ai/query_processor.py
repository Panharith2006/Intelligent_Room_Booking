import logging
import json
import re
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class QueryProcessor:
    """
    Query Understanding & Processing with LLM-based input evaluation.
    
    Uses the INPUT MODEL for:
    - Intent classification
    - Entity extraction
    - Query decomposition/expansion
    - Complexity estimation
    - Routing decisions
    
    This model should differ from the EVALUATION model used by SelfRAG for output metrics.
    """

    def __init__(self, llm_client=None):
        # llm_client here is the INPUT model, used for query understanding and processing
        self.llm_client = llm_client

    # =========================
    # MAIN PIPELINE
    # =========================
    def process_query(self, query: str, context: Dict = None) -> Dict:

        logger.info(f"Processing query: {query[:80]}")

        # 1. Normalize (deterministic step)
        normalized = self._normalize(query)

        # 2. Unified LLM understanding (intent + entities + routing)
        llm_output = self._llm_understand_query(normalized, context)

        intent = llm_output.get("intent", {})
        entities = llm_output.get("entities", {})
        routing = llm_output.get("routing", {})

        complexity = routing.get("complexity_score", 2.5)
        execution_plan = routing.get("execution_plan", {})
        routing_strategy = routing.get("routing_strategy", "FAST_HYBRID_RETRIEVAL")

        # 3. Conditional execution (based on LLM decision only)
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
            "sub_queries": sub_queries if sub_queries else None,
            "expanded_queries": expanded_queries if expanded_queries else None,
            "complexity": complexity,
            "routing_strategy": routing_strategy,
            "execution_plan": execution_plan,
        }

    def _normalize(self, query: str) -> str:
        return query.lower().strip()

    def _llm_understand_query(self, query: str, context: Dict = None) -> Dict:

        if not self.llm_client:
            logger.warning("LLM not available, using safe fallback output")
            return self._fallback_output()

        prompt = f"""
You are a Query Understanding Agent for an Agentic RAG system.

STRICT RULES:
- Return ONLY valid JSON (no extra keys, no explanation, no markdown)
- No code blocks (no ```json or ```)
- No trailing commas
- Ensure ALL required fields are present
- Do not include any text outside JSON

TASKS:
1. Identify intent
2. Extract structured entities with correct formats
3. Decide routing strategy
4. Estimate complexity (1.0-5.0)
5. Decide if decomposition or expansion is needed

---

INTENTS:
- booking
- information
- modification
- cancellation
- availability

---

ROUTING STRATEGY:
- FAST_HYBRID_RETRIEVAL (for simple queries, complexity < 2.5)
- MULTI_QUERY_RETRIEVAL (for complex queries, complexity >= 2.5)

---

ENTITY FORMATS (use null for missing):
- date: YYYY-MM-DD format (e.g., "2026-04-30")
- start_time, end_time: HH:MM format (e.g., "14:00")
- room_type: one of [classroom, lab, conference, auditorium, library, study, other]
- equipment: array of strings (e.g., ["projector", "wifi"])
- capacity, attendees: positive integers

---

REQUIRED RESPONSE FORMAT (exact schema):
{{
  "intent": {{
    "primary": "booking|information|modification|cancellation|availability",
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

EXAMPLE:
Query: "Book a conference room with projector for 30 people tomorrow 2-4pm"
Output:
{{
  "intent": {{
    "primary": "booking",
    "confidence": 0.95
  }},
  "entities": {{
    "room_type": "conference",
    "capacity": 30,
    "attendees": 30,
    "date": "2026-04-30",
    "start_time": "14:00",
    "end_time": "16:00",
    "equipment": ["projector"]
  }},
  "routing": {{
    "complexity_score": 3.2,
    "routing_strategy": "MULTI_QUERY_RETRIEVAL",
    "execution_plan": {{
      "decompose_query": false,
      "expand_query": true
    }},
    "reason": "Multiple constraints with equipment and specific time"
  }},
  "sub_queries": []
}}

---

Query:
"{query}"

Return only JSON. No other text."""

        try:
            response = self.llm_client(prompt)
            response_text = response if isinstance(response, str) else str(response)
            
            # Safe JSON parsing with fallback
            data = self._safe_json_parse(response_text)
            
            # Normalize schema to guarantee structure
            data = self._normalize_schema(data)
            
            # Validate and clean entities
            data = self._validate_entities(data)
            
            # Constraint reasoning layer (detect conflicts, infer missing, validate logic)
            data = self._reason_constraints(data)
            
            # Clamp complexity score
            if "routing" in data and "complexity_score" in data["routing"]:
                score = float(data["routing"]["complexity_score"])
                data["routing"]["complexity_score"] = max(1.0, min(score, 5.0))

            return data

        except Exception as e:
            logger.error(f"LLM understanding failed: {e}")
            return self._fallback_output()

    # =========================
    # FALLBACK (ONLY SAFETY NET)
    # =========================
    def _fallback_output(self) -> Dict:
        return {
            "intent": {
                "primary": "information",
                "confidence": 0.5
            },
            "entities": {},
            "routing": {
                "complexity_score": 2.5,
                "routing_strategy": "FAST_HYBRID_RETRIEVAL",
                "execution_plan": {
                    "decompose_query": False,
                    "expand_query": False
                },
                "reason": "fallback mode"
            },
            "sub_queries": []
        }

    # =========================
    # SAFE JSON PARSING (ROBUST)
    # =========================
    def _safe_json_parse(self, text: str) -> Dict:
        """
        Robustly parse JSON from LLM response.
        Handles: markdown blocks, extra text, trailing commas, partial JSON.
        """
        text = text.strip()
        
        # Remove markdown code blocks (```json or ```)
        text = re.sub(r"```json\s*", "", text)
        text = re.sub(r"```\s*", "", text)
        
        # Extract first JSON object using regex
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            logger.error("No JSON object found in LLM response")
            raise ValueError("No JSON found")
        
        json_text = match.group()
        
        # Try to parse - will fail on trailing commas or malformed JSON
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON decode failed, attempting cleanup: {e}")
            # Remove trailing commas (common LLM error)
            json_text = re.sub(r",(\s*[}\]])", r"\1", json_text)
            return json.loads(json_text)

    # =========================
    # SCHEMA NORMALIZATION (GUARANTEE STRUCTURE)
    # =========================
    def _normalize_schema(self, data: Dict) -> Dict:
        """
        Ensure all required fields exist in response.
        Prevents downstream logic from breaking if LLM forgets fields.
        """
        # Top-level structure
        if not isinstance(data, dict):
            return self._fallback_output()
        
        data.setdefault("intent", {})
        data.setdefault("entities", {})
        data.setdefault("routing", {})
        data.setdefault("sub_queries", [])
        
        # Intent structure
        if not isinstance(data["intent"], dict):
            data["intent"] = {}
        data["intent"].setdefault("primary", "information")
        data["intent"].setdefault("confidence", 0.5)
        
        # Routing structure
        if not isinstance(data["routing"], dict):
            data["routing"] = {}
        data["routing"].setdefault("complexity_score", 2.5)
        data["routing"].setdefault("routing_strategy", "FAST_HYBRID_RETRIEVAL")
        data["routing"].setdefault("execution_plan", {})
        
        # Execution plan structure
        if not isinstance(data["routing"]["execution_plan"], dict):
            data["routing"]["execution_plan"] = {}
        data["routing"]["execution_plan"].setdefault("decompose_query", False)
        data["routing"]["execution_plan"].setdefault("expand_query", False)
        
        # Entities (can be empty dict)
        if not isinstance(data["entities"], dict):
            data["entities"] = {}
        
        return data

    # =========================
    # ENTITY VALIDATION
    # =========================
    def _validate_entities(self, data: Dict) -> Dict:
        """Validate and clean extracted entities."""
        entities = data.get("entities", {})
        
        # Validate date format (YYYY-MM-DD)
        if entities.get("date"):
            try:
                datetime.strptime(str(entities["date"]), "%Y-%m-%d")
            except (ValueError, TypeError):
                entities["date"] = None
        
        # Validate time format (HH:MM)
        for time_field in ["start_time", "end_time"]:
            if entities.get(time_field):
                try:
                    datetime.strptime(str(entities[time_field]), "%H:%M")
                except (ValueError, TypeError):
                    entities[time_field] = None
        
        # Validate room_type enum
        if entities.get("room_type"):
            valid_types = ["classroom", "lab", "conference", "auditorium", "library", "study", "other"]
            if str(entities["room_type"]).lower() not in valid_types:
                entities["room_type"] = None
        
        # Validate integer fields
        for int_field in ["capacity", "attendees"]:
            if entities.get(int_field):
                try:
                    entities[int_field] = int(entities[int_field])
                except (ValueError, TypeError):
                    entities[int_field] = None
        
        # Clean null values from entities
        entities = {k: v for k, v in entities.items() if v is not None}
        data["entities"] = entities
        
        return data

    # =========================
    # CONSTRAINT REASONING LAYER
    # =========================
    def _reason_constraints(self, data: Dict) -> Dict:
        """
        Semantic constraint reasoning layer:
        - Detect conflicts (capacity mismatch, impossible times)
        - Infer missing constraints (attendees → capacity)
        - Validate logical consistency
        - Return reasoning about constraints
        """
        entities = data.get("entities", {})
        constraints = {
            "conflicts": [],
            "inferred": [],
            "missing_for_intent": [],
            "valid": True
        }
        
        # Detect capacity conflicts
        if "capacity" in entities and "attendees" in entities:
            if entities["attendees"] > entities["capacity"]:
                constraints["conflicts"].append(
                    f"Attendees ({entities['attendees']}) > Capacity ({entities['capacity']})"
                )
                constraints["valid"] = False
        
        # Detect impossible time ranges
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
        
        # Infer missing capacity from attendees
        if "attendees" in entities and "capacity" not in entities:
            # Use attendees as capacity (user knows how many people will be there)
            entities["capacity"] = entities["attendees"]
            constraints["inferred"].append(
                f"Inferred capacity = attendees ({entities['attendees']})"
            )
        
        # Infer missing attendees from capacity (if no attendees specified, assume full capacity needed)
        if "capacity" in entities and "attendees" not in entities and "booking" in data.get("intent", {}).get("primary", ""):
            # Only infer for booking intent
            entities["attendees"] = entities["capacity"]
            constraints["inferred"].append(
                f"Inferred attendees = capacity ({entities['capacity']}) for booking intent"
            )
        
        # Validate required fields by intent
        intent_primary = data.get("intent", {}).get("primary", "information")
        
        if intent_primary == "booking":
            # Booking requires at least date and time range
            if "date" not in entities:
                constraints["missing_for_intent"].append("date (required for booking)")
            if "start_time" not in entities or "end_time" not in entities:
                constraints["missing_for_intent"].append("start_time or end_time (required for booking)")
        
        elif intent_primary == "availability":
            # Availability check requires at least date or date + time
            if "date" not in entities:
                constraints["missing_for_intent"].append("date (required for availability check)")
        
        elif intent_primary == "modification" or intent_primary == "cancellation":
            # Modification/cancellation might need booking ID or original details
            if not entities or (len(entities) < 1):
                constraints["missing_for_intent"].append("booking details or ID (required for modification/cancellation)")
        
        # Add reasoning to routing
        if "routing" not in data:
            data["routing"] = {}
        data["routing"]["constraint_reasoning"] = constraints
        
        # Update valid flag
        data["routing"]["constraints_valid"] = constraints["valid"]
        
        logger.info(f"Constraint reasoning: {constraints}")
        
        return data

    # =========================
    # DECOMPOSITION (MULTI-INTENT DETECTION - LLM-based)
    # =========================
    def decompose_query(self, query: str) -> List[str]:
        """
        Smart multi-intent detection using LLM.
        Detects if query contains multiple distinct intents that need separate handling.
        Not just keyword splitting - semantic analysis.
        
        Examples:
        - "Book A2 and check B3 availability" → 2 intents (booking + availability)
        - "Book room with projector and WiFi" → 1 intent (just multiple constraints)
        - "Can I book tomorrow and modify next week's booking?" → 2 intents (booking + modification)
        """
        
        if not self.llm_client:
            # Fallback: simple regex split on "and" if LLM unavailable
            return [q.strip() for q in re.split(r"\band\b", query, flags=re.IGNORECASE) if q.strip()]
        
        decomposition_prompt = f"""
Analyze this query to detect multiple distinct intents.
Return sub-queries only if the query contains multiple separate intents/goals.

IMPORTANT DISTINCTION:
- Multiple CONSTRAINTS = Same intent → Do NOT decompose
  Example: "room with projector and WiFi" = booking intent with constraints
  
- Multiple INTENTS = Different goals → DO decompose
  Example: "book room A2 and check availability B3" = 2 separate intents
  Example: "modify booking and check cancellation policy" = 2 separate intents

Intents: booking, information, modification, cancellation, availability

Query: "{query}"

Return JSON:
{{
  "has_multiple_intents": true or false,
  "sub_queries": [
    "sub-query 1",
    "sub-query 2"
  ],
  "reasoning": "brief explanation"
}}

Return empty sub_queries list if single intent."""
        
        try:
            response = self.llm_client(decomposition_prompt)
            response_text = response if isinstance(response, str) else str(response)
            
            # Safe JSON parsing
            data = self._safe_json_parse(response_text)
            
            if data.get("has_multiple_intents", False):
                sub_queries = data.get("sub_queries", [])
                if isinstance(sub_queries, list) and len(sub_queries) > 1:
                    logger.info(f"Multi-intent detected: {len(sub_queries)} sub-queries")
                    return [q.strip() for q in sub_queries if q.strip()]
            
            logger.info("Single intent detected, no decomposition needed")
            return []
            
        except Exception as e:
            logger.warning(f"Multi-intent detection failed: {e}, using fallback")
            # Fallback: simple regex split on "and"
            return [q.strip() for q in re.split(r"\band\b", query, flags=re.IGNORECASE) if q.strip()]

    # =========================
    # EXPANSION
    # =========================
    def expand_query(self, query: str, entities: Dict) -> List[str]:

        expanded = [query]

        synonyms = {
            "book": ["reserve", "schedule"],
            "room": ["space", "area"],
            "need": ["want", "require"],
        }

        for word, syns in synonyms.items():
            for syn in syns:
                if word in query:
                    expanded.append(query.replace(word, syn))

        if entities.get("capacity"):
            expanded.append(f"room for {entities['capacity']} people")

        return expanded[:5]


# =========================
# FACTORY
# =========================
def process_query(query: str, context: Dict = None, llm_client=None):
    return QueryProcessor(llm_client=llm_client).process_query(query, context)