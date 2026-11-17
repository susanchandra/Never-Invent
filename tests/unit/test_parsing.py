"""
Unit tests for parsing module (normalizers and ProfileParser).
"""

from pathlib import Path
import pytest

from neverinvent.ingestion.models import DocumentType, RawDocument, SourceSpan
from neverinvent.parsing import (
    CandidateProfile,
    ProfileParser,
    calculate_duration_months,
    normalize_date,
    normalize_skill,
    parse_numeric_metric,
)


def test_normalize_skill():
    assert normalize_skill("PyThon") == "python"
    assert normalize_skill("k8s") == "kubernetes"
    assert normalize_skill("React.js") == "react"
    assert normalize_skill("AWS") == "amazon web services"
    assert normalize_skill("Golang") == "go"
    assert normalize_skill("unknown_tool_xyz") == "unknown_tool_xyz"


def test_normalize_date():
    assert normalize_date("January 2020") == "2020-01"
    assert normalize_date("2021") == "2021-01"
    assert normalize_date("04/2022") == "2022-04"
    assert normalize_date("Present") == "Present"
    assert normalize_date("current") == "Present"
    assert normalize_date("not a date") is None


def test_calculate_duration_months():
    # 2020-01 to 2022-01 = 24 months
    assert calculate_duration_months("2020-01", "2022-01") == 24
    # Present uses fixed 2026-11
    assert calculate_duration_months("2025-11", "Present") == 12
    # Invalid dates
    assert calculate_duration_months("invalid", "2022-01") is None
    assert calculate_duration_months(None, "2022-01") is None
    # End before start returns None
    assert calculate_duration_months("2024-01", "2020-01") is None


def test_parse_numeric_metric():
    text = "Improved query performance by 45.5% and reduced latency by 120ms."
    metrics = parse_numeric_metric(text)
    assert len(metrics) == 2
    assert (45.5, "%", "increase") in metrics
    assert (120.0, "ms", None) in metrics

    currency_text = "Generated $1.5M in cost savings and managed $500K budget."
    c_metrics = parse_numeric_metric(currency_text)
    assert len(c_metrics) == 2
    assert (1500000.0, "$", "total") in c_metrics
    assert (500000.0, "$", "total") in c_metrics


def test_profile_parser_comprehensive():
    resume_text = """Alice Smith
alice.smith@example.com | (555) 123-4567

Skills
Python, PyTorch, FAISS, Docker, Kubernetes, AWS

Work Experience
Google - Senior Machine Learning Engineer
Jan 2021 - Present
- Designed search ranking models improving relevance by 18%.
- Scaled inference service handling 500ms requests.

Meta - Machine Learning Engineer
Jan 2019 - Dec 2020
- Built data processing pipelines using Python and Spark.

Education
Stanford University
B.S. in Computer Science
2015 - 2019
"""
    raw_doc = RawDocument(
        source_path="alice_resume.txt",
        document_type=DocumentType.TXT,
        full_text=resume_text,
        page_spans=[
            SourceSpan(
                page_number=1,
                char_start=0,
                char_end=len(resume_text),
                text=resume_text,
            )
        ],
        page_count=1,
    )

    parser = ProfileParser()
    profile: CandidateProfile = parser.parse(raw_doc)

    assert profile.candidate_name == "Alice Smith"
    assert profile.email == "alice.smith@example.com"
    assert profile.phone == "(555) 123-4567"

    # Verify skills
    skill_names = [s.name for s in profile.skills]
    assert "python" in skill_names
    assert "pytorch" in skill_names
    assert "kubernetes" in skill_names
    assert "amazon web services" in skill_names

    # Check that skills have source spans
    py_skill = next(s for s in profile.skills if s.name == "python")
    assert py_skill.source_span is not None
    assert py_skill.source_span.text == "Python"
    assert raw_doc.full_text[py_skill.source_span.char_start : py_skill.source_span.char_end] == "Python"

    # Verify experience
    assert len(profile.experience) == 2
    exp1 = profile.experience[0]
    assert "Google" in exp1.company
    assert exp1.start_date == "2021-01"
    assert exp1.end_date == "Present"
    assert exp1.is_current is True
    assert exp1.duration_months is not None
    assert len(exp1.responsibilities) == 2

    exp2 = profile.experience[1]
    assert "Meta" in exp2.company
    assert exp2.start_date == "2019-01"
    assert exp2.end_date == "2020-12"
    assert exp2.duration_months == 23
    assert len(exp2.responsibilities) == 1

    # Verify education
    assert len(profile.education) >= 1
    assert any("Stanford" in ed.institution for ed in profile.education)

    # Verify metrics
    assert any(m.quantity == 18.0 and m.unit == "%" for m in profile.metrics)


def test_profile_parser_empty_doc():
    raw_doc = RawDocument(
        source_path="empty.txt",
        document_type=DocumentType.TXT,
        full_text="",
        page_spans=[],
        page_count=1,
    )
    parser = ProfileParser()
    profile = parser.parse(raw_doc)
    assert profile.candidate_name is None
    assert len(profile.skills) == 0
    assert len(profile.experience) == 0
    assert len(profile.metrics) == 0
