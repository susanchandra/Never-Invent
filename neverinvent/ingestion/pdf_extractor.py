"""
ingestion/pdf_extractor.py — PDF text extraction with source provenance.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import pymupdf

from neverinvent.ingestion.models import (
    DocumentType,
    ExtractionWarning,
    IngestionError,
    RawDocument,
    SourceSpan,
)

logger = logging.getLogger(__name__)


def _extract_metadata(doc: pymupdf.Document) -> dict:
    meta = doc.metadata or {}

    def _clean(value: Optional[str]) -> Optional[str]:
        if not value or not value.strip():
            return None
        return value.strip()

    return {
        "title": _clean(meta.get("title")),
        "author": _clean(meta.get("author")),
        "creation_date": _clean(meta.get("creationDate")),
    }


def _extract_page_text_pymupdf(page: pymupdf.Page) -> str:
    try:
        return page.get_text("text") or ""
    except Exception as exc:
        logger.warning("PyMuPDF page text extraction failed: %s", exc)
        return ""


def _extract_page_text_pdfplumber(path: str, page_index: int) -> str:
    try:
        import pdfplumber

        with pdfplumber.open(path) as pdf:
            if page_index >= len(pdf.pages):
                return ""
            page = pdf.pages[page_index]
            text = page.extract_text() or ""
            return text
    except Exception as exc:
        logger.warning("pdfplumber fallback failed on page %d: %s", page_index, exc)
        return ""


def extract_pdf(file_path: str | Path) -> RawDocument:
    path = Path(file_path).resolve()

    if not path.exists():
        raise IngestionError(f"File not found: {path}")
    if not path.is_file():
        raise IngestionError(f"Not a regular file: {path}")
    if path.stat().st_size == 0:
        raise IngestionError(f"File is empty (0 bytes): {path}")

    file_size = path.stat().st_size

    try:
        doc = pymupdf.open(str(path))
    except Exception as exc:
        raise IngestionError(f"Cannot open PDF '{path.name}': {exc}") from exc

    if doc.is_encrypted:
        doc.close()
        raise IngestionError(
            f"PDF is encrypted/password-protected: {path.name}. "
            "Cannot extract text without the password."
        )

    page_count = len(doc)
    if page_count == 0:
        doc.close()
        raise IngestionError(f"PDF has no pages: {path.name}")

    metadata = _extract_metadata(doc)
    warnings: list[ExtractionWarning] = []
    page_spans: list[SourceSpan] = []
    text_parts: list[str] = []
    char_cursor = 0

    for page_index in range(page_count):
        page_number = page_index + 1
        page = doc[page_index]

        page_text = _extract_page_text_pymupdf(page)

        if not page_text.strip():
            page_text = _extract_page_text_pdfplumber(str(path), page_index)
            if not page_text.strip():
                warnings.append(
                    ExtractionWarning(
                        code="EMPTY_PAGE",
                        message=f"Page {page_number} yielded no extractable text.",
                        page_number=page_number,
                    )
                )

        span = SourceSpan(
            page_number=page_number,
            char_start=char_cursor,
            char_end=char_cursor + len(page_text),
            page_char_start=0,
            page_char_end=len(page_text),
            text=page_text,
        )
        page_spans.append(span)
        text_parts.append(page_text)
        char_cursor += len(page_text)

    doc.close()
    full_text = "".join(text_parts)

    if not full_text.strip():
        warnings.append(
            ExtractionWarning(
                code="EMPTY_DOCUMENT",
                message="No extractable text found in the entire document.",
            )
        )

    return RawDocument(
        source_path=str(path),
        document_type=DocumentType.PDF,
        full_text=full_text,
        page_spans=page_spans,
        page_count=page_count,
        warnings=warnings,
        file_size_bytes=file_size,
        **metadata,
    )
