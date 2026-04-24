import logging
from typing import Dict, List, Optional
from datetime import datetime
import json

# Import all advanced RAG components
from ai.query_processor import QueryProcessor
from ai.hybrid_retriever import HybridRetriever, MultiQueryRetriever
from ai.reranker import HybridReRanker, DocumentReRanker
from ai.self_rag import SelfRAG
from ai.vector_store import VectorStore

logger = logging.getLogger(__name__)

class AgenticRAG:
    
    def __init__(
        self,
        vector_store: VectorStore = None,
        llm_client=None,
        enable_self_rag: bool = True,
        enable_reranking: bool = True,
        enable_multi_query: bool = True
    ):
        # Initialize vector store
        self.vector_store = vector_store or VectorStore()
        self.llm_client = llm_client
        
        # Feature flags
        self.enable_self_rag = enable_self_rag
        self.enable_reranking = enable_reranking
        self.enable_multi_query = enable_multi_query
        
        # Initialize components
        logger.info("Initializing Agentic RAG components...")
        
        # Query processor
        self.query_processor = QueryProcessor(llm_client)
        
        # Hybrid retriever
        self.retriever = HybridRetriever(
            vector_store=self.vector_store,
            keyword_index=None,  # Can add BM25 index later
            database_client=None  # Uses Django ORM
        )
        
        # Multi-query retriever (wraps hybrid retriever)
        if self.enable_multi_query:
            self.multi_query_retriever = MultiQueryRetriever(self.retriever, num_queries=3)
        
        # Re-ranker
        if self.enable_reranking:
            try:
                self.reranker = HybridReRanker()
                logger.info(" Re-ranking enabled")
            except Exception as e:
                logger.warning(f"Re-ranking initialization failed: {e}")
                self.enable_reranking = False
        
        # Self-RAG
        if self.enable_self_rag:
            self.self_rag = SelfRAG(self.retriever, llm_client)
            logger.info(" Self-RAG enabled")
        
        logger.info(f" Agentic RAG initialized (Self-RAG: {self.enable_self_rag}, "
                   f"Re-ranking: {self.enable_reranking}, Multi-Query: {self.enable_multi_query})")
    
    def process_query(
        self,
        query: str,
        context: Dict = None,
        conversation_history: List[Dict] = None,
        user_info: Dict = None,
        top_k: int = 5,
        use_self_rag: bool = None
    ) -> Dict:
        
        logger.info(f"=" * 80)
        logger.info(f"Processing query: {query}")
        logger.info(f"=" * 80)
        
        start_time = datetime.now()
        
        # Step 1: Query Understanding & Preprocessing
        logger.info("Step 1: Query Processing...")
        processed_query = self.query_processor.process_query(query, context)
        
        intent = processed_query['intent']
        entities = processed_query['entities']
        sub_queries = processed_query['sub_queries']
        expanded_queries = processed_query['expanded_queries']
        complexity = processed_query['complexity']
        
        logger.info(f"  Intent: {intent.get('primary') if isinstance(intent, dict) else intent}")
        logger.info(f"  Entities: {entities}")
        logger.info(f"  Complexity: {complexity}/5")
        
        # Step 2: Retrieval Strategy Selection
        logger.info("Step 2: Retrieval...")
        
        # Decide whether to use multi-query based on complexity
        use_multi_query = self.enable_multi_query and complexity >= 3
        
        if use_multi_query:
            logger.info(f"  Using multi-query retrieval with {len(expanded_queries)} variations")
            retrieved_docs = self.multi_query_retriever.retrieve(
                query=query,
                query_variations=expanded_queries,
                entities=entities,
                intent=intent,
                top_k=top_k * 2  # Retrieve more for re-ranking
            )
        else:
            logger.info("  Using standard hybrid retrieval")
            retrieved_docs = self.retriever.retrieve(
                query=query,
                entities=entities,
                intent=intent,
                top_k=top_k * 2,
                use_query_routing=True
            )
        
        logger.info(f"  Retrieved {len(retrieved_docs)} documents")
        
        # Step 3: Re-Ranking (if enabled)
        if self.enable_reranking and retrieved_docs:
            logger.info("Step 3: Re-ranking...")
            retrieved_docs = self.reranker.rerank(
                query=query,
                documents=retrieved_docs,
                top_k=top_k
            )
            logger.info(f"  Re-ranked to top {len(retrieved_docs)} documents")
        else:
            # Just take top_k
            retrieved_docs = retrieved_docs[:top_k]
        
        # Step 4: Context Compression (optional)
        compressed_docs = self._compress_context(retrieved_docs, query, entities)
        
        # Step 5: Self-RAG or Standard Generation
        use_self_rag_flag = use_self_rag if use_self_rag is not None else self.enable_self_rag
        
        if use_self_rag_flag:
            logger.info("Step 4: Self-RAG Generation...")
            try:
                self_rag_result = self.self_rag.generate_with_reflection(
                    query=query,
                    entities=entities,
                    intent=intent,
                    context=context,
                    max_iterations=2
                )
                
                # Safely extract response with fallback
                response_text = self_rag_result.get('response') or self._generate_response(
                    query=query,
                    retrieved_docs=compressed_docs,
                    entities=entities,
                    intent=intent,
                    context=context
                )
                reflection_scores = self_rag_result.get('reflection_scores', {})
                
                logger.info(f"  Reflection scores: {reflection_scores}")
            except Exception as e:
                logger.warning(f"Self-RAG failed, falling back to standard generation: {e}")
                response_text = self._generate_response(
                    query=query,
                    retrieved_docs=compressed_docs,
                    entities=entities,
                    intent=intent,
                    context=context
                )
                reflection_scores = None
        else:
            logger.info("Step 4: Standard Generation...")
            response_text = self._generate_response(
                query=query,
                retrieved_docs=compressed_docs,
                entities=entities,
                intent=intent,
                context=context
            )
            reflection_scores = None
        
        # Calculate processing time
        processing_time = (datetime.now() - start_time).total_seconds()
        
        # Prepare result
        result = {
            'response_text': response_text,
            'retrieved_docs': [
                {
                    'text': doc.get('text', '')[:200],  # Truncate for response
                    'score': doc.get('score', 0.0),
                    'source': doc.get('source', 'unknown'),
                    'metadata': doc.get('metadata', {})
                }
                for doc in compressed_docs
            ],
            'entities': entities,
            'intent': intent,
            'complexity': complexity,
            'reflection_scores': reflection_scores,
            'processing_time': processing_time,
            'metadata': {
                'num_retrieved': len(retrieved_docs),
                'num_re_ranked': len(compressed_docs) if self.enable_reranking else 0,
                'used_multi_query': use_multi_query,
                'used_self_rag': use_self_rag_flag,
                'query_variations': expanded_queries if use_multi_query else [query]
            }
        }
        
        logger.info(f"✓ Processing complete in {processing_time:.2f}s")
        logger.info(f"=" * 80)
        
        return result
    
    def _compress_context(
        self,
        documents: List[Dict],
        query: str,
        entities: Dict
    ) -> List[Dict]:
        if not documents:
            return []
        
        # For now, simple deduplication and truncation
        # In production, could use extractive summarization
        
        compressed = []
        seen_texts = set()
        
        for doc in documents:
            text = doc.get('text', '')
            
            # Skip near-duplicates
            text_hash = hash(text[:100])  # Hash first 100 chars
            if text_hash in seen_texts:
                continue
            seen_texts.add(text_hash)
            
            # Truncate very long documents
            if len(text) > 1000:
                # Extract sentences containing query terms
                query_terms = set(query.lower().split())
                sentences = text.split('.')
                relevant_sentences = []
                
                for sentence in sentences:
                    sentence_terms = set(sentence.lower().split())
                    if query_terms & sentence_terms:  # Intersection
                        relevant_sentences.append(sentence)
                
                if relevant_sentences:
                    text = '. '.join(relevant_sentences[:3]) + '.'  # Top 3 relevant sentences
                else:
                    text = text[:500]  # Just truncate
            
            doc_copy = doc.copy()
            doc_copy['text'] = text
            compressed.append(doc_copy)
        
        return compressed
    
    def _generate_response(
        self,
        query: str,
        retrieved_docs: List[Dict],
        entities: Dict,
        intent: Dict,
        context: Dict
    ) -> str:

        if not retrieved_docs:
            return self._handle_no_results(query, entities, intent)
        
        # Get primary intent
        if isinstance(intent, dict):
            primary_intent = intent.get('primary', 'information')
        else:
            primary_intent = intent
        
        # Intent-specific response generation
        if primary_intent == 'booking':
            return self._generate_booking_response(query, retrieved_docs, entities, context)
        
        elif primary_intent == 'information':
            return self._generate_information_response(query, retrieved_docs, entities)
        
        elif primary_intent == 'availability':
            return self._generate_availability_response(query, retrieved_docs, entities)
        
        else:
            # Generic response
            context_text = "\n\n".join([doc.get('text', '') for doc in retrieved_docs[:3]])
            return f"Based on the available information:\n\n{context_text[:500]}"
    
    def _generate_booking_response(
        self,
        query: str,
        docs: List[Dict],
        entities: Dict,
        context: Dict
    ) -> str:
        

        # Check if we have room information from structured query
        room_docs = [d for d in docs if d.get('source') == 'structured']
        
        if room_docs:
            # We have real-time room data
            response = "I found the following available rooms:\n\n"
            
            for i, doc in enumerate(room_docs[:3], 1):
                metadata = doc.get('metadata', {})
                response += f"{i}. Room {metadata.get('room_number', 'N/A')} "
                response += f"(Capacity: {metadata.get('capacity', 'N/A')})\n"
                
                building = metadata.get('building')
                if building:
                    response += f"   Location: Building {building}\n"
                
                features = metadata.get('features', {})
                feature_list = [k.replace('_', ' ').title() for k, v in features.items() if v]
                if feature_list:
                    response += f"   Features: {', '.join(feature_list)}\n"
                
                response += "\n"
            
            # Add booking instructions
            if entities.get('date') and entities.get('start_time'):
                response += f"\nTo book, please confirm:\n"
                response += f"- Date: {entities.get('date')}\n"
                response += f"- Time: {entities.get('start_time')} - {entities.get('end_time', 'TBD')}\n"
                response += f"- Room: [Select from above]\n"
            else:
                response += "\nPlease specify date and time to proceed with booking."
        else:
            # General booking information
            response = "To book a room, I'll need the following information:\n\n"
            
            missing = []
            if not entities.get('date'):
                missing.append("- Date (e.g., tomorrow, 15/03/2026)")
            if not entities.get('start_time'):
                missing.append("- Start time (e.g., 2 PM, 14:00)")
            if not entities.get('end_time'):
                missing.append("- End time (e.g., 4 PM, 16:00)")
            if not entities.get('capacity'):
                missing.append("- Number of people")
            
            if missing:
                response += "\n".join(missing)
            else:
                response += "You've provided all the required information. Searching for available rooms..."
        
        return response
    
    def _generate_information_response(
        self,
        query: str,
        docs: List[Dict],
        entities: Dict
    ) -> str:
    

        # Combine top documents
        info = []
        for doc in docs[:3]:
            text = doc.get('text', '').strip()
            if text:
                info.append(text)
        
        if info:
            response = "\n\n".join(info)
            # Truncate if too long
            if len(response) > 800:
                response = response[:800] + "...\n\nWould you like more specific information?"
        else:
            response = "I couldn't find specific information about that. Could you rephrase your question?"
        
        return response
    
    def _generate_availability_response(
        self,
        query: str,
        docs: List[Dict],
        entities: Dict
    ) -> str:
        
        
        room_docs = [d for d in docs if d.get('source') == 'structured']
        
        if room_docs and entities.get('date'):
            available_count = sum(1 for d in room_docs if d.get('metadata', {}).get('available', False))
            
            response = f"Availability for {entities.get('date')}:\n\n"
            
            if available_count > 0:
                response += f"✓ {available_count} room(s) available\n\n"
                for doc in room_docs[:5]:
                    metadata = doc.get('metadata', {})
                    if metadata.get('available'):
                        response += f"- Room {metadata.get('room_number')}: Available "
                        response += f"(Capacity: {metadata.get('capacity')})\n"
            else:
                response += "✗ No rooms available for the specified time.\n\n"
                response += "Try different times or dates?"
        else:
            response = "To check availability, please specify:\n"
            if not entities.get('date'):
                response += "- Date\n"
            if not entities.get('start_time'):
                response += "- Start time\n"
            if not entities.get('end_time'):
                response += "- End time\n"
        
        return response
    
    def _handle_no_results(self, query: str, entities: Dict, intent: Dict) -> str:
        

        response = "I couldn't find relevant information for your query. "
        
        # Provide helpful suggestions
        if isinstance(intent, dict):
            primary_intent = intent.get('primary')
        else:
            primary_intent = intent
        
        if primary_intent == 'booking':
            response += "To help you book a room, please provide:\n"
            response += "- Date (e.g., tomorrow, 15/03/2026)\n"
            response += "- Time (e.g., 2-4 PM)\n"
            response += "- Number of people\n"
        else:
            response += "Could you rephrase your question or provide more details?"
        
        return response
    
    def get_conversation_summary(self, conversation_history: List[Dict]) -> str:
        
        if not conversation_history:
            return ""
        
        # Extract key information from history
        summary_parts = []
        
        for turn in conversation_history[-3:]:  # Last 3 turns
            role = turn.get('role', 'user')
            content = turn.get('content', '')
            
            if role == 'user':
                summary_parts.append(f"User asked: {content[:100]}")
            else:
                summary_parts.append(f"Assistant: {content[:100]}")
        
        return " | ".join(summary_parts)


# Convenience function
def process_with_agentic_rag(
    query: str,
    vector_store: VectorStore = None,
    context: Dict = None,
    user_info: Dict = None,
    top_k: int = 5
) -> Dict:
   
    rag = AgenticRAG(vector_store=vector_store)
    return rag.process_query(
        query=query,
        context=context,
        user_info=user_info,
        top_k=top_k
    )
