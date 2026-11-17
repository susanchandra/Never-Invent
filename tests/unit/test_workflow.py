"""
Unit tests for verification pipeline, proposal diffing, and manual edit re-verification.
"""

import pytest

from neverinvent.generation.models import GenerationType
from neverinvent.parsing.models import (
    CandidateProfile,
    MetricClaim,
    SkillItem,
    WorkExperience,
)
from neverinvent.workflow import (
    ApprovalDecision,
    ProposalStatus,
    VerificationPipeline,
)


@pytest.fixture
def sample_candidate() -> CandidateProfile:
    return CandidateProfile(
        candidate_name="Alice Smith",
        skills=[
            SkillItem(name="python", original_text="Python"),
            SkillItem(name="pytorch", original_text="PyTorch"),
        ],
        experience=[
            WorkExperience(
                company="Google",
                original_company_text="Google",
                title="Senior ML Engineer",
                start_date="2021-01",
                end_date="Present",
                responsibilities=["Designed search ranking models improving relevance by 18%."],
            )
        ],
        metrics=[
            MetricClaim(
                raw_metric_text="improving relevance by 18%",
                quantity=18.0,
                unit="%",
                direction="increase",
                context="Designed search ranking models improving relevance by 18%.",
            )
        ],
    )


def test_pipeline_faithful_proposal(sample_candidate):
    pipeline = VerificationPipeline()
    proposal = pipeline.process_proposal(
        proposed_text="Engineered search ranking models improving relevance by 18%.",
        candidate_profile=sample_candidate,
        original_text="Designed search ranking models improving relevance by 18%.",
        generation_type=GenerationType.RESUME_BULLET_SUGGESTION,
    )

    assert proposal.status == ProposalStatus.ALL_SUPPORTED
    assert proposal.unsupported_count == 0
    assert proposal.supported_count >= 1
    assert proposal.decision == ApprovalDecision.PENDING
    assert proposal.requires_human_review is True


def test_pipeline_fabricated_proposal(sample_candidate):
    pipeline = VerificationPipeline()
    proposal = pipeline.process_proposal(
        proposed_text="Engineered search ranking models improving relevance by 40%.",
        candidate_profile=sample_candidate,
        original_text="Designed search ranking models improving relevance by 18%.",
        generation_type=GenerationType.RESUME_BULLET_SUGGESTION,
    )

    # 40% vs 18% is caught as unsupported!
    assert proposal.status == ProposalStatus.CONTAINS_UNSUPPORTED
    assert proposal.unsupported_count >= 1
    # Check that diff detected the metric change
    assert any(d.kind == "changed_metric" for d in proposal.diff_highlights)


def test_manual_edit_reverification(sample_candidate):
    pipeline = VerificationPipeline()

    # Initial proposal has fabricated metric (40%)
    initial = pipeline.process_proposal(
        proposed_text="Engineered search ranking models improving relevance by 40%.",
        candidate_profile=sample_candidate,
        original_text="Designed search ranking models improving relevance by 18%.",
    )
    assert initial.status == ProposalStatus.CONTAINS_UNSUPPORTED

    # User manually corrects the metric to 18%
    corrected_text = "Engineered search ranking models improving relevance by 18%."
    reverified = pipeline.reverify_manual_edit(initial, corrected_text, sample_candidate)

    # Re-verification confirms it is now fully supported!
    assert reverified.status == ProposalStatus.ALL_SUPPORTED
    assert reverified.unsupported_count == 0
    assert reverified.provider == "manual_user_edit"


def test_pipeline_unparsed_text_safety_fallback(sample_candidate):
    pipeline = VerificationPipeline()
    proposal = pipeline.process_proposal(
        proposed_text="...",
        candidate_profile=sample_candidate,
    )
    # Does not crash or silently approve
    assert proposal.status in (ProposalStatus.CONTAINS_AMBIGUOUS, ProposalStatus.EXTRACTION_WARNING)
    assert len(proposal.warnings) > 0
    assert proposal.requires_human_review is True
