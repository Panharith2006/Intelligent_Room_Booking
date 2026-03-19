"""
Hybrid Retrieval System for Advanced RAG
Combines semantic search, keyword search, and structured database queries
"""
import logging
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import numpy as np

logger = logging.getLogger(__name__)


class HybridRetriever:
    """
    Hybrid retrieval combining multiple search strategies:
    
    1. Semantic Search (Dense Vectors) - Embeddings similarity
    2. Keyword Search (Sparse Vectors) - BM25 algorithm
    3. Structured Query (Database) - SQL queries for real-time data
    
    Uses Reciprocal Rank Fusion (RRF) to combine results.
    """
    
    def __init__(
        self,
        vector_store,
        keyword_index=None,
        database_client=None,
        weights: Dict[str, float] = None
    ):
        """
        Initialize hybrid retriever.
        
        Args:
            vector_store: Vector database (ChromaDB) for semantic search
            keyword_index: Optional keyword search index (BM25)
            database_client: Optional database client for structured queries
            weights: Fusion weights for different search methods
        """
        self.vector_store = vector_store
        self.keyword_index = keyword_index
        self.database_client = database_client
        
        # Default weights for fusion
        self.weights = weights or {
            'semantic': 0.5,
            'keyword': 0.3,
            'structured': 0.2
        }
        
        logger.info(f"Hybrid retriever initialized with weights: {self.weights}")
    
    def retrieve(
        self,
        query: str,
        entities: Dict = None,
        intent: str = None,
        top_k: int = 10,
        filters: Dict = None,
        use_query_routing: bool = True
    ) -> List[Dict]:
        """
        Main retrieval method using hybrid approach.
        
        Args:
            query: User query string
            entities: Extracted entities (date, time, capacity, etc.)
            intent: Query intent (booking, information, etc.)
            top_k: Number of results to return
            filters: Optional metadata filters
            use_query_routing: Whether to route query to optimal retriever
            
        Returns:
            List of retrieved documents with scores and metadata
        """
        logger.info(f"Hybrid retrieval for query: {query[:100]}")
        logger.info(f"Intent: {intent}, Entities: {len(entities or {})}")
        
        # Query routing - select optimal retrieval strategy
        if use_query_routing and intent:
            retrieval_strategy = self._route_query(intent, entities)
            logger.info(f"Query routed to strategy: {retrieval_strategy}")
        else:
            retrieval_strategy = 'hybrid'
        
        # Execute retrieval based on strategy
        if retrieval_strategy == 'semantic_only':
            results = self._semantic_search(query, top_k, filters)
        
        elif retrieval_strategy == 'keyword_only':
            results = self._keyword_search(query, top_k, filters)
        
        elif retrieval_strategy == 'structured_only':
            results = self._structured_query(query, entities, top_k)
        
        else:  # hybrid
            results = self._hybrid_search(query, entities, top_k, filters)
        
        logger.info(f"Retrieved {len(results)} results")
        return results
    
    def _route_query(self, intent: str, entities: Dict) -> str:
        """
        Route query to optimal retrieval strategy.
        
        Routing Logic:
        - Real-time availability → Structured Query
        - Policy/document questions → Semantic Search
        - Specific room/ID lookups → Keyword Search
        - Complex queries → Hybrid Search
        """
        # Real-time availability check
        if intent in ['booking', 'availability'] and entities and 'date' in entities:
            return 'structured_only'
        
        # Policy/information queries
        elif intent == 'information' and any(keyword in intent for keyword in ['policy', 'rule', 'guide']):
            return 'semantic_only'
        
        # Specific ID/number lookups
        elif entities and ('room_number' in entities or 'building' in entities):
            return 'keyword_only'
        
        # Default to hybrid for complex queries
        else:
            return 'hybrid'
    
    def _semantic_search(self, query: str, top_k: int, filters: Dict = None) -> List[Dict]:
        """
        Semantic search using vector embeddings.
        
        Uses ChromaDB with cosine similarity.
        """
        if not self.vector_store:
            logger.warning("Vector store not available for semantic search")
            return []
        
        try:
            # Search in knowledge base collection
            results_kb = self.vector_store.search(
                collection_name='knowledge_base',
                query_text=query,
                n_results=top_k,
                where=filters
            )
            
            # Search in rooms info collection
            results_rooms = self.vector_store.search(
                collection_name='rooms_info',
                query_text=query,
                n_results=top_k // 2,
                where=filters
            )
            
            # Search in policies collection
            results_policies = self.vector_store.search(
                collection_name='booking_policies',
                query_text=query,
                n_results=top_k // 2,
                where=filters
            )
            
            # Combine results
            all_results = []
            
            for result_set in [results_kb, results_rooms, results_policies]:
                if result_set and result_set.get('documents'):
                    for i, doc in enumerate(result_set['documents'][0]):
                        metadata = result_set['metadatas'][0][i] if result_set.get('metadatas') else {}
                        distance = result_set['distances'][0][i] if result_set.get('distances') else 0.0
                        
                        # Convert distance to similarity score (1 - distance for cosine)
                        score = 1.0 - distance
                        
                        all_results.append({
                            'text': doc,
                            'score': score,
                            'metadata': metadata,
                            'source': 'semantic'
                        })
            
            # Sort by score and limit
            all_results.sort(key=lambda x: x['score'], reverse=True)
            return all_results[:top_k]
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def _keyword_search(self, query: str, top_k: int, filters: Dict = None) -> List[Dict]:
        """
        Keyword search using BM25 algorithm.
        
        Good for exact matches and specific terms.
        """
        if not self.keyword_index:
            logger.warning("Keyword index not available, falling back to semantic search")
            return self._semantic_search(query, top_k, filters)
        
        try:
            # Perform BM25 search
            results = self.keyword_index.search(query, limit=top_k, filters=filters)
            
            # Format results
            formatted_results = []
            for result in results:
                formatted_results.append({
                    'text': result.get('text', ''),
                    'score': result.get('score', 0.0),
                    'metadata': result.get('metadata', {}),
                    'source': 'keyword'
                })
            
            return formatted_results
            
        except Exception as e:
            logger.error(f"Keyword search failed: {e}")
            return []
    
    def _structured_query(self, query: str, entities: Dict, top_k: int) -> List[Dict]:
        """
        Structured database query for real-time data.
        
        Directly queries Django models for:
        - Room availability
        - Booking information
        - User data
        """
        if not entities:
            logger.warning("No entities provided for structured query")
            return []
        
        try:
            from booking.models import Room, Booking
            from django.db.models import Q
            from datetime import datetime, time as dt_time
            
            results = []
            
            # Query rooms based on entities
            rooms_query = Room.objects.filter(is_available=True)
            
            # Apply filters
            if entities.get('capacity'):
                rooms_query = rooms_query.filter(capacity__gte=entities['capacity'])
            
            if entities.get('building'):
                building = entities['building']
                rooms_query = rooms_query.filter(
                    Q(building_name__icontains=building) | Q(building__icontains=building)
                )
            
            if entities.get('room_number'):
                rooms_query = rooms_query.filter(room_number__iexact=entities['room_number'])
            
            if entities.get('purpose'):
                purpose = entities['purpose']
                # Map purpose to room type
                type_mapping = {
                    'meeting': 'meeting',
                    'conference': 'conference',
                    'lecture': 'lecture',
                    'lab': 'lab',
                    'workshop': 'training'
                }
                room_type = type_mapping.get(purpose)
                if room_type:
                    rooms_query = rooms_query.filter(room_type=room_type)
            
            # Check availability if date/time provided
            if entities.get('date') and entities.get('start_time'):
                date = entities['date']
                start_time = entities['start_time']
                end_time = entities.get('end_time', '23:59')
                
                # Find rooms without conflicts
                available_rooms = []
                for room in rooms_query[:top_k * 2]:  # Check more rooms than needed
                    # Check for conflicts
                    conflicts = Booking.objects.filter(
                        room=room,
                        date=date,
                        status__in=['pending', 'approved']
                    ).filter(
                        Q(start_time__lt=end_time, end_time__gt=start_time)
                    )
                    
                    if not conflicts.exists():
                        available_rooms.append(room)
                        
                        # Format as result
                        results.append({
                            'text': f"Room {room.room_number} - {room.name} (Capacity: {room.capacity})",
                            'score': 1.0,  # Available rooms get perfect score
                            'metadata': {
                                'room_id': room.id,
                                'room_number': room.room_number,
                                'capacity': room.capacity,
                                'building': getattr(room, 'building_name', None) or getattr(room, 'building', ''),
                                'features': {
                                    'projector': getattr(room, 'has_projector', False),
                                    'whiteboard': getattr(room, 'has_whiteboard', False),
                                    'computer': getattr(room, 'has_computer', False)
                                },
                                'available': True
                            },
                            'source': 'structured'
                        })
                    
                    if len(results) >= top_k:
                        break
            else:
                # Just return room information
                for room in rooms_query[:top_k]:
                    results.append({
                        'text': f"Room {room.room_number} - {room.name} (Capacity: {room.capacity})",
                        'score': 0.8,
                        'metadata': {
                            'room_id': room.id,
                            'room_number': room.room_number,
                            'capacity': room.capacity,
                            'building': getattr(room, 'building_name', None) or getattr(room, 'building', ''),
                            'features': {
                                'projector': getattr(room, 'has_projector', False),
                                'whiteboard': getattr(room, 'has_whiteboard', False),
                                'computer': getattr(room, 'has_computer', False)
                            }
                        },
                        'source': 'structured'
                    })
            
            logger.info(f"Structured query returned {len(results)} results")
            return results
            
        except Exception as e:
            logger.error(f"Structured query failed: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    def _hybrid_search(
        self,
        query: str,
        entities: Dict,
        top_k: int,
        filters: Dict = None
    ) -> List[Dict]:
        """
        Combine semantic, keyword, and structured searches using RRF.
        
        Reciprocal Rank Fusion (RRF):
        score(doc) = Σ 1 / (k + rank(doc))
        where k=60 is a constant
        """
        # Perform all searches
        semantic_results = self._semantic_search(query, top_k * 2, filters)
        keyword_results = self._keyword_search(query, top_k * 2, filters) if self.keyword_index else []
        structured_results = self._structured_query(query, entities, top_k) if entities else []
        
        # Apply RRF fusion
        fused_results = self._reciprocal_rank_fusion(
            [semantic_results, keyword_results, structured_results],
            ['semantic', 'keyword', 'structured']
        )
        
        # Apply weights
        for result in fused_results:
            source = result.get('source', 'semantic')
            weight = self.weights.get(source, 0.5)
            result['score'] = result['score'] * weight
        
        # Sort by final score
        fused_results.sort(key=lambda x: x['score'], reverse=True)
        
        return fused_results[:top_k]
    
    def _reciprocal_rank_fusion(
        self,
        result_lists: List[List[Dict]],
        sources: List[str],
        k: int = 60
    ) -> List[Dict]:
        """
        Combine multiple result lists using Reciprocal Rank Fusion.
        
        RRF Formula: score(doc) = Σ 1 / (k + rank(doc))
        
        Args:
            result_lists: List of result lists from different retrievers
            sources: Source names for each result list
            k: RRF constant (default 60)
            
        Returns:
            Fused and ranked results
        """
        # Track documents by unique identifier (text hash)
        doc_scores = {}
        doc_metadata = {}
        
        for results, source in zip(result_lists, sources):
            for rank, doc in enumerate(results, start=1):
                text = doc.get('text', '')
                doc_id = hash(text)  # Simple hash as unique ID
                
                # Calculate RRF score
                rrf_score = 1.0 / (k + rank)
                
                # Accumulate scores
                if doc_id in doc_scores:
                    doc_scores[doc_id] += rrf_score
                else:
                    doc_scores[doc_id] = rrf_score
                    doc_metadata[doc_id] = {
                        'text': text,
                        'metadata': doc.get('metadata', {}),
                        'sources': [source]
                    }
                
                # Track which sources contributed
                if doc_id in doc_metadata and source not in doc_metadata[doc_id]['sources']:
                    doc_metadata[doc_id]['sources'].append(source)
        
        # Create final result list
        fused_results = []
        for doc_id, score in doc_scores.items():
            metadata = doc_metadata[doc_id]
            fused_results.append({
                'text': metadata['text'],
                'score': score,
                'metadata': metadata['metadata'],
                'sources': metadata['sources'],  # Multiple sources
                'source': metadata['sources'][0]  # Primary source
            })
        
        # Sort by score
        fused_results.sort(key=lambda x: x['score'], reverse=True)
        
        return fused_results


class MultiQueryRetriever:
    """
    Generate multiple query variations and retrieve for each.
    
    Improves recall by capturing different phrasings of the same question.
    """
    
    def __init__(self, base_retriever: HybridRetriever, num_queries: int = 3):
        """
        Initialize multi-query retriever.
        
        Args:
            base_retriever: Base hybrid retriever
            num_queries: Number of query variations to generate
        """
        self.base_retriever = base_retriever
        self.num_queries = num_queries
    
    def retrieve(
        self,
        query: str,
        query_variations: List[str] = None,
        entities: Dict = None,
        intent: str = None,
        top_k: int = 10
    ) -> List[Dict]:
        """
        Retrieve using multiple query variations.
        
        Args:
            query: Original query
            query_variations: Pre-generated query variations
            entities: Extracted entities
            intent: Query intent
            top_k: Number of final results
            
        Returns:
            Combined results from all query variations
        """
        # Use provided variations or generate new ones
        if query_variations is None:
            query_variations = [query]
        
        logger.info(f"Multi-query retrieval with {len(query_variations)} variations")
        
        # Retrieve for each variation
        all_results = []
        for variation in query_variations:
            results = self.base_retriever.retrieve(
                query=variation,
                entities=entities,
                intent=intent,
                top_k=top_k,
                use_query_routing=False  # Already routed
            )
            all_results.append(results)
        
        # Fuse results using RRF
        fused = self.base_retriever._reciprocal_rank_fusion(
            all_results,
            [f"query_{i}" for i in range(len(all_results))]
        )
        
        # Deduplicate by text similarity (keep highest scoring)
        deduplicated = self._deduplicate_results(fused)
        
        return deduplicated[:top_k]
    
    def _deduplicate_results(self, results: List[Dict], similarity_threshold: float = 0.9) -> List[Dict]:
        """
        Remove duplicate/very similar results.
        
        Uses simple text similarity (could be enhanced with embedding similarity).
        """
        if not results:
            return []
        
        deduplicated = [results[0]]  # Always keep top result
        
        for result in results[1:]:
            text = result.get('text', '').lower()
            
            # Check similarity with already selected results
            is_duplicate = False
            for selected in deduplicated:
                selected_text = selected.get('text', '').lower()
                
                # Simple similarity: check if one is substring of other
                if text in selected_text or selected_text in text:
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(result)
        
        return deduplicated


# Convenience function
def hybrid_retrieve(
    query: str,
    vector_store,
    entities: Dict = None,
    intent: str = None,
    top_k: int = 10,
    use_multi_query: bool = False,
    query_variations: List[str] = None
) -> List[Dict]:
    """
    Convenience function for hybrid retrieval.
    
    Args:
        query: User query
        vector_store: Vector database
        entities: Extracted entities
        intent: Query intent
        top_k: Number of results
        use_multi_query: Whether to use multi-query retrieval
        query_variations: Pre-generated query variations
        
    Returns:
        Retrieved documents
    """
    retriever = HybridRetriever(vector_store)
    
    if use_multi_query:
        multi_retriever = MultiQueryRetriever(retriever)
        return multi_retriever.retrieve(
            query=query,
            query_variations=query_variations,
            entities=entities,
            intent=intent,
            top_k=top_k
        )
    else:
        return retriever.retrieve(
            query=query,
            entities=entities,
            intent=intent,
            top_k=top_k
        )
