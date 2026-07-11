"""
Storage layer.
Everything lives in one SQLite file - documents AND chunks+embeddings.
No ChromaDB (avoids the hnswlib C++ compile issue on Windows), no separate
vector database service. Search uses brute-force cosine similarity via numpy,
which is completely fine at the scale of a personal/small-team document set.

Note: on Railway's free tier, disk is ephemeral (wiped on redeploy) - fine
for local testing in Antigravity. For production persistence, swap this for
Supabase Postgres + pgvector later (same upgrade path as Task 9).
"""
import sqlite3
import uuid
import json
from datetime import datetime, timezone
from contextlib import contextmanager

import numpy as np

DB_PATH = "documents.db"


def init_db():
    with get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                id TEXT PRIMARY KEY,
                filename TEXT NOT NULL,
                page_count INTEGER,
                chunk_count INTEGER DEFAULT 0,
                status TEXT DEFAULT 'processing',
                error TEXT,
                created_at TEXT
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id TEXT PRIMARY KEY,
                document_id TEXT NOT NULL,
                source_file TEXT NOT NULL,
                page_number INTEGER NOT NULL,
                chunk_index INTEGER,
                content TEXT NOT NULL,
                embedding TEXT NOT NULL,
                FOREIGN KEY (document_id) REFERENCES documents(id)
            )
        """)
        conn.commit()


@contextmanager
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_document(filename: str) -> str:
    doc_id = str(uuid.uuid4())
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO documents (id, filename, status, created_at) VALUES (?, ?, 'processing', ?)",
            (doc_id, filename, now()),
        )
        conn.commit()
    return doc_id


def update_document(doc_id: str, **fields):
    if not fields:
        return
    cols = ", ".join(f"{k} = ?" for k in fields)
    vals = list(fields.values()) + [doc_id]
    with get_conn() as conn:
        conn.execute(f"UPDATE documents SET {cols} WHERE id = ?", vals)
        conn.commit()


def get_document(doc_id: str):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (doc_id,)).fetchone()
        return dict(row) if row else None


def list_documents():
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM documents ORDER BY created_at DESC").fetchall()
        return [dict(r) for r in rows]


def save_chunks(doc_id: str, filename: str, chunks: list[dict], embeddings: list[list[float]]):
    with get_conn() as conn:
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            conn.execute(
                """INSERT INTO chunks (id, document_id, source_file, page_number, chunk_index, content, embedding)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    str(uuid.uuid4()),
                    doc_id,
                    filename,
                    chunk["page_number"],
                    i,
                    chunk["content"],
                    json.dumps(embedding),
                ),
            )
        conn.commit()


def search_chunks(query_embedding: list[float], top_k: int = 5):
    with get_conn() as conn:
        rows = conn.execute("SELECT * FROM chunks").fetchall()

    if not rows:
        return []

    query_vec = np.array(query_embedding)
    query_norm = np.linalg.norm(query_vec)

    scored = []
    for row in rows:
        chunk_vec = np.array(json.loads(row["embedding"]))
        chunk_norm = np.linalg.norm(chunk_vec)
        if query_norm == 0 or chunk_norm == 0:
            similarity = 0.0
        else:
            similarity = float(np.dot(query_vec, chunk_vec) / (query_norm * chunk_norm))
        scored.append((similarity, row))

    scored.sort(key=lambda x: x[0], reverse=True)

    return [
        {
            "content": row["content"],
            "source_file": row["source_file"],
            "page_number": row["page_number"],
            "similarity": round(similarity, 4),
        }
        for similarity, row in scored[:top_k]
    ]
