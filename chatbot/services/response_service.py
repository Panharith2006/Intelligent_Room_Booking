"""
Response payload helpers to keep controller code clean and safe.
"""

def build_chat_response(
	response_text: str,
	response_html,
	actions: list,
	entities: dict,
	primary_intent,
	reflection_scores: dict,
	session_id: str,
	rag_result: dict,
	retrieved_docs: list,
) -> dict:
	"""
	Build structured response for chatbot API.
	Safe version with defensive programming.
	"""

	# -----------------------------
	# Safety normalization
	# -----------------------------
	if reflection_scores is None:
		reflection_scores = {}

	if rag_result is None:
		rag_result = {}

	if retrieved_docs is None:
		retrieved_docs = []

	if entities is None:
		entities = {}

	# Normalize intent safely
	intent_value = primary_intent
	if isinstance(primary_intent, dict):
		intent_value = primary_intent.get("primary", "unknown")

	return {
		"reply_text": response_text,
		"reply_html": response_html,
		"actions": actions or [],
		"slots": entities,
		"intent": intent_value,
		"confidence": reflection_scores.get("overall", 0.8),
		"session_id": session_id,
		"rag_mode": "advanced",
		"metadata": {
			"processing_time": rag_result.get("processing_time", 0),
			"num_documents": len(retrieved_docs),
			"complexity": rag_result.get("complexity", 1),
			"reflection_scores": reflection_scores,
		},
	}