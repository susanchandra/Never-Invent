"""
retrieval/models.py — Data structures for search retrieval and ranking results.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from neverinvent.jobs.models import JobDescription


class RetrievalMethod(str, Enum):
    BM25 = "bm25"
    DENSE = "dense"
    HYBRID_RRF = "hybrid_rrf"
    HYBRID_LINEAR = "hybrid_linear"


class RetrievalResult(BaseModel):
    """
    A single ranked job match returned by a retriever.
    Scores are relative to the retrieval method used.
    """
    job_id: str
    rank: int = Field(description="1-based rank position in search result list")
    score: float = Field(description="Raw or normalized score assigned by retrieval method")
    method: RetrievalMethod
    job: Optional[JobDescription] = Field(default=None, description="Complete job record if hydrated")

    def __repr__(self) -> str:
        return f"RetrievalResult(rank={self.rank}, job_id={self.job_id!r}, score={self.score:.4f}, method={self.method.value})"
