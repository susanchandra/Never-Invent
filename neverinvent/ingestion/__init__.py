"""
ingestion package — PDF and TXT extractors with source provenance.
"""

from neverinvent.ingestion.models import (
    DocumentType,
    ExtractionWarning,
    RawDocument,
    SourceSpan,
)
from neverinvent.ingestion.pdf_extractor import IngestionError, extract_pdf
from neverinvent.ingestion.txt_extractor import extract_txt

__all__ = [
    "DocumentType",
    "ExtractionWarning",
    "RawDocument",
    "SourceSpan",
    "IngestionError",
    "extract_pdf",
    "extract_txt",
]
