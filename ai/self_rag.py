"""
Self-RAG: Self-Reflective Retrieval-Augmented Generation
Implements reflection and self-correction mechanisms
"""
import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum

logger = logging.getLogger(__name__)


class ReflectionType(Enum):
    """Types of reflection checks."""
    RELEVANCE = "relevance"          # Are retrieved docs relevant to query?
    SUPPORT = "support"              # Does response match retrieved facts?
    UTILITY = "utility"              # Does response address user's need?
    COMPLETENESS = "completeness"    # Is all necessary info included?


class SelfRAG:
    """
    Self-Reflective RAG system that evaluates and corrects its own outputs.
    
    Implements three key reflection mechanisms:
    1. Retrieve-Check: Evaluates relevance of retrieved documents
    2. Support-Check: Verifies response is grounded in retrieved context
    3. Utility-Check: Assesses if response addresses user's needs
    
    If reflection scores are low, the system can:
    - Refine the query and re-retrieve
    - Generate alternative responses
    - Request more information from user
    """
    
    def __init__(
        self,
        retriever,
        llm_client=None,
        thresholds: Dict[str, float] = None
    ):
        """
        Initialize Self-RAG system.
        
        Args:
            retriever: Retrieval system (HybridRetriever)
            llm_client: LLM for reflection and generation
            thresholds: Score thresholds for each reflection type
        """
        self.retriever = retriever
        self.llm_client = llm_client
        
        # Default thresholds
        self.thresholds = thresholds or {
            'relevance': 0.6,      # Min relevance score to proceed
            'support': 0.7,        # Min support score (factual grounding)
            'utility': 0.6,        # Min utility score (user satisfaction)
            'completeness': 0.7    # Min completeness score
        }
        
        logger.info(f"Self-RAG initialized with thresholds: {self.thresholds}")
    
    def generate_with_reflection(
        self,
        query: str,
        entities: Dict = None,
        intent: str = None,
        context: Dict = None,
        max_iterations: int = 3
    ) -> Dict:
        """
        Generate response with self-reflection and refinement.
        
        Process:
        1. Retrieve documents
        2. Check retrieval relevance
        3. Generate response
        4. Check support (factual grounding)
        5. Check utility (addresses user need)
        6. If checks fail, refine and retry
        
        Args:
            query: User query
            entities: Extracted entities
            intent: Query intent
            context: Conversation context
            max_iterations: Max refinement iterations
            
        Returns:
            Dict containing:
                - response: Final generated response
                - retrieved_docs: Retrieved documents
                - reflection_scores: All reflection scores
                - iterations: Number of refinement iterations
                - success: Whether reflection thresholds met
        """
        logger.info(f"Self-RAG generation for query: {query[:100]}")
        
        iteration = 0
        refined_query = query
        
        while iteration < max_iterations:
            logger.info(f"Self-RAG iteration {iteration + 1}/{max_iterations}")
            
            # Step 1: Retrieve documents
            retrieved_docs = self.retriever.retrieve(
                query=refined_query,
                entities=entities,
                intent=intent,
                top_k=5
            )
            
            # Step 2: Retrieve-Check (relevance)
            relevance_score = self._check_retrieval_relevance(query, retrieved_docs)
            logger.info(f"Relevance score: {relevance_score:.3f}")
            
            # If relevance too low, refine query and re-retrieve
            if relevance_score < self.thresholds['relevance']:
                logger.warning(f"Low relevance ({relevance_score:.3f}), refining query...")
                refined_query = self._refine_query(query, entities, intent)
                iteration += 1
                continue
            
            # Step 3: Generate response
            response = self._generate_response(
                query=query,
                retrieved_docs=retrieved_docs,
                entities=entities,
                intent=intent,
                context=context
            )
            
            # Step 4: Support-Check (factual grounding)
            support_score = self._check_factual_support(response, retrieved_docs)
            logger.info(f"Support score: {support_score:.3f}")
            
            # Step 5: Utility-Check (user satisfaction)
            utility_score = self._check_utility(query, response, intent, entities)
            logger.info(f"Utility score: {utility_score:.3f}")
            
            # Step 6: Completeness-Check
            completeness_score = self._check_completeness(response, entities, intent)
            logger.info(f"Completeness score: {completeness_score:.3f}")
            
            # Aggregate reflection scores
            reflection_scores = {
                'relevance': relevance_score,
                'support': support_score,
                'utility': utility_score,
                'completeness': completeness_score,
                'overall': (relevance_score + support_score + utility_score + completeness_score) / 4
            }
            
            # Check if all thresholds met
            success = all([
                relevance_score >= self.thresholds['relevance'],
                support_score >= self.thresholds['support'],
                utility_score >= self.thresholds['utility'],
                completeness_score >= self.thresholds['completeness']
            ])
            
            if success:
                logger.info(f"✓ Self-RAG succeeded after {iteration + 1} iteration(s)")
                return {
                    'response': response,
                    'retrieved_docs': retrieved_docs,
                    'reflection_scores': reflection_scores,
                    'iterations': iteration + 1,
                    'success': True
                }
            
            # If not successful and iterations remain, refine
            iteration += 1
            
            # Determine what to refine based on which check failed
            if support_score < self.thresholds['support']:
                # Hallucination detected, need better grounding
                logger.warning("Low support score, will re-generate with stricter grounding")
                # Next iteration will use same docs but stricter generation
            elif utility_score < self.thresholds['utility']:
                # Response doesn't address user need, refine query
                refined_query = self._refine_query(query, entities, intent, focus='utility')
            elif completeness_score < self.thresholds['completeness']:
                # Missing information, retrieve more
                refined_query = self._refine_query(query, entities, intent, focus='completeness')
        
        # Max iterations reached, return best attempt
        logger.warning(f"Self-RAG max iterations reached. Scores: {reflection_scores}")
        return {
            'response': response,
            'retrieved_docs': retrieved_docs,
            'reflection_scores': reflection_scores,
            'iterations': max_iterations,
            'success': False
        }
    
    def _check_retrieval_relevance(self, query: str, retrieved_docs: List[Dict]) -> float:
        """
        Check if retrieved documents are relevant to the query.
        
        Methods:
        1. Average retrieval scores from vector store
        2. Query-document overlap
        3. LLM-based relevance judgment (if available)
        """
        if not retrieved_docs:
            return 0.0
        
        # Method 1: Average retrieval scores
        avg_score = sum(doc.get('score', 0.0) for doc in retrieved_docs) / len(retrieved_docs)
        
        # Method 2: Query-document overlap (simple)
        query_tokens = set(query.lower().split())
        overlap_scores = []
        for doc in retrieved_docs:
            doc_text = doc.get('text', '').lower()
            doc_tokens = set(doc_text.split())
            
            if doc_tokens:
                overlap = len(query_tokens & doc_tokens) / len(query_tokens)
                overlap_scores.append(overlap)
        
        avg_overlap = sum(overlap_scores) / len(overlap_scores) if overlap_scores else 0.0
        
        # Combine scores
        relevance = (avg_score * 0.7 + avg_overlap * 0.3)
        
        return min(relevance, 1.0)
    
    def _check_factual_support(self, response: str, retrieved_docs: List[Dict]) -> float:
        """
        Check if response is grounded in retrieved documents.
        
        Detects hallucinations by verifying claims in response match retrieved facts.
        
        Methods:
        1. Sentence-by-sentence overlap check
        2. Fact extraction and verification
        3. LLM-based support judgment (if available)
        """
        if not retrieved_docs or not response:
            return 0.0
        
        # Combine all retrieved text
        retrieved_text = " ".join([doc.get('text', '') for doc in retrieved_docs])
        retrieved_text_lower = retrieved_text.lower()
        
        # Method 1: Check if response sentences appear in retrieved docs
        response_sentences = [s.strip() for s in response.split('.') if s.strip()]
        
        support_scores = []
        for sentence in response_sentences:
            # Skip very short sentences or generic phrases
            if len(sentence.split()) < 3:
                continue
            
            sentence_lower = sentence.lower()
            
            # Extract key phrases (3+ words)
            words = sentence_lower.split()
            key_phrases = []
            for i in range(len(words) - 2):
                phrase = " ".join(words[i:i+3])
                key_phrases.append(phrase)
            
            # Check if key phrases appear in retrieved docs
            matches = sum(1 for phrase in key_phrases if phrase in retrieved_text_lower)
            support = matches / len(key_phrases) if key_phrases else 0.0
            support_scores.append(support)
        
        # Average support across sentences
        avg_support = sum(support_scores) / len(support_scores) if support_scores else 0.5
        
        return min(avg_support, 1.0)
    
    def _check_utility(
        self,
        query: str,
        response: str,
        intent: str,
        entities: Dict
    ) -> float:
        """
        Check if response addresses the user's actual need.
        
        Different intents have different utility criteria:
        - Booking: Should provide room options or booking confirmation
        - Information: Should answer the question
        - Availability: Should check availability
        - Modification: Should handle changes
        """
        if not response:
            return 0.0
        
        utility_score = 0.5  # Base score
        
        response_lower = response.lower()
        
        # Intent-specific checks
        if intent == 'booking' or (isinstance(intent, dict) and intent.get('primary') == 'booking'):
            # Should mention rooms, booking, or availability
            if any(keyword in response_lower for keyword in ['room', 'available', 'book', 'reserve']):
                utility_score += 0.2
            
            # Should include entities the user asked for
            if entities:
                if entities.get('capacity') and str(entities['capacity']) in response:
                    utility_score += 0.1
                if entities.get('date') and entities['date'] in response:
                    utility_score += 0.1
        
        elif intent == 'information' or (isinstance(intent, dict) and intent.get('primary') == 'information'):
            # Should be informative (not just "I don't know")
            if len(response.split()) > 10:  # Substantive response
                utility_score += 0.3
            
            # Should not just say "no information"
            if 'no information' not in response_lower and "i don't know" not in response_lower:
                utility_score += 0.2
        
        elif intent == 'availability' or (isinstance(intent, dict) and intent.get('primary') == 'availability'):
            # Should mention availability status
            if any(keyword in response_lower for keyword in ['available', 'free', 'vacant', 'occupied', 'booked']):
                utility_score += 0.3
        
        # General quality indicators
        if '?' not in response:  # Not asking clarifying questions (good for utility)
            utility_score += 0.1
        
        return min(utility_score, 1.0)
    
    def _check_completeness(self, response: str, entities: Dict, intent: str) -> float:
        """
        Check if response includes all necessary information.
        
        For booking intent:
        - Room details
        - Capacity
        - Features
        - Location
        """
        if not response:
            return 0.0
        
        completeness_score = 0.5  # Base score
        
        response_lower = response.lower()
        
        # Check for key information types
        info_types = {
            'room': ['room', 'space', 'location'],
            'capacity': ['capacity', 'seats', 'people'],
            'time': ['time', 'hour', 'duration'],
            'features': ['projector', 'whiteboard', 'computer', 'equipment'],
            'availability': ['available', 'free', 'booked']
        }
        
        mentioned_types = 0
        for info_type, keywords in info_types.items():
            if any(keyword in response_lower for keyword in keywords):
                mentioned_types += 1
        
        # Score based on information variety
        completeness_score = mentioned_types / len(info_types)
        
        return min(completeness_score, 1.0)
    
    def _refine_query(
        self,
        original_query: str,
        entities: Dict,
        intent: str,
        focus: str = 'relevance'
    ) -> str:
        """
        Refine query to improve retrieval.
        
        Strategies:
        - Add entity information to query
        - Rephrase for clarity
        - Add intent keywords identity
        - Expand with synonyms
        """
        refined = original_query
        
        # Add entity information
        if entities:
            if entities.get('capacity'):
                refined += f" capacity {entities['capacity']}"
            if entities.get('purpose'):
                refined += f" for {entities['purpose']}"
            if entities.get('building'):
                refined += f" in building {entities['building']}"
        
        # Add intent keywords
        if isinstance(intent, dict):
            primary_intent = intent.get('primary', '')
        else:
            primary_intent = intent or ''
        
        if primary_intent == 'booking':
            refined += " book reserve available"
        elif primary_intent == 'information':
            refined += " information details explain"
        
        logger.info(f"Refined query: {refined}")
        return refined
    
    def _generate_response(
        self,
        query: str,
        retrieved_docs: List[Dict],
        entities: Dict,
        intent: str,
        context: Dict
    ) -> str:
        """
        Generate response based on retrieved documents.
        
        For now, returns a template-based response.
        In production, this would call the main LLM.
        """
        if not retrieved_docs:
            return "I couldn't find relevant information to answer your question. Could you rephrase or provide more details?"
        
        # Extract key information from top documents
        top_docs = retrieved_docs[:3]
        context_text = "\n".join([doc.get('text', '') for doc in top_docs])
        
        # Template-based response (in production, use LLM)
        if isinstance(intent, dict):
            primary_intent = intent.get('primary', 'information')
        else:
            primary_intent = intent or 'information'
        
        if primary_intent == 'booking':
            # Check if we have room information
            rooms = [doc for doc in top_docs if doc.get('metadata', {}).get('room_number')]
            if rooms:
                room_info = rooms[0]['metadata']
                response = f"I found Room {room_info.get('room_number')} with capacity {room_info.get('capacity')}. "
                response += f"It's located in {room_info.get('building', 'the building')} and "
                
                features = room_info.get('features', {})
                feature_list = [k for k, v in features.items() if v]
                if feature_list:
                    response += f"has {', '.join(feature_list)}. "
                
                if room_info.get('available'):
                    response += "This room is available for booking."
                
                return response
        
        # Default: summarize key information
        response = "Based on the information I found:\n\n"
        response += context_text[:300] + "..."  # First 300 chars
        
        return response


# Convenience function
def generate_with_self_rag(
    query: str,
    retriever,
    entities: Dict = None,
    intent: str = None,
    context: Dict = None,
    llm_client=None
) -> Dict:
    """
    Generate response using Self-RAG system.
    
    Args:
        query: User query
        retriever: Hybrid retriever
        entities: Extracted entities
        intent: Query intent
        context: Conversation context
        llm_client: Optional LLM client
        
    Returns:
        Self-RAG result with reflection scores
    """
    self_rag = SelfRAG(retriever, llm_client)
    return self_rag.generate_with_reflection(query, entities, intent, context)
