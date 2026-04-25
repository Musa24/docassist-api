"""PDF text extraction using PyMuPDF (fitz).

Thin wrapper around fitz that returns a (text, page_count) tuple.
Route handlers catch PdfExtractionError and convert to HTTP 422.
"""

from pathlib import Path

import fitz


class PdfExtractionError(Exception):
    """Raised when a PDF cannot be opened or parsed."""


def extract_text(path: str | Path) -> tuple[str, int]:
    """Open a PDF at `path` and return (all-pages-concatenated text, page count).

    Raises:
        PdfExtractionError: if the file is missing, not a valid PDF, or
            cannot be parsed. The original cause is chained via `from`.
    """
    try:
        doc = fitz.open(path, filetype="pdf")
    except Exception as exc:
        raise PdfExtractionError(f"Failed to open PDF at {path}: {exc}") from exc

    try:
        pages = [page.get_text() for page in doc]
    except Exception as exc:
        raise PdfExtractionError(f"Failed to extract text from {path}: {exc}") from exc
    finally:
        doc.close()

    return "\n".join(pages), len(pages)
