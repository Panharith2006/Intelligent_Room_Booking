import logging
import re
from typing import Dict, List, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueryProcessor:

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

        # =========================
        # INTENT PATTERNS
        # =========================
        self.intent_patterns = {
            "booking": [
                r"\b(book|reserve|schedule|get|need|want)\b.*\b(room|space)\b",
                r"\bi\s+(need|want|require)\b.*\b(room|space)\b",
                r"\broom\s+for\b",
            ],
            "information": [
                r"\b(what|how|when|where|why|tell|explain)\b",
                r"\b(policy|rule|guideline|information)\b",
            ],
            "modification": [
                r"\b(change|modify|update|reschedule|edit)\b",
            ],
            "cancellation": [
                r"\b(cancel|delete|remove)\b.*\b(booking|reservation)\b",
            ],
            "availability": [
                r"\b(available|free|vacant|open)\b",
                r"\bcheck\s+availability\b",
            ],
        }

    # =========================
    # MAIN PIPELINE
    # =========================
    def process_query(self, query: str, context: Dict = None) -> Dict:

        logger.info(f"Processing query: {query[:80]}")

        normalized = self._normalize(query)
        intent = self.classify_intent(normalized)
        entities = self.extract_entities(normalized, context)

        sub_queries = self.decompose_query(normalized)
        expanded = self.expand_query(normalized, entities)

        complexity = self._complexity(normalized, entities, sub_queries)

        return {
            "original_query": query,
            "normalized_query": normalized,
            "intent": intent,
            "entities": entities,
            "sub_queries": sub_queries,
            "expanded_queries": expanded,
            "complexity": complexity,
        }

    # =========================
    # NORMALIZATION
    # =========================
    def _normalize(self, query: str) -> str:
        query = query.lower().strip()
        query = re.sub(r"\s+", " ", query)
        query = re.sub(r"[^\w\s\-:,.?!]", "", query)
        return query

    # =========================
    # INTENT CLASSIFICATION
    # =========================
    def classify_intent(self, query: str) -> Dict:

        scores = {}

        for intent, patterns in self.intent_patterns.items():
            score = sum(
                1 for p in patterns if re.search(p, query, re.IGNORECASE)
            )

            if score:
                scores[intent] = min(score / len(patterns), 1.0)

        if not scores:
            scores = {"information": 0.5}

        primary = max(scores, key=scores.get)

        return {
            "primary": primary,
            "scores": scores,
            "confidence": scores[primary],
        }

    # =========================
    # ENTITY EXTRACTION
    # =========================
    def extract_entities(self, query: str, context: Dict = None) -> Dict:

        entities = {}

        # DATE
        date = self._extract_date(query)
        if date:
            entities["date"] = date
        elif context and context.get("date"):
            entities["date"] = context["date"]

        # TIME
        start, end = self._extract_time(query)
        if start:
            entities["start_time"] = start
        if end:
            entities["end_time"] = end

        # fallback context
        if context:
            entities.setdefault("start_time", context.get("start_time"))
            entities.setdefault("end_time", context.get("end_time"))

        # CAPACITY
        cap = self._extract_capacity(query)
        if cap:
            entities["capacity"] = cap

        # ROOM
        room = re.search(r"\b([A-Z]\d{2,4})\b", query, re.IGNORECASE)
        if room:
            entities["room_number"] = room.group(1).upper()

        # BUILDING
        building = re.search(r"\bbuilding\s+([A-Z])\b", query, re.IGNORECASE)
        if building:
            entities["building"] = building.group(1).upper()

        # PURPOSE
        purpose = re.search(
            r"\b(meeting|lecture|conference|workshop|lab|exam)\b",
            query,
            re.IGNORECASE,
        )
        if purpose:
            entities["purpose"] = purpose.group(1).lower()

        return {k: v for k, v in entities.items() if v is not None}

    # =========================
    # DATE
    # =========================
    def _extract_date(self, query: str) -> Optional[str]:

        today = datetime.now()

        if "today" in query:
            return today.strftime("%Y-%m-%d")

        if "tomorrow" in query:
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")

        match = re.search(r"in\s+(\d+)\s+days?", query)
        if match:
            return (today + timedelta(days=int(match.group(1)))).strftime("%Y-%m-%d")

        return None

    # =========================
    # TIME
    # =========================
    def _extract_time(self, query: str):

        times = []

        matches = re.findall(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)?\b", query)

        for h, m, mer in matches:
            hour = int(h)
            minute = int(m) if m else 0

            if mer == "pm" and hour < 12:
                hour += 12
            if mer == "am" and hour == 12:
                hour = 0

            times.append(f"{hour:02d}:{minute:02d}")

        if len(times) >= 2:
            return times[0], times[1]

        if len(times) == 1:
            start = times[0]
            h = (int(start.split(":")[0]) + 2) % 24
            return start, f"{h:02d}:00"

        return None, None

    # =========================
    # CAPACITY
    # =========================
    def _extract_capacity(self, query: str) -> Optional[int]:
        match = re.search(r"\b(\d+)\s*(people|person|students?)\b", query)
        return int(match.group(1)) if match else None

    # =========================
    # DECOMPOSE
    # =========================
    def decompose_query(self, query: str) -> List[str]:
        return [q.strip() for q in re.split(r"\band\b", query) if q.strip()]

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

        if "capacity" in entities:
            expanded.append(f"room for {entities['capacity']} people")

        return expanded[:5]

    # =========================
    # COMPLEXITY
    # =========================
    def _complexity(self, query: str, entities: Dict, sub_queries: List[str]) -> int:

        score = 1

        if len(entities) > 3:
            score += 1
        if len(query.split()) > 15:
            score += 1
        if len(sub_queries) > 1:
            score += 1

        return min(score, 5)


# =========================
# FACTORY
# =========================
def process_query(query: str, context: Dict = None):
    return QueryProcessor().process_query(query, context)