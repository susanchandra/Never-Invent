"""
Unit tests for deterministic verification engine and strategies.
"""

import pytest

from neverinvent.claims.models import Claim, ClaimType
from neverinvent.ingestion.models import SourceSpan
from neverinvent.parsing.models import (
    CandidateProfile,
    Education,
    MetricClaim,
    SkillItem,
    WorkExperience,
)
from neverinvent.verification import ClaimVerifier, Verdict, VerificationStrategy


@pytest.fixture
def sample_alice_profile() -> CandidateProfile:
    """Fixture matching Alice Smith's parsed profile from Phase 1."""
    return CandidateProfile(
        candidate_name="Alice Smith",
        email="alice.smith@example.com",
        phone="(555) 123-4567",
        skills=[
            SkillItem(name="python", original_text="Python"),
            SkillItem(name="pytorch", original_text="PyTorch"),
            SkillItem(name="kubernetes", original_text="Kubernetes"),
            SkillItem(name="amazon web services", original_text="AWS"),
            SkillItem(name="faiss", original_text="FAISS"),
        ],
        experience=[
            WorkExperience(
                company="Google",
                original_company_text="Google",
                title="Senior Machine Learning Engineer",
                original_title_text="Senior Machine Learning Engineer",
                start_date="2021-01",
                end_date="Present",
                is_current=True,
                duration_months=70,  # to Nov 2026
                responsibilities=[
                    "Designed search ranking models improving relevance by 18%.",
                    "Scaled inference service handling 500ms requests.",
                ],
            ),
            WorkExperience(
                company="Meta",
                original_company_text="Meta",
                title="Machine Learning Engineer",
                original_title_text="Machine Learning Engineer",
                start_date="2019-01",
                end_date="2020-12",
                is_current=False,
                duration_months=23,
                responsibilities=["Built data processing pipelines using Python and Spark."],
            ),
        ],
        education=[
            Education(
                institution="Stanford University",
                original_institution_text="Stanford University",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                start_date="2015-01",
                end_date="2019-01",
            )
        ],
        metrics=[
            MetricClaim(
                raw_metric_text="improving relevance by 18%",
                quantity=18.0,
                unit="%",
                direction="increase",
                context="Designed search ranking models improving relevance by 18%.",
            ),
            MetricClaim(
                raw_metric_text="handling 500ms requests",
                quantity=500.0,
                unit="ms",
                direction=None,
                context="Scaled inference service handling 500ms requests.",
            ),
        ],
    )


def test_exact_match(sample_alice_profile):
    verifier = ClaimVerifier()
    claim = Claim(
        claim_id=Claim.make_id("Python", ClaimType.SKILL),
        original_claim_text="Python",
        normalized_value="python",
        claim_type=ClaimType.SKILL,
        extraction_method="test",
        source_text="Alice knows Python.",
    )
    res = verifier.verify(claim, sample_alice_profile)
    assert res.final_verdict == Verdict.SUPPORTED
    assert res.primary_strategy in (VerificationStrategy.EXACT_MATCH, VerificationStrategy.NORMALIZED_MATCH)
    assert not res.requires_human_review


def test_alias_match(sample_alice_profile):
    verifier = ClaimVerifier()
    claim = Claim(
        claim_id=Claim.make_id("k8s", ClaimType.SKILL),
        original_claim_text="k8s",
        normalized_value="k8s",
        claim_type=ClaimType.SKILL,
        extraction_method="test",
        source_text="Expert in k8s.",
    )
    res = verifier.verify(claim, sample_alice_profile)
    assert res.final_verdict == Verdict.SUPPORTED
    assert res.primary_strategy == VerificationStrategy.ALIAS_MATCH


def test_numerical_match_and_inflation(sample_alice_profile):
    verifier = ClaimVerifier()

    # Faithful metric
    faithful_claim = Claim(
        claim_id=Claim.make_id("improved relevance by 18%", ClaimType.METRIC),
        original_claim_text="improved relevance by 18%",
        normalized_value="18%",
        claim_type=ClaimType.METRIC,
        numeric_value=18.0,
        unit="%",
        extraction_method="test",
        source_text="Designed search ranking models improving relevance by 18%.",
    )
    res1 = verifier.verify(faithful_claim, sample_alice_profile)
    assert res1.final_verdict == Verdict.SUPPORTED

    # Inflated metric: 18% -> 40%
    inflated_claim = Claim(
        claim_id=Claim.make_id("improved relevance by 40%", ClaimType.METRIC),
        original_claim_text="improved relevance by 40%",
        normalized_value="40%",
        claim_type=ClaimType.METRIC,
        numeric_value=40.0,
        unit="%",
        extraction_method="test",
        source_text="Designed search ranking models improving relevance by 40%.",
    )
    res2 = verifier.verify(inflated_claim, sample_alice_profile)
    assert res2.final_verdict == Verdict.UNSUPPORTED
    assert len(res2.contradicting_evidence) > 0


def test_temporal_date_and_duration(sample_alice_profile):
    verifier = ClaimVerifier()

    # Exaggerated duration: 15 years experience
    exaggerated = Claim(
        claim_id=Claim.make_id("15 years of experience", ClaimType.DURATION),
        original_claim_text="15 years of experience",
        normalized_value="15 years",
        claim_type=ClaimType.DURATION,
        numeric_value=15.0,
        unit="years",
        extraction_method="test",
        source_text="Alice has over 15 years of experience.",
    )
    res = verifier.verify(exaggerated, sample_alice_profile)
    assert res.final_verdict == Verdict.UNSUPPORTED

    # Date contradiction for Meta: claim Jan 2015 to Dec 2018 (actual is Jan 2019 to Dec 2020)
    date_contradiction = Claim(
        claim_id=Claim.make_id("Worked at Meta Jan 2015 - Dec 2018", ClaimType.DATE),
        original_claim_text="Jan 2015 - Dec 2018",
        normalized_value="2015-01--2018-12",
        claim_type=ClaimType.DATE,
        temporal_start="2015-01",
        temporal_end="2018-12",
        extraction_method="test",
        source_text="Worked at Meta from Jan 2015 to Dec 2018.",
    )
    res_date = verifier.verify(date_contradiction, sample_alice_profile)
    assert res_date.final_verdict == Verdict.UNSUPPORTED


def test_seniority_contradiction(sample_alice_profile):
    verifier = ClaimVerifier()
    claim = Claim(
        claim_id=Claim.make_id("VP of Engineering at Google", ClaimType.JOB_TITLE),
        original_claim_text="VP of Engineering",
        normalized_value="vp of engineering",
        claim_type=ClaimType.JOB_TITLE,
        extraction_method="test",
        source_text="Served as VP of Engineering at Google.",
    )
    res = verifier.verify(claim, sample_alice_profile)
    assert res.final_verdict == Verdict.UNSUPPORTED


def test_invented_skill_and_unsupported_fact(sample_alice_profile):
    verifier = ClaimVerifier()

    # Invented skill not in profile
    invented_skill = Claim(
        claim_id=Claim.make_id("Rust", ClaimType.SKILL),
        original_claim_text="Rust",
        normalized_value="rust",
        claim_type=ClaimType.SKILL,
        extraction_method="test",
        source_text="Proficient in Rust.",
    )
    res_skill = verifier.verify(invented_skill, sample_alice_profile)
    assert res_skill.final_verdict == Verdict.UNSUPPORTED

    # Unsubstantiated general achievement (missing evidence -> AMBIGUOUS)
    unsubstantiated = Claim(
        claim_id=Claim.make_id("Won Hackathon in 2022", ClaimType.ACHIEVEMENT),
        original_claim_text="Won Hackathon in 2022",
        normalized_value="won hackathon in 2022",
        claim_type=ClaimType.ACHIEVEMENT,
        extraction_method="test",
        source_text="Won internal hackathon in 2022.",
    )
    res_ach = verifier.verify(unsubstantiated, sample_alice_profile)
    assert res_ach.final_verdict == Verdict.AMBIGUOUS
    assert res_ach.requires_human_review is True
