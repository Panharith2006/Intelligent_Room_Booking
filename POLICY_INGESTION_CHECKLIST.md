# Policy Ingestion Checklist ✓

## What Was Done

### Files Created
- [x] `ai/ingest_policies.py` — Core ingestion logic
- [x] `ai/management/__init__.py` — Django management module
- [x] `ai/management/commands/__init__.py` — Django commands module
- [x] `ai/management/commands/ingest_policies.py` — Django CLI command
- [x] `ai/apps.py` — Django AppConfig
- [x] `POLICY_INGESTION_GUIDE.md` — User documentation
- [x] `ai/test_policy_rag.py` — Verification test suite

### Files Modified
- [x] `room_booking_system/settings.py` — Added 'ai' to INSTALLED_APPS

---

## Quick Start (Copy & Paste)

### 1. Ingest Policies
```bash
python manage.py ingest_policies
```

Expected output:
```
🚀 Starting policy ingestion...
✓ Successfully ingested 15 policy chunks into booking_policies collection
Vector store stats: {'booking_policies': 15, 'knowledge_base': 0, 'rooms_info': 0}
✓ Policy document ingested successfully!
```

### 2. Verify Ingestion
```bash
python manage.py ingest_policies --verify
```

This will test queries like:
- "What is the maximum booking duration?"
- "Can I cancel a booking less than 3 hours before?"
- "How many active bookings can a user have?"

### 3. Run Full Test Suite
```bash
python manage.py shell
from ai.test_policy_rag import *
# Or run the test file
```

---

## How RAG Flows Work Now

### Example: User Asks Chatbot
**User:** "Can I cancel my booking less than 3 hours before?"

### Processing:
1. **Query** → HybridRetriever
2. **Retriever** → Searches policy.md vectors
3. **Top Results** → Cancellation policy sections returned
4. **LLM** (Ollama) → Generates response using policy context

**Chatbot Response:**
> "According to the booking policy, cancellations made less than 3 hours before the scheduled start time are considered **late cancellations** and may result in penalties. Your late cancellation count will be recorded, and when you reach two late cancellations, the system will issue a warning notification."

---

## Architecture Now

```
policy.md
    ↓
[LangChainDocumentLoader]
    ↓ (chunks + metadata)
[ChromaDB] (booking_policies collection)
    ↓
[VectorStore] ← get_vector_store()
    ↓
[HybridRetriever] ← search_policies()
    ↓
[AgenticRAG] ← process query + retrieve
    ↓
[ChatAgent] → LLM (Ollama)
    ↓
Response to User
```

---

## Test It Out

1. **Terminal 1** — Start Django:
   ```bash
   python manage.py runserver
   ```

2. **Terminal 2** — Ingest policies:
   ```bash
   python manage.py ingest_policies --verify
   ```

3. **Browser** — Go to chatbot:
   ```
   http://localhost:8000/chatbot/chat/
   ```

4. **Ask a policy question:**
   - "What is the maximum booking duration?"
   - "How many active bookings can I have?"
   - "What happens if I cancel late?"

---

## Next Steps for You

### Option A: Add More Documents
Create new files and add to RAG:
- FAQ.md
- Room_Usage_Guidelines.md
- Admin_Procedures.md

Then ingest:
```bash
python manage.py ingest_documents --file FAQ.md --collection knowledge_base
```

### Option B: Improve Retrieval Quality
- Adjust chunk_size in ingest_policies.py (currently 800)
- Test reranker effectiveness
- Add custom metadata filters

### Option C: Add Rooms Info
Populate `rooms_info` collection:
```python
from ai.vector_store import get_vector_store
vs = get_vector_store()
# Add room descriptions, capacity, equipment
```

---

## Troubleshooting

### "Management command not found"
- Verify 'ai' is in INSTALLED_APPS
- Restart Django server

### "ChromaDB error"
- Delete `vector_db/chroma.sqlite3`
- Re-run ingestion (will recreate)

### "LangChain import error"
- Run: `pip install langchain`

### "Chunks too large/small"
- Edit chunk_size in `ai/ingest_policies.py` line 35

---

## Success Indicators ✓

After running `python manage.py ingest_policies --verify`:
- [x] 15 chunks ingested
- [x] Test queries return results
- [x] Vector store stats show booking_policies count
- [x] Hybrid retriever can retrieve policy sections
- [x] Chatbot can answer policy questions with context
