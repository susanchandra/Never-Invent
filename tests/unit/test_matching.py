"""
Unit tests for evidence-grounded candidate-job matching and dealbreakers.
"""

import pytest

from neverinvent.ingestion.models import SourceSpan
from neverinvent.jobs.models import JobDescription, JobSource
from neverinvent.matching import EvidenceGroundedMatcher, SkillMatchStatus
from neverinvent.parsing.models import (
    CandidateProfile,
    Education,
    SkillItem,
    WorkExperience,
)


@pytest.fixture
def sample_candidate() -> CandidateProfile:
    return CandidateProfile(
        candidate_name="Alice Smith",
        skills=[
            SkillItem(
                name="python",
                original_text="Python",
                source_span=SourceSpan(char_start=10, char_end=16, text="Python"),
            ),
            SkillItem(
                name="pytorch",
                original_text="PyTorch",
                source_span=SourceSpan(char_start=18, char_end=25, text="PyTorch"),
            ),
            SkillItem(name="kubernetes", original_text="k8s"),
        ],
        experience=[
            WorkExperience(
                company="Google",
                original_company_text="Google",
                title="Senior ML Engineer",
                start_date="2021-01",
                end_date="2024-01",
                duration_months=36,
            ),
            WorkExperience(
                company="Meta",
                original_company_text="Meta",
                title="ML Engineer",
                start_date="2019-01",
                end_date="2020-12",
                duration_months=24,
            ),
        ],
        education=[
            Education(
                institution="Stanford University",
                original_institution_text="Stanford University",
                degree="Bachelor of Science",
            )
        ],
    )


def test_matching_skills_and_evidence(sample_candidate):
    job = JobDescription(
        job_id="job_001",
        title="ML Engineer",
        normalized_title="ml engineer",
        company="AI Labs",
        raw_description="Python & PyTorch engineer with Go experience.",
        required_skills=["python", "pytorch"],
        preferred_skills=["kubernetes", "go"],
        source_type=JobSource.SYNTHETIC,
    )

    matcher = EvidenceGroundedMatcher()
    breakdown = matcher.match(sample_candidate, job)

    assert breakdown.supported_required_count == 2
    assert breakdown.total_required_count == 2

    # Required skills all supported
    assert all(item.status == SkillMatchStatus.SUPPORTED for item in breakdown.required_skills_match)
    py_match = next(i for i in breakdown.required_skills_match if i.skill_name == "python")
    assert py_match.supporting_evidence is not None
    assert py_match.supporting_evidence.evidence_text == "Python"
    assert py_match.supporting_evidence.source_span is not None

    # Preferred skills: k8s alias matches kubernetes; go is missing
    assert breakdown.supported_preferred_count == 1
    assert breakdown.total_preferred_count == 2
    k8s_match = next(i for i in breakdown.preferred_skills_match if i.skill_name == "kubernetes")
    assert k8s_match.status == SkillMatchStatus.SUPPORTED
    go_match = next(i for i in breakdown.preferred_skills_match if i.skill_name == "go")
    assert go_match.status == SkillMatchStatus.MISSING

    # Grounded score calculation: (2/2)*0.70 + (1/2)*0.30 = 0.70 + 0.15 = 0.85
    assert breakdown.grounded_match_score == 0.85
    assert breakdown.dealbreaker_result.passed is True


def test_dealbreaker_experience_pass_and_fail(sample_candidate):
    matcher = EvidenceGroundedMatcher()

    # Candidate has 36 + 24 = 60 months = 5.0 years experience
    # Job requires 4 years -> PASS
    job_pass = JobDescription(
        job_id="job_p",
        title="Senior Engineer",
        normalized_title="senior engineer",
        company="Co",
        raw_description="...",
        min_years_experience=4,
        source_type=JobSource.SYNTHETIC,
    )
    res_pass = matcher.match(sample_candidate, job_pass)
    assert res_pass.dealbreaker_result.passed is True

    # Job requires 10 years -> FAIL
    job_fail = JobDescription(
        job_id="job_f",
        title="Principal Engineer",
        normalized_title="principal engineer",
        company="Co",
        raw_description="...",
        min_years_experience=10,
        source_type=JobSource.SYNTHETIC,
    )
    res_fail = matcher.match(sample_candidate, job_fail)
    assert res_fail.dealbreaker_result.passed is False
    assert len(res_fail.dealbreaker_result.failed_reasons) > 0


def test_dealbreaker_missing_field_does_not_fail():
    # If candidate has no documented education, do not fail
    cand_no_edu = CandidateProfile(candidate_name="Bob")
    job_req_edu = JobDescription(
        job_id="job_edu",
        title="Researcher",
        normalized_title="researcher",
        company="Co",
        raw_description="...",
        education_level="Master of Science",
        source_type=JobSource.SYNTHETIC,
    )
    matcher = EvidenceGroundedMatcher()
    res = matcher.match(cand_no_edu, job_req_edu)
    # A missing resume field is not assumed ineligible
    assert res.dealbreaker_result.passed is True


def test_matching_empty_skill_categories(sample_candidate):
    matcher = EvidenceGroundedMatcher()

    # Case 1: Job has required skills only (no preferred skills)
    job_req_only = JobDescription(
        job_id="job_req_only",
        title="ML Engineer",
        normalized_title="ml engineer",
        company="Co",
        raw_description="...",
        required_skills=["python", "pytorch"],
        preferred_skills=[],
        source_type=JobSource.SYNTHETIC,
    )
    # Alice has python and pytorch -> 2/2 required -> 100% score (not capped at 70%)
    res1 = matcher.match(sample_candidate, job_req_only)
    assert res1.grounded_match_score == 1.0

    # Case 2: Job has preferred skills only (no required skills)
    job_pref_only = JobDescription(
        job_id="job_pref_only",
        title="ML Engineer",
        normalized_title="ml engineer",
        company="Co",
        raw_description="...",
        required_skills=[],
        preferred_skills=["pytorch"],
        source_type=JobSource.SYNTHETIC,
    )
    # Alice has pytorch -> 1/1 preferred -> 100% score (not capped at 30%)
    res2 = matcher.match(sample_candidate, job_pref_only)
    assert res2.grounded_match_score == 1.0

    # Case 3: Job has neither category populated -> insufficient information, 0.0 score
    job_empty = JobDescription(
        job_id="job_empty",
        title="General Role",
        normalized_title="general role",
        company="Co",
        raw_description="...",
        required_skills=[],
        preferred_skills=[],
        source_type=JobSource.SYNTHETIC,
    )
    res3 = matcher.match(sample_candidate, job_empty)
    assert res3.grounded_match_score == 0.0
    assert "Insufficient job information" in res3.explanation
