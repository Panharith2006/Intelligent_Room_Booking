"""
Advanced Query Processing for RAG System
Handles query decomposition, expansion, intent classification, and entity extraction
"""
import logging
import re
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import json

logger = logging.getLogger(__name__)


class QueryProcessor:
    """
    Advanced query understanding and preprocessing for room booking chatbot.
    
    Features:
    - Query decomposition (break complex queries into sub-queries)
    - Query expansion (generate semantic variations)
    - Intent classification (booking, information, modification, cancellation)
    - Entity extraction (date, time, capacity, room, building)
    """
    
    def __init__(self, llm_client=None):
        """
        Initialize query processor.
        
        Args:
            llm_client: Optional LLM client for advanced decomposition
        """
        self.llm_client = llm_client
        
        # Intent patterns
        self.intent_patterns = {
            'booking': [
                r'\b(book|reserve|need|want|schedule|get)\s+(a\s+)?(room|space)',
                r'\bi\s+(need|want|require)\s+.*(room|space)',
                r'\broom\s+for\b',
            ],
            'information': [
                r'\b(what|how|when|where|why|tell|explain|info|information)\b',
                r'\b(policy|policies|rule|rules|guideline)',
                r'\b(capacity|feature|equipment|amenity)',
            ],
            'modification': [
                r'\b(change|modify|update|edit|reschedule|move)\b',
                r'\b(extend|shorten|adjust)\b',
            ],
            'cancellation': [
                r'\b(cancel|delete|remove)\s+(my\s+)?(booking|reservation)',
            ],
            'availability': [
                r'\b(available|free|vacant|open|check availability)\b',
                r'\bwhat.*rooms.*available\b',
                r'\bany.*rooms?\b',
            ]
        }
        
        # Entity extraction patterns
        self.entity_patterns = {
            'date': [
                r'\b(today|tomorrow|tonight)\b',
                r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
                r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b',
                r'\b(next|this)\s+(week|month|monday|tuesday|wednesday|thursday|friday)\b',
                r'\bin\s+(\d+)\s+days?\b',
            ],
            'time': [
                r'\b(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)?\b',
                r'\b(\d{1,2})\s*(am|pm|AM|PM)\b',
                r'\b(morning|afternoon|evening|night|noon)\b',
            ],
            'capacity': [
                r'\b(\d+)\s+(people|person|students?|participants?|attendees?)\b',
                r'\b(capacity|size|seats?)\s*(of|:)?\s*(\d+)\b',
                r'\bfor\s+(\d+)\b',
            ],
            'room': [
                r'\broom\s+([A-Z]\d+|[A-Z]-?\d+)\b',
                r'\b([A-Z]\d{2,4})\b',
            ],
            'building': [
                r'\bbuilding\s+([A-Z])\b',
                r'\bin\s+building\s+([A-Z])\b',
                r'\b([A-Z])\s+building\b',
            ],
            'purpose': [
                r'\bfor\s+(a\s+)?(meeting|lecture|conference|workshop|lab|study|exam|presentation)\b',
                r'\b(meeting|lecture|conference|workshop|lab|study|exam|presentation)\b',
            ]
        }
        
    def process_query(self, query: str, context: Dict = None) -> Dict:
        """
        Main processing pipeline for user query.
        
        Args:
            query: User's natural language query
            context: Optional conversation context
            
        Returns:
            Dict containing:
                - original_query: Original query text
                - normalized_query: Cleaned and normalized query
                - intent: Primary intent classification
                - entities: Extracted entities
                - sub_queries: Decomposed sub-queries
                - expanded_queries: Semantic variations
                - complexity: Query complexity score (1-5)
        """
        logger.info(f"Processing query: {query[:100]}...")
        
        # Normalize query
        normalized = self._normalize_query(query)
        
        # Classify intent
        intent = self.classify_intent(normalized)
        
        # Extract entities
        entities = self.extract_entities(normalized, context)
        
        # Decompose complex queries
        sub_queries = self.decompose_query(normalized, intent, entities)
        
        # Expand query with variations
        expanded_queries = self.expand_query(normalized, intent, entities)
        
        # Calculate complexity
        complexity = self._calculate_complexity(normalized, sub_queries, entities)
        
        result = {
            'original_query': query,
            'normalized_query': normalized,
            'intent': intent,
            'entities': entities,
            'sub_queries': sub_queries,
            'expanded_queries': expanded_queries,
            'complexity': complexity,
        }
        
        logger.info(f"Query processed - Intent: {intent}, Entities: {len(entities)}, Complexity: {complexity}")
        return result
    
    def _normalize_query(self, query: str) -> str:
        """Clean and normalize query text."""
        # Convert to lowercase
        normalized = query.lower().strip()
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        
        # Remove special characters (keep letters, numbers, common punctuation)
        normalized = re.sub(r'[^\w\s\-:,.?!]', '', normalized)
        
        return normalized
    
    def classify_intent(self, query: str) -> Dict[str, float]:
        """
        Classify query intent with confidence scores.
        
        Returns:
            Dict of intent -> confidence score
        """
        intent_scores = {}
        
        for intent, patterns in self.intent_patterns.items():
            score = 0.0
            for pattern in patterns:
                if re.search(pattern, query, re.IGNORECASE):
                    score += 1.0
            
            # Normalize score
            if score > 0:
                intent_scores[intent] = min(score / len(patterns), 1.0)
        
        # Default to information intent if no clear match
        if not intent_scores:
            intent_scores['information'] = 0.5
        
        # Get primary intent (highest score)
        primary_intent = max(intent_scores, key=intent_scores.get)
        
        return {
            'primary': primary_intent,
            'scores': intent_scores,
            'confidence': intent_scores[primary_intent]
        }
    
    def extract_entities(self, query: str, context: Dict = None) -> Dict:
        """
        Extract structured entities from query.
        
        Args:
            query: Normalized query text
            context: Optional context from previous conversation
            
        Returns:
            Dict of entity_type -> entity_value
        """
        entities = {}
        
        # Extract date
        date_entity = self._extract_date(query)
        if date_entity:
            entities['date'] = date_entity
        elif context and context.get('date'):
            entities['date'] = context['date']
        
        # Extract time
        time_entities = self._extract_time(query)
        if time_entities:
            entities.update(time_entities)
        elif context:
            if context.get('start_time'):
                entities['start_time'] = context['start_time']
            if context.get('end_time'):
                entities['end_time'] = context['end_time']
        
        # Extract capacity
        capacity = self._extract_capacity(query)
        if capacity:
            entities['capacity'] = capacity
        elif context and context.get('capacity'):
            entities['capacity'] = context['capacity']
        
        # Extract room number
        room_match = None
        for pattern in self.entity_patterns['room']:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                room_match = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                break
        if room_match:
            entities['room_number'] = room_match.upper()
        
        # Extract building
        building_match = None
        for pattern in self.entity_patterns['building']:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                building_match = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                break
        if building_match:
            entities['building'] = building_match.upper()
        
        # Extract purpose
        purpose_match = None
        for pattern in self.entity_patterns['purpose']:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                # Get the last matched group that isn't 'a'
                for group in reversed(match.groups()):
                    if group and group != 'a':
                        purpose_match = group
                        break
                if purpose_match:
                    break
        if purpose_match:
            entities['purpose'] = purpose_match.lower()
        
        return entities
    
    def _extract_date(self, query: str) -> Optional[str]:
        """Extract date and convert to YYYY-MM-DD format."""
        today = datetime.now()
        
        # Relative dates
        if re.search(r'\btoday\b', query):
            return today.strftime('%Y-%m-%d')
        if re.search(r'\btomorrow\b', query):
            return (today + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # Day of week (next occurrence)
        day_pattern = r'\b(next\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b'
        day_match = re.search(day_pattern, query, re.IGNORECASE)
        if day_match:
            day_name = day_match.group(2).lower()
            days = ['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday']
            target_day = days.index(day_name)
            current_day = today.weekday()
            days_ahead = (target_day - current_day) % 7
            if days_ahead == 0:
                days_ahead = 7  # Next week
            target_date = today + timedelta(days=days_ahead)
            return target_date.strftime('%Y-%m-%d')
        
        # "in X days"
        days_ahead_pattern = r'\bin\s+(\d+)\s+days?\b'
        days_match = re.search(days_ahead_pattern, query)
        if days_match:
            days = int(days_match.group(1))
            return (today + timedelta(days=days)).strftime('%Y-%m-%d')
        
        # Explicit date format
        date_pattern = r'\b(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})\b'
        date_match = re.search(date_pattern, query)
        if date_match:
            day, month, year = date_match.groups()
            year = int(year)
            if year < 100:
                year += 2000
            try:
                date = datetime(year, int(month), int(day))
                return date.strftime('%Y-%m-%d')
            except ValueError:
                # Try MM-DD-YYYY format
                try:
                    date = datetime(year, int(day), int(month))
                    return date.strftime('%Y-%m-%d')
                except ValueError:
                    pass
        
        return None
    
    def _extract_time(self, query: str) -> Dict[str, str]:
        """Extract start and end times."""
        times = {}
        
        # Find all time mentions
        time_matches = []
        
        # HH:MM format with optional AM/PM
        for match in re.finditer(r'\b(\d{1,2}):(\d{2})\s*(am|pm|AM|PM)?\b', query):
            hour = int(match.group(1))
            minute = int(match.group(2))
            meridiem = match.group(3)
            
            if meridiem and meridiem.upper() == 'PM' and hour < 12:
                hour += 12
            elif meridiem and meridiem.upper() == 'AM' and hour == 12:
                hour = 0
            
            time_matches.append(f"{hour:02d}:{minute:02d}")
        
        # H AM/PM format
        for match in re.finditer(r'\b(\d{1,2})\s*(am|pm|AM|PM)\b', query):
            hour = int(match.group(1))
            meridiem = match.group(2)
            
            if meridiem.upper() == 'PM' and hour < 12:
                hour += 12
            elif meridiem.upper() == 'AM' and hour == 12:
                hour = 0
            
            time_matches.append(f"{hour:02d}:00")
        
        # Named times
        if re.search(r'\bmorning\b', query):
            time_matches.append("09:00")
        if re.search(r'\bafternoon\b', query):
            time_matches.append("14:00")
        if re.search(r'\bevening\b', query):
            time_matches.append("18:00")
        if re.search(r'\bnoon\b', query):
            time_matches.append("12:00")
        
        # Assign start and end times
        if len(time_matches) >= 2:
            times['start_time'] = time_matches[0]
            times['end_time'] = time_matches[1]
        elif len(time_matches) == 1:
            times['start_time'] = time_matches[0]
            # Infer 2-hour duration
            start_hour = int(time_matches[0].split(':')[0])
            end_hour = (start_hour + 2) % 24
            times['end_time'] = f"{end_hour:02d}:00"
        
        return times
    
    def _extract_capacity(self, query: str) -> Optional[int]:
        """Extract capacity/number of people."""
        for pattern in self.entity_patterns['capacity']:
            match = re.search(pattern, query, re.IGNORECASE)
            if match:
                # Find the number in the match
                for group in match.groups():
                    if group and group.isdigit():
                        return int(group)
        return None
    
    def decompose_query(self, query: str, intent: Dict, entities: Dict) -> List[str]:
        """
        Decompose complex queries into simpler sub-queries.
        
        Example:
            "I need a room for 20 people tomorrow afternoon with a projector and check booking policies"
            →
            ["Find room with capacity 20", 
             "Available tomorrow afternoon",
             "Must have projector",
             "Get booking policies"]
        """
        sub_queries = []
        
        # If query has multiple intents, split them
        intent_scores = intent.get('scores', {})
        multiple_intents = [k for k, v in intent_scores.items() if v > 0.3]
        
        if len(multiple_intents) > 1:
            # Check for conjunctions
            if re.search(r'\band\s+(also\s+)?(check|get|tell|show)', query):
                parts = re.split(r'\band\s+(also\s+)?(check|get|tell|show)', query)
                sub_queries.extend([p.strip() for p in parts if p and len(p.strip()) > 5])
        
        # If no sub-queries detected, return original
        if not sub_queries:
            sub_queries = [query]
        
        return sub_queries
    
    def expand_query(self, query: str, intent: Dict, entities: Dict) -> List[str]:
        """
        Generate semantic variations of the query for better retrieval.
        
        Example:
            "meeting room" → ["conference room", "meeting space", "discussion room"]
        """
        expanded = [query]  # Always include original
        
        # Synonym mappings
        synonyms = {
            'meeting': ['conference', 'discussion', 'gathering'],
            'room': ['space', 'area', 'facility'],
            'book': ['reserve', 'schedule', 'arrange'],
            'need': ['require', 'want', 'looking for'],
            'available': ['free', 'vacant', 'open'],
        }
        
        # Generate variations
        for word, syns in synonyms.items():
            if word in query:
                for syn in syns:
                    variation = query.replace(word, syn)
                    if variation not in expanded:
                        expanded.append(variation)
        
        # Add entity-focused queries
        if 'capacity' in entities:
            expanded.append(f"room for {entities['capacity']} people")
        if 'purpose' in entities:
            expanded.append(f"{entities['purpose']} room")
        if 'building' in entities:
            expanded.append(f"rooms in building {entities['building']}")
        
        return expanded[:5]  # Limit to top 5 variations
    
    def _calculate_complexity(self, query: str, sub_queries: List[str], entities: Dict) -> int:
        score = 1
        
        # Entity count
        if len(entities) > 3:
            score += 1
        if len(entities) > 5:
            score += 1
        
        # Query length
        word_count = len(query.split())
        if word_count > 15:
            score += 1
        if word_count > 25:
            score += 1
        
        # Sub-queries
        if len(sub_queries) > 1:
            score += 1
        
        # Conditional words
        conditionals = ['if', 'unless', 'provided', 'alternatively', 'or', 'prefer']
        if any(c in query for c in conditionals):
            score += 1
        
        return min(score, 5)


# Convenience function
def process_query(query: str, context: Dict = None, llm_client=None) -> Dict:
    processor = QueryProcessor(llm_client)
    return processor.process_query(query, context)
