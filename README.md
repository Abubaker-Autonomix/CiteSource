# Source Citation RAG — Backend (Task 10)

No API keys. Runs locally with SQLite (documents + chunks + embeddings).
Search uses brute-force cosine similarity via numpy - no vector database
service needed, no C++ compiler required (this avoids the ChromaDB/hnswlib
build issue that needs Microsoft C++ Build Tools on Windows).

## Files
- `main.py` — FastAPI app
- `extractor.py` — PyMuPDF PDF text extraction (with page numbers)
- `chunker.py` — Recursive character chunker (same pattern as Task 9)
- `embedder.py` — Local free embeddings (fastembed - ONNX-based, lightweight, no torch)
- `storage.py` — SQLite for everything: documents, chunks, embeddings, search
- `requirements.txt`

## Setup (Antigravity terminal)

```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install --no-cache-dir -r requirements.txt
uvicorn main:app --reload --port 8001
```

**Space note:** total project (venv + downloaded embedding model) should land
around 500-700MB - well under 1GB. This uses `fastembed` (ONNX-based)
instead of `sentence-transformers`+`torch`, which would have pushed the
project past 1.5-2GB. First embedding call downloads the model (~130MB) once.

Using port **8001** (not 8000) so this can run alongside the Task 9 backend
if needed.

## Quick test

1. Visit `http://localhost:8001/docs`
2. `POST /api/documents` — upload a PDF file
3. `GET /api/documents/{document_id}` — poll until `status: "ready"`
4. `POST /api/search` — `{"query": "your question", "top_k": 5}` → returns
   matching chunks, each with `source_file` and `page_number` (the citation)

## Endpoints

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/documents` | Upload a PDF, triggers extract→chunk→embed pipeline |
| GET | `/api/documents` | List all uploaded documents |
| GET | `/api/documents/{id}` | Check processing status |
| POST | `/api/search` | Semantic search, returns chunks with page-number citations |
