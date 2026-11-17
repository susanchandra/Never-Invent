"""
matching/models.py — Data models for evidence-grounded candidate-job matching.

Design contracts:
- Separates required skills from preferred skills.
- Explicitly distinguishes SUPPORTED skills from MISSING skills.
- Does NOT use BM25 or FAISS scores as proof of skill possession.
- Formula for grounded_match_score is explicit, deterministic, and documented:
    Score = (supported_required / max(1, total_required)) * 0.70
          + (supported_preferred / max(1, total_preferred)) * 0.30
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from neverinvent.claims.models import Evidence


class SkillMatchStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    MISSING = "MISSING"


class SkillMatchItem(BaseModel):
    skill_name: str
    is_required: bool
    status: SkillMatchStatus
    supporting_evidence: Optional[Evidence] = None


class DealbreakerResult(BaseModel):
    passed: bool
    failed_reasons: list[str] = Field(default_factory=list)
    checked_criteria: list[str] = Field(default_factory=list)


class MatchBreakdown(BaseModel):
    """
    Detailed evidence-grounded breakdown for a candidate-job pair.
    """
    job_id: str
    job_title: str
    company: str
    required_skills_match: list[SkillMatchItem] = Field(default_factory=list)
    preferred_skills_match: list[SkillMatchItem] = Field(default_factory=list)
    dealbreaker_result: DealbreakerResult
    supported_required_count: int = 0
    total_required_count: int = 0
    supported_preferred_count: int = 0
    total_preferred_count: int = 0
    grounded_match_score: float = Field(
        ge=0.0,
        le=1.0,
        description="Explicit grounded formula score: 70% required skills coverage + 30% preferred skills coverage.",
    )
    explanation: str
