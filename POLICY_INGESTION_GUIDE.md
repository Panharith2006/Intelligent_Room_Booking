# Policy Ingestion Guide

## Overview
Your `policy.md` file has been set up to be automatically ingested into the RAG vector store (ChromaDB `booking_policies` collection).

## What Was Created

### 1. **ai/ingest_policies.py**
   - `ingest_policy_document()` — Loads policy.md and chunks it
   - `verify_policy_ingestion()` — Tests that policies were stored correctly

### 2. **ai/management/commands/ingest_policies.py**
   - Django management command for easy ingestion
   - Supports `--verify` flag to test ingestion
   - Supports `--clear` flag to reset before ingesting

### 3. **ai/apps.py**
   - Registered 'ai' app in INSTALLED_APPS
   - Django now recognizes management commands

---

## How to Use

### Option 1: Simple Ingestion (Recommended)
```bash
python manage.py ingest_policies
```

### Option 2: Ingest + Verify
```bash
python manage.py ingest_policies --verify
```

### Option 3: Clear Old Policies, Then Ingest
```bash
python manage.py ingest_policies --clear --verify
```

---

## What Happens During Ingestion

1. **Loads** `policy.md` from project root
2. **Chunks** the text into ~800-character segments with 150-char overlap
3. **Adds metadata** to each chunk:
   - `document_type`: "booking_policy"
   - `category`: "university_rules"
   - `source_file`: "policy.md"
   - `ingestion_time`: ISO timestamp
4. **Stores** chunks in ChromaDB `booking_policies` collection
5. **Logs** success with chunk count

---

## How Chatbot Uses It

When user asks: *"Can I cancel a booking less than 3 hours before?"*

### RAG Flow:
1. **HybridRetriever** sends query to `vector_store.search_policies()`
2. **ChromaDB** finds semantically similar chunks from policy.md
3. **Results** returned with distances (relevance scores)
4. **LLM** (Ollama) generates response using policy chunks as context

---

## Verifying Ingestion

Run test queries:
```bash
python manage.py ingest_policies --verify
```

This tests queries like:
- "What is the maximum booking duration?"
- "Can I cancel a booking less than 3 hours before?"
- "How many active bookings can a user have?"
- "What is the late cancellation policy?"

You'll see top matching chunks from policy.md.

---

## Collection Stats

After ingestion, check stats with:
```python
from ai.vector_store import get_vector_store
vs = get_vector_store()
print(vs.get_collection_stats())
# Output: {'booking_policies': 15, 'knowledge_base': 0, 'rooms_info': 0}
```

---

## Troubleshooting

### "Policy file not found"
- Check that `policy.md` exists at project root
- Path: `d:/Year 3/PP/Project_S2/RoomBooking - Copy/policy.md`

### "LangChain not installed"
- Run: `pip install langchain`

### "ChromaDB not working"
- Check `vector_db/` directory exists
- Vector store at: `./vector_db/chroma.sqlite3`

### Chunks too small/large?
Edit `ai/ingest_policies.py` line 34-36:
```python
loader = LangChainDocumentLoader(
    chunk_size=800,        # Change this
    chunk_overlap=150,     # And this
)
```

---

## Next Steps

1. **Run the ingestion** (see How to Use section)
2. **Test with chatbot** — ask policy questions
3. **Monitor performance** — check retrieval quality
4. **Add more docs** — expand RAG with procedure guides, FAQ, etc.
