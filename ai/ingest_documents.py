"""ai/ingest_documents.py
"""
import os
import logging
from pathlib import Path
from typing import Optional, Dict

logger = logging.getLogger(__name__)

def ingest_document(
    file_path: str,
    collection_name: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    extra_metadata: Optional[Dict] = None,
    user_id: Optional[int] = None
) -> bool:
    """
    Generic document ingestion function.
    
    Args:
        file_path: Path to document (relative to project root or absolute)
        collection_name: Target collection ("knowledge_base", "rooms_info", "booking_policies")
        chunk_size: Characters per chunk (default: 800)
        chunk_overlap: Overlap between chunks (default: 150)
        extra_metadata: Additional metadata to attach to all chunks
        user_id: User ID for document isolation (optional)
    
    Returns:
        bool: True if successful, False otherwise
    
    Example:
        ingest_document("FAQ.md", "knowledge_base", extra_metadata={"document_type": "faq"})
    """
    
    from ai.document_ingestion_langchain import LangChainDocumentLoader
    from ai.vector_store import get_vector_store
    
    # Resolve file path
    if not os.path.isabs(file_path):
        file_path = os.path.join(Path(__file__).parent.parent, file_path)
    
    if not os.path.exists(file_path):
        logger.error(f"File not found: {file_path}")
        return False
    
    logger.info(f"Starting ingestion | File: {file_path} | Collection: {collection_name}")
    
    try:
        # Step 1: Load and chunk the document
        loader = LangChainDocumentLoader(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            splitter_type="recursive"
        )
        
        chunks = loader.load_and_chunk_file(
            file_path,
            user_id=user_id,
            extra_metadata=extra_metadata
        )
        
        if not chunks:
            logger.error(f"No chunks generated from {file_path}")
            return False
        
        logger.info(f"Successfully chunked document into {len(chunks)} chunks")
        
        # Step 2: Store in vector database
        vector_store = get_vector_store()
        
        documents = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        ids = [chunk["id"] for chunk in chunks]
        
        success = vector_store.add_documents(
            collection_name=collection_name,
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        if success:
            logger.info(f" Successfully ingested {len(chunks)} chunks into '{collection_name}'")
            
            # Print stats
            stats = vector_store.get_collection_stats()
            logger.info(f"Vector store stats: {stats}")
            
            return True
        else:
            logger.error("Failed to add documents to vector store")
            return False
    
    except Exception as e:
        logger.error(f"Document ingestion failed: {e}", exc_info=True)
        return False


def clear_collection(collection_name: str) -> bool:
    try:
        from ai.vector_store import get_vector_store
        vector_store = get_vector_store()
        vector_store.clear_collection(collection_name)
        logger.info(f" Cleared collection '{collection_name}'")
        return True
    except Exception as e:
        logger.error(f"Failed to clear collection: {e}")
        return False


