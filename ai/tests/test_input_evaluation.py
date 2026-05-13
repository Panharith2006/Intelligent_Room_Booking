"""
Test suite for INPUT EVALUATION (QueryProcessor)

Tests how well the input model:
- Classifies user intent
- Extracts entities
- Estimates complexity
- Decomposes/expands queries
"""

import json
from typing import Dict, Any
from ai.query_processor import QueryProcessor


class MockInputModel:
    """Mock LLM for testing input evaluation"""
    
    def __call__(self, prompt: str) -> str:
        """Simple mock that returns structured responses"""
        
        # Mock response for query understanding
        if "Classify the intent" in prompt or "intent" in prompt.lower():
            return json.dumps({
                "intent": {
                    "primary": "booking",
                    "confidence": 0.95,
                    "secondary": None
                },
                "entities": {
                    "room": "A2",
                    "capacity": "50",
                    "date": "Monday",
                    "time": "2 PM"
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
        
        return "{}"


def test_intent_classification():
    """Test 1: Intent Classification"""
    print("\n" + "="*80)
    print("TEST 1: INTENT CLASSIFICATION")
    print("="*80)
    
    input_model = MockInputModel()
    processor = QueryProcessor(llm_client=input_model)
    
    test_queries = [
        "Can I book room A2 for 50 people on Monday?",
        "What is the booking policy?",
        "I want to cancel my booking for tomorrow",
        "Is room B5 available at 3 PM?",
    ]
    
    for query in test_queries:
        result = processor.process_query(query)
        intent = result['intent']
        
        print(f"\nQuery: {query}")
        print(f"  Primary Intent: {intent.get('primary', 'N/A')}")
        print(f"  Confidence: {intent.get('confidence', 'N/A')}")
        print(f"  ✓ Pass" if intent.get('confidence', 0) > 0.8 else "  ✗ Low confidence")


def test_entity_extraction():
    """Test 2: Entity Extraction"""
    print("\n" + "="*80)
    print("TEST 2: ENTITY EXTRACTION")
    print("="*80)
    
    input_model = MockInputModel()
    processor = QueryProcessor(llm_client=input_model)
    
    test_cases = [
        {
            "query": "Book room A2 for 50 people on Monday at 2 PM",
            "expected_entities": ["room", "capacity", "date", "time"]
        },
        {
            "query": "Is conference room B5 available?",
            "expected_entities": ["room"]
        },
    ]
    
    for test in test_cases:
        result = processor.process_query(test["query"])
        entities = result['entities']
        
        print(f"\nQuery: {test['query']}")
        print(f"  Extracted Entities: {entities}")
        
        found = [e for e in test["expected_entities"] if e in entities]
        coverage = len(found) / len(test["expected_entities"]) * 100
        print(f"  Coverage: {coverage:.0f}% ({len(found)}/{len(test['expected_entities'])})")
        print(f"  ✓ Pass" if coverage >= 50 else "  ✗ Low coverage")


def test_complexity_scoring():
    """Test 3: Complexity Scoring (1-5 scale)"""
    print("\n" + "="*80)
    print("TEST 3: COMPLEXITY SCORING")
    print("="*80)
    
    input_model = MockInputModel()
    processor = QueryProcessor(llm_client=input_model)
    
    test_cases = [
        ("Book room A2", 1, "Simple single booking"),
        ("Show me available rooms with capacity > 50 on Monday and Tuesday", 4, "Complex multi-criteria"),
        ("What's the policy?", 1, "Simple information"),
        ("Find rooms by department, check availability, and estimate costs", 5, "Very complex"),
    ]
    
    for query, expected_complexity, description in test_cases:
        result = processor.process_query(query)
        complexity = result['complexity']
        
        print(f"\nQuery: {query}")
        print(f"  Description: {description}")
        print(f"  Expected Complexity: {expected_complexity}/5")
        print(f"  Actual Complexity: {complexity:.1f}/5")
        print(f"  ✓ Pass" if abs(complexity - expected_complexity) <= 1 else "  ✗ Mismatch")


def test_query_decomposition():
    """Test 4: Query Decomposition (Complex → Sub-queries)"""
    print("\n" + "="*80)
    print("TEST 4: QUERY DECOMPOSITION")
    print("="*80)
    
    input_model = MockInputModel()
    processor = QueryProcessor(llm_client=input_model)
    
    test_queries = [
        "Find rooms with capacity > 100 in building A and B that are available on Monday and Tuesday",
        "What rooms can accommodate 50 people for a 3-hour meeting?",
    ]
    
    for query in test_queries:
        result = processor.process_query(query)
        sub_queries = result['sub_queries']
        
        print(f"\nQuery: {query}")
        print(f"  Decomposed into {len(sub_queries) if sub_queries else 0} sub-queries")
        if sub_queries:
            for i, sq in enumerate(sub_queries, 1):
                print(f"    {i}. {sq}")
        else:
            print(f"  (No decomposition needed)")


def test_routing_strategy():
    """Test 5: Routing Strategy Selection"""
    print("\n" + "="*80)
    print("TEST 5: ROUTING STRATEGY SELECTION")
    print("="*80)
    
    input_model = MockInputModel()
    processor = QueryProcessor(llm_client=input_model)
    
    test_cases = [
        ("Simple query", 1.5),
        ("Medium complexity", 3.0),
        ("Very complex multi-step query", 4.5),
    ]
    
    for description, complexity in test_cases:
        print(f"\nComplexity Score: {complexity}/5 ({description})")
        
        if complexity >= 3:
            print(f"  Strategy: MULTI_QUERY_RETRIEVAL (Generate 3 query variations)")
            print(f"  Top-K: 10 (K×2 candidates)")
        else:
            print(f"  Strategy: HYBRID_RETRIEVAL (Vector + Keyword)")
            print(f"  Top-K: 5")


def run_all_tests():
    """Run all input evaluation tests"""
    print("\n" + "█"*80)
    print("INPUT EVALUATION TEST SUITE")
    print("Testing: QueryProcessor (Input Model)")
    print("█"*80)
    
    try:
        test_intent_classification()
        test_entity_extraction()
        test_complexity_scoring()
        test_query_decomposition()
        test_routing_strategy()
        
        print("\n" + "█"*80)
        print("✓ ALL TESTS COMPLETED")
        print("█"*80)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    run_all_tests()
