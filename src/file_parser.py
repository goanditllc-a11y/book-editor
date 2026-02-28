"""
src/file_parser.py
Parse PDF, EPUB, DOCX and TXT files into plain text.
Each parser returns a standardised result dict.
"""

from __future__ import annotations

import os
import re


_RESULT_TEMPLATE: dict = {
    "text": "",
    "title": "",
    "author": "",
    "word_count": 0,
    "error": None,
}


def _word_count(text: str) -> int:
    return len(text.split())


def _clean(text: str) -> str:
    """Normalise whitespace while preserving paragraph breaks."""
    # Collapse multiple blank lines into one
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Remove carriage returns
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    return text.strip()


# ---------------------------------------------------------------------------
# Individual parsers
# ---------------------------------------------------------------------------

def _parse_pdf(path: str) -> dict:
    result = dict(_RESULT_TEMPLATE)
    try:
        import fitz  # PyMuPDF
    except ImportError:
        result["error"] = "PyMuPDF (fitz) is not installed. Run: pip install PyMuPDF"
        return result

    try:
        doc = fitz.open(path)
        meta = doc.metadata or {}
        result["title"] = (meta.get("title") or "").strip()
        result["author"] = (meta.get("author") or "").strip()

        pages: list[str] = []
        for page in doc:
            pages.append(page.get_text("text"))
        doc.close()

        text = "\n\n".join(pages)
        result["text"] = _clean(text)
        result["word_count"] = _word_count(result["text"])
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"PDF parse error: {exc}"
    return result


def _parse_docx(path: str) -> dict:
    result = dict(_RESULT_TEMPLATE)
    try:
        from docx import Document
        from docx.opc.exceptions import PackageNotFoundError
    except ImportError:
        result["error"] = "python-docx is not installed. Run: pip install python-docx"
        return result

    try:
        doc = Document(path)

        # Try to get title from core properties
        try:
            props = doc.core_properties
            result["title"] = (props.title or "").strip()
            result["author"] = (props.author or "").strip()
        except Exception:  # noqa: BLE001
            pass

        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        text = "\n\n".join(paragraphs)
        result["text"] = _clean(text)
        result["word_count"] = _word_count(result["text"])
    except PackageNotFoundError:
        result["error"] = "Invalid or corrupted DOCX file."
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"DOCX parse error: {exc}"
    return result


def _parse_epub(path: str) -> dict:
    result = dict(_RESULT_TEMPLATE)
    try:
        import ebooklib
        from ebooklib import epub
    except ImportError:
        result["error"] = "ebooklib is not installed. Run: pip install ebooklib"
        return result

    try:
        from html.parser import HTMLParser

        class _StripHTML(HTMLParser):
            def __init__(self):
                super().__init__()
                self._parts: list[str] = []

            def handle_data(self, data: str) -> None:
                self._parts.append(data)

            def get_text(self) -> str:
                return " ".join(self._parts)

        book = epub.read_epub(path)

        # Metadata
        titles = book.get_metadata("DC", "title")
        if titles:
            result["title"] = str(titles[0][0]).strip()
        authors = book.get_metadata("DC", "creator")
        if authors:
            result["author"] = str(authors[0][0]).strip()

        parts: list[str] = []
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                html = item.get_content().decode("utf-8", errors="replace")
                parser = _StripHTML()
                parser.feed(html)
                chunk = parser.get_text().strip()
                if chunk:
                    parts.append(chunk)

        text = "\n\n".join(parts)
        result["text"] = _clean(text)
        result["word_count"] = _word_count(result["text"])
    except Exception as exc:  # noqa: BLE001
        result["error"] = f"EPUB parse error: {exc}"
    return result


def _parse_txt(path: str) -> dict:
    result = dict(_RESULT_TEMPLATE)
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252", "iso-8859-1"]
    text = None
    for enc in encodings:
        try:
            with open(path, "r", encoding=enc, errors="strict") as fh:
                text = fh.read()
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if text is None:
        # Last resort: read with replacement
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()

    result["text"] = _clean(text)
    result["word_count"] = _word_count(result["text"])
    return result


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def parse_file(path: str, filename: str) -> dict:
    """
    Detect file type from *filename* extension and parse *path*.
    Returns a dict with keys: text, title, author, word_count, error.
    """
    result = dict(_RESULT_TEMPLATE)
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".pdf":
        result = _parse_pdf(path)
    elif ext == ".docx":
        result = _parse_docx(path)
    elif ext in (".epub",):
        result = _parse_epub(path)
    elif ext == ".txt":
        result = _parse_txt(path)
    else:
        result["error"] = f"Unsupported file type: '{ext}'. Supported: PDF, DOCX, EPUB, TXT"

    # Fall back to filename stem as title if none was extracted
    if not result.get("title"):
        stem = os.path.splitext(os.path.basename(filename))[0]
        result["title"] = stem.replace("_", " ").replace("-", " ").strip()

    return result
