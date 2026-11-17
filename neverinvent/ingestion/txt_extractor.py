"""
ingestion/txt_extractor.py — Plain text document ingestion with character and line provenance.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from neverinvent.ingestion.models import (
    DocumentType,
    ExtractionWarning,
    IngestionError,
    RawDocument,
    SourceSpan,
)

logger = logging.getLogger(__name__)


def extract_txt(file_path: str | Path, encoding: str = "utf-8") -> RawDocument:
    path = Path(file_path).resolve()

    if not path.exists():
        raise IngestionError(f"File not found: {path}")
    if not path.is_file():
        raise IngestionError(f"Not a regular file: {path}")
    if path.stat().st_size == 0:
        raise IngestionError(f"File is empty (0 bytes): {path}")

    file_size = path.stat().st_size
    warnings: list[ExtractionWarning] = []

    content: Optional[str] = None
    encodings_to_try = [encoding, "utf-8-sig", "utf-8", "latin-1", "cp1252"]

    for enc in encodings_to_try:
        try:
            with open(path, "r", encoding=enc) as f:
                content = f.read()
            if enc != encoding and enc not in ("utf-8", "utf-8-sig"):
                warnings.append(
                    ExtractionWarning(
                        code="ENCODING_FALLBACK",
                        message=f"Decoded with fallback encoding '{enc}' instead of requested '{encoding}'",
                    )
                )
            break
        except (UnicodeDecodeError, LookupError):
            continue

    if content is None:
        raise IngestionError(f"Failed to decode text file '{path.name}' with standard encodings.")

    span = SourceSpan(
        page_number=1,
        char_start=0,
        char_end=len(content),
        page_char_start=0,
        page_char_end=len(content),
        text=content,
    )

    if not content.strip():
        warnings.append(
            ExtractionWarning(
                code="EMPTY_DOCUMENT",
                message="Document contains only whitespace or blank lines.",
                page_number=1,
            )
        )

    return RawDocument(
        source_path=str(path),
        document_type=DocumentType.TXT,
        full_text=content,
        page_spans=[span],
        page_count=1,
        warnings=warnings,
        file_size_bytes=file_size,
        title=path.stem,
    )
