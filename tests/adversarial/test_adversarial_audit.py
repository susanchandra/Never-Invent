"""
tests/adversarial/test_adversarial_audit.py — Adversarial regression tests verifying system hardening.

Probes verified & hardened:
1. Approval integrity: Unsupported proposals and unverified final_text edits are strictly rejected (HTTP 400).
   Ambiguous proposals require explicit justification notes. Duplicate decisions are forbidden.
2. Word boundary matching: 'java' does not match 'javascript'; 'rust' does not match 'frustrated'.
3. Overlapping tenures: Concurrent employment intervals are merged; duration inflation is caught.
4. Matcher empty category: 0-skill candidate on empty-preferred job receives 0.00% match score.
5. Numerical context disambiguation: Unrelated % metrics are classified as AMBIGUOUS, not false-blocked as UNSUPPORTED.
6. Upload size ceiling: Files exceeding 10 MB are rejected with HTTP 413.
"""

import io
import pytest
from fastapi.testclient import TestClient

from neverinvent.api.main import app
from neverinvent.claims.models import Claim, ClaimType
from neverinvent.generation.models import GenerationType
from neverinvent.jobs.models import JobDescription, JobSource
from neverinvent.matching.matcher import EvidenceGroundedMatcher
from neverinvent.parsing.models import (
    CandidateProfile,
    MetricClaim,
    SkillItem,
    WorkExperience,
)
from neverinvent.persistence import init_db
from neverinvent.verification.models import Verdict
from neverinvent.verification.strategies.normalized_match import verify_normalized_match
from neverinvent.verification.strategies.numerical import verify_numerical
from neverinvent.verification.strategies.temporal import verify_temporal
from neverinvent.workflow.models import ApprovalDecision, ProposalStatus, VerifiedProposal


@pytest.fixture(scope="module")
def client():
    init_db("sqlite:///:memory:")
    with TestClient(app) as c:
        yield c


def test_adversarial_approval_integrity_and_tamper_rejection(client):
    """
    REGRESSION GUARD 1: Unsupported proposals cannot be approved; unverified final_text edits are rejected.
    """
    resume_text = (
        "Alice Smith\nSkills\nPython\n"
        "Work Experience\nGoogle\nJan 2021 - Present\n"
        "- Designed search ranking models improving relevance by 18%.\n"
    )
    up_resp = client.post("/api/resume/upload", data={"raw_text_input": resume_text})
    cid = up_resp.json()["candidate_id"]
    job_id = client.get("/api/jobs").json()["jobs"][0]["job_id"]

    # Generate proposal with fabricated metric (40%)
    fab_resp = client.post(
        "/api/verify/generate",
        json={
            "candidate_id": cid,
            "job_id": job_id,
            "generation_type": "resume_bullet_suggestion",
            "mode": "fabricated_metric",
            "target_bullet": "Designed search ranking models improving relevance by 18%.",
        },
    )
    fab_prop = fab_resp.json()["proposal"]
    assert fab_prop["status"] == ProposalStatus.CONTAINS_UNSUPPORTED.value
    assert fab_prop["unsupported_count"] >= 1

    # 1. Attempt to approve the UNSUPPORTED proposal directly -> MUST BE REJECTED WITH 400
    bypass_resp = client.post(
        "/api/approve/decision",
        json={
            "proposal_id": fab_prop["proposal_id"],
            "decision": "APPROVED",
            "final_text": fab_prop["proposed_text"],
            "notes": "Trying to approve unsupported claim",
        },
    )
    assert bypass_resp.status_code == 400
    assert "UNSUPPORTED" in bypass_resp.json()["detail"]

    # 2. Attempt to sneak in arbitrary unverified text -> MUST BE REJECTED WITH 400
    tamper_resp = client.post(
        "/api/approve/decision",
        json={
            "proposal_id": fab_prop["proposal_id"],
            "decision": "REJECTED",
            "final_text": "Different unverified text submitted without reverification",
            "notes": "Tampered text",
        },
    )
    assert tamper_resp.status_code == 400
    assert "Submitted final_text does not match" in tamper_resp.json()["detail"]

    # 3. Legitimate rejection is accepted
    reject_resp = client.post(
        "/api/approve/decision",
        json={
            "proposal_id": fab_prop["proposal_id"],
            "decision": "REJECTED",
            "final_text": fab_prop["proposed_text"],
            "notes": "Candidate rejected fabricated bullet",
        },
    )
    assert reject_resp.status_code == 200
    assert reject_resp.json()["decision"] == "REJECTED"

    # 4. Duplicate decision on finalized proposal -> MUST BE REJECTED WITH 400
    dup_resp = client.post(
        "/api/approve/decision",
        json={
            "proposal_id": fab_prop["proposal_id"],
            "decision": "REJECTED",
            "final_text": fab_prop["proposed_text"],
            "notes": "Trying to finalize again",
        },
    )
    assert dup_resp.status_code == 400
    assert "already been finalized" in dup_resp.json()["detail"]


def test_adversarial_substring_match_prevented():
    """
    REGRESSION GUARD 2: Unanchored substring matching is prevented by word-boundary checks.
    """
    profile = CandidateProfile(
        candidate_name="Bob",
        skills=[],
        experience=[
            WorkExperience(
                company="TechCo",
                original_company_text="TechCo",
                responsibilities=["Experienced with JavaScript; frustrated with legacy tools."],
            )
        ],
    )
    # 1. Candidate knows JavaScript, NOT Java
    java_claim = Claim(
        claim_id="c_java",
        original_claim_text="Java",
        normalized_value="java",
        claim_type=ClaimType.SKILL,
        extraction_method="test",
        source_text="Proficient in Java.",
    )
    res_java = verify_normalized_match(java_claim, profile)
    assert res_java.verdict != Verdict.SUPPORTED
    assert res_java.verdict == Verdict.AMBIGUOUS

    # 2. Candidate wrote 'frustrated', NOT Rust
    rust_claim = Claim(
        claim_id="c_rust",
        original_claim_text="Rust",
        normalized_value="rust",
        claim_type=ClaimType.SKILL,
        extraction_method="test",
        source_text="Proficient in Rust.",
    )
    res_rust = verify_normalized_match(rust_claim, profile)
    assert res_rust.verdict != Verdict.SUPPORTED
    assert res_rust.verdict == Verdict.AMBIGUOUS


def test_adversarial_overlapping_tenures_merged():
    """
    REGRESSION GUARD 3: Overlapping calendar intervals are merged to prevent concurrent double counting.
    """
    # Candidate worked 2 concurrent roles between Jan 2021 and Dec 2022 (24 calendar months total)
    profile = CandidateProfile(
        candidate_name="Carol",
        experience=[
            WorkExperience(
                company="Company A",
                original_company_text="Company A",
                start_date="2021-01",
                end_date="2022-12",
                duration_months=24,
            ),
            WorkExperience(
                company="Company B (Concurrent)",
                original_company_text="Company B",
                start_date="2021-01",
                end_date="2022-12",
                duration_months=24,
            ),
        ],
    )

    # Claim 4 years of experience (48 months vs 24 actual calendar months)
    claim_4yrs = Claim(
        claim_id="c_4y",
        original_claim_text="4 years of experience",
        normalized_value="4 years",
        claim_type=ClaimType.DURATION,
        numeric_value=4.0,
        unit="years",
        extraction_method="test",
        source_text="Has 4 years of experience.",
    )
    res = verify_temporal(claim_4yrs, profile)
    # Correctly identified as UNSUPPORTED exaggeration
    assert res.verdict == Verdict.UNSUPPORTED


def test_adversarial_matching_score_empty_preferred_category():
    """
    REGRESSION GUARD 4: Empty preferred skills category does not award free score to 0-skill candidate.
    """
    candidate_no_skills = CandidateProfile(candidate_name="Dave", skills=[])
    job_no_pref = JobDescription(
        job_id="job_hard",
        title="Senior C++ Dev",
        normalized_title="senior c++ dev",
        company="Co",
        raw_description="...",
        required_skills=["c++", "cuda", "cmake"],
        preferred_skills=[],
        source_type=JobSource.SYNTHETIC,
    )
    matcher = EvidenceGroundedMatcher()
    breakdown = matcher.match(candidate_no_skills, job_no_pref)

    # 0/3 required skills on empty preferred job gets 0.00% score (not 30%)
    assert breakdown.grounded_match_score == 0.00


def test_adversarial_numerical_context_disambiguation():
    """
    REGRESSION GUARD 5: Unrelated % metric is classified as AMBIGUOUS, avoiding false contradiction.
    """
    profile = CandidateProfile(
        candidate_name="Eve",
        metrics=[
            MetricClaim(
                raw_metric_text="improved search latency by 18%",
                quantity=18.0,
                unit="%",
                context="improved search latency by 18%",
            )
        ],
    )
    # Claim mentions code coverage (90%) - not search latency
    claim = Claim(
        claim_id="c_cov",
        original_claim_text="improved code coverage to 90%",
        normalized_value="90%",
        claim_type=ClaimType.METRIC,
        numeric_value=90.0,
        unit="%",
        extraction_method="test",
        source_text="improved code coverage to 90%",
    )
    res = verify_numerical(claim, profile)
    # Correctly marked AMBIGUOUS (no matching or contradicting evidence), NOT false UNSUPPORTED!
    assert res.verdict == Verdict.AMBIGUOUS


def test_adversarial_oversized_upload_rejected(client):
    """
    REGRESSION GUARD 6: File uploads exceeding 10 MB are rejected with HTTP 413.
    """
    # 10.5 MB payload
    large_content = b"x" * (10 * 1024 * 1024 + 512 * 1024)
    file_payload = ("large_resume.txt", io.BytesIO(large_content), "text/plain")

    resp = client.post("/api/resume/upload", files={"file": file_payload})
    assert resp.status_code == 413
    assert "exceeds maximum permitted limit" in resp.json()["detail"]
