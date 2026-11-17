"""
Unit tests for claims models and extractor.
"""

import pytest

from neverinvent.claims.extractor import ClaimExtractor
from neverinvent.claims.models import Claim, ClaimType, Evidence, EvidenceBundle
from neverinvent.ingestion.models import SourceSpan
from neverinvent.parsing.models import ExtractionStatus


def test_claim_id_deterministic():
    id1 = Claim.make_id("Experienced with Python", ClaimType.SKILL)
    id2 = Claim.make_id("Experienced with Python", ClaimType.SKILL)
    id3 = Claim.make_id("Experienced with Python", ClaimType.JOB_TITLE)
    assert id1 == id2
    assert id1 != id3


def test_evidence_bundle():
    claim = Claim(
        claim_id=Claim.make_id("Python", ClaimType.SKILL),
        original_claim_text="Python",
        normalized_value="python",
        claim_type=ClaimType.SKILL,
        extraction_method="test",
        source_text="Python",
    )
    ev = Evidence(
        evidence_id=Evidence.make_id("Python", "skills"),
        evidence_text="Python",
        evidence_type="skill",
        profile_field="skills",
        source_span=SourceSpan(char_start=0, char_end=6, text="Python"),
    )
    bundle = EvidenceBundle(claim=claim, supporting=[ev])
    assert bundle.has_support is True
    assert bundle.has_contradiction is False


def test_extractor_skill_and_metric():
    extractor = ClaimExtractor()
    text = "Alice is proficient in Python and improved latency by 40%."
    claims = extractor.extract(text)

    types = {c.claim_type for c in claims}
    assert ClaimType.SKILL in types
    assert ClaimType.METRIC in types

    skill_claim = next(c for c in claims if c.claim_type == ClaimType.SKILL)
    assert skill_claim.normalized_value == "python"

    metric_claim = next(c for c in claims if c.claim_type == ClaimType.METRIC)
    assert metric_claim.numeric_value == 40.0
    assert metric_claim.unit == "%"


def test_extractor_employer_and_duration():
    extractor = ClaimExtractor()
    text = "Worked at Google for 5 years of experience."
    claims = extractor.extract(text)

    types = {c.claim_type for c in claims}
    assert ClaimType.EMPLOYER in types
    assert ClaimType.DURATION in types

    emp_claim = next(c for c in claims if c.claim_type == ClaimType.EMPLOYER)
    assert "google" in emp_claim.normalized_value

    dur_claim = next(c for c in claims if c.claim_type == ClaimType.DURATION)
    assert dur_claim.numeric_value == 5.0
    assert "year" in dur_claim.unit


def test_extractor_education_and_cert():
    extractor = ClaimExtractor()
    text = "Holds a Bachelor's in Computer Science and is AWS Certified Solutions Architect."
    claims = extractor.extract(text)

    types = {c.claim_type for c in claims}
    assert ClaimType.EDUCATION in types
    assert ClaimType.CERTIFICATION in types


def test_extractor_empty_and_unclear():
    extractor = ClaimExtractor()
    assert extractor.extract("") == []
    assert extractor.extract("   ") == []

    # Responsibility fallback
    claims = extractor.extract("Led cross-functional engineering initiatives across multiple teams.")
    assert len(claims) == 1
    assert claims[0].claim_type == ClaimType.RESPONSIBILITY
    assert claims[0].extraction_confidence == ExtractionStatus.UNCERTAIN
