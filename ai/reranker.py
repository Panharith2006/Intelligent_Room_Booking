"""
Cross-Encoder Re-Ranker for RAG System
Improves retrieval precision by re-scoring retrieved documents
"""
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np

logger = logging.getLogger(__name__)


class DocumentReRanker:
    """
    Re-ranks retrieved documents using a cross-encoder model.
    
    Cross-encoders process query and document together, producing
    a relevance score that's more accurate than cosine similarity alone.
    
    Model: cross-encoder/ms-marco-MiniLM-L-6-v2
    - Trained on MS MARCO dataset
    - Input: (query, document) pair
    - Output: Relevance score 0-1
    """
    
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """
        Initialize re-ranker with cross-encoder model.
        
        Args:
            model_name: HuggingFace cross-encoder model name
        """
        self.model_name = model_name
        self.model = None
        self._load_model()
    
    def _load_model(self):
        """Lazy load the cross-encoder model."""
        try:
            from sentence_transformers import CrossEncoder
            logger.info(f"Loading cross-encoder model: {self.model_name}...")
            self.model = CrossEncoder(self.model_name)
            logger.info(f"✓ Cross-encoder model loaded: {self.model_name}")
            return True
        except ImportError:
            logger.warning("sentence-transformers not installed. Install with: pip install sentence-transformers")
            logger.warning("Re-ranking will be disabled")
            return False
        except Exception as e:
            logger.error(f"Failed to load cross-encoder model: {e}")
            return False
    
    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = None,
        score_field: str = 'score',
        text_field: str = 'text'
    ) -> List[Dict]:
        """
        Re-rank documents based on relevance to query.
        
        Args:
            query: User query
            documents: List of document dicts with text content
            top_k: Number of top documents to return (None = all)
            score_field: Field name to store re-ranking score
            text_field: Field name containing document text
            
        Returns:
            Re-ranked list of documents with updated scores
        """
        if not self.model:
            logger.warning("Cross-encoder model not available, skipping re-ranking")
            return documents
        
        if not documents:
            return []
        
        logger.info(f"Re-ranking {len(documents)} documents for query: {query[:100]}...")
        
        try:
            # Prepare query-document pairs
            pairs = []
            for doc in documents:
                text = doc.get(text_field, '')
                if isinstance(text, str):
                    pairs.append([query, text])
                else:
                    pairs.append([query, str(text)])
            
            # Get relevance scores from cross-encoder
            scores = self.model.predict(pairs)
            
            # Update documents with new scores
            reranked_docs = []
            for doc, score in zip(documents, scores):
                doc_copy = doc.copy()
                doc_copy['original_score'] = doc_copy.get(score_field, 0.0)
                doc_copy[score_field] = float(score)
                doc_copy['reranked'] = True
                reranked_docs.append(doc_copy)
            
            # Sort by new score
            reranked_docs.sort(key=lambda x: x[score_field], reverse=True)
            
            # Apply top_k filter
            if top_k:
                reranked_docs = reranked_docs[:top_k]
            
            logger.info(f"✓ Re-ranking complete. Top score: {reranked_docs[0][score_field]:.4f}")
            
            return reranked_docs
            
        except Exception as e:
            logger.error(f"Re-ranking failed: {e}")
            return documents
    
    def rerank_pairs(
        self,
        query: str,
        texts: List[str]
    ) -> List[Tuple[str, float]]:
        """
        Re-rank a list of text strings and return with scores.
        
        Args:
            query: User query
            texts: List of text strings to rank
            
        Returns:
            List of (text, score) tuples sorted by relevance
        """
        if not self.model:
            logger.warning("Cross-encoder model not available")
            return [(text, 0.0) for text in texts]
        
        try:
            # Prepare pairs
            pairs = [[query, text] for text in texts]
            
            # Get scores
            scores = self.model.predict(pairs)
            
            # Combine and sort
            ranked = list(zip(texts, scores))
            ranked.sort(key=lambda x: x[1], reverse=True)
            
            return ranked
            
        except Exception as e:
            logger.error(f"Re-ranking pairs failed: {e}")
            return [(text, 0.0) for text in texts]
    
    def score_relevance(self, query: str, document: str) -> float:
        """
        Get relevance score for a single query-document pair.
        
        Args:
            query: User query
            document: Document text
            
        Returns:
            Relevance score (0-1, higher is more relevant)
        """
        if not self.model:
            return 0.0
        
        try:
            score = self.model.predict([query, document])
            return float(score)
        except Exception as e:
            logger.error(f"Scoring failed: {e}")
            return 0.0


class HybridReRanker:
    """
    Combine multiple ranking signals for improved results.
    
    Combines:
    1. Cross-encoder relevance score
    2. Original retrieval score (cosine similarity)
    3. Metadata boosting (recency, source authority)
    4. Query-document overlap metrics
    """
    
    def __init__(self, cross_encoder_model: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        """Initialize hybrid re-ranker."""
        self.cross_encoder = DocumentReRanker(cross_encoder_model)
        
        # Weights for different signals
        self.weights = {
            'cross_encoder': 0.5,      # Cross-encoder score
            'retrieval_score': 0.2,    # Original cosine similarity
            'metadata': 0.15,          # Metadata boosting
            'overlap': 0.15            # Query-document overlap
        }
    
    def rerank(
        self,
        query: str,
        documents: List[Dict],
        top_k: int = None,
        text_field: str = 'text'
    ) -> List[Dict]:
        """
        Re-rank using multiple signals.
        
        Args:
            query: User query
            documents: List of document dicts
            top_k: Number of top results to return
            text_field: Field containing document text
            
        Returns:
            Re-ranked documents
        """
        if not documents:
            return []
        
        logger.info(f"Hybrid re-ranking {len(documents)} documents...")
        
        # Get cross-encoder scores
        ce_docs = self.cross_encoder.rerank(query, documents, top_k=None, text_field=text_field)
        
        # Calculate additional signals
        for doc in ce_docs:
            # Metadata score
            metadata_score = self._calculate_metadata_score(doc)
            doc['metadata_score'] = metadata_score
            
            # Overlap score
            overlap_score = self._calculate_overlap_score(query, doc.get(text_field, ''))
            doc['overlap_score'] = overlap_score
            
            # Combine scores
            hybrid_score = (
                self.weights['cross_encoder'] * doc.get('score', 0.0) +
                self.weights['retrieval_score'] * doc.get('original_score', 0.0) +
                self.weights['metadata'] * metadata_score +
                self.weights['overlap'] * overlap_score
            )
            doc['hybrid_score'] = hybrid_score
        
        # Sort by hybrid score
        ce_docs.sort(key=lambda x: x['hybrid_score'], reverse=True)
        
        # Apply top_k
        if top_k:
            ce_docs = ce_docs[:top_k]
        
        logger.info(f"✓ Hybrid re-ranking complete. Top hybrid score: {ce_docs[0]['hybrid_score']:.4f}")
        
        return ce_docs
    
    def _calculate_metadata_score(self, doc: Dict) -> float:
        """
        Calculate score boost based on document metadata.
        
        Factors:
        - Recency (newer documents scored higher)
        - Source authority (official sources boosted)
        - Document type (policies > general info)
        """
        score = 0.5  # Base score
        
        metadata = doc.get('metadata', {})
        
        # Recency boost (if document has timestamp)
        if 'timestamp' in metadata or 'date' in metadata:
            # Boost recent documents
            score += 0.2
        
        # Source authority boost
        source = metadata.get('source', '').lower()
        if any(keyword in source for keyword in ['policy', 'rule', 'official', 'guide']):
            score += 0.2
        
        # Document type boost
        doc_type = metadata.get('type', '').lower()
        if doc_type in ['policy', 'rule', 'regulation']:
            score += 0.15
        elif doc_type in ['guide', 'manual', 'documentation']:
            score += 0.1
        
        return min(score, 1.0)
    
    def _calculate_overlap_score(self, query: str, document: str) -> float:
        """
        Calculate query-document term overlap score.
        
        Uses Jaccard similarity on word tokens.
        """
        if not document:
            return 0.0
        
        try:
            # Tokenize and normalize
            query_tokens = set(query.lower().split())
            doc_tokens = set(document.lower().split())
            
            # Remove stop words (simple version)
            stop_words = {'the', 'a', 'an', 'is', 'are', 'was', 'were', 'in', 'on', 'at', 'to', 'for'}
            query_tokens -= stop_words
            doc_tokens -= stop_words
            
            # Calculate Jaccard similarity
            if not query_tokens or not doc_tokens:
                return 0.0
            
            intersection = len(query_tokens & doc_tokens)
            union = len(query_tokens | doc_tokens)
            
            jaccard = intersection / union if union > 0 else 0.0
            
            return jaccard
            
        except Exception as e:
            logger.error(f"Overlap calculation failed: {e}")
            return 0.0


class MMRReRanker:
    """
    Maximal Marginal Relevance (MMR) Re-Ranker.
    
    Balances relevance and diversity to avoid redundant results.
    Useful when you want varied information, not just similar documents.
    
    MMR = λ * relevance - (1-λ) * max_similarity_to_selected
    """
    
    def __init__(self, lambda_param: float = 0.7):
        """
        Initialize MMR re-ranker.
        
        Args:
            lambda_param: Balance between relevance (1.0) and diversity (0.0)
                         Default 0.7 = 70% relevance, 30% diversity
        """
        self.lambda_param = lambda_param
    
    def rerank(
        self,
        documents: List[Dict],
        top_k: int,
        score_field: str = 'score',
        embedding_field: str = 'embedding'
    ) -> List[Dict]:
        """
        Re-rank documents using MMR for diversity.
        
        Args:
            documents: List of documents with scores and embeddings
            top_k: Number of documents to return
            score_field: Field containing relevance scores
            embedding_field: Field containing document embeddings
            
        Returns:
            Diversified list of documents
        """
        if not documents or top_k <= 0:
            return []
        
        logger.info(f"MMR re-ranking {len(documents)} documents for diversity...")
        
        selected = []
        remaining = documents.copy()
        
        # Select first document (highest relevance)
        remaining.sort(key=lambda x: x.get(score_field, 0.0), reverse=True)
        selected.append(remaining.pop(0))
        
        # Iteratively select diverse documents
        while len(selected) < top_k and remaining:
            mmr_scores = []
            
            for doc in remaining:
                relevance = doc.get(score_field, 0.0)
                
                # Calculate max similarity to already selected documents
                max_sim = 0.0
                if embedding_field in doc and embedding_field in selected[0]:
                    doc_emb = doc[embedding_field]
                    for sel_doc in selected:
                        sel_emb = sel_doc.get(embedding_field)
                        if sel_emb is not None:
                            sim = self._cosine_similarity(doc_emb, sel_emb)
                            max_sim = max(max_sim, sim)
                
                # Calculate MMR score
                mmr = self.lambda_param * relevance - (1 - self.lambda_param) * max_sim
                mmr_scores.append((doc, mmr))
            
            # Select document with highest MMR
            if mmr_scores:
                best_doc, best_score = max(mmr_scores, key=lambda x: x[1])
                selected.append(best_doc)
                remaining.remove(best_doc)
        
        logger.info(f"✓ MMR re-ranking complete. Selected {len(selected)} diverse documents")
        
        return selected
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors."""
        try:
            v1 = np.array(vec1)
            v2 = np.array(vec2)
            
            dot_product = np.dot(v1, v2)
            norm_product = np.linalg.norm(v1) * np.linalg.norm(v2)
            
            if norm_product == 0:
                return 0.0
            
            return dot_product / norm_product
        except Exception:
            return 0.0


# Convenience functions
def rerank_documents(query: str, documents: List[Dict], top_k: int = 5, method: str = 'cross_encoder') -> List[Dict]:
    """
    Convenience function for document re-ranking.
    
    Args:
        query: User query
        documents: List of documents to re-rank
        top_k: Number of top results to return
        method: Re-ranking method ('cross_encoder', 'hybrid', 'mmr')
        
    Returns:
        Re-ranked documents
    """
    if method == 'cross_encoder':
        reranker = DocumentReRanker()
        return reranker.rerank(query, documents, top_k=top_k)
    
    elif method == 'hybrid':
        reranker = HybridReRanker()
        return reranker.rerank(query, documents, top_k=top_k)
    
    elif method == 'mmr':
        reranker = MMRReRanker()
        return reranker.rerank(documents, top_k=top_k)
    
    else:
        logger.warning(f"Unknown re-ranking method: {method}")
        return documents[:top_k]
