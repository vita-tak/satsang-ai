from pathlib import Path


def load_document(pdf_path: Path) -> str:
    """
    Extract text from a PDF using PyMuPDF.
    """
    import pymupdf

    doc = pymupdf.open(str(pdf_path))
    pages = [page.get_text() for page in doc]
    doc.close()
    return "\n".join(pages)