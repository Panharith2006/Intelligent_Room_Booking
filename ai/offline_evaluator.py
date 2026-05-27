import logging
import json
import time
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class OfflineEvaluator:
    
    def __init__(
        self,
        retriever=None,
        eval_llm_client=None,
        output_dir: str = "./eval_results"
    ):
       
        self.retriever = retriever
        self.eval_llm_client = eval_llm_client
        self.output_dir = output_dir
        
        logger.info(f"Offline Evaluator initialized")
        logger.info(f"   NOTE: This runs OFFLINE only, never during runtime inference")
    
    # =====================================================
    # MAIN EVALUATION PIPELINE
    # =====================================================
    def evaluate_outputs(
        self,
        test_cases: List[Dict],
        rag_system,
        output_file: Optional[str] = None,
    ) -> Dict:
        
        logger.info("\n" + "="*80)
        logger.info("OFFLINE EVALUATION - Running on test dataset")
        logger.info("="*80)
        logger.info(f"Evaluating {len(test_cases)} test cases...")
        
        start_time = time.time()
        results = []
        errors = []
        
        for i, test_case in enumerate(test_cases, 1):
            logger.info(f"\n  Test Case {i}/{len(test_cases)}: {test_case.get('query', '')[:50]}...")
            
            try:
                # Generate output
                rag_output = rag_system.process_query(
                    query=test_case.get("query", ""),
                    context=test_case.get("context"),
                )
                
                # Evaluate output
                eval_result = self._evaluate_output(
                    test_case=test_case,
                    rag_output=rag_output,
                )
                
                results.append(eval_result)
                
                # Log scores for this case
                scores = eval_result.get("evaluation_scores", {})
                logger.info(f"    ✅ Faithfulness: {scores.get('faithfulness', 0):.2f} | "
                          f"Relevance: {scores.get('relevance', 0):.2f} | "
                          f"Completeness: {scores.get('completeness', 0):.2f}")
                
            except Exception as e:
                logger.error(f"    ❌ Error evaluating case {i}: {e}")
                errors.append({"case_id": i, "error": str(e)})
        
        # Aggregate results
        aggregated = self._aggregate_results(results)
        aggregated["total_cases"] = len(test_cases)
        aggregated["successful_cases"] = len(results)
        aggregated["failed_cases"] = len(errors)
        aggregated["evaluation_time_seconds"] = time.time() - start_time
        
        # Print summary
        logger.info("\n" + "="*80)
        logger.info("EVALUATION SUMMARY")
        logger.info("="*80)
        logger.info(f"Successful: {len(results)}/{len(test_cases)}")
        logger.info(f"Failed: {len(errors)}")
        logger.info(f"Time: {aggregated['evaluation_time_seconds']:.2f}s")
        logger.info(f"\nMetrics:")
        logger.info(f"  Faithfulness: {aggregated.get('avg_faithfulness', 0):.3f}")
        logger.info(f"  Relevance: {aggregated.get('avg_relevance', 0):.3f}")
        logger.info(f"  Completeness: {aggregated.get('avg_completeness', 0):.3f}")
        logger.info(f"  Retrieval F1: {aggregated.get('avg_retrieval_f1', 0):.3f}")
        logger.info(f"  Overall Quality: {aggregated.get('avg_overall_quality', 0):.3f}")
        logger.info("="*80 + "\n")
        
        # Save results
        if output_file:
            self._save_results(aggregated, results, errors, output_file)
        
        return aggregated
    
    # =====================================================
    # SINGLE OUTPUT EVALUATION
    # =====================================================
    
    def _evaluate_output(
        self,
        test_case: Dict,
        rag_output: Dict,
    ) -> Dict:
        
        query = test_case.get("query", "")
        expected_docs = test_case.get("expected_docs", [])
        response_text = rag_output.get("response_text", "")
        retrieved_docs = rag_output.get("retrieved_docs", [])
        entities = rag_output.get("entities", {})
        
        # 1. Retrieval Evaluation (deterministic)
        retrieval_metrics = self._evaluate_retrieval(retrieved_docs, expected_docs)
        
        # 2. Generation Evaluation (LLM-based, OFFLINE)
        generation_metrics = self._evaluate_generation(
            query=query,
            response=response_text,
            retrieved_docs=retrieved_docs,
            entities=entities,
        )
        
        # 3. Combine metrics
        overall_quality = (
            0.4 * retrieval_metrics.get("f1_score", 0.5) +
            0.6 * generation_metrics.get("generation_quality", 0.5)
        )
        
        return {
            "query": query,
            "response": response_text,
            "retrieval_metrics": retrieval_metrics,
            "generation_metrics": generation_metrics,
            "evaluation_scores": {
                "faithfulness": generation_metrics.get("faithfulness", 0.5),
                "relevance": generation_metrics.get("relevance", 0.5),
                "completeness": generation_metrics.get("completeness", 0.5),
                "retrieval_f1": retrieval_metrics.get("f1_score", 0.5),
            },
            "overall_quality": overall_quality,
        }
    
    # =====================================================
    # RETRIEVAL EVALUATION (Deterministic, No LLM)
    # =====================================================
    
    def _evaluate_retrieval(
        self,
        retrieved_docs: List[Dict],
        expected_docs: List[Dict] | List[str],
    ) -> Dict:
       
        # Extract IDs from retrieved docs
        retrieved_ids = {self._extract_doc_id(d) for d in retrieved_docs if self._extract_doc_id(d)}
        
        # Extract IDs from expected docs (handle both dict and string lists)
        expected_ids = set()
        for doc in expected_docs:
            if isinstance(doc, dict):
                doc_id = self._extract_doc_id(doc)
                if doc_id:
                    expected_ids.add(doc_id)
            elif isinstance(doc, str):
                expected_ids.add(doc)
        
        # Calculate metrics
        if not expected_ids:
            # No ground truth available
            return {
                "recall": 0.5,
                "precision": 0.5,
                "f1_score": 0.5,
                "has_ground_truth": False,
            }
        
        tp = len(retrieved_ids.intersection(expected_ids))
        recall = tp / len(expected_ids) if expected_ids else 0.0
        precision = tp / len(retrieved_ids) if retrieved_ids else 0.0
        f1 = (
            2 * (precision * recall) / (precision + recall)
            if (precision + recall) > 0
            else 0.0
        )
        
        return {
            "recall": recall,
            "precision": precision,
            "f1_score": f1,
            "has_ground_truth": True,
            "true_positives": tp,
            "retrieved_count": len(retrieved_ids),
            "expected_count": len(expected_ids),
        }
    
    # =====================================================
    # GENERATION EVALUATION (LLM-based)
    # =====================================================
    def _evaluate_generation(
        self,
        query: str,
        response: str,
        retrieved_docs: List[Dict],
        entities: Dict = None,
    ) -> Dict:
        
        if not self.eval_llm_client:
            logger.warning("No LLM client for evaluation, returning defaults")
            return {
                "faithfulness": 0.5,
                "relevance": 0.5,
                "completeness": 0.5,
                "generation_quality": 0.5,
            }
        
        faithfulness = self._evaluate_faithfulness(response, retrieved_docs)
        relevance = self._evaluate_relevance(query, response)
        completeness = self._evaluate_completeness(response, entities)
        
        generation_quality = (faithfulness + relevance + completeness) / 3
        
        return {
            "faithfulness": faithfulness,
            "relevance": relevance,
            "completeness": completeness,
            "generation_quality": generation_quality,
        }
    
    def _evaluate_faithfulness(self, response: str, docs: List[Dict]) -> float:
        """Is response grounded in retrieved documents?"""
        if not response or not docs:
            return 0.5
        
        doc_text = "\n".join(d.get("text", "") for d in docs[:3])
        
        prompt = f"""Evaluate faithfulness: is the response grounded in the documents?

Documents:
{doc_text[:500]}

Response:
{response[:500]}

Score 0.0-1.0 where:
- 1.0 = completely grounded
- 0.5 = partially grounded
- 0.0 = completely hallucinated

Respond with ONLY the score."""
        
        try:
            result = self.eval_llm_client(prompt)
            score = float(result.strip())
            return min(max(score, 0.0), 1.0)
        except Exception as e:
            logger.warning(f"Faithfulness eval failed: {e}")
            return 0.5
    
    def _evaluate_relevance(self, query: str, response: str) -> float:
        """Does response address the query?"""
        if not response:
            return 0.0
        
        prompt = f"""Evaluate relevance: does the response address the query?

Query:
{query}

Response:
{response[:500]}

Score 0.0-1.0 where:
- 1.0 = perfectly relevant
- 0.5 = partially relevant
- 0.0 = completely irrelevant

Respond with ONLY the score."""
        
        try:
            result = self.eval_llm_client(prompt)
            score = float(result.strip())
            return min(max(score, 0.0), 1.0)
        except Exception as e:
            logger.warning(f"Relevance eval failed: {e}")
            return 0.5
    
    def _evaluate_completeness(self, response: str, entities: Dict = None) -> float:
        """Does response cover all required information?"""
        if not response or not entities:
            return 0.5
        
        entities_str = "\n".join(f"- {k}: {v}" for k, v in entities.items())
        
        prompt = f"""Evaluate completeness: does response cover all requirements?

Required Information:
{entities_str}

Response:
{response[:500]}

Score 0.0-1.0 where:
- 1.0 = complete
- 0.5 = partial
- 0.0 = incomplete

Respond with ONLY the score."""
        
        try:
            result = self.eval_llm_client(prompt)
            score = float(result.strip())
            return min(max(score, 0.0), 1.0)
        except Exception as e:
            logger.warning(f"Completeness eval failed: {e}")
            return 0.5
    
    # =====================================================
    # HELPERS
    # =====================================================
    def _extract_doc_id(self, doc: Dict) -> str:
        """Extract document ID from various possible keys."""
        if not isinstance(doc, dict):
            return ""
        
        for key in ("id", "doc_id", "document_id", "source_id", "pk", "uuid"):
            value = doc.get(key)
            if value:
                return str(value)
        
        return ""
    
    def _aggregate_results(self, results: List[Dict]) -> Dict:
        """Aggregate metrics from all test cases."""
        if not results:
            return {}
        
        faithfulness = [r.get("evaluation_scores", {}).get("faithfulness", 0.5) for r in results]
        relevance = [r.get("evaluation_scores", {}).get("relevance", 0.5) for r in results]
        completeness = [r.get("evaluation_scores", {}).get("completeness", 0.5) for r in results]
        f1_scores = [r.get("evaluation_scores", {}).get("retrieval_f1", 0.5) for r in results]
        overall = [r.get("overall_quality", 0.5) for r in results]
        
        return {
            "avg_faithfulness": sum(faithfulness) / len(faithfulness),
            "avg_relevance": sum(relevance) / len(relevance),
            "avg_completeness": sum(completeness) / len(completeness),
            "avg_retrieval_f1": sum(f1_scores) / len(f1_scores),
            "avg_overall_quality": sum(overall) / len(overall),
            "min_overall_quality": min(overall),
            "max_overall_quality": max(overall),
        }
    
    def _save_results(
        self,
        aggregated: Dict,
        results: List[Dict],
        errors: List[Dict],
        output_file: str,
    ):
        """Save evaluation results to JSON file."""
        import os
        
        os.makedirs(self.output_dir, exist_ok=True)
        filepath = os.path.join(self.output_dir, output_file)
        
        data = {
            "timestamp": datetime.now().isoformat(),
            "aggregated_metrics": aggregated,
            "individual_results": results,
            "errors": errors,
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        logger.info(f"Results saved to: {filepath}")
