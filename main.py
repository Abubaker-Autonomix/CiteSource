"""
Source Citation RAG - FastAPI backend.
"""

import os
import shutil
import tempfile

from fastapi import FastAPI, UploadFile, File, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import storage
import extractor
import chunker
import embedder

app = FastAPI(title="Source Citation RAG Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize DB (Supabase schema is managed externally)
storage.init_db()


def process_document(doc_id: str, pdf_path: str, filename: str):
    try:
        pages = extractor.extract_pdf_pages(pdf_path)
        chunk_fn = chunker.RecursiveCharacterChunker()

        all_chunks = []
        for page in pages:
            pieces = chunk_fn.split(page["text"], chunk_size=800, chunk_overlap=100)
            for piece in pieces:
                all_chunks.append({"content": piece, "page_number": page["page_number"]})

        if not all_chunks:
            storage.update_document(doc_id, status="failed", error="No extractable text found")
            return

        texts = [c["content"] for c in all_chunks]
        embeddings = embedder.embed_texts(texts)
        storage.save_chunks(doc_id, filename, all_chunks, embeddings)

        storage.update_document(
            doc_id, status="ready", page_count=len(pages), chunk_count=len(all_chunks)
        )
    except Exception as e:
        storage.update_document(doc_id, status="failed", error=str(e))
    finally:
        if os.path.exists(pdf_path):
            os.remove(pdf_path)


@app.post("/api/documents")
async def upload_document(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported")

    doc_id = storage.create_document(file.filename)

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    with tmp as f:
        shutil.copyfileobj(file.file, f)

    background_tasks.add_task(process_document, doc_id, tmp.name, file.filename)
    return {"id": doc_id, "status": "processing"}


@app.get("/api/documents")
def list_documents():
    return storage.get_documents()          # ← Fixed


@app.get("/api/documents/{doc_id}")
def get_document(doc_id: str):
    doc = storage.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


class RenameRequest(BaseModel):
    filename: str


@app.patch("/api/documents/{doc_id}")
def rename_document(doc_id: str, req: RenameRequest):
    doc = storage.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    updated = storage.rename_document(doc_id, req.filename)
    return updated


@app.delete("/api/documents/{doc_id}")
def delete_document(doc_id: str):
    doc = storage.get_document(doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    storage.delete_document(doc_id)
    return {"id": doc_id, "deleted": True}


@app.delete("/api/documents")
def clear_documents():
    storage.clear_documents()
    return {"cleared": True}


class SearchRequest(BaseModel):
    query: str
    top_k: int = 5


@app.post("/api/search")
def search(req: SearchRequest):
    query_embedding = embedder.embed_texts([req.query])[0]
    results = storage.search(query_embedding, req.top_k)   # ← Fixed
    return {"query": req.query, "results": results}


@app.get("/")
def root():
    return {"status": "ok", "message": "Source Citation RAG API is running"}
