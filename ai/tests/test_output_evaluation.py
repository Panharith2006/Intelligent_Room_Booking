"""
Test suite for OUTPUT EVALUATION (SelfRAG)

Tests how well the output model evaluates:
- Faithfulness: Is response grounded in documents?
- Relevance: Does response address query?
- Completeness: Does response cover all required info?
"""

import json
from typing import Dict, List, Any
from ai.self_rag import SelfRAG


class MockRetriever:
    """Mock retriever for testing"""
    
    def retrieve(self, query: str, **kwargs) -> List[Dict]:
        """Return mock documents"""
        return [
            {
                "document": "Maximum booking duration is 8 hours. Approval required for all bookings.",
                "text": "booking policy",
                "score": 0.9
            },
            {
                "document": "Conference rooms can accommodate up to 100 people.",
                "text": "room capacity",
                "score": 0.85
            },
            {
                "document": "Room booking must be done 24 hours in advance.",
                "text": "advance booking",
                "score": 0.7
            }
        ]


class MockOutputModel:
    """Mock LLM for output evaluation"""
    
    def __call__(self, prompt: str) -> str:
        """Return mock evaluation scores"""
        
        # Determine which evaluation is being requested
        if "grounded" in prompt.lower() or "faithfulness" in prompt.lower():
            return "0.85"  # 85% faithful
        elif "relevant" in prompt.lower() or "relevance" in prompt.lower():
            return "0.90"  # 90% relevant
        elif "completely" in prompt.lower() or "complete" in prompt.lower():
            return "0.75"  # 75% complete
        
        return "0.5"


def test_faithfulness_evaluation():
    """Test 1: Faithfulness Evaluation (Grounding in Documents)"""
    print("\n" + "="*80)
    print("TEST 1: FAITHFULNESS EVALUATION")
    print("="*80)
    print("Question: Is the response grounded in retrieved documents?")
    
    retriever = MockRetriever()
    eval_model = MockOutputModel()
    self_rag = SelfRAG(retriever, llm_client=eval_model)
    
    test_cases = [
        {
            "response": "Maximum booking duration is 8 hours and approval is required.",
            "docs": retriever.retrieve("booking policy"),
            "expected": "high",  # Should be high - directly from documents
            "description": "Direct claim from documents"
        },
        {
            "response": "You can book for 8 hours. Rooms have excellent views.",
            "docs": retriever.retrieve("booking"),
            "expected": "medium",  # Partial - some claims not in docs
            "description": "Mix of documented and inferred claims"
        },
        {
            "response": "Booking costs $50 per hour and includes catering.",
            "docs": retriever.retrieve("booking"),
            "expected": "low",  # Low - not mentioned in documents
            "description": "Claims not in retrieved documents"
        },
    ]
    
    for test in test_cases:
        score = self_rag._compute_faithfulness(test["response"], test["docs"])
        
        print(f"\n  {test['description']}")
        print(f"    Response: \"{test['response'][:60]}...\"")
        print(f"    Faithfulness Score: {score:.2f}")
        print(f"    Expected: {test['expected'].upper()}")
        
        if test["expected"] == "high" and score > 0.75:
            print(f"    ✓ Pass")
        elif test["expected"] == "medium" and 0.4 < score < 0.75:
            print(f"    ✓ Pass")
        elif test["expected"] == "low" and score < 0.4:
            print(f"    ✓ Pass")
        else:
            print(f"    ✗ Mismatch")


def test_relevance_evaluation():
    """Test 2: Relevance Evaluation (Query-Response Alignment)"""
    print("\n" + "="*80)
    print("TEST 2: RELEVANCE EVALUATION")
    print("="*80)
    print("Question: Does the response address the user's query?")
    
    eval_model = MockOutputModel()
    retriever = MockRetriever()
    self_rag = SelfRAG(retriever, llm_client=eval_model)
    
    test_cases = [
        {
            "query": "Can I book room A2 for 50 people on Monday at 2 PM?",
            "response": "Yes, room A2 can accommodate 50 people. Monday 2 PM is available.",
            "expected": "high",
            "description": "Direct answer to query"
        },
        {
            "query": "What's the booking policy?",
            "response": "Maximum 8 hours booking duration. You also need approval. Also, rooms have nice desks.",
            "expected": "medium",
            "description": "Answers query but includes off-topic info"
        },
        {
            "query": "What's the booking policy?",
            "response": "Room A5 has a nice view and costs $100 per hour.",
            "expected": "low",
            "description": "Doesn't address the query"
        },
    ]
    
    for test in test_cases:
        score = self_rag._compute_relevance(test["query"], test["response"])
        
        print(f"\n  {test['description']}")
        print(f"    Query: \"{test['query'][:50]}...\"")
        print(f"    Response: \"{test['response'][:50]}...\"")
        print(f"    Relevance Score: {score:.2f}")
        print(f"    Expected: {test['expected'].upper()}")
        
        if test["expected"] == "high" and score > 0.75:
            print(f"    ✓ Pass")
        elif test["expected"] == "medium" and 0.4 < score < 0.75:
            print(f"    ✓ Pass")
        elif test["expected"] == "low" and score < 0.4:
            print(f"    ✓ Pass")
        else:
            print(f"    ✗ Mismatch")


def test_completeness_evaluation():
    """Test 3: Completeness Evaluation (Coverage of Required Info)"""
    print("\n" + "="*80)
    print("TEST 3: COMPLETENESS EVALUATION")
    print("="*80)
    print("Question: Does the response cover all required information?")
    
    eval_model = MockOutputModel()
    retriever = MockRetriever()
    self_rag = SelfRAG(retriever, llm_client=eval_model)
    
    test_cases = [
        {
            "response": "Room A2 available on Monday at 2 PM. Capacity: 50 people. Duration: 8 hours.",
            "entities": {
                "room": "A2",
                "date": "Monday",
                "time": "2 PM",
                "capacity": "50",
                "duration": "8 hours"
            },
            "expected": "high",
            "description": "All required info present"
        },
        {
            "response": "Room A2 is available. Capacity is 50 people.",
            "entities": {
                "room": "A2",
                "date": "Monday",
                "time": "2 PM",
                "capacity": "50",
            },
            "expected": "medium",
            "description": "Missing date and time info"
        },
        {
            "response": "The room is nice.",
            "entities": {
                "room": "A2",
                "date": "Monday",
                "time": "2 PM",
                "capacity": "50",
            },
            "expected": "low",
            "description": "Missing most required info"
        },
    ]
    
    for test in test_cases:
        score = self_rag._compute_completeness(test["response"], test["entities"])
        
        print(f"\n  {test['description']}")
        print(f"    Response: \"{test['response'][:50]}...\"")
        print(f"    Required Info: {list(test['entities'].keys())}")
        print(f"    Completeness Score: {score:.2f}")
        print(f"    Expected: {test['expected'].upper()}")
        
        if test["expected"] == "high" and score > 0.75:
            print(f"    ✓ Pass")
        elif test["expected"] == "medium" and 0.4 < score < 0.75:
            print(f"    ✓ Pass")
        elif test["expected"] == "low" and score < 0.4:
            print(f"    ✓ Pass")
        else:
            print(f"    ✗ Mismatch")


def test_reflection_pipeline():
    """Test 4: Full Reflection Pipeline (Automatic Quality Improvement)"""
    print("\n" + "="*80)
    print("TEST 4: REFLECTION PIPELINE")
    print("="*80)
    print("Question: Does pipeline iterate to improve response quality?")
    
    retriever = MockRetriever()
    eval_model = MockOutputModel()
    self_rag = SelfRAG(
        retriever,
        llm_client=eval_model,
        thresholds={
            "faithfulness": 0.6,
            "relevance": 0.5,
            "completeness": 0.6,
            "context_recall": 0.5,
            "context_precision": 0.6,
            "routing_accuracy": 0.7,
        }
    )
    
    query = "Can I book room A2 for 50 people on Monday?"
    entities = {"room": "A2", "capacity": "50", "date": "Monday"}
    
    result = self_rag.generate_with_reflection(
        query=query,
        entities=entities,
        intent="booking",
        max_iterations=3
    )
    
    print(f"\nQuery: {query}")
    print(f"\nPipeline Execution:")
    print(f"  ├─ Iterations: {result['iterations']}")
    print(f"  ├─ Success: {'✓ Yes' if result['success'] else '✗ No'}")
    print(f"  └─ Response: \"{result['response'][:60]}...\"")
    
    scores = result['evaluation_scores']
    print(f"\nEvaluation Scores:")
    print(f"  Retrieval Quality: {scores['retrieval_quality']:.2f}")
    print(f"    ├─ Context Recall: {scores['context_recall']:.2f}")
    print(f"    └─ Context Precision: {scores['context_precision']:.2f}")
    print(f"  Generation Quality: {scores['generation_quality']:.2f}")
    print(f"    ├─ Faithfulness: {scores['faithfulness']:.2f}")
    print(f"    ├─ Relevance: {scores['relevance']:.2f}")
    print(f"    └─ Completeness: {scores['completeness']:.2f}")
    print(f"  Overall Quality: {scores['overall_quality']:.2f}")
    
    if result['success']:
        print(f"\n  ✓ All thresholds met - Response accepted")
    else:
        print(f"\n  ⚠ Some thresholds below target - Would refine and retry")


def test_threshold_sensitivity():
    """Test 5: Threshold Sensitivity (How thresholds affect pipeline)"""
    print("\n" + "="*80)
    print("TEST 5: THRESHOLD SENSITIVITY")
    print("="*80)
    print("Question: How do evaluation thresholds affect pipeline behavior?")
    
    retriever = MockRetriever()
    eval_model = MockOutputModel()
    
    threshold_configs = [
        {
            "name": "STRICT",
            "thresholds": {
                "faithfulness": 0.9,
                "relevance": 0.9,
                "completeness": 0.9,
                "context_recall": 0.8,
                "context_precision": 0.8,
                "routing_accuracy": 0.9,
            }
        },
        {
            "name": "BALANCED",
            "thresholds": {
                "faithfulness": 0.6,
                "relevance": 0.5,
                "completeness": 0.6,
                "context_recall": 0.5,
                "context_precision": 0.6,
                "routing_accuracy": 0.7,
            }
        },
        {
            "name": "LENIENT",
            "thresholds": {
                "faithfulness": 0.4,
                "relevance": 0.3,
                "completeness": 0.4,
                "context_recall": 0.3,
                "context_precision": 0.4,
                "routing_accuracy": 0.5,
            }
        },
    ]
    
    for config in threshold_configs:
        self_rag = SelfRAG(retriever, llm_client=eval_model, thresholds=config["thresholds"])
        
        result = self_rag.generate_with_reflection(
            query="Book room A2 for 50 people",
            entities={"room": "A2", "capacity": "50"},
            max_iterations=3
        )
        
        print(f"\n  {config['name']} Configuration:")
        print(f"    ├─ Success: {'✓ Yes' if result['success'] else '✗ No'}")
        print(f"    ├─ Iterations: {result['iterations']}")
        print(f"    └─ Overall Quality: {result['evaluation_scores']['overall_quality']:.2f}")


def run_all_tests():
    """Run all output evaluation tests"""
    print("\n" + "█"*80)
    print("OUTPUT EVALUATION TEST SUITE")
    print("Testing: SelfRAG (Output Model)")
    print("█"*80)
    
    try:
        test_faithfulness_evaluation()
        test_relevance_evaluation()
        test_completeness_evaluation()
        test_reflection_pipeline()
        test_threshold_sensitivity()
        
        print("\n" + "█"*80)
        print("✓ ALL TESTS COMPLETED")
        print("█"*80)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
