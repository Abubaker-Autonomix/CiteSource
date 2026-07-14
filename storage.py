"""
Storage layer using Neon (Postgres + pgvector) via psycopg2.
Replaces the old SQLite/ephemeral-disk approach so data survives redeploys.
"""

import os
from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row

DATABASE_URL = os.environ["DATABASE_URL"]  # full Neon connection string


@contextmanager
def get_conn():
    conn = psycopg.connect(DATABASE_URL)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """No-op: schema is already created in Neon via SQL Editor.
    Kept so main.py's startup call doesn't break."""
    pass


def create_document(filename: str) -> str:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "insert into documents (filename, status) values (%s, 'processing') returning id",
                (filename,),
            )
            doc_id = cur.fetchone()[0]
            return str(doc_id)


def _rows_to_dicts(cur, rows):
    cols = [desc[0] for desc in cur.description]
    return [dict(zip(cols, row)) for row in rows]


def update_document(doc_id: str, status: str, page_count: int | None = None,
                     chunk_count: int | None = None, error: str | None = None):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                update documents
                set status = %s,
                    page_count = coalesce(%s, page_count),
                    chunk_count = coalesce(%s, chunk_count),
                    error = coalesce(%s, error)
                where id = %s
                """,
                (status, page_count, chunk_count, error, doc_id),
            )


def save_chunks(doc_id: str, filename: str, chunks: list[dict], embeddings: list[list[float]]):
    with get_conn() as conn:
        with conn.cursor() as cur:
            rows = [
                (doc_id, chunk["content"], str(embeddings[i]))
                for i, chunk in enumerate(chunks)
            ]
            cur.executemany(
                "insert into chunks (doc_id, content, embedding) values (%s, %s, %s::vector)",
                rows,
            )


def get_documents() -> list[dict]:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select * from documents order by created_at desc")
            return cur.fetchall()


def get_document(doc_id: str) -> dict | None:
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("select * from documents where id = %s", (doc_id,))
            return cur.fetchone()


def rename_document(doc_id: str, new_filename: str) -> dict | None:
    """Edit: update a document's filename."""
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                "update documents set filename = %s where id = %s returning *",
                (new_filename, doc_id),
            )
            return cur.fetchone()


def delete_document(doc_id: str) -> bool:
    """Delete a single document and its chunks.
    Safe to call even if there's no ON DELETE CASCADE FK set up in Neon,
    since chunks are deleted explicitly first."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("delete from chunks where doc_id = %s", (doc_id,))
            cur.execute("delete from documents where id = %s", (doc_id,))
            return cur.rowcount > 0


def clear_documents() -> None:
    """Clear: wipe all documents and chunks (e.g. 'Clear All' button)."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("truncate table chunks, documents restart identity cascade")


def search(query_embedding: list[float], top_k: int = 5, match_threshold: float = 0.1) -> list[dict]:
    embedding_str = str(query_embedding)
    with get_conn() as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                select id, doc_id, content,
                       1 - (embedding <=> %s::vector) as similarity
                from chunks
                where 1 - (embedding <=> %s::vector) > %s
                order by embedding <=> %s::vector
                limit %s
                """,
                (embedding_str, embedding_str, match_threshold, embedding_str, top_k),
            )
            return cur.fetchall()
