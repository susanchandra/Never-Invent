"""
claims/models.py — Strongly typed claim and evidence models for Phase 2.

Design contracts:
- A Claim is one atomic, independently verifiable factual assertion.
- An Evidence object references verbatim text from the parsed candidate profile.
- EvidenceBundle groups supporting and contradicting evidence for a single claim.
- Verification models never infer new facts; they only classify existing ones.
- ExtractionStatus is reused from parsing.models to signal extraction confidence.
"""

from __future__ import annotations

import hashlib
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field

from neverinvent.ingestion.models import SourceSpan
from neverinvent.parsing.models import ExtractionStatus


class ClaimType(str, Enum):
    """
    Typed categories of atomic factual claims.

    Each category corresponds to a distinct verification strategy
    so that the verifier can choose the appropriate check.
    """

    SKILL = "SKILL"
    EMPLOYER = "EMPLOYER"
    PROJECT = "PROJECT"
    JOB_TITLE = "JOB_TITLE"
    EDUCATION = "EDUCATION"
    CERTIFICATION = "CERTIFICATION"
    DATE = "DATE"
    DURATION = "DURATION"
    METRIC = "METRIC"
    QUANTITY = "QUANTITY"
    ACHIEVEMENT = "ACHIEVEMENT"
    RESPONSIBILITY = "RESPONSIBILITY"


class Claim(BaseModel):
    """
    One atomic, independently verifiable factual assertion extracted from
    AI-generated text (a resume edit or job-match explanation).

    A claim must be as narrow as possible.  Compound statements must be split
    into separate Claim objects before verification.  The verifier receives one
    Claim at a time and returns one VerificationResult.
    """

    claim_id: str = Field(
        description="Deterministic SHA-256 hex digest of source_text + claim_type."
    )
    original_claim_text: str = Field(
        description="Verbatim text from which this claim was extracted (may contain the full sentence)."
    )
    normalized_value: str = Field(
        description="Normalized canonical form of the core claim value (lowercase, stripped)."
    )
    claim_type: ClaimType

    # Contextual slots — None means 'not applicable for this claim type'
    subject: Optional[str] = Field(
        default=None,
        description="The entity the claim is about (e.g. company name, skill name, project name).",
    )
    numeric_value: Optional[float] = Field(
        default=None,
        description="Parsed numeric quantity, if claim contains one (e.g. 40.0 for '40%').",
    )
    unit: Optional[str] = Field(
        default=None,
        description="Unit of numeric_value (e.g. '%', 'years', 'ms', '$').",
    )
    temporal_start: Optional[str] = Field(
        default=None,
        description="YYYY-MM start date, if claim specifies a time range.",
    )
    temporal_end: Optional[str] = Field(
        default=None,
        description="YYYY-MM end date or 'Present', if claim specifies a time range.",
    )

    # Extraction provenance
    extraction_method: str = Field(
        description="Name of the extraction method (e.g. 'regex_skill', 'regex_metric')."
    )
    extraction_confidence: ExtractionStatus = Field(
        default=ExtractionStatus.EXPLICIT,
        description="Confidence of extraction: EXPLICIT, UNCERTAIN, or UNRESOLVED.",
    )
    source_text: str = Field(
        description="Verbatim sentence or clause from which this claim was extracted."
    )

    @staticmethod
    def make_id(source_text: str, claim_type: ClaimType) -> str:
        """Deterministic claim ID: SHA-256 of (source_text + claim_type)."""
        raw = f"{source_text}::{claim_type.value}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class Evidence(BaseModel):
    """
    One piece of evidence extracted from the candidate's resume profile.

    Evidence is always verbatim text anchored to a SourceSpan.
    It must never be constructed by inference or generation.
    """

    evidence_id: str = Field(
        description="Deterministic ID: SHA-256 of evidence_text + profile_field."
    )
    evidence_text: str = Field(description="Verbatim text from the resume document.")
    source_span: Optional[SourceSpan] = Field(
        default=None,
        description="Exact location in the source document. None when span not available.",
    )
    evidence_type: str = Field(
        description=(
            "What kind of evidence this is. One of: "
            "'skill', 'work_experience', 'education', 'certification', "
            "'project', 'metric', 'responsibility'."
        )
    )
    profile_field: str = Field(
        description="Which CandidateProfile field this was drawn from (e.g. 'skills', 'experience[0]')."
    )

    @staticmethod
    def make_id(evidence_text: str, profile_field: str) -> str:
        """Deterministic evidence ID: SHA-256 of (evidence_text + profile_field)."""
        raw = f"{evidence_text}::{profile_field}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


class EvidenceBundle(BaseModel):
    """
    Groups supporting and contradicting evidence for a single claim.

    The verifier populates this during the verification pass and returns it
    as part of the VerificationResult.  An empty supporting list does NOT mean
    UNSUPPORTED — it means evidence is absent (→ AMBIGUOUS).
    """

    claim: Claim
    supporting: list[Evidence] = Field(default_factory=list)
    contradicting: list[Evidence] = Field(default_factory=list)

    @property
    def has_support(self) -> bool:
        return len(self.supporting) > 0

    @property
    def has_contradiction(self) -> bool:
        return len(self.contradicting) > 0
