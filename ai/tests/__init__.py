"""
Test suite for Agentic RAG system

This package contains comprehensive tests for:
1. INPUT EVALUATION (test_input_evaluation.py)
   - QueryProcessor: Intent classification, entity extraction, complexity scoring
   
2. OUTPUT EVALUATION (test_output_evaluation.py)
   - SelfRAG: Faithfulness, relevance, completeness evaluation
   
3. INTEGRATION TESTS (test_rag_integration.py)
   - Full pipeline: End-to-end query processing and response generation

Run individual tests:
  python -m ai.tests.test_input_evaluation
  python -m ai.tests.test_output_evaluation
  python -m ai.tests.test_rag_integration

Run all tests:
  python -m pytest ai/tests/ -v
"""
