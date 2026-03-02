"""
Vector Store Management using ChromaDB
Handles document embeddings for RAG (Retrieval-Augmented Generation)
"""
import os
import logging
from typing import List, Dict, Optional
from pathlib import Path
import chromadb
from chromadb.config import Settings

logger = logging.getLogger(__name__)


class VectorStore:
    """
    Manages vector embeddings using ChromaDB for semantic search.
    
    Features:
    - Local persistent storage
    - Automatic embedding generation using sentence-transformers
    - Semantic similarity search
    - Document metadata management
    """
    
    def __init__(self, persist_directory: str = None):
        """
        Initialize ChromaDB vector store.
        
        Args:
            persist_directory: Path to store ChromaDB data. Defaults to BASE_DIR/vector_db
        """
        if persist_directory is None:
            from django.conf import settings
            persist_directory = os.path.join(settings.BASE_DIR, 'vector_db')
        
        # Ensure directory exists
        os.makedirs(persist_directory, exist_ok=True)
        
        logger.info(f"Initializing ChromaDB at: {persist_directory}")
        
        # Initialize ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Create or get collections
        self.knowledge_collection = self._get_or_create_collection("knowledge_base")
        self.rooms_collection = self._get_or_create_collection("rooms_info")
        self.policies_collection = self._get_or_create_collection("booking_policies")
        
        logger.info("✓ Vector store initialized successfully")
    
    def _get_or_create_collection(self, name: str):
        """Get or create a ChromaDB collection with default embedding function."""
        try:
            collection = self.client.get_or_create_collection(
                name=name,
                metadata={"hnsw:space": "cosine"}  # Use cosine similarity
            )
            logger.info(f"✓ Collection '{name}' ready (documents: {collection.count()})")
            return collection
        except Exception as e:
            logger.error(f"Failed to create collection '{name}': {e}")
            raise
    
    def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: List[Dict],
        ids: List[str]
    ) -> bool:
        """
        Add documents to a specific collection.
        
        Args:
            collection_name: Name of the collection ('knowledge_base', 'rooms_info', 'booking_policies')
            documents: List of text documents to embed and store
            metadatas: List of metadata dicts for each document
            ids: List of unique IDs for each document
            
        Returns:
            bool: True if successful
        """
        try:
            collection = self.client.get_collection(collection_name)
            
            # Validate inputs
            if not (len(documents) == len(metadatas) == len(ids)):
                raise ValueError("documents, metadatas, and ids must have same length")
            
            # Add to ChromaDB (automatic embedding generation)
            collection.upsert(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"✓ Added {len(documents)} documents to '{collection_name}'")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add documents to '{collection_name}': {e}")
            return False
    
    def semantic_search(
        self,
        query: str,
        collection_name: str = "knowledge_base",
        n_results: int = 5
    ) -> List[Dict]:
        """
        Perform semantic similarity search.
        
        Args:
            query: Search query text
            collection_name: Which collection to search
            n_results: Number of results to return
            
        Returns:
            List of dicts with keys: 'id', 'document', 'metadata', 'distance'
        """
        try:
            collection = self.client.get_collection(collection_name)
            
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                include=['documents', 'metadatas', 'distances']
            )
            
            # Format results
            formatted_results = []
            if results['ids'] and len(results['ids']) > 0:
                for i in range(len(results['ids'][0])):
                    formatted_results.append({
                        'id': results['ids'][0][i],
                        'document': results['documents'][0][i],
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i]
                    })
            
            logger.info(f"✓ Found {len(formatted_results)} results for query in '{collection_name}'")
            return formatted_results
            
        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return []
    
    def search_rooms(self, query: str, n_results: int = 10) -> List[Dict]:
        """Search for relevant room information."""
        return self.semantic_search(query, collection_name="rooms_info", n_results=n_results)
    
    def search_knowledge(self, query: str, n_results: int = 5) -> List[Dict]:
        """Search knowledge base (FAQs, documentation, guides)."""
        return self.semantic_search(query, collection_name="knowledge_base", n_results=n_results)
    
    def search_policies(self, query: str, n_results: int = 3) -> List[Dict]:
        """Search booking policies and rules."""
        return self.semantic_search(query, collection_name="booking_policies", n_results=n_results)
    
    def get_collection_stats(self) -> Dict[str, int]:
        """Get statistics about all collections."""
        try:
            stats = {
                'knowledge_base': self.knowledge_collection.count(),
                'rooms_info': self.rooms_collection.count(),
                'booking_policies': self.policies_collection.count()
            }
            return stats
        except Exception as e:
            logger.error(f"Failed to get collection stats: {e}")
            return {}
    
    def clear_collection(self, collection_name: str) -> bool:
        """Clear all documents from a collection."""
        try:
            self.client.delete_collection(collection_name)
            self._get_or_create_collection(collection_name)
            logger.info(f"✓ Cleared collection '{collection_name}'")
            return True
        except Exception as e:
            logger.error(f"Failed to clear collection '{collection_name}': {e}")
            return False
    
    def reset_all(self) -> bool:
        """Reset all collections (use with caution!)."""
        try:
            self.client.reset()
            # Recreate collections
            self.knowledge_collection = self._get_or_create_collection("knowledge_base")
            self.rooms_collection = self._get_or_create_collection("rooms_info")
            self.policies_collection = self._get_or_create_collection("booking_policies")
            logger.warning("⚠ All vector store data has been reset")
            return True
        except Exception as e:
            logger.error(f"Failed to reset vector store: {e}")
            return False


# Global vector store instance
_vector_store = None


def get_vector_store() -> VectorStore:
    """Get or create global vector store instance."""
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStore()
    return _vector_store
