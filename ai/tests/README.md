# Agentic RAG Test Suite

Comprehensive testing framework for the Agentic RAG system covering input evaluation, output evaluation, and full pipeline integration.

## Test Files

### 1. `test_input_evaluation.py` — INPUT MODEL TESTING

Tests the **QueryProcessor** component (Input Evaluation Model)

**What it tests:**
- Intent Classification: Correctly identifying user intent (booking, information, modification, etc.)
- Entity Extraction: Extracting structured data (room, capacity, date, time)
- Complexity Scoring: Estimating query complexity (1-5 scale)
- Query Decomposition: Breaking complex queries into sub-queries
- Routing Strategy: Selecting appropriate retrieval strategy based on complexity

**Run it:**
```bash
python -m ai.tests.test_input_evaluation
```

**Expected Output:**
```
TEST 1: INTENT CLASSIFICATION
  Query: "Can I book room A2 for 50 people on Monday?"
  Primary Intent: booking
  Confidence: 0.95
  ✓ Pass

TEST 2: ENTITY EXTRACTION
  Query: "Book room A2 for 50 people on Monday at 2 PM"
  Extracted Entities: {'room': 'A2', 'capacity': '50', 'date': 'Monday', 'time': '2 PM'}
  Coverage: 100% (4/4)
  ✓ Pass
```

---

### 2. `test_output_evaluation.py` — OUTPUT MODEL TESTING

Tests the **SelfRAG** component (Output Evaluation Model)

**What it tests:**
- **Faithfulness**: Is the response grounded in retrieved documents? (Hallucination detection)
- **Relevance**: Does the response address the user's query?
- **Completeness**: Does the response cover all required information?
- **Full Reflection Pipeline**: Automatic quality improvement through iteration
- **Threshold Sensitivity**: How evaluation thresholds affect behavior

**Run it:**
```bash
python -m ai.tests.test_output_evaluation
```

**Expected Output:**
```
TEST 1: FAITHFULNESS EVALUATION
  Direct claim from documents
    Response: "Maximum booking duration is 8 hours and approval is required."
    Faithfulness Score: 0.85
    Expected: HIGH
    ✓ Pass

TEST 2: RELEVANCE EVALUATION
  Direct answer to query
    Query: "Can I book room A2 for 50 people on Monday at 2 PM?"
    Response: "Yes, room A2 can accommodate 50 people. Monday 2 PM is available."
    Relevance Score: 0.90
    Expected: HIGH
    ✓ Pass

TEST 3: COMPLETENESS EVALUATION
  All required info present
    Response: "Room A2 available on Monday at 2 PM. Capacity: 50 people. Duration: 8 hours."
    Required Info: ['room', 'date', 'time', 'capacity', 'duration']
    Completeness Score: 0.75
    Expected: HIGH
    ✓ Pass
```

---

### 3. `test_rag_integration.py` — FULL PIPELINE TESTING

Tests the complete **AgenticRAG** pipeline integration

**What it tests:**
- **Basic Flow**: Single iteration through full pipeline
- **Complexity Routing**: Query routing based on complexity score
- **Quality Iteration**: Automatic refinement when quality is below threshold
- **Performance Metrics**: Success rate, latency, iterations
- **Error Handling**: Graceful degradation with missing components

**Run it:**
```bash
python -m ai.tests.test_rag_integration
```

**Expected Output:**
```
TEST 1: BASIC PIPELINE FLOW
Processing Query: "Can I book room A2 for 50 people on Monday?"

Pipeline Stages:
  ✓ Stage 1: Query Processing
    └─ Intent: booking
  ✓ Stage 2: Retrieval
    └─ Strategy: HYBRID_RETRIEVAL
  ✓ Stage 3: Response Generation
    └─ Response: "Yes, room A2 can accommodate 50 people..."
  ✓ Stage 4: Quality Evaluation
    ├─ Faithfulness: 0.85
    ├─ Relevance: 0.90
    ├─ Completeness: 0.75
    └─ Overall Quality: 0.83

  ✓ Pipeline execution successful
```

---

## Test Architecture

```
Input Model (QueryProcessor)
├─ Test: test_input_evaluation.py
├─ Tests: Intent, entities, complexity, decomposition
└─ Purpose: Verify query understanding quality

        ↓ (Query → Normalized Understanding)

Retrieval (Hybrid Retriever + Multi-Query)
├─ Test: Tested via integration tests
├─ Routing: Based on complexity scores
└─ Purpose: Retrieve relevant documents

        ↓ (Documents + Query → Generation)

Output Model (SelfRAG)
├─ Test: test_output_evaluation.py
├─ Tests: Faithfulness, relevance, completeness
├─ Purpose: Evaluate response quality
└─ Iteration: Refine if below thresholds

        ↓ (Response with Scores)

Full Pipeline Integration
├─ Test: test_rag_integration.py
├─ Tests: End-to-end flow, metrics, error handling
└─ Purpose: Verify complete system behavior
```

---

## Quick Start Guide

### Option 1: Run Individual Tests
```bash
# Test input evaluation
python -m ai.tests.test_input_evaluation

# Test output evaluation
python -m ai.tests.test_output_evaluation

# Test full integration
python -m ai.tests.test_rag_integration
```

### Option 2: Run All Tests with Pytest
```bash
# Install pytest if not already installed
pip install pytest

# Run all tests with verbose output
pytest ai/tests/ -v

# Run specific test file
pytest ai/tests/test_input_evaluation.py -v

# Run specific test function
pytest ai/tests/test_output_evaluation.py::test_faithfulness_evaluation -v
```

### Option 3: Create Custom Test Script
```python
from ai.tests.test_input_evaluation import run_all_tests as test_input
from ai.tests.test_output_evaluation import run_all_tests as test_output
from ai.tests.test_rag_integration import run_all_tests as test_integration

# Run all tests
test_input()
test_output()
test_integration()
```

---

## Understanding Test Results

### ✓ Pass
- Test condition met successfully
- Component behavior matches expectations
- Score within acceptable range

### ⚠ Warning
- Test completed but with caveats
- Component behavior acceptable but not optimal
- Score within acceptable but suboptimal range

### ✗ Fail
- Test condition not met
- Component behavior does not match expectations
- Score outside acceptable range

---

## Key Metrics Explained

### Input Evaluation Scores

- **Intent Confidence** (0.0-1.0): How confident the model is about the primary intent
  - ✓ > 0.8: Good
  - ⚠ 0.5-0.8: Acceptable
  - ✗ < 0.5: Needs improvement

- **Entity Coverage** (%): Percentage of expected entities extracted
  - ✓ > 80%: Excellent
  - ⚠ 50-80%: Good
  - ✗ < 50%: Poor

- **Complexity Score** (1-5): Estimated query complexity
  - 1-2: Simple queries (single action)
  - 2-3: Moderate queries (some complexity)
  - 3-5: Complex queries (multiple steps)

### Output Evaluation Scores

- **Faithfulness** (0.0-1.0): Response grounding in documents
  - ✓ > 0.75: Excellent grounding
  - ⚠ 0.4-0.75: Moderate grounding
  - ✗ < 0.4: High hallucination risk

- **Relevance** (0.0-1.0): Query-response semantic alignment
  - ✓ > 0.75: Highly relevant
  - ⚠ 0.4-0.75: Somewhat relevant
  - ✗ < 0.4: Poorly relevant

- **Completeness** (0.0-1.0): Coverage of required information
  - ✓ > 0.75: Complete coverage
  - ⚠ 0.4-0.75: Partial coverage
  - ✗ < 0.4: Incomplete coverage

- **Overall Quality** (0.0-1.0): Weighted combination
  - ✓ > 0.7: High quality
  - ⚠ 0.5-0.7: Acceptable quality
  - ✗ < 0.5: Low quality (requires iteration)

---

## Troubleshooting

### Tests fail with "ModuleNotFoundError"
```bash
# Make sure you're in project root and run:
export PYTHONPATH="${PYTHONPATH}:."
python -m ai.tests.test_input_evaluation
```

### Mock models not working
- Ensure you're using the mock models provided in test files
- Don't try to connect to real LLM APIs in tests

### Pipeline tests skip stages
- Check if components are enabled: `enable_self_rag`, `enable_reranking`, etc.
- Verify mock models are initialized properly

### Low scores in evaluation tests
- This is expected! Mock evaluations return fixed scores
- Use real LLM models in `test_rag_integration.py` for production testing
- Adjust thresholds if needed for your use case

---

## Customizing Tests

### Use Your Own Models
```python
from ai.agentic_rag import AgenticRAG
from your_models import YourInputModel, YourOutputModel

input_model = YourInputModel()
output_model = YourOutputModel()

rag = AgenticRAG(
    llm_client=input_model,
    eval_llm_client=output_model
)

# Run tests with your models
result = rag.process_query("Your test query")
```

### Adjust Evaluation Thresholds
```python
from ai.self_rag import SelfRAG

custom_thresholds = {
    "faithfulness": 0.8,      # Strict
    "relevance": 0.85,        # Strict
    "completeness": 0.9,      # Very strict
    "context_recall": 0.7,
    "context_precision": 0.75,
    "routing_accuracy": 0.9,
}

self_rag = SelfRAG(retriever, llm_client, thresholds=custom_thresholds)
```

### Add More Test Cases
```python
def test_custom_scenario():
    """Your custom test"""
    # Add your test logic here
    pass

# Add to run_all_tests() or create new test file
```

---

## Next Steps

1. **Run all three test suites** to understand your system
2. **Review failing tests** and adjust thresholds or models as needed
3. **Integrate tests into CI/CD** for continuous quality monitoring
4. **Add domain-specific test cases** for your room booking system
5. **Monitor metrics over time** to detect degradation

---

## Support

For questions about:
- **Input evaluation**: Check `ai/query_processor.py` documentation
- **Output evaluation**: Check `ai/self_rag.py` documentation
- **Pipeline integration**: Check `ai/agentic_rag.py` documentation
