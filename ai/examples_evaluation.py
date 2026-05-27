import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def example_1_runtime_chatbot():
   
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 1: RUNTIME CHATBOT")
    logger.info("="*80)
    logger.info("Pipeline: Query → Retrieval → Generation → Response")
    logger.info("NO evaluation during runtime ✅")
    
    from ai.agentic_rag import AgenticRAG
    from ai.vector_store import get_vector_store
    
    # Initialize RAG (no evaluation models needed)
    rag = AgenticRAG(
        vector_store=get_vector_store(),
        llm_client=None,  # Only needed for query understanding
        enable_reranking=True,
        enable_multi_query=True,
        # NO eval_llm_client - not needed for runtime!
    )
    
    logger.info("✅ RAG initialized (lean, fast, no evaluation)")
    
    # User asks a question
    query = "Find me a meeting room tomorrow at 2pm for 10 people"
    logger.info(f"\nUser: {query}")
    
    # Process query - FAST, no evaluation
    result = rag.process_query(query=query, top_k=5)
    
    logger.info(f"\nChatbot Response:")
    logger.info(f"  {result['response_text'][:100]}...")
    logger.info(f"  Processing time: {result['processing_time']:.2f}s")
    logger.info(f"  Retrieved docs: {len(result['retrieved_docs'])}")
    logger.info(f"  NO evaluation metrics added (not needed for chat)")


def example_2_offline_evaluation():
    """
    EXAMPLE 2: Offline evaluation on test dataset
    
    This is a SEPARATE process from runtime chatbot.
    Run this to benchmark and assess quality.
    """
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 2: OFFLINE EVALUATION")
    logger.info("="*80)
    logger.info("Pipeline: Test Cases → Generate → Evaluate → Report")
    logger.info("Uses evaluation models (LLM) ✅")
    
    from ai.agentic_rag import AgenticRAG
    from ai.offline_evaluator import OfflineEvaluator
    from ai.vector_store import get_vector_store
    from ai.kernel_config import create_kernel_huggingface
    
    # Step 1: Initialize RAG (same as runtime, but we'll also have eval LLM)
    rag = AgenticRAG(
        vector_store=get_vector_store(),
        llm_client=None,
        enable_reranking=True,
    )
    
    # Step 2: Initialize evaluator with HuggingFace
    hf_api_key = os.getenv("HUGGINGFACE_API_KEY")
    if not hf_api_key:
        logger.warning("⚠️  HUGGINGFACE_API_KEY not set, skipping evaluation example")
        return
    
    try:
        kernel, llm_service = create_kernel_huggingface(api_key=hf_api_key)
        evaluator = OfflineEvaluator(
            retriever=rag.retriever,
            eval_llm_client=llm_service,
        )
    except Exception as e:
        logger.warning(f"Could not initialize HuggingFace: {e}")
        return
    
    # Step 3: Define test dataset
    test_cases = [
        {
            "query": "Find a meeting room tomorrow at 2pm for 10 people",
            "expected_docs": ["room_101", "booking_policy"],
            "context": {"date": "2025-01-01", "time": "14:00", "capacity": 10},
        },
        {
            "query": "What are the booking policies?",
            "expected_docs": ["policy_general", "policy_rules"],
            "context": {},
        },
        {
            "query": "How do I cancel a booking?",
            "expected_docs": ["faq_cancellation", "policy_cancellation"],
            "context": {},
        },
    ]
    
    logger.info(f"\n✅ Defined {len(test_cases)} test cases")
    
    # Step 4: Run offline evaluation
    logger.info("\n🧪 Running offline evaluation...")
    results = evaluator.evaluate_outputs(
        test_cases=test_cases,
        rag_system=rag,
        output_file="evaluation_results.json",
    )
    
    logger.info("\n📊 Evaluation Results:")
    logger.info(f"   Faithfulness: {results.get('avg_faithfulness', 0):.3f}")
    logger.info(f"   Relevance: {results.get('avg_relevance', 0):.3f}")
    logger.info(f"   Completeness: {results.get('avg_completeness', 0):.3f}")
    logger.info(f"   Retrieval F1: {results.get('avg_retrieval_f1', 0):.3f}")
    logger.info(f"   Overall Quality: {results.get('avg_overall_quality', 0):.3f}")


def example_3_workflow():
    """
    EXAMPLE 3: Complete development workflow
    
    Shows when to use runtime vs offline evaluation.
    """
    logger.info("\n" + "="*80)
    logger.info("EXAMPLE 3: RECOMMENDED WORKFLOW")
    logger.info("="*80)
    
    workflow = """
    DAY 1 - DEVELOPMENT:
    ─────────────────
    1. Create test dataset with expected outputs
    2. Run offline evaluation to assess quality
    3. Analyze results:
       - Faithfulness low? → Improve retrieval
       - Relevance low? → Better query understanding  
       - Completeness low? → Enhance generation
    4. Iterate and re-test
    
    DAY 2 - DEPLOYMENT:
    ──────────────────
    1. Deploy with RUNTIME mode (default)
    2. RAG processes user queries FAST (no evaluation)
    3. No evaluation overhead on production
    4. System always responsive
    
    DAY 7 - MONITORING:
    ──────────────────
    1. Collect production queries
    2. Create new test cases
    3. Run offline evaluation
    4. Check if quality has degraded
    5. If scores drop, investigate components
    
    RESULT:
    ✅ Fast production system (no eval overhead)
    ✅ Accurate quality assessment (offline eval)
    ✅ Data-driven improvements (test results)
    """
    
    logger.info(workflow)


def print_architecture():
    """Print the architecture overview."""
    diagram = """
    
╔════════════════════════════════════════════════════════════════════════════╗
║                 RUNTIME vs OFFLINE ARCHITECTURE                           ║
╚════════════════════════════════════════════════════════════════════════════╝

┌─ RUNTIME MODE (Production Chat) ──────────────────────────────────────────┐
│                                                                            │
│   User Request                                                             │
│        ↓                                                                   │
│   Query Processing (extract intent, entities)                              │
│        ↓                                                                   │
│   Retrieval (hybrid search, multi-query, reranking)                        │
│        ↓                                                                   │
│   Response Generation (LLM + context)                                      │
│        ↓                                                                   │
│   Return Response to User                                                  │
│        ↓                                                                   │
│   ❌ NO EVALUATION (not done here)                                         │
│                                                                            │
│   Performance: FAST (< 1s)                                                │
│   Dependencies: Query processing LLM only                                  │
│   Reliability: High (no extra API calls)                                   │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘

┌─ OFFLINE MODE (Testing/Benchmarking) ─────────────────────────────────────┐
│                                                                            │
│   Test Cases (expected outputs)                                            │
│        ↓                                                                   │
│   Generate Outputs (use runtime RAG)                                       │
│        ↓                                                                   │
│   Retrieve Metrics (deterministic)                                         │
│        ├─ Recall/Precision/F1 (document matching)                          │
│        └─ No LLM needed                                                   │
│        ↓                                                                   │
│   Generate Metrics (LLM-based evaluation)                                  │
│        ├─ Faithfulness (grounded in docs?)                                │
│        ├─ Relevance (addresses query?)                                     │
│        ├─ Completeness (covers requirements?)                              │
│        └─ LLM needed here                                                 │
│        ↓                                                                   │
│   Generate Report (with scores and analysis)                               │
│        ↓                                                                   │
│   ✅ EVALUATION COMPLETE                                                   │
│                                                                            │
│   Performance: SLOWER (evaluation is thorough)                             │
│   Dependencies: Evaluation LLM                                             │
│   Use Case: Quality assurance, benchmarking                                │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘

KEY INSIGHT:
━━━━━━━━━━━
Evaluation happens AFTER output generation, not during inference.
This is the RESEARCH best practice (Self-RAG paper).

Production Chat:     Responsive ⚡ and Reliable ✅
Testing/QA:         Accurate 🎯 and Comprehensive 📊
    """
    logger.info(diagram)


if __name__ == "__main__":
    print_architecture()
    
    logger.info("\n🚀 Running examples...\n")
    
    try:
        example_1_runtime_chatbot()
    except Exception as e:
        logger.error(f"Example 1 error: {e}", exc_info=True)
    
    try:
        example_2_offline_evaluation()
    except Exception as e:
        logger.error(f"Example 2 error: {e}", exc_info=True)
    
    try:
        example_3_workflow()
    except Exception as e:
        logger.error(f"Example 3 error: {e}", exc_info=True)
    
    logger.info("\n✅ Examples complete!")
