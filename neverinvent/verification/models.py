"""
verification/models.py — Verdict, strategy enums, and verification result models.

Design contracts:
- Verdict semantics:
    SUPPORTED: Adequate direct evidence exists in the candidate's resume profile.
    UNSUPPORTED: Explicit contradiction exists OR value is definitively outside documented range.
    AMBIGUOUS: Incomplete evidence, uncertain extraction, or missing evidence (absence != proof).
- VerificationResult records every strategy evaluated, matched evidence, latency, and human review flag.
- Zero imports from retrieval or generation modules.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from neverinvent.claims.models import Claim, Evidence


class Verdict(str, Enum):
    """Core three-valued verification verdict."""

    SUPPORTED = "SUPPORTED"
    UNSUPPORTED = "UNSUPPORTED"
    AMBIGUOUS = "AMBIGUOUS"


class VerificationStrategy(str, Enum):
    """Typed verification strategy identifiers."""

    EXACT_MATCH = "exact_match"
    NORMALIZED_MATCH = "normalized_match"
    ALIAS_MATCH = "alias_match"
    NUMERICAL = "numerical"
    TEMPORAL = "temporal"
    ENTITY = "entity"
    CONTRADICTION = "contradiction"
    EVIDENCE_SUFFICIENCY = "evidence_sufficiency"


class StrategyResult(BaseModel):
    """Result of running a single verification strategy against a Claim."""

    strategy: VerificationStrategy
    verdict: Verdict
    matched_evidence: list[Evidence] = Field(default_factory=list)
    contradicting_evidence: list[Evidence] = Field(default_factory=list)
    explanation: str
    confidence: float = Field(
        default=1.0, ge=0.0, le=1.0, description="Confidence in this strategy's verdict."
    )


class VerificationResult(BaseModel):
    """
    Comprehensive verification assessment for a single Claim against a CandidateProfile.
    """

    claim: Claim
    final_verdict: Verdict
    primary_strategy: VerificationStrategy
    all_strategy_results: list[StrategyResult] = Field(default_factory=list)
    matched_evidence: list[Evidence] = Field(default_factory=list)
    contradicting_evidence: list[Evidence] = Field(default_factory=list)
    rationale: str
    requires_human_review: bool = Field(
        default=False,
        description="True whenever verdict is AMBIGUOUS or extraction was uncertain.",
    )
    latency_ms: float = Field(
        default=0.0, ge=0.0, description="Elapsed verification time in milliseconds."
    )
