"""
api/routers/verification.py — Endpoints for generating verified proposals and reverifying edits.
"""

from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from neverinvent.generation import (
    GenerationMode,
    GenerationRequest,
    GenerationType,
    GroqGenerator,
    MockGenerator,
    ResumeBulletEditor,
)
from neverinvent.persistence.database import get_db_session
from neverinvent.persistence.repository import Repository
from neverinvent.workflow.pipeline import VerificationPipeline

router = APIRouter(prefix="/api/verify", tags=["verification"])


class ProposalGenerateRequest(BaseModel):
    candidate_id: str
    job_id: str
    generation_type: GenerationType = GenerationType.RESUME_BULLET_SUGGESTION
    mode: GenerationMode = GenerationMode.FAITHFUL
    target_bullet: Optional[str] = None
    provider: str = "mock"  # "mock" or "groq"


class ReverifyRequest(BaseModel):
    proposal_id: str
    candidate_id: str
    edited_text: str


@router.post("/generate")
def generate_verified_proposal(
    req: ProposalGenerateRequest, session: Session = Depends(get_db_session)
):
    """
    Generate an unverified proposal via generator, route through independent claim verification,
    compute diff, persist, and return the VerifiedProposal.
    """
    repo = Repository(session)
    candidate = repo.get_candidate(req.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    job = repo.get_job(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    # 1. Select generator
    if req.provider.lower() == "groq":
        generator = GroqGenerator()
    else:
        generator = MockGenerator()

    gen_req = GenerationRequest(
        candidate_profile=candidate,
        job_description=job,
        generation_type=req.generation_type,
        mode=req.mode,
        target_bullet=req.target_bullet,
    )

    try:
        gen_resp = generator.generate(gen_req)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Generation failed: {exc}")

    # 2. Route through Verification Pipeline
    pipeline = VerificationPipeline()
    proposal = pipeline.process_proposal(
        proposed_text=gen_resp.generated_text,
        candidate_profile=candidate,
        original_text=req.target_bullet,
        generation_type=req.generation_type,
        provider=gen_resp.provider,
        model_name=gen_resp.model_name,
    )

    # 3. Persist proposal
    repo.save_proposal(proposal, candidate_id=req.candidate_id, job_id=req.job_id)

    return {"proposal": proposal}


@router.post("/reverify")
def reverify_proposal(req: ReverifyRequest, session: Session = Depends(get_db_session)):
    """
    Re-verify a manually edited proposal before human approval.
    """
    repo = Repository(session)
    candidate = repo.get_candidate(req.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    orig_proposal = repo.get_proposal(req.proposal_id)
    if not orig_proposal:
        raise HTTPException(status_code=404, detail="Original proposal not found.")

    pipeline = VerificationPipeline()
    reverified = pipeline.reverify_manual_edit(
        original_proposal=orig_proposal,
        edited_text=req.edited_text,
        candidate_profile=candidate,
    )

    # Update in DB
    repo.save_proposal(reverified, candidate_id=req.candidate_id)

    return {"proposal": reverified}
