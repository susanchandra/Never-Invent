"""
ingestion/models.py — Core data models and exceptions for raw document ingestion.

Design contracts:
- Ingestion never infers meaning; it only records what was extracted.
- Every character position is preserved to enable auditability.
- Source spans reference the original document bytes, not normalised text.
- Missing metadata fields are None, never fabricated.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class IngestionError(Exception):
    """Raised for unrecoverable ingestion failures across all document types."""


class DocumentType(str, Enum):
    """Supported ingestion document types."""

    PDF = "pdf"
    TXT = "txt"
    UNKNOWN = "unknown"


class SourceSpan(BaseModel):
    """
    A contiguous span of text extracted from a source document.

    char_start and char_end refer to character offsets within the
    concatenated full_text of the parent RawDocument, NOT within the page.
    page_char_start / page_char_end are offsets within the page text, when
    available.
    """

    page_number: Optional[int] = Field(
        default=None,
        description="1-based page number. None if not determinable.",
        ge=1,
    )
    char_start: int = Field(
        description="Character offset (inclusive) in the full document text.",
        ge=0,
    )
    char_end: int = Field(
        description="Character offset (exclusive) in the full document text.",
        ge=0,
    )
    page_char_start: Optional[int] = Field(
        default=None,
        description="Character offset within the page text. None if not available.",
        ge=0,
    )
    page_char_end: Optional[int] = Field(
        default=None,
        description="Character offset within the page text. None if not available.",
        ge=0,
    )
    text: str = Field(description="The extracted text at this span (verbatim, unmodified).")

    @field_validator("char_end")
    @classmethod
    def end_after_start(cls, char_end: int, info) -> int:
        """char_end must be >= char_start."""
        char_start = info.data.get("char_start", 0)
        if char_end < char_start:
            raise ValueError(
                f"char_end ({char_end}) must be >= char_start ({char_start})"
            )
        return char_end

    @property
    def length(self) -> int:
        """Number of characters in this span."""
        return self.char_end - self.char_start

    def __repr__(self) -> str:
        snippet = self.text[:40].replace("\n", "\\n")
        return (
            f"SourceSpan(page={self.page_number}, "
            f"chars={self.char_start}:{self.char_end}, "
            f"text={snippet!r}...)"
        )


class ExtractionWarning(BaseModel):
    """
    Records a non-fatal issue encountered during extraction.
    """

    code: str = Field(description="Short machine-readable warning code.")
    message: str = Field(description="Human-readable description.")
    page_number: Optional[int] = Field(default=None, ge=1)

    def __str__(self) -> str:
        page_info = f" (page {self.page_number})" if self.page_number else ""
        return f"[{self.code}]{page_info} {self.message}"


class RawDocument(BaseModel):
    """
    The output of a single document ingestion run.
    """

    source_path: str = Field(description="Absolute path to the source file.")
    document_type: DocumentType = Field(description="Detected file type.")
    full_text: str = Field(description="Complete verbatim text of the document.")
    page_spans: list[SourceSpan] = Field(
        default_factory=list,
        description="One SourceSpan per page (PDF) or logical section (TXT).",
    )
    page_count: Optional[int] = Field(
        default=None,
        description="Total pages. None for plain-text documents.",
        ge=1,
    )
    warnings: list[ExtractionWarning] = Field(
        default_factory=list,
        description="Non-fatal issues encountered during extraction.",
    )
    title: Optional[str] = None
    author: Optional[str] = None
    creation_date: Optional[str] = None
    file_size_bytes: Optional[int] = Field(default=None, ge=0)

    @property
    def is_empty(self) -> bool:
        """True when the document yielded no extractable text."""
        return not self.full_text.strip()

    @property
    def has_warnings(self) -> bool:
        return len(self.warnings) > 0

    def get_span_at(self, char_pos: int) -> Optional[SourceSpan]:
        """
        Return the page span that contains the given character position.
        """
        for span in self.page_spans:
            if span.char_start <= char_pos < span.char_end:
                return span
        return None

    def get_text_slice(self, char_start: int, char_end: int) -> str:
        """Return a substring of full_text safely, clamped to valid range."""
        start = max(0, char_start)
        end = min(len(self.full_text), char_end)
        return self.full_text[start:end]

    def __repr__(self) -> str:
        return (
            f"RawDocument(path={Path(self.source_path).name!r}, "
            f"type={self.document_type.value}, "
            f"pages={self.page_count}, "
            f"chars={len(self.full_text)}, "
            f"warnings={len(self.warnings)})"
        )
