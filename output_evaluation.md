# Output Evaluation: Code Implementation and Runtime Flow

This document explains exactly how output evaluation is implemented in `SelfRAG` and how each metric is computed during runtime.

---

## 1. Where Evaluation Happens in Code

Evaluation runs inside:

- `SelfRAG.generate_with_reflection(...)`

Main steps per query:

1. Retrieve documents (`retriever.retrieve(...)`)
2. Compute retrieval metrics
3. If retrieval is too weak, refine query and retry
4. Generate response
5. Compute generation metrics (LLM-based)
6. Compute system metrics (latency, routing)
7. Aggregate quality scores
8. Check thresholds -> success/fail

---

## 2. Retrieval Quality Metrics

## 2.1 Context Recall (Standard Formula)

Definition:

```text
Context_Recall = |Retrieved ∩ Relevant| / |Relevant|
```

In code:

- Method: `_compute_context_recall(retrieved_docs, relevant_doc_ids_in_corpus)`
- `Retrieved` is built from retrieved doc IDs
- `Relevant` is `relevant_doc_ids_in_corpus` (ground truth labels)

Implementation behavior:

- If ground-truth IDs are provided, strict formula is used.
- If ground-truth IDs are missing, it falls back to proxy recall (`_compute_context_recall_proxy`) for online runtime.

Proxy recall (fallback only):

```text
proxy_recall = min(avg(normalized_scores) + doc_count_bonus, 1.0)
doc_count_bonus = min(#(score > 0.5)/min(5, K), 0.2)
```

## 2.2 Context Precision (Standard Formula)

Definition:

```text
Context_Precision = |Retrieved ∩ Relevant| / |Retrieved|
```

In code:

- Method: `_compute_context_precision(retrieved_docs, relevant_doc_ids_in_corpus)`
- Uses same set intersection with retrieved IDs and relevant IDs.

Implementation behavior:

- If ground-truth IDs are provided, strict formula is used.
- If ground-truth IDs are missing, it falls back to proxy precision (`_compute_context_precision_proxy`) using score threshold `score > 0.5`.

## 2.3 Required Input for Strict Retrieval Metrics

Strict recall/precision need query-level ground truth:

- `relevant_doc_ids_in_corpus: List[str]`

You can pass it either:

1. Direct parameter:

```python
self_rag.generate_with_reflection(
	query=query,
	entities=entities,
	intent=intent,
	relevant_doc_ids_in_corpus=["12", "33", "A2"],
)
```

2. Or through context:

```python
self_rag.generate_with_reflection(
	query=query,
	context={"relevant_doc_ids_in_corpus": ["12", "33", "A2"]},
)
```

---

## 3. Generation Quality Metrics (LLM-Based)

These three metrics are evaluated by `llm_client` (evaluation model).

## 3.1 Faithfulness

Definition:

```text
Faithfulness = LLM_Evaluate_Grounding(response, documents)
```

Code path:

- Method: `_compute_faithfulness(response, docs)`
- Sends documents + response in a scoring prompt
- Expects a numeric output in `[0.0, 1.0]`
- Fallback score on exception: `0.5`

## 3.2 Relevance

Definition:

```text
Relevance = LLM_Evaluate_Relevance(query, response)
```

Code path:

- Method: `_compute_relevance(query, response)`
- Sends query + response in a scoring prompt
- Expects numeric score `[0.0, 1.0]`
- Fallback on exception: `0.5`

## 3.3 Completeness

Definition:

```text
Completeness = LLM_Evaluate_Coverage(response, entities)
```

Code path:

- Method: `_compute_completeness(response, entities)`
- Uses extracted required entities as coverage checklist
- Expects numeric score `[0.0, 1.0]`
- If entities missing -> returns `0.5`
- On exception -> returns `0.5`

---

## 4. System Metrics

## 4.1 Latency

Definition:

```text
Latency_ms = (EndTime - StartTime) * 1000
```

In code:

```python
start_time = time.time()
# ... pipeline work ...
latency_ms = (time.time() - start_time) * 1000
self.pipeline_metrics["total_latency_ms"] += latency_ms
```

## 4.2 Iteration Efficiency

Definition:

```text
Iteration_Efficiency = 1 / (iteration + 1)
```

In code:

- First successful attempt -> `1.0`
- Second attempt -> `0.5`
- Third attempt -> `0.33`

## 4.3 Routing Accuracy

Current implementation:

- Placeholder in `_compute_routing_accuracy(intent)`
- Returns `1.0` if intent exists, otherwise `0.5`

---

## 5. Aggregated Scores

Computed in `evaluation_scores`:

```text
Retrieval_Quality = (Context_Recall + Context_Precision) / 2
Generation_Quality = (Faithfulness + Relevance + Completeness) / 3
Latency_Factor = 1 - min(latency_ms / 1500, 1)

Overall_Quality =
	0.3 * Retrieval_Quality +
	0.5 * Generation_Quality +
	0.2 * Latency_Factor
```

---

## 6. Success Logic (Pass/Fail)

A query is marked successful only if all threshold checks pass:

- `context_recall >= threshold`
- `context_precision >= threshold`
- `faithfulness >= threshold`
- `relevance >= threshold`
- `completeness >= threshold`
- `routing_accuracy >= threshold`

If any required metric fails, the system may refine query and retry until `max_iterations`.

---

## 7. How It Works: One Runtime Example

Example input:

```python
result = self_rag.generate_with_reflection(
	query="Can I book room A2 for 50 people on Monday?",
	entities={"room": "A2", "capacity": "50", "date": "Monday"},
	intent="booking",
	relevant_doc_ids_in_corpus=["doc_2", "doc_5", "doc_9"],
	max_iterations=3,
)
```

Assume retriever returns IDs: `doc_2, doc_5, doc_11, doc_20, doc_31`

Then:

- `Retrieved = {2,5,11,20,31}`
- `Relevant = {2,5,9}`
- `Intersection = {2,5}` (2 true positives)

Metrics:

- `Context Recall = 2 / 3 = 0.667`
- `Context Precision = 2 / 5 = 0.400`

If recall is above threshold but precision is below threshold, final success is `False` unless later iterations improve it.

After response generation, LLM assigns:

- faithfulness (groundedness)
- relevance (answers query)
- completeness (covers required entities)

System computes latency and overall weighted quality, then returns:

```python
{
	"response": "...",
	"retrieved_docs": [...],
	"evaluation_scores": {
		"context_recall": ...,
		"context_precision": ...,
		"faithfulness": ...,
		"relevance": ...,
		"completeness": ...,
		"routing_accuracy": ...,
		"latency_ms": ...,
		"iteration_efficiency": ...,
		"retrieval_quality": ...,
		"generation_quality": ...,
		"overall_quality": ...,
	},
	"iterations": ...,
	"success": True/False,
}
```

---