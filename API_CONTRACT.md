# API Contract — Task 10 (Source of Truth)

This is the exact shape every endpoint returns. When the frontend prompt is
written, these field names are copied in directly — no guessing, no renaming.
This is what caused the "undefined" bug in Task 9.

## POST /api/documents
Request: multipart form, field name `file` (a .pdf)
Response:
```json
{ "id": "uuid-string", "status": "processing" }
```

## GET /api/documents
Response: array of document objects
```json
[
  {
    "id": "uuid-string",
    "filename": "report.pdf",
    "page_count": 12,
    "chunk_count": 34,
    "status": "processing",
    "error": null,
    "created_at": "2026-07-11T10:00:00+00:00"
  }
]
```
`status` is one of: `"processing" | "ready" | "failed"`

## GET /api/documents/{id}
Response: single document object (same shape as one item above)

## POST /api/search
Request:
```json
{ "query": "your question", "top_k": 5 }
```
Response:
```json
{
  "query": "your question",
  "results": [
    {
      "content": "the matching chunk text...",
      "source_file": "report.pdf",
      "page_number": 4,
      "similarity": 0.82
    }
  ]
}
```
`similarity` is 0-1, higher = better match.

## Rule going forward
Any time the frontend prompt or generated code uses a different field name
than what's listed here (e.g. `document_id` instead of `id`, `page` instead
of `page_number`, `text` instead of `content`), that's the bug — fix the
frontend to match this contract, not the other way around, since this file
is the single source of truth both sides build against.
