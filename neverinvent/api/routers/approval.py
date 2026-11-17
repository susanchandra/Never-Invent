"""
api/routers/approval.py — Endpoints for human approval decisions and audit trail.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from neverinvent.persistence.database import get_db_session
from neverinvent.persistence.repository import Repository
from neverinvent.workflow.models import ApprovalDecision, ProposalStatus

router = APIRouter(prefix="/api/approve", tags=["approval"])


class ApprovalDecisionRequest(BaseModel):
    proposal_id: str
    decision: ApprovalDecision
    final_text: str
    notes: Optional[str] = None


@router.post("/decision")
def record_decision(
    req: ApprovalDecisionRequest, session: Session = Depends(get_db_session)
):
    """
    Record explicit human approval, rejection, or manual edit approval for a proposal.
    Stores immutable audit trail record.
    Enforces strict verification invariants:
    - Rejects stale/duplicate finalizations.
    - Requires final_text to match verified proposed_text.
    - Forbids approving CONTAINS_UNSUPPORTED proposals.
    - Mandates non-empty rationale for AMBIGUOUS overrides.
    """
    repo = Repository(session)
    proposal = repo.get_proposal(req.proposal_id)
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found.")

    if proposal.decision != ApprovalDecision.PENDING:
        raise HTTPException(
            status_code=400,
            detail=f"Proposal has already been finalized with decision: {proposal.decision.value}. Duplicate decisions are forbidden.",
        )

    # Submitted final text must match the verified text
    if req.final_text.strip() != proposal.proposed_text.strip():
        raise HTTPException(
            status_code=400,
            detail="Submitted final_text does not match the verified proposal text. Manual edits must be submitted to /api/verify/reverify for independent verification before approval.",
        )

    # Strict verdict checks
    if req.decision != ApprovalDecision.REJECTED:
        if proposal.status == ProposalStatus.CONTAINS_UNSUPPORTED or proposal.unsupported_count > 0:
            raise HTTPException(
                status_code=400,
                detail="Cannot approve a proposal containing UNSUPPORTED claims. Prohibited by verification integrity rules.",
            )

        if proposal.status == ProposalStatus.CONTAINS_AMBIGUOUS or proposal.ambiguous_count > 0:
            if not req.notes or not req.notes.strip():
                raise HTTPException(
                    status_code=400,
                    detail="Approving a proposal with AMBIGUOUS claims requires explicit human review notes and rationale.",
                )
            req.decision = ApprovalDecision.AMBIGUOUS_OVERRIDE_APPROVED
        elif proposal.provider == "manual_user_edit":
            req.decision = ApprovalDecision.MANUALLY_EDITED_APPROVED
        else:
            req.decision = ApprovalDecision.APPROVED

    audit = repo.record_approval(
        proposal_id=req.proposal_id,
        decision=req.decision,
        final_text=req.final_text,
        notes=req.notes,
    )

    return {
        "status": "success",
        "audit_id": audit.id,
        "proposal_id": audit.proposal_id,
        "decision": audit.decision,
        "final_text": audit.final_text,
        "timestamp": audit.timestamp.isoformat() if audit.timestamp else None,
    }


@router.get("/audits")
def get_audit_trail(session: Session = Depends(get_db_session)):
    repo = Repository(session)
    audits = repo.list_approvals()
    is_valid, error = repo.verify_audit_chain()
    return {
        "total": len(audits),
        "chain_valid": is_valid,
        "chain_error": error,
        "audits": audits,
    }


@router.get("/verify-chain")
def verify_audit_ledger_chain(session: Session = Depends(get_db_session)):
    """
    Cryptographic verification endpoint for the append-only audit trail.
    Walks the SHA-256 hash chain and returns 200 with integrity status or 400 if tampered.
    """
    repo = Repository(session)
    is_valid, error = repo.verify_audit_chain()
    if not is_valid:
        raise HTTPException(status_code=400, detail=f"Audit chain verification failed: {error}")
    return {"status": "valid", "detail": "All audit blocks verified against SHA-256 hash chain."}
