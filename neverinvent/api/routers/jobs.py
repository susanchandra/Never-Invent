"""
api/routers/jobs.py — Endpoints for job listings, retrieval search, and evidence-grounded matching.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from neverinvent.jobs.job_loader import load_jobs_from_jsonl
from neverinvent.jobs.models import JobDescription
from neverinvent.matching import EvidenceGroundedMatcher
from neverinvent.persistence.database import get_db_session
from neverinvent.persistence.repository import Repository
from neverinvent.retrieval import BM25Retriever, DenseRetriever, HybridRetriever

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

_SAMPLE_JOBS_PATH = Path("data/job_postings/sample_jobs.jsonl")


def _ensure_jobs_seeded(repo: Repository) -> list[JobDescription]:
    existing = repo.list_jobs()
    if existing:
        return existing

    if _SAMPLE_JOBS_PATH.exists():
        jobs, _ = load_jobs_from_jsonl(_SAMPLE_JOBS_PATH)
        for j in jobs:
            repo.save_job(j)
        return repo.list_jobs()

    return []


class JobSearchRequest(BaseModel):
    query: str
    method: str = "bm25"  # "bm25", "dense", "hybrid"
    top_k: int = 5


class JobMatchRequest(BaseModel):
    candidate_id: str
    job_id: str


@router.get("")
def list_jobs(session: Session = Depends(get_db_session)):
    repo = Repository(session)
    jobs = _ensure_jobs_seeded(repo)
    return {"total": len(jobs), "jobs": jobs}


@router.post("/search")
def search_jobs(req: JobSearchRequest, session: Session = Depends(get_db_session)):
    repo = Repository(session)
    jobs = _ensure_jobs_seeded(repo)
    if not jobs:
        return {"query": req.query, "results": []}

    method = req.method.lower()
    if method == "dense":
        retriever = DenseRetriever()
        retriever.fit(jobs)
        results = retriever.search(req.query, top_k=req.top_k)
    elif method == "hybrid":
        bm25 = BM25Retriever()
        dense = DenseRetriever()
        hybrid = HybridRetriever(bm25_retriever=bm25, dense_retriever=dense)
        hybrid.fit(jobs)
        results = hybrid.search_rrf(req.query, top_k=req.top_k)
    else:
        bm25 = BM25Retriever()
        bm25.fit(jobs)
        results = bm25.search(req.query, top_k=req.top_k)

    return {"query": req.query, "method": req.method, "results": results}


@router.post("/match")
def match_job(req: JobMatchRequest, session: Session = Depends(get_db_session)):
    repo = Repository(session)
    candidate = repo.get_candidate(req.candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")

    job = repo.get_job(req.job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found.")

    matcher = EvidenceGroundedMatcher()
    breakdown = matcher.match(candidate, job)
    return {"breakdown": breakdown}
