"""
PDF extraction with page-level citation metadata, using PyMuPDF (fitz).
No API keys needed - runs entirely locally.
"""
import fitz  # PyMuPDF


def extract_pdf_pages(pdf_path: str) -> list[dict]:
    """Returns a list of {page_number, text} dicts, one per non-empty page."""
    doc = fitz.open(pdf_path)
    pages = []
    for page_num, page in enumerate(doc, start=1):
        text = page.get_text("text")
        if text.strip():
            pages.append({"page_number": page_num, "text": text})
    doc.close()
    return pages
