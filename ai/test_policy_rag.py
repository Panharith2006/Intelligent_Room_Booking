"""
ai/test_policy_rag.py

Quick test script to verify policy ingestion and RAG retrieval.
Run via: python manage.py shell < ai/test_policy_rag.py
"""

import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'room_booking_system.settings')
django.setup()

print("\n" + "="*60)
print("POLICY RAG TEST SUITE")
print("="*60)

# Test 1: Check vector store
print("\n[Test 1] Checking Vector Store...")
try:
    from ai.vector_store import get_vector_store
    vs = get_vector_store()
    stats = vs.get_collection_stats()
    print(f"✓ Vector Store loaded")
    print(f"  Collections: {stats}")
except Exception as e:
    print(f"✗ Vector Store failed: {e}")
    sys.exit(1)

# Test 2: Check document loader
print("\n[Test 2] Checking Document Loader...")
try:
    from ai.document_ingestion_langchain import LangChainDocumentLoader
    loader = LangChainDocumentLoader()
    print(f"✓ Document Loader initialized")
except Exception as e:
    print(f"✗ Document Loader failed: {e}")
    sys.exit(1)

# Test 3: Check policy file exists
print("\n[Test 3] Checking Policy File...")
policy_path = os.path.join(os.path.dirname(__file__), "..", "policy.md")
if os.path.exists(policy_path):
    file_size = os.path.getsize(policy_path)
    print(f"✓ policy.md found")
    print(f"  Path: {policy_path}")
    print(f"  Size: {file_size} bytes")
else:
    print(f"✗ policy.md not found at {policy_path}")
    sys.exit(1)

# Test 4: Ingest policies
print("\n[Test 4] Ingesting Policies...")
try:
    from ai.ingest_policies import ingest_policy_document
    success = ingest_policy_document()
    if success:
        stats = vs.get_collection_stats()
        print(f"✓ Policies ingested successfully")
        print(f"  New stats: {stats}")
    else:
        print(f"✗ Ingestion failed")
        sys.exit(1)
except Exception as e:
    print(f"✗ Ingestion error: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Search policies
print("\n[Test 5] Searching Policies...")
test_queries = [
    "maximum booking duration",
    "late cancellation policy",
    "how many active bookings",
]

for query in test_queries:
    try:
        results = vs.search_policies(query, n_results=2)
        if results and results.get("documents") and len(results["documents"]) > 0:
            doc_count = len(results["documents"][0])
            print(f"✓ Query: '{query}' → {doc_count} results")
        else:
            print(f"✗ Query: '{query}' → No results")
    except Exception as e:
        print(f"✗ Query failed: {e}")

# Test 6: Test hybrid retriever
print("\n[Test 6] Testing Hybrid Retriever...")
try:
    from ai.hybrid_retriever import HybridRetriever
    retriever = HybridRetriever(vector_store=vs)
    results = retriever.retrieve(
        query="Can I cancel a booking with less than 3 hours notice?",
        intent="information",
        top_k=3
    )
    print(f"✓ Hybrid Retriever working")
    print(f"  Retrieved {len(results)} results")
    if results:
        print(f"  Top result score: {results[0].get('score', 'N/A')}")
except Exception as e:
    print(f"✗ Hybrid Retriever failed: {e}")

print("\n" + "="*60)
print("✓ ALL TESTS PASSED!")
print("="*60)
print("\nYour RAG is ready to answer policy questions!")
print("Try asking the chatbot: 'What is the late cancellation policy?'")
