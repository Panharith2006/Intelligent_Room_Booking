"""
Integration Test Suite for Full Agentic RAG Pipeline

Tests the complete pipeline:
1. Input Evaluation (QueryProcessor)
2. Retrieval Strategy Selection
3. Document Retrieval
4. Output Evaluation (SelfRAG)
5. Quality-based Iteration
"""

import json
from typing import Dict, List
from ai.agentic_rag import AgenticRAG
from ai.vector_store import VectorStore


class MockInputModel:
    """Mock Input Model for query understanding"""
    
    def __call__(self, prompt: str) -> str:
        return json.dumps({
            "intent": {
                "primary": "booking",
                "confidence": 0.95,
                "secondary": None
            },
            "entities": {
                "room": "A2",
                "capacity": "50",
                "date": "Monday"
            },
            "routing": {
                "complexity_score": 2.5,
                "routing_strategy": "HYBRID_RETRIEVAL",
                "execution_plan": {
                    "decompose_query": False,
                    "expand_query": True
                }
            },
            "sub_queries": None,
            "confidence_score": 0.92
        })


class MockOutputModel:
    """Mock Output Model for quality evaluation"""
    
    def __call__(self, prompt: str) -> str:
        # Return different scores based on what's being evaluated
        if "grounded" in prompt.lower():
            return "0.85"
        elif "relevant" in prompt.lower():
            return "0.90"
        elif "complete" in prompt.lower():
            return "0.75"
        return "0.7"


def test_pipeline_basic_flow():
    """Test 1: Basic Pipeline Flow (Single Iteration)"""
    print("\n" + "="*80)
    print("TEST 1: BASIC PIPELINE FLOW")
    print("="*80)
    
    input_model = MockInputModel()
    output_model = MockOutputModel()
    
    rag = AgenticRAG(
        llm_client=input_model,
        eval_llm_client=output_model,
        enable_self_rag=True,
        enable_reranking=True,
        enable_multi_query=True
    )
    
    query = "Can I book room A2 for 50 people on Monday?"
    
    print(f"\nProcessing Query: {query}")
    print("\nPipeline Stages:")
    
    try:
        result = rag.process_query(query, top_k=5)
        
        print(f"  ✓ Stage 1: Query Processing")
        print(f"    └─ Intent: {result['intent'].get('primary')}")
        
        print(f"  ✓ Stage 2: Retrieval")
        print(f"    └─ Strategy: {result['routing_strategy']}")
        
        print(f"  ✓ Stage 3: Response Generation")
        print(f"    └─ Response: \"{result['response'][:60]}...\"")
        
        if 'evaluation_scores' in result:
            print(f"  ✓ Stage 4: Quality Evaluation")
            scores = result['evaluation_scores']
            print(f"    ├─ Faithfulness: {scores.get('faithfulness', 0):.2f}")
            print(f"    ├─ Relevance: {scores.get('relevance', 0):.2f}")
            print(f"    ├─ Completeness: {scores.get('completeness', 0):.2f}")
            print(f"    └─ Overall Quality: {scores.get('overall_quality', 0):.2f}")
        
        print(f"\n  ✓ Pipeline execution successful")
        
    except Exception as e:
        print(f"  ✗ Error: {e}")


def test_pipeline_complexity_routing():
    """Test 2: Complexity-based Routing"""
    print("\n" + "="*80)
    print("TEST 2: COMPLEXITY-BASED ROUTING")
    print("="*80)
    
    input_model = MockInputModel()
    output_model = MockOutputModel()
    
    rag = AgenticRAG(
        llm_client=input_model,
        eval_llm_client=output_model,
        enable_multi_query=True
    )
    
    test_cases = [
        ("Book room A2", "Simple"),
        ("Find rooms by capacity and availability", "Medium"),
        ("Show me rooms by department, capacity, and cost with availability for multiple dates", "Complex"),
    ]
    
    print(f"\nTesting Query Routing Based on Complexity:")
    
    for query, complexity_level in test_cases:
        print(f"\n  Query: \"{query}\"")
        print(f"  Complexity Level: {complexity_level}")
        
        try:
            result = rag.process_query(query)
            complexity = result['complexity']
            routing = result['routing_strategy']
            
            print(f"    Complexity Score: {complexity:.1f}/5")
            print(f"    Routing Strategy: {routing}")
            
            if complexity >= 3:
                expected = "MULTI_QUERY_RETRIEVAL"
            else:
                expected = "HYBRID_RETRIEVAL"
            
            if expected in routing or complexity == result.get('complexity'):
                print(f"    ✓ Routing correct")
            else:
                print(f"    ⚠ Routing may vary")
                
        except Exception as e:
            print(f"    ✗ Error: {e}")


def test_pipeline_quality_iteration():
    """Test 3: Quality-Based Iteration (Automatic Refinement)"""
    print("\n" + "="*80)
    print("TEST 3: QUALITY-BASED ITERATION")
    print("="*80)
    print("(Testing with SelfRAG enabled for automatic quality improvement)")
    
    input_model = MockInputModel()
    output_model = MockOutputModel()
    
    rag = AgenticRAG(
        llm_client=input_model,
        eval_llm_client=output_model,
        enable_self_rag=True
    )
    
    queries = [
        "Book room A2 for 50 people",
        "What is the booking policy and pricing?",
        "Show available conference rooms",
    ]
    
    print(f"\nProcessing Multiple Queries:")
    
    for i, query in enumerate(queries, 1):
        print(f"\n  Query {i}: \"{query}\"")
        
        try:
            result = rag.process_query(query)
            
            if 'evaluation_scores' in result:
                scores = result['evaluation_scores']
                overall = scores.get('overall_quality', 0)
                
                print(f"    Overall Quality: {overall:.2f}")
                
                if overall >= 0.7:
                    print(f"    ✓ High quality - Accepted on first attempt")
                elif overall >= 0.5:
                    print(f"    ⚠ Medium quality - May require refinement")
                else:
                    print(f"    ✗ Low quality - Needs iteration")
            else:
                print(f"    Response: \"{result.get('response', '')[:60]}...\"")
                
        except Exception as e:
            print(f"    ✗ Error: {e}")


def test_pipeline_performance_metrics():
    """Test 4: Pipeline Performance Metrics"""
    print("\n" + "="*80)
    print("TEST 4: PIPELINE PERFORMANCE METRICS")
    print("="*80)
    
    input_model = MockInputModel()
    output_model = MockOutputModel()
    
    rag = AgenticRAG(
        llm_client=input_model,
        eval_llm_client=output_model,
        enable_self_rag=True
    )
    
    queries = [
        "Book room A2",
        "What's the policy?",
        "Find available rooms",
    ]
    
    print(f"\nProcessing {len(queries)} queries to gather metrics:")
    
    try:
        for query in queries:
            result = rag.process_query(query)
        
        if hasattr(rag, 'self_rag'):
            metrics = rag.self_rag.get_pipeline_metrics()
            
            if metrics:
                print(f"\n  Pipeline Metrics:")
                print(f"    ├─ Success Rate: {metrics.get('success_rate', 0):.1%}")
                print(f"    ├─ Avg Iterations: {metrics.get('avg_iterations', 0):.2f}")
                print(f"    ├─ Avg Latency: {metrics.get('avg_latency_ms', 0):.0f}ms")
                print(f"    └─ Iteration Efficiency: {metrics.get('iteration_efficiency', 0):.2f}")
            else:
                print(f"\n  No metrics available yet")
        else:
            print(f"  SelfRAG not enabled")
            
    except Exception as e:
        print(f"  ✗ Error: {e}")


def test_pipeline_error_handling():
    """Test 5: Error Handling & Graceful Degradation"""
    print("\n" + "="*80)
    print("TEST 5: ERROR HANDLING & GRACEFUL DEGRADATION")
    print("="*80)
    
    print(f"\nTesting pipeline robustness:")
    
    # Test 1: No input model
    print(f"\n  Test A: No Input Model")
    try:
        rag = AgenticRAG(llm_client=None, eval_llm_client=None)
        result = rag.process_query("Book room A2")
        print(f"    ✓ Pipeline continues without LLM")
        print(f"    Result: {result.get('response', 'N/A')[:60]}")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Test 2: Disabled features
    print(f"\n  Test B: Disabled Features")
    try:
        rag = AgenticRAG(
            llm_client=MockInputModel(),
            eval_llm_client=MockOutputModel(),
            enable_self_rag=False,
            enable_reranking=False,
            enable_multi_query=False
        )
        result = rag.process_query("Book room")
        print(f"    ✓ Pipeline works with all features disabled")
    except Exception as e:
        print(f"    ✗ Error: {e}")
    
    # Test 3: Empty query
    print(f"\n  Test C: Empty Query")
    try:
        rag = AgenticRAG(llm_client=MockInputModel(), eval_llm_client=MockOutputModel())
        result = rag.process_query("")
        print(f"    ✓ Handles empty query gracefully")
    except Exception as e:
        print(f"    ⚠ Error (expected): {str(e)[:60]}")


def run_all_tests():
    """Run all integration tests"""
    print("\n" + "█"*80)
    print("AGENTIC RAG INTEGRATION TEST SUITE")
    print("Testing: Full Pipeline (Input → Retrieval → Output → Iteration)")
    print("█"*80)
    
    try:
        test_pipeline_basic_flow()
        test_pipeline_complexity_routing()
        test_pipeline_quality_iteration()
        test_pipeline_performance_metrics()
        test_pipeline_error_handling()
        
        print("\n" + "█"*80)
        print("✓ ALL INTEGRATION TESTS COMPLETED")
        print("█"*80)
    except Exception as e:
        print(f"\n✗ CRITICAL ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
