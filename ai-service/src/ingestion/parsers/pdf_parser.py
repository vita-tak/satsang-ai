from pathlib import Path

import pymupdf


def load_document(pdf_path: Path) -> str:
    """Extract all text from a PDF using PyMuPDF."""
    doc = pymupdf.open(str(pdf_path))
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)


def load_pages(pdf_path: Path, start_page: int, end_page: int) -> str:
    """
    Extract text from a page range (1-indexed, end_page exclusive).
    """
    doc = pymupdf.open(str(pdf_path))
    pages = [doc[i].get_text() for i in range(start_page - 1, end_page - 1)]
    doc.close()
    return "\n".join(pages)