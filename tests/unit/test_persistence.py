"""
Unit tests for persistence models, database initialization, and repository.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from neverinvent.generation.models import GenerationType
from neverinvent.jobs.models import JobDescription, JobSource
from neverinvent.parsing.models import CandidateProfile, SkillItem
from neverinvent.persistence import Base, Repository
from neverinvent.workflow.models import ApprovalDecision, ProposalStatus, VerifiedProposal


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    try:
        yield session
    finally:
        session.close()


def test_candidate_profile_persistence(db_session):
    repo = Repository(db_session)
    profile = CandidateProfile(
        candidate_name="Alice Smith",
        skills=[SkillItem(name="python", original_text="Python")],
    )

    cid = repo.save_candidate(profile, raw_text="Alice Smith Python")
    assert cid.startswith("cand_")

    loaded = repo.get_candidate(cid)
    assert loaded is not None
    assert loaded.candidate_name == "Alice Smith"
    assert len(loaded.skills) == 1
    assert loaded.skills[0].name == "python"


def test_job_persistence(db_session):
    repo = Repository(db_session)
    job = JobDescription(
        job_id="job_persist_1",
        title="ML Engineer",
        normalized_title="ml engineer",
        company="Startup AI",
        raw_description="Build models.",
        required_skills=["python"],
        source_type=JobSource.SYNTHETIC,
    )

    repo.save_job(job)
    loaded = repo.get_job("job_persist_1")
    assert loaded is not None
    assert loaded.title == "ML Engineer"

    jobs = repo.list_jobs()
    assert len(jobs) == 1


def test_proposal_and_approval_audit(db_session):
    repo = Repository(db_session)
    proposal = VerifiedProposal(
        proposal_id="prop_001",
        generation_type=GenerationType.RESUME_BULLET_SUGGESTION,
        original_text="Designed models.",
        proposed_text="Engineered search models.",
        provider="mock",
        model_name="test",
        status=ProposalStatus.ALL_SUPPORTED,
        supported_count=1,
    )

    repo.save_proposal(proposal, candidate_id="c1", job_id="j1")
    loaded_prop = repo.get_proposal("prop_001")
    assert loaded_prop is not None
    assert loaded_prop.status == ProposalStatus.ALL_SUPPORTED
    assert loaded_prop.decision == ApprovalDecision.PENDING

    # Record human approval
    audit = repo.record_approval(
        proposal_id="prop_001",
        decision=ApprovalDecision.APPROVED,
        final_text="Engineered search models.",
        notes="Confirmed by candidate.",
    )
    assert audit.decision == "APPROVED"

    # Verify audit record persisted
    audits = repo.list_approvals()
    assert len(audits) == 1
    assert audits[0]["proposal_id"] == "prop_001"
    assert audits[0]["decision"] == "APPROVED"

    # Proposal state is updated
    updated_prop = repo.get_proposal("prop_001")
    assert updated_prop.decision == ApprovalDecision.APPROVED
    assert updated_prop.decision_notes == "Confirmed by candidate."
