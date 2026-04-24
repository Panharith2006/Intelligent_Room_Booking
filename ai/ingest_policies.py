"""
ai/ingest_policies.py

One-time or scheduled task to ingest policy documents into the RAG system.
Loads policy.md into the booking_policies collection in ChromaDB.
"""

import os
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def ingest_policy_document():
    """
    Load policy.md into the RAG vector store.
    Should be called once during setup or via management command.
    """
    
    from ai.document_ingestion_langchain import LangChainDocumentLoader
    from ai.vector_store import get_vector_store
    
    # Path to your policy file
    policy_path = os.path.join(Path(__file__).parent.parent, "policy.md")
    
    if not os.path.exists(policy_path):
        logger.error(f"Policy file not found at {policy_path}")
        return False
    
    logger.info(f"Loading policy from: {policy_path}")
    
    try:
        # Step 1: Load and chunk the document
        loader = LangChainDocumentLoader(
            chunk_size=800,        # Smaller chunks for policy clarity
            chunk_overlap=150,
            splitter_type="recursive"
        )
        
        chunks = loader.load_and_chunk_file(
            policy_path,
            user_id=None,  # System document (not user-specific)
            extra_metadata={
                "document_type": "booking_policy",
                "category": "university_rules",
                "document_name": "University Room Booking Policies"
            }
        )
        
        logger.info(f"Successfully chunked policy into {len(chunks)} chunks")
        
        # Step 2: Store in vector database
        vector_store = get_vector_store()
        
        documents = [chunk["text"] for chunk in chunks]
        metadatas = [chunk["metadata"] for chunk in chunks]
        ids = [chunk["id"] for chunk in chunks]
        
        success = vector_store.add_documents(
            collection_name="booking_policies",
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        if success:
            logger.info(f"✓ Successfully ingested {len(chunks)} policy chunks into booking_policies collection")
            
            # Print stats
            stats = vector_store.get_collection_stats()
            logger.info(f"Vector store stats: {stats}")
            
            return True
        else:
            logger.error("Failed to add documents to vector store")
            return False
    
    except Exception as e:
        logger.error(f"Policy ingestion failed: {e}", exc_info=True)
        return False


def verify_policy_ingestion():
    """
    Verify that policies were ingested correctly.
    Searches for sample policy queries.
    """
    
    from ai.vector_store import get_vector_store
    
    vector_store = get_vector_store()
    
    test_queries = [
        "What is the maximum booking duration?",
        "Can I cancel a booking less than 3 hours before?",
        "How many active bookings can a user have?",
        "What is the late cancellation policy?",
    ]
    
    logger.info("=== Verifying Policy Ingestion ===")
    
    for query in test_queries:
        logger.info(f"\nQuery: '{query}'")
        results = vector_store.search_policies(query, n_results=2)
        
        if results and results.get("documents") and len(results["documents"]) > 0:
            for i, doc in enumerate(results["documents"][0]):
                logger.info(f"  Result {i+1}: {doc[:100]}...")
        else:
            logger.warning(f"  No results found")
    
    logger.info("=== Verification Complete ===")


if __name__ == "__main__":
    # For standalone testing (outside Django)
    import django
    from django.conf import settings
    
    if not settings.configured:
        print("Please run this through Django management command or Django shell")
    else:
        success = ingest_policy_document()
        if success:
            verify_policy_ingestion()
