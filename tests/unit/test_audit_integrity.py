"""
tests/unit/test_audit_integrity.py — Tests for cryptographic SHA-256 hash chaining of audit records.

Verifies:
1. Monotonic sequence numbering and valid hash linkage.
2. Detection of record payload tampering (e.g. altering final approved text).
3. Detection of record deletion (sequence gap or broken hash linkage).
4. Detection of record reordering.
"""

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from neverinvent.persistence.database import Base
from neverinvent.persistence.models import ApprovalAuditRecord
from neverinvent.persistence.repository import Repository
from neverinvent.workflow.models import ApprovalDecision


@pytest.fixture
def repo():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()
    yield Repository(session)
    session.close()


def test_audit_chain_valid_multiblock(repo):
    """Multiple sequential approvals produce an intact, mathematically valid hash chain."""
    r1 = repo.record_approval(
        proposal_id="prop_001",
        decision=ApprovalDecision.APPROVED,
        final_text="Engineered distributed PyTorch training pipeline on 8 A100s.",
    )
    r2 = repo.record_approval(
        proposal_id="prop_002",
        decision=ApprovalDecision.MANUALLY_EDITED_APPROVED,
        final_text="Reduced latency by 18% using TensorRT.",
        notes="Corrected 40% exaggeration down to documented 18%.",
    )
    r3 = repo.record_approval(
        proposal_id="prop_003",
        decision=ApprovalDecision.REJECTED,
        final_text="Led company-wide AI strategy as VP of Engineering.",
        notes="Rejected ungrounded VP claim.",
    )

    assert r1.sequence_number == 1
    assert r1.previous_hash == "GENESIS_BLOCK_0000000000000000000000000000000000000000000000000000"
    assert r2.sequence_number == 2
    assert r2.previous_hash == r1.current_hash
    assert r3.sequence_number == 3
    assert r3.previous_hash == r2.current_hash

    is_valid, error = repo.verify_audit_chain()
    assert is_valid is True
    assert error is None


def test_audit_chain_detects_payload_tampering(repo):
    """Modifying a finalized audit record's text invalidates the SHA-256 hash check."""
    repo.record_approval(
        proposal_id="prop_001",
        decision=ApprovalDecision.APPROVED,
        final_text="Truthful claim: reduced latency by 18%.",
    )
    repo.record_approval(
        proposal_id="prop_002",
        decision=ApprovalDecision.APPROVED,
        final_text="Another truthful claim: designed search index.",
    )

    is_valid, _ = repo.verify_audit_chain()
    assert is_valid is True

    # Malicious actor tampers directly with record #1 in the database
    target = repo.session.query(ApprovalAuditRecord).filter_by(sequence_number=1).first()
    target.final_text = "TAMPERED: reduced latency by 90% and invented Rust."
    repo.session.commit()

    is_valid, error = repo.verify_audit_chain()
    assert is_valid is False
    assert "Tampered record detected at sequence #1" in error


def test_audit_chain_detects_record_deletion(repo):
    """Deleting an intermediate block creates a sequence gap and breaks cryptographic linkage."""
    repo.record_approval(
        proposal_id="prop_001",
        decision=ApprovalDecision.APPROVED,
        final_text="Block 1 text.",
    )
    repo.record_approval(
        proposal_id="prop_002",
        decision=ApprovalDecision.APPROVED,
        final_text="Block 2 text.",
    )
    repo.record_approval(
        proposal_id="prop_003",
        decision=ApprovalDecision.APPROVED,
        final_text="Block 3 text.",
    )

    is_valid, _ = repo.verify_audit_chain()
    assert is_valid is True

    # Delete block #2
    block2 = repo.session.query(ApprovalAuditRecord).filter_by(sequence_number=2).first()
    repo.session.delete(block2)
    repo.session.commit()

    is_valid, error = repo.verify_audit_chain()
    assert is_valid is False
    assert ("Sequence gap detected" in error) or ("Broken hash link" in error)
