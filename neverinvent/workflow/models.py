"""
workflow/models.py — Data models for verified proposals and approval workflow.

Design contracts:
- Preserves original and proposed text side by side.
- Records all atomic claims and their independent verification results.
- Never auto-approves proposals.
- Unsupported claims are prominently flagged, not suppressed.
- Ambiguous claims mandate human review.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from neverinvent.claims.models import Claim
from neverinvent.generation.models import GenerationType
from neverinvent.verification.models import Verdict, VerificationResult


class ProposalStatus(str, Enum):
    ALL_SUPPORTED = "ALL_SUPPORTED"
    CONTAINS_UNSUPPORTED = "CONTAINS_UNSUPPORTED"
    CONTAINS_AMBIGUOUS = "CONTAINS_AMBIGUOUS"
    EXTRACTION_WARNING = "EXTRACTION_WARNING"


class ApprovalDecision(str, Enum):
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    MANUALLY_EDITED_APPROVED = "MANUALLY_EDITED_APPROVED"
    AMBIGUOUS_OVERRIDE_APPROVED = "AMBIGUOUS_OVERRIDE_APPROVED"
    PENDING = "PENDING"


class DiffHighlight(BaseModel):
    """Word-level or numeric difference between original and proposed text."""
    kind: str  # "addition", "deletion", "changed_metric"
    value: str
    original_value: Optional[str] = None


class VerifiedProposal(BaseModel):
    """
    Complete verified proposal object ready for candidate review and approval.
    """
    model_config = {"protected_namespaces": ()}

    proposal_id: str
    generation_type: GenerationType
    original_text: Optional[str] = None
    proposed_text: str
    provider: str
    model_name: str
    claims: list[Claim] = Field(default_factory=list)
    verification_results: list[VerificationResult] = Field(default_factory=list)
    status: ProposalStatus
    supported_count: int = 0
    unsupported_count: int = 0
    ambiguous_count: int = 0
    requires_human_review: bool = True
    warnings: list[str] = Field(default_factory=list)
    diff_highlights: list[DiffHighlight] = Field(default_factory=list)
    decision: ApprovalDecision = ApprovalDecision.PENDING
    decision_notes: Optional[str] = None
    decision_timestamp: Optional[str] = None

    @staticmethod
    def make_id(proposed_text: str, generation_type: GenerationType) -> str:
        raw = f"{proposed_text}::{generation_type.value}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
