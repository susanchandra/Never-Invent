"""
Unit tests for ingestion module (PDF and TXT extraction, source provenance).
"""

import pytest
from pathlib import Path
import pymupdf

from neverinvent.ingestion import (
    DocumentType,
    IngestionError,
    RawDocument,
    SourceSpan,
    extract_pdf,
    extract_txt,
)


def test_source_span_validation():
    span = SourceSpan(
        page_number=1,
        char_start=0,
        char_end=10,
        text="Sample text",
    )
    assert span.length == 10
    assert span.page_number == 1

    with pytest.raises(ValueError):
        SourceSpan(
            page_number=1,
            char_start=15,
            char_end=5,
            text="Invalid span",
        )


def test_extract_txt_valid(tmp_path: Path):
    sample_text = "Jane Doe\nSenior AI Engineer\nPython, PyTorch, FAISS\n"
    txt_file = tmp_path / "resume.txt"
    txt_file.write_text(sample_text, encoding="utf-8")

    doc = extract_txt(txt_file)
    assert doc.document_type == DocumentType.TXT
    assert doc.full_text == sample_text
    assert len(doc.page_spans) == 1
    assert doc.page_spans[0].text == sample_text
    assert not doc.is_empty
    assert len(doc.warnings) == 0


def test_extract_txt_unicode(tmp_path: Path):
    unicode_text = "Hélène Müller — Ingénieur en Intelligence Artificielle: 🚀 © 2026"
    txt_file = tmp_path / "resume_unicode.txt"
    txt_file.write_text(unicode_text, encoding="utf-8")

    doc = extract_txt(txt_file)
    assert doc.full_text == unicode_text
    assert doc.page_spans[0].text == unicode_text


def test_extract_txt_empty(tmp_path: Path):
    txt_file = tmp_path / "empty.txt"
    txt_file.write_text("", encoding="utf-8")

    with pytest.raises(IngestionError, match="empty"):
        extract_txt(txt_file)


def test_extract_txt_whitespace_only(tmp_path: Path):
    txt_file = tmp_path / "whitespace.txt"
    txt_file.write_text("   \n\n\t  ", encoding="utf-8")

    doc = extract_txt(txt_file)
    assert doc.is_empty
    assert any(w.code == "EMPTY_DOCUMENT" for w in doc.warnings)


def test_extract_non_existent():
    with pytest.raises(IngestionError, match="not found"):
        extract_txt("non_existent_file_path.txt")
    with pytest.raises(IngestionError, match="not found"):
        extract_pdf("non_existent_file_path.pdf")


def test_extract_pdf_synthetic_multipage(tmp_path: Path):
    pdf_path = tmp_path / "candidate_cv.pdf"
    doc = pymupdf.open()

    p1 = doc.new_page()
    p1.insert_text((50, 72), "John Doe\nStaff Machine Learning Engineer\nGoogle 2020-2024")

    p2 = doc.new_page()
    p2.insert_text((50, 72), "Education:\nB.S. in Computer Science, Stanford University 2016-2020")

    doc.save(str(pdf_path))
    doc.close()

    raw_doc = extract_pdf(pdf_path)
    assert raw_doc.document_type == DocumentType.PDF
    assert raw_doc.page_count == 2
    assert len(raw_doc.page_spans) == 2
    assert "John Doe" in raw_doc.page_spans[0].text
    assert "Stanford" in raw_doc.page_spans[1].text

    # Check provenance invariant: full_text slice matches page span char_start/char_end
    for span in raw_doc.page_spans:
        slice_text = raw_doc.get_text_slice(span.char_start, span.char_end)
        assert slice_text == span.text


def test_extract_pdf_malformed(tmp_path: Path):
    bad_pdf = tmp_path / "corrupted.pdf"
    bad_pdf.write_bytes(b"%PDF-1.4\nJUNK DATA THAT IS NOT A VALID PDF\n%%EOF")

    with pytest.raises(IngestionError):
        extract_pdf(bad_pdf)
