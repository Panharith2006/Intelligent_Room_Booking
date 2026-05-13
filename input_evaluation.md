# Input Evaluation Metrics

## 1. Query Normalization

**Definition:** Standardize raw user input for consistent processing downstream.

**Process:**
```
1. Lowercase conversion
2. Whitespace normalization (collapse multiple spaces to single space)
3. Special character removal (keep only alphanumeric, hyphen, colon, comma, period, question mark, exclamation)
4. Trim leading/trailing whitespace
```

**Formula:**
```
normalized_query = query.lower().strip()

Simple deterministic normalization 
Entity extraction and special character handling moved to LLM stage.
```

**Implementation in query_processor.py:**
```python
def _normalize(self, query: str) -> str:
    """Simple deterministic normalization."""
    return query.lower().strip()
```

**Note:** Current implementation uses simple lowercase + strip (no regex). Complex regex removed to keep deterministic step simple. Entity extraction and special character handling are now done by LLM stage.

**Example:**
```
Raw:       "Can I  Book   Room A2?? ($$$)"
Normalized: "can i book room a2"
```

---

## 2. Intent Classification (LLM-based)

**Definition:** Determine user's intent (what action they want to perform) using local LLM inference.

**Supported Intents:**
- `booking`: User wants to reserve/book a room
- `information`: User seeks policy or FAQ information
- `modification`: User wants to change existing booking
- `cancellation`: User wants to cancel a booking
- `availability`: User checks room availability

**Formula:**
```
Intent = LLM_Classify(query, intent_categories)

Intent_Prompt:
  "Classify the intent of this room booking query into ONE of: 
   booking, information, modification, cancellation, availability.
   
   Query: '{normalized_query}'
   
   Respond with ONLY:
   intent: [one of the above]
   confidence: [0.0 to 1.0]"

Response Parsing:
  primary_intent = extract_intent_from_response(llm_output)
  confidence = extract_confidence_from_response(llm_output)
  
  if primary_intent not in valid_intents:
    primary_intent = "information"  # Default fallback
    confidence = 0.5
```

**Implementation in query_processor.py:**
```python
# Intent classification is now part of the UNIFIED LLM understanding call
# See _llm_understand_query() below

def _llm_understand_query(self, query: str, context: Dict = None) -> Dict:
    """
    Unified LLM understanding - single call returns:
    {intent, entities, routing, sub_queries, complexity}
    
    This consolidates:
    - Intent classification
    - Entity extraction
    - Complexity scoring
    - Routing decision
    - Multi-intent detection
    
    Into ONE LLM call for efficiency and consistency.
    """
    # Single LLM prompt returns all understanding in one JSON response
    # Includes intent, entities, routing with complexity_score and execution_plan
```

**Output Structure:**
```python
{
    "primary": "booking",           # Main intent
    "scores": {"booking": 0.95},    # Intent confidence
    "confidence": 0.95              # Overall confidence (0-1)
}
```

**Interpretation:**
- **0.85-1.0**: Very high confidence - Clear user intent
- **0.65-0.85**: High confidence - Intent well-determined
- **0.50-0.65**: Medium confidence - Some ambiguity
- **< 0.50**: Low confidence - Intent unclear, fallback to general approach

**Reference:** 
- Gangadharaiah & Narayana (2016). "Intent Detection in Conversational AI"
- BERT-based Intent Classification: Devlin et al. (2019)

---

## 2.5 Router/Control Agent (Agentic Decision Layer)

**Definition:** Autonomous agent that decides which processing steps to execute, skip, or repeat based on query characteristics and current state.

**Decision Framework:**
```
Router evaluates query and decides:
  1. RUN_STEP: Always execute (normalization, intent classification)
  2. SKIP_STEP: Skip if unnecessary (e.g., decomposition for single-intent queries)
  3. REPEAT_STEP: Re-run if needed (e.g., re-extract entities if incomplete)
  4. ROUTE_STRATEGY: Determine retrieval approach (fast vs multi-query)
```

**Router Logic:**
```
Router_Decision(normalized_query, intent, entities, complexity):

  # NORMALIZATION (always)
  ALWAYS_RUN(normalize)
  
  # INTENT CLASSIFICATION (always)
  ALWAYS_RUN(classify_intent)
  
  # ENTITY EXTRACTION (always, but validate result)
  ALWAYS_RUN(extract_entities)
  IF entities_count < 1 AND intent != "information":
    REPEAT(extract_entities)  # Re-run if too few entities for booking
  
  # DECOMPOSITION (conditional, LLM-based multi-intent detection)
  LLM detects if query has multiple DISTINCT INTENTS (not just constraints)
  IF LLM.has_multiple_intents == true:
    RUN(decompose_query)  # Split into sub-queries
    ROUTING_STRATEGY = "MULTI_QUERY_RETRIEVAL"
  ELSE:
    SKIP(decompose_query)  # Single intent, keep as-is
  
  # COMPLEXITY SCORING (semantic LLM-based)
  semantic_complexity = LLM_Score_Complexity(query, entities, intent)
  
  # EXPANSION (conditional)
  IF semantic_complexity >= 2.5:
    RUN(expand_query)      # Multi-query retrieval for complex queries
    ROUTING_STRATEGY = "MULTI_QUERY_RETRIEVAL"
  ELSE:
    SKIP(expand_query)     # Fast path for simple queries
    ROUTING_STRATEGY = "FAST_HYBRID_RETRIEVAL"
  
  RETURN {
    execution_plan: {normalize, classify_intent, extract_entities, [decompose_query], [expand_query]},
    routing_strategy: ROUTING_STRATEGY,
    complexity_score: semantic_complexity,
    sub_queries: [LLM_detected_intents] or []
  }
```

**Agentic Benefits:**
- ✅ Eliminates unnecessary computations (skip decomposition for constraint-heavy queries)
- ✅ Semantic decomposition (detects actual intent boundaries, not just "and")
- ✅ Validates intermediate results (re-extract if entities too sparse)
- ✅ Semantic routing (complexity goes beyond discrete counting)
- ✅ Fallback mechanisms (repeat failed steps automatically)
- ✅ Adaptive behavior (adjusts processing based on query characteristics)

**Implementation in query_processor.py:**

Router is now integrated INTO the unified LLM call. The LLM itself decides:

```python
# LLM response includes routing decision:
"routing": {
    "complexity_score": 3.2,         # LLM-determined semantic complexity
    "routing_strategy": "MULTI_QUERY_RETRIEVAL",  # Based on complexity
    "execution_plan": {
        "decompose_query": false,     # LLM decides if multi-intent
        "expand_query": true          # LLM decides if expansion needed
    },
    "reason": "explanation"
}

# Main process_query() then conditionally runs based on execution_plan:
if execution_plan.get("decompose_query", False):
    sub_queries = self.decompose_query(normalized)  # LLM-based multi-intent detection

if execution_plan.get("expand_query", False):
    expanded_queries = self.expand_query(normalized, entities)  # Synonym expansion
```

**Routing Decision Rules (LLM-decided):**
- Complexity >= 2.5 → MULTI_QUERY_RETRIEVAL
- Complexity < 2.5 → FAST_HYBRID_RETRIEVAL

---

## 3. Entity Extraction (LLM-based)

**Definition:** Extract relevant entities from query using local LLM inference (room number, date, time, capacity, building, purpose, equipment).

**Supported Entities:**
- `room_number`: Room code (e.g., A101, B205)
- `room_type`: Type of room (classroom, lab, conference, auditorium, library, study, other)
- `capacity`: Maximum capacity needed for the room
- `attendees`: Number of people actually attending
- `date`: Booking date in YYYY-MM-DD format
- `start_time`: Start time in HH:MM format
- `end_time`: End time in HH:MM format
- `purpose`: Purpose of booking (meeting, lecture, conference, workshop, lab, exam)
- `equipment`: List of required equipment (projector, whiteboard, computer, wifi, etc.)

**Formula:**
```
entities = LLM_Extract(query, entity_types)

Entity_Prompt:
  "Extract structured entities from this room booking query.
   
   Query: '{normalized_query}'
   
   Extract and return ONLY valid JSON (no markdown, no extra text):
   {
       "room_number": "<room code like A101, B205, or null>",
       "room_type": "<conference/meeting/lecture/lab/classroom/auditorium/study/other or null>",
       "capacity": "<maximum people needed for room, integer or null>",
       "attendees": "<number of people attending, integer or null>",
       "date": "<YYYY-MM-DD format or null>",
       "start_time": "<HH:MM format or null>",
       "end_time": "<HH:MM format or null>",
       "purpose": "<purpose of booking or null>",
       "equipment": [<list of equipment like 'projector', 'whiteboard', 'computer', 'wifi', or empty list>]
   }
   
   Return only valid JSON. Convert all values to null if not found."

Response Parsing:
  1. Clean response (remove markdown code blocks if present)
  2. Parse JSON
  3. Validate and normalize each field:
     - room_number: uppercase, strip whitespace
     - room_type: lowercase, validate against allowed values
     - capacity/attendees: convert to integer
     - date: validate YYYY-MM-DD format
     - start_time/end_time: validate HH:MM format
     - purpose: lowercase, strip whitespace
     - equipment: list of lowercase strings
  4. Filter out None values
  5. Return populated entities dict
```

**Implementation in query_processor.py:**
```python
def extract_entities(self, query: str, context: Dict = None) -> Dict:
    """Extract entities using LLM"""
    
    if not self.llm_client:
        logger.error("LLM client not available")
        return {}
    
    entity_prompt = f"""Extract structured entities...(see above)"""
    
    response = self.llm_client(entity_prompt)
    
    # Clean response
    response_text = response.strip()
    if response_text.startswith("```"):
        response_text = response_text.split("```")[1]
        if response_text.startswith("json"):
            response_text = response_text[4:]
    response_text = response_text.strip()
    
    # Parse JSON
    entities_data = json.loads(response_text)
    
    # Build result with validation
    result = {}
    
    if entities_data.get("room_number"):
        result["room_number"] = str(entities_data["room_number"]).upper().strip()
    
    if entities_data.get("room_type"):
        room_type = str(entities_data["room_type"]).lower().strip()
        valid_types = ["classroom", "lab", "conference", "auditorium", "library", "study", "other"]
        if room_type in valid_types:
            result["room_type"] = room_type
    
    if entities_data.get("capacity"):
        result["capacity"] = int(entities_data["capacity"])
    
    if entities_data.get("attendees"):
        result["attendees"] = int(entities_data["attendees"])
    
    if entities_data.get("date"):
        date_str = str(entities_data["date"]).strip()
        datetime.strptime(date_str, "%Y-%m-%d")  # Validate
        result["date"] = date_str
    
    if entities_data.get("start_time"):
        time_str = str(entities_data["start_time"]).strip()
        datetime.strptime(time_str, "%H:%M")  # Validate
        result["start_time"] = time_str
    
    if entities_data.get("end_time"):
        time_str = str(entities_data["end_time"]).strip()
        datetime.strptime(time_str, "%H:%M")  # Validate
        result["end_time"] = time_str
    
    if entities_data.get("purpose"):
        result["purpose"] = str(entities_data["purpose"]).strip()
    
    if entities_data.get("equipment"):
        equipment = entities_data["equipment"]
        if isinstance(equipment, list) and equipment:
            result["equipment"] = [str(e).lower().strip() for e in equipment]
    
    return result
```

**Output Structure:**
```python
{
    "room_number": "A2",              # Room code
    "room_type": "conference",        # Room type
    "capacity": 50,                   # Max capacity
    "attendees": 25,                  # Actual attendees
    "date": "2026-04-30",            # Booking date
    "start_time": "14:00",           # Start time
    "end_time": "16:00",             # End time
    "purpose": "meeting",            # Purpose
    "equipment": ["projector", "whiteboard"]  # Equipment list
}
```

**Advantages of LLM-based Extraction:**
- ✅ Handles synonyms: "suite 101", "meeting space", "room" all recognized
- ✅ Understands informal language: "50 folks" → capacity: 50
- ✅ Extracts implicit information: "board meeting" → purpose: meeting
- ✅ Robust to paraphrasing: "Need place for 20 people" → capacity: 20
- ✅ Captures special requirements: "need WiFi and projector" → equipment: [wifi, projector]

**Error Handling:**
- If LLM unavailable: returns empty dict {}
- If JSON parse fails: logs error, returns empty dict
- If validation fails (date format wrong): field skipped
- Invalid room_type values: field skipped
- Returns only valid, populated fields

**Example:**
```
Raw Query: "Book a meeting space for 30 folks tomorrow 2 to 4 with WiFi"

LLM Response (JSON):
{
    "room_number": null,
    "room_type": "conference",
    "capacity": 30,
    "attendees": 30,
    "date": "2026-04-30",
    "start_time": "14:00",
    "end_time": "16:00",
    "purpose": "meeting",
    "equipment": ["wifi"]
}

Extracted Entities:
{
    "room_type": "conference",
    "capacity": 30,
    "attendees": 30,
    "date": "2026-04-30",
    "start_time": "14:00",
    "end_time": "16:00",
    "purpose": "meeting",
    "equipment": ["wifi"]
}
(room_number omitted - was null)
```

**Database Field Mapping:**
All extracted entities map directly to Room/Booking model fields:
- Room.room_number, Room.room_type, Room.capacity
- Booking.start_time, Booking.end_time, Booking.purpose, Booking.attendees
- Room.equipment (TextField)

---

## 3.5 Constraint Reasoning Layer (Semantic Understanding)

**Definition:** Semantic reasoning layer that goes beyond extraction to detect conflicts, infer missing constraints, and validate logical consistency. Transforms raw entity extraction into true query understanding.

**Purpose:**
- Extract entities → Understanding constraints
- Detect logical conflicts early
- Infer implicit information
- Validate intent-specific requirements
- Enable constraint-based retrieval/filtering

**Reasoning Operations:**

### 3.5.1 Conflict Detection

**Capacity Mismatch:**
```
IF attendees > capacity:
  CONFLICT: "Attendees (50) > Capacity (40)"
  ACTION: Mark constraints_valid = false
  IMPACT: May need to offer alternative rooms or clarification
```

**Impossible Time Range:**
```
IF start_time >= end_time:
  CONFLICT: "Invalid time range: 14:00 >= 16:00"
  ACTION: Mark constraints_valid = false
  IMPACT: Cannot proceed with booking
```

### 3.5.2 Constraint Inference

**Capacity from Attendees:**
```
IF attendees provided AND capacity not provided:
  INFER: capacity = attendees
  REASONING: User knows how many people will attend
  EXAMPLE: "30 people" → infer capacity: 30
```

**Attendees from Capacity (booking intent only):**
```
IF capacity provided AND attendees not provided AND intent contains "booking":
  INFER: attendees = capacity
  REASONING: For booking intent, assume full capacity will be used
  EXAMPLE: capacity: 50 → infer attendees: 50
  
  IF NOT booking intent:
    DON'T infer (availability checks don't need to fill all seats)
```

### 3.5.3 Intent-Specific Validation

**Booking Intent:**
```
REQUIRES:
- date (YYYY-MM-DD)
- start_time + end_time (HH:MM)

OPTIONAL:
- room_number (specific room)
- room_type (type of room)
- capacity/attendees
- equipment
- purpose

MISSING: ["date"] → Add to missing_for_intent
```

**Availability Check Intent:**
```
REQUIRES:
- date (YYYY-MM-DD)

OPTIONAL:
- start_time + end_time (specific time window)
- room_type
- capacity
- equipment

MISSING: ["date"] → Add to missing_for_intent
```

**Modification/Cancellation Intent:**
```
REQUIRES:
- booking_id OR original booking details

OPTIONAL:
- new_date, new_time, new_room (for modification)

MISSING: ["booking details"] → Add to missing_for_intent
```

**Output Structure:**
```python
{
    "constraint_reasoning": {
        "conflicts": [
            "Attendees (50) > Capacity (40)"
        ],
        "inferred": [
            "Inferred capacity = attendees (50)",
            "Inferred attendees = capacity (50)"
        ],
        "missing_for_intent": [
            "date (required for booking)",
            "start_time or end_time (required for booking)"
        ],
        "valid": false  # true if no conflicts detected
    },
    "constraints_valid": false
}
```

**Implementation in query_processor.py:**
```python
def _reason_constraints(self, data: Dict) -> Dict:
    """Semantic constraint reasoning layer."""
    
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
        start = datetime.strptime(entities["start_time"], "%H:%M")
        end = datetime.strptime(entities["end_time"], "%H:%M")
        if start >= end:
            constraints["conflicts"].append(
                f"Invalid time range: {entities['start_time']} >= {entities['end_time']}"
            )
            constraints["valid"] = False
    
    # Infer capacity from attendees
    if "attendees" in entities and "capacity" not in entities:
        entities["capacity"] = entities["attendees"]
        constraints["inferred"].append(
            f"Inferred capacity = attendees ({entities['attendees']})"
        )
    
    # Validate by intent
    intent_primary = data.get("intent", {}).get("primary", "information")
    if intent_primary == "booking":
        if "date" not in entities:
            constraints["missing_for_intent"].append("date")
        if "start_time" not in entities or "end_time" not in entities:
            constraints["missing_for_intent"].append("start_time/end_time")
    
    return data
```

**Example:**
```
Query: "Book a meeting for 30 people in room with capacity 20 tomorrow 2-4pm"

Extracted Entities:
{
  "capacity": 20,
  "attendees": 30,
  "date": "2026-04-30",
  "start_time": "14:00",
  "end_time": "16:00",
  "purpose": "meeting"
}

Constraint Reasoning:
{
  "conflicts": [
    "Attendees (30) > Capacity (20)"
  ],
  "inferred": [],
  "missing_for_intent": [],
  "valid": false
}

ACTION: Inform user of conflict, suggest larger room or fewer attendees
```

**Advantages:**
- ✅ Catches logical errors early
- ✅ Infers implicit requirements
- ✅ Validates against intent
- ✅ Enables smart fallback (suggest alternative room sizes)
- ✅ Provides clear reasoning for rejection/modification
- ✅ Prevents downstream booking failures

---

## 4. Query Decomposition (LLM-based Multi-Intent Detection)

**Definition:** Intelligently detect if query contains multiple distinct intents that require separate handling. Not just keyword splitting - semantic analysis of intent boundaries.

**Key Distinction:**
- ❌ **Multiple Constraints** = Same intent → Do NOT decompose
  - Example: "Find room with projector AND WiFi" = 1 booking intent, 2 constraints
  - Action: Keep as single query
  
- ✅ **Multiple Intents** = Different goals → DO decompose
  - Example: "Book room A2 AND check availability B3" = 2 intents (booking + availability)
  - Example: "Modify my booking AND cancel next week's" = 2 intents (modification + cancellation)
  - Action: Split into sub-queries

**Formula:**
```
sub_queries = LLM_Detect_Multiple_Intents(query)

Decomposition_Prompt:
  "Analyze this query for multiple DISTINCT INTENTS (not just constraints).
   
   Query: '{query}'
   
   Return:
   {
     "has_multiple_intents": true|false,
     "sub_queries": ["intent1 query", "intent2 query"],
     "reasoning": "explanation"
   }"

Logic:
  IF has_multiple_intents == true AND len(sub_queries) > 1:
    DECOMPOSE: Use each sub-query separately
  ELSE:
    DO NOT DECOMPOSE: Keep as single query
```

**Implementation in query_processor.py:**

Decomposition decision is made by the unified LLM call. If LLM returns `execution_plan.decompose_query = true`, then:

```python
def decompose_query(self, query: str) -> List[str]:
    """
    Smart multi-intent detection using LLM.
    Called only if LLM decided decomposition is needed.
    Detects multiple distinct intents and returns sub-queries.
    """
    
    if not self.llm_client:
        # Fallback: simple regex split on "and" if LLM unavailable
        return [q.strip() for q in re.split(r"\band\b", query, flags=re.IGNORECASE) if q.strip()]
    
    decomposition_prompt = f"""
Analyze for multiple DISTINCT INTENTS (not constraints).

Query: "{query}"

Return JSON:
{{
  "has_multiple_intents": true or false,
  "sub_queries": ["sub-query 1", "sub-query 2"],
  "reasoning": "explanation"
}}
"""
    
    try:
        response = self.llm_client(decomposition_prompt)
        data = self._safe_json_parse(response)  # Safe parsing with markdown/comma handling
        
        if data.get("has_multiple_intents", False):
            sub_queries = data.get("sub_queries", [])
            if isinstance(sub_queries, list) and len(sub_queries) > 1:
                logger.info(f"Multi-intent detected: {len(sub_queries)} sub-queries")
                return [q.strip() for q in sub_queries if q.strip()]
        
        return []  # No multiple intents or decomposition not needed
        
    except Exception as e:
        logger.warning(f"Multi-intent detection failed: {e}, using fallback")
        return [q.strip() for q in re.split(r"\band\b", query) if q.strip()]
```

**Supported Intent Combinations:**

| Intents | Example | Decompose |
|---|---|---|
| booking + availability | "Book A2 and check B3?" | ✅ Yes (2 distinct goals) |
| booking + modification | "Book tomorrow and modify next week?" | ✅ Yes (2 distinct goals) |
| booking + information | "Book A2 and show policy?" | ✅ Yes (2 distinct goals) |
| booking + cancellation | "Book A2 and cancel old?" | ✅ Yes (2 distinct goals) |
| booking + multiple constraints | "Book room with projector and WiFi" | ❌ No (1 intent, 2 constraints) |
| availability + multiple filters | "Check availability in B3 and C4" | ❌ No (same intent, 2 locations) |
| information + multiple topics | "Show policy and equipment info" | ❌ No (same general intent) |

**Example:**
```
Query: "Book a conference room with projector for tomorrow and also check availability of room A2 next week"

Decomposition Analysis:
{
  "has_multiple_intents": true,
  "sub_queries": [
    "Book a conference room with projector for tomorrow",
    "Check availability of room A2 next week"
  ],
  "reasoning": "Two distinct intents: booking (first part) + availability check (second part)"
}

Result: Process as 2 separate queries
  1. booking intent + entities (projector, tomorrow)
  2. availability intent + entities (room A2, next week)
```

**Advantages:**
- ✅ Handles non-standard "and" phrasing
- ✅ Distinguishes constraints from separate intents
- ✅ Semantic analysis, not keyword matching
- ✅ Fallback to regex if LLM unavailable
- ✅ Captures real multi-goal queries
- ✅ Prevents false decomposition of constraint-heavy queries

---

## OLD: Query Decomposition (Deprecated - Keyword-based)

## 5. Complexity Score (LLM-based Semantic Scoring)

**Definition:** Quantify semantic difficulty of query using LLM to determine optimal retrieval strategy and processing steps. Replaces discrete counting with continuous semantic evaluation.

**Why Semantic Scoring?**
- ❌ OLD: Count-based (discrete 1-5 score) missed nuance
  - Query "Book A2" = score 1, Query "Find any conference room" = also low
  - Both routed identically despite different complexity
- ✅ NEW: Semantic-based (continuous 1.0-5.0) captures meaning
  - Considers intent difficulty, constraint complexity, temporal/spatial specificity
  - Routes based on actual difficulty, not just counts

**Complexity Dimensions:**
```
Semantic_Complexity = LLM_Evaluate(
  temporal_complexity,     # Specific date vs relative (tomorrow, next week)
  spatial_complexity,      # Specific room vs any available
  constraint_complexity,   # Equipment, capacity, special requirements
  intent_difficulty,       # Simple info vs complex booking/modification
  ambiguity_level         # Clear vs ambiguous requirements
)

Range: [1.0, 5.0] (continuous, not discrete)
```

**Scoring Scale:**
```
1.0 - 1.5: Very Simple
  Examples: "What is room A2?", "Is room B1 available tomorrow?"
  → FAST_HYBRID_RETRIEVAL, skip expansion

1.5 - 2.5: Simple
  Examples: "Book room A2 tomorrow 2-4pm", "Find a conference room"
  → FAST_HYBRID_RETRIEVAL, optional expansion

2.5 - 3.5: Moderate
  Examples: "I need a conference room with projector for 30 people Tuesday"
  → MULTI_QUERY_RETRIEVAL, run expansion

3.5 - 4.5: Complex
  Examples: "Find me any large meeting space with wifi and phone for 50 people next month"
  → MULTI_QUERY_RETRIEVAL, full expansion, re-ranking

4.5 - 5.0: Very Complex
  Examples: "Modify my Tuesday booking to a different room and time with equipment changes"
  → MULTI_QUERY_RETRIEVAL, expansion, re-ranking, multi-step decomposition
```

**How Gemma Produces the Complexity Score:**

There is no hand-written math formula here. If your `llm_client` is Gemma (default model in this project is `gemma3:1b`), Gemma reads the normalized query plus the extracted intent and entities, then predicts a single complexity value in the response JSON.

The prompt tells Gemma to judge these five things:
- temporal specificity: exact date/time vs vague timing
- spatial constraints: specific room vs any room
- equipment needs: projector, WiFi, etc.
- intent difficulty: simple information request vs booking/modification/cancellation
- requirement clarity: clear request vs ambiguous request

So the model is not “counting words” or applying a formula. It is making a semantic judgment from the text and returning a number between 1.0 and 5.0.

```python
# Conceptually, the LLM receives a prompt like this:
Complexity_Prompt:
  "Evaluate the semantic complexity of this room booking query.
   Consider: temporal specificity, spatial constraints, equipment needs,
   intent difficulty, and requirement clarity.

   Query: '{normalized_query}'
   Intent: {intent}
   Entities: {entities}

   Respond with ONLY:
   complexity_score: [1.0 to 5.0]
   reasoning: [brief explanation]"

# The model returns JSON that already contains:
# - complexity_score
# - routing_strategy
# - execution_plan
# - reason
```

**What the Code Does After Gemma Responds:**
```python
# 1. Parse the JSON response
# 2. Normalize the schema so missing fields do not break the pipeline
# 3. Validate extracted entities
# 4. Apply constraint reasoning
# 5. Clamp complexity to the valid range

score = float(data["routing"]["complexity_score"])
data["routing"]["complexity_score"] = max(1.0, min(score, 5.0))
```

**Teacher Explanation (Short Version):**
Gemma does not use a hand-written formula. It reads the full query, figures out the user's intent, extracts the important facts, and then predicts how hard the query is to answer. The Python code does not invent the score; it only validates Gemma's JSON, cleans the fields, and clamps the score to a safe range.

**Worked Example:**
- Query: "I need a conference room with projector and WiFi for 30 people next Tuesday 10-12"
- Gemma sees the intent as `booking`
- Gemma extracts entities such as `room_type=conference`, `equipment=[projector, wifi]`, `capacity=30`, `date=next Tuesday`, `start_time=10:00`, `end_time=12:00`
- Gemma assigns a higher complexity score because the request has multiple constraints and a specific time range
- The code keeps the score only if it is between `1.0` and `5.0`
- If the score is `2.5` or higher, the system uses `MULTI_QUERY_RETRIEVAL`
- If the score is below `2.5`, the system uses `FAST_HYBRID_RETRIEVAL`

**Teaching Definitions:**

| Term | Meaning | Example |
|------|---------|---------|
| Intent | The user's main goal or action | "book", "cancel", "check availability" |
| Entities | The important facts inside the query | room number, date, time, capacity, equipment |
| Temporal specificity | How exact the date/time is | "next Tuesday 10-12" is more specific than "sometime next week" |
| Spatial constraint | How specific the room/location is | "room A2" is more specific than "any conference room" |
| Equipment need | Extra resources the room must have | projector, WiFi, whiteboard |
| Requirement clarity | How complete and unambiguous the request is | "book room A2 tomorrow 2-4 PM" is clear |
| Complexity score | Gemma's overall judgment of how hard the query is to process | 1.0 = simple, 5.0 = very complex |

**Simple teaching rule:**
- More exact time, more room restrictions, and more equipment needs usually mean a higher complexity score.
- The score is not a formula; it is Gemma's semantic judgment from the full query.

**Important:** The routing threshold is also semantic, not formula-based:
- `complexity_score >= 2.5` → `MULTI_QUERY_RETRIEVAL`
- `complexity_score < 2.5` → `FAST_HYBRID_RETRIEVAL`

**Fallback:** If the model is unavailable or returns invalid output, the system uses `2.5` as a safe moderate default.

**Complexity Scoring (Integrated in Unified LLM Call):**

Complexity is part of the unified LLM understanding call, which means the same Gemma response contains intent, entities, routing, and the score in one JSON object.

```python
# Unified LLM call returns complexity as part of routing structure
Response includes:
"routing": {
    "complexity_score": 3.2,
    "routing_strategy": "MULTI_QUERY_RETRIEVAL",
    "execution_plan": {
        "decompose_query": false,
        "expand_query": true
    },
    "reason": "Multiple constraints with equipment and specific time"
}

# Post-processing ensures valid range:
score = float(data["routing"]["complexity_score"])
data["routing"]["complexity_score"] = max(1.0, min(score, 5.0))

# Fallback (if LLM unavailable):
# complexity_score defaults to 2.5 (moderate threshold)
```

**Comparison: Old vs New**
```
Query: "Find a conference room with projector for 20 people tomorrow 2-4pm"

OLD (Discrete Counting):
  entities: 6 (>3) → +1 = score 2
  words: 16 (>15) → +1 = score 3
  sub_queries: 1 (≤1) → no add
  FINAL SCORE: 3 (Moderate)
  Reasoning: Just counting, misses semantic intent

NEW (Semantic LLM-based):
  Temporal: specific date (tomorrow) + specific time (2-4pm) = moderate
  Spatial: room type specified (conference) = simple
  Constraints: 1 constraint (projector) + 1 (capacity 20) = moderate
  Intent: booking with explicit requirements = moderate-high
  FINAL SCORE: 3.2 (Moderate)
  Reasoning: Specific requirements but single room type, clear intent
```

**Example Calculations:**

```
Example 1: Simple query
  Query: "Is room A2 available?"
  Intent: availability
  Entities: {} (0 entities)
  
  LLM Evaluation:
    Temporal: single day, no time = simple
    Spatial: specific room = simple
    Constraints: none = simple
  Complexity_score: 1.2
  Routing: FAST_HYBRID_RETRIEVAL, no expansion

Example 2: Moderate query
  Query: "Can I book conference room A2 on Monday for 50 people?"
  Intent: booking
  Entities: {date: "Monday", room_number: "A2", capacity: 50, room_type: "conference"}
  
  LLM Evaluation:
    Temporal: relative date (Monday) = simple
    Spatial: specific room = simple
    Constraints: 1 (capacity) = simple
  Complexity_score: 2.1
  Routing: FAST_HYBRID_RETRIEVAL, no expansion

Example 3: Complex query
  Query: "I need a conference room with projector and WiFi for 30 people Tuesday 10-12"
  Intent: booking
  Entities: {date: "Tuesday", room_type: "conference", capacity: 30, equipment: ["projector", "wifi"], start_time: "10:00", end_time: "12:00"}
  
  LLM Evaluation:
    Temporal: relative date + specific time range = moderate
    Spatial: room type specified = simple
    Constraints: 2 (equipment) = moderate
  Complexity_score: 3.2
  Routing: MULTI_QUERY_RETRIEVAL, expansion enabled

Example 4: Very Complex query
  Query: "Book rooms A2 and B3 for 50 people and also check cross-department booking policy"
  Intent: booking + information (2 distinct intents)
  Entities: {room_number: ["A2", "B3"], capacity: 50}
  
  LLM Evaluation:
    Multiple intents detected: booking + information
    Decomposition: YES (2 separate intents)
  Complexity_score: 4.1
  Routing: MULTI_QUERY_RETRIEVAL, expansion enabled, decomposition enabled

### 5.2 Complexity Score Interpretation

**Complexity Levels & Routing Decision:**

| Score | Level | Characteristics | Routing Strategy | Execution Plan |
|-------|-------|-----------------|------------------|----------------|
| 1.0-1.5 | Very Simple | Minimal entities, short query | FAST_HYBRID_RETRIEVAL | expand: false |
| 1.5-2.5 | Simple | 1-3 entities, clear intent | FAST_HYBRID_RETRIEVAL | expand: false |
| 2.5-3.5 | Moderate | 3-4 entities, some constraints | MULTI_QUERY_RETRIEVAL | expand: true |
| 3.5-4.5 | Complex | 4+ entities, multiple constraints | MULTI_QUERY_RETRIEVAL | expand: true |
| 4.5-5.0 | Very Complex | Many entities, complex logic | MULTI_QUERY_RETRIEVAL | expand: true |

**Routing Rule:**
```
IF complexity_score >= 2.5:
    routing_strategy = "MULTI_QUERY_RETRIEVAL"
    execution_plan.expand_query = True
ELSE:
    routing_strategy = "FAST_HYBRID_RETRIEVAL"
    execution_plan.expand_query = False
```

**Routing Decision (Determined by LLM):**
```
Complexity Score Range Determines Strategy:

IF complexity_score >= 2.5:
    routing_strategy = "MULTI_QUERY_RETRIEVAL"
    execution_plan.expand_query = True
    REASON: Query has multiple facets needing coverage
    
ELSE (complexity_score < 2.5):
    routing_strategy = "FAST_HYBRID_RETRIEVAL"
    execution_plan.expand_query = False
    REASON: Simple query sufficient with single pass
```






**Example:**
```
Original: "I need to book a room for 30 people"

Expansions:
  1. "I need to book a room for 30 people" (original)
  2. "I want to book a room for 30 people" (need→want)
  3. "I require to book a room for 30 people" (need→require)
  4. "I need to reserve a room for 30 people" (book→reserve)
  5. "room for 30 people" (entity-based)
```

---

## 7. Complete Query Processing Pipeline with Agentic Router

**End-to-end flow with router control:**

```
Raw User Input
    ↓
1. Normalization (ALWAYS, Deterministic)
    └─ query.lower().strip()
    └─ Output: normalized_query
    ↓
2. UNIFIED LLM UNDERSTANDING (SINGLE CALL)
    ├─ Intent Classification (LLM)
    ├─ Entity Extraction (LLM)
    ├─ Complexity Scoring (LLM, 1.0-5.0 semantic)
    ├─ Routing Decision (LLM-decided)
    ├─ Execution Plan (decompose? expand?)
    └─ Output: {
    │   "intent": {primary, confidence},
    │   "entities": {room, date, time, capacity, equipment, ...},
    │   "routing": {
    │       "complexity_score": 3.2,
    │       "routing_strategy": "MULTI_QUERY_RETRIEVAL",
    │       "execution_plan": {decompose_query, expand_query},
    │       "reason": "explanation"
    │   },
    │   "sub_queries": []
    │ }
    ↓
3. VALIDATION & REASONING (DETERMINISTIC)
    ├─ Safe JSON parsing (markdown + trailing comma handling)
    ├─ Schema normalization (guarantee all fields exist)
    ├─ Entity validation (date format, time format, enums, types)
    ├─ Constraint reasoning:
    │   ├─ Conflict detection (attendees > capacity, invalid time range)
    │   ├─ Inference (capacity ← attendees, attendees ← capacity)
    │   └─ Intent-specific validation
    └─ Output: routing + constraint_reasoning added to response
    ↓
4. CONDITIONAL EXECUTION (Based on LLM execution_plan)
    ├─ IF execution_plan.decompose_query == True:
    │   └─ Run decompose_query(normalized) → LLM multi-intent detection
    │   └─ Output: sub_queries[]
    │
    ├─ IF execution_plan.expand_query == True:
    │   └─ Run expand_query(normalized, entities) → Synonym expansion
    │   └─ Output: expanded_queries[]
    │
    └─ Otherwise: skip (sub_queries = None, expanded_queries = None)
    ↓
Final Output: {
    "original_query": string,
    "normalized_query": string,
    "intent": {primary, confidence},
    "entities": dict,
    "sub_queries": list or None,
    "expanded_queries": list or None,
    "complexity": float(1.0-5.0),
    "routing_strategy": "FAST_HYBRID_RETRIEVAL|MULTI_QUERY_RETRIEVAL",
    "execution_plan": {decompose_query: bool, expand_query: bool}
}
    ↓
DOWNSTREAM ROUTING:
  IF routing_strategy == "MULTI_QUERY_RETRIEVAL":
    → Use expanded_queries[] for multi-query retrieval + re-ranking
  ELSE (FAST_HYBRID_RETRIEVAL):
    → Use normalized_query directly for fast hybrid retrieval
```

## 9. Example Query Processing

### Example 1: Simple Booking Query
```
Raw: "Can I book room A2?"

Step 1 - Normalize:
  "can i book room a2"

Step 2 - Intent:
  primary: "booking"
  confidence: 0.95

Step 3 - Entities:
  {room_number: "A2"}

Step 4 - Decompose:
  ["can i book room a2"]

Step 5 - Complexity (LLM Evaluation):
  Temporal: single date, no time = simple
  Spatial: specific room = simple
  Constraints: none = simple
  Complexity_score: 1.1
  Routing: FAST_HYBRID_RETRIEVAL (complexity < 2.5)

Step 6 - Expansion: (skip, complexity < 2.5)
  Not applicable

Routing: FAST_HYBRID_RETRIEVAL
```

### Example 2: Complex Multi-Entity Query
```
Raw: "Can I book room A2 building B for 50 people tomorrow at 2 PM?"

Step 1 - Normalize:
  "can i book room a2 building b for 50 people tomorrow at 2 pm"

Step 2 - Intent:
  primary: "booking"
  confidence: 0.98

Step 3 - Entities (LLM-extracted):
  {
    room_number: "A2",
    capacity: 50,
    attendees: 50,
    date: "2026-04-30",
    start_time: "14:00",
    end_time: "16:00"
  }
  (room_type, purpose, equipment: null → omitted)

Step 4 - Decompose:
  ["can i book room a2 building b for 50 people tomorrow at 2 pm"]

Step 5 - Complexity (LLM Evaluation):
  Temporal: relative date + specific time = moderate
  Spatial: specific room = simple
  Constraints: 1 (capacity) = simple
  Complexity_score: 2.8
  Routing: MULTI_QUERY_RETRIEVAL (complexity >= 2.5)

Step 6 - Expansion: (complexity >= 2.5)
  1. "can i book room a2 building b for 50 people tomorrow at 2 pm" (original)
  2. "can i reserve room a2 building b for 50 people tomorrow at 2 pm" (book→reserve)
  3. "can i schedule room a2 building b for 50 people tomorrow at 2 pm" (book→schedule)
  4. "room for 50 people" (entity-based)
  5. "can i book space a2 building b for 50 people tomorrow at 2 pm" (room→space)

Routing: MULTI-QUERY RETRIEVAL (2 variations)
```

### Example 3: Complex Query with Equipment & Room Type
```
Raw: "I need a conference room with projector and WiFi for 30 people next Tuesday 10-12"

Step 1 - Normalize:
  "i need a conference room with projector and wifi for 30 people next tuesday 10-12"

Step 2 - Intent:
  primary: "booking"
  confidence: 0.96

Step 3 - Entities (LLM-extracted):
  {
    room_type: "conference",
    equipment: ["projector", "wifi"],
    attendees: 30,
    capacity: 30,
    date: "2026-05-06",      (next Tuesday from 2026-04-29)
    start_time: "10:00",
    end_time: "12:00",
    purpose: "meeting"        (inferred from "need" + room type)
  }

Step 4 - Decompose:
  ["i need a conference room with projector and wifi for 30 people next tuesday 10-12"]

Step 5 - Complexity (LLM Evaluation):
  Temporal: relative date + specific time range = moderate
  Spatial: room type specified (conference) = simple
  Constraints: 2 (equipment) = moderate
  Complexity_score: 3.2
  Routing: MULTI_QUERY_RETRIEVAL (complexity >= 2.5)

Step 6 - Expansion: (complexity >= 2.5)
  1. "i need a conference room with projector and wifi for 30 people next tuesday 10-12" (original)
  2. "i want a conference room with projector and wifi for 30 people next tuesday 10-12" (need→want)
  3. "i require a conference room with projector and wifi for 30 people next tuesday 10-12" (need→require)
  4. "room for 30 people" (entity-based)
  5. "i need a space with projector and wifi for 30 people next tuesday 10-12" (room→space)

Routing: MULTI-QUERY RETRIEVAL (2 variations)
```

