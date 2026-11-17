"""
persistence/models.py — SQLAlchemy ORM models for candidate profiles, jobs, proposals, and approvals.
"""

from __future__ import annotations

import datetime
import hashlib
import json
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from neverinvent.persistence.database import Base


class CandidateRecord(Base):
    __tablename__ = "candidate_profiles"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    profile_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class JobRecord(Base):
    __tablename__ = "jobs"

    job_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str] = mapped_column(String(255))
    raw_description: Mapped[str] = mapped_column(Text)
    job_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class ProposalRecord(Base):
    __tablename__ = "verified_proposals"

    proposal_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    candidate_id: Mapped[str] = mapped_column(String(64), index=True)
    job_id: Mapped[str] = mapped_column(String(64), index=True)
    generation_type: Mapped[str] = mapped_column(String(64))
    original_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    proposed_text: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(String(64))
    model_name: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(64))
    supported_count: Mapped[int] = mapped_column(Integer, default=0)
    unsupported_count: Mapped[int] = mapped_column(Integer, default=0)
    ambiguous_count: Mapped[int] = mapped_column(Integer, default=0)
    proposal_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )


class ApprovalAuditRecord(Base):
    __tablename__ = "approval_audits"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    sequence_number: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    proposal_id: Mapped[str] = mapped_column(String(64), index=True)
    decision: Mapped[str] = mapped_column(String(64))  # APPROVED, REJECTED, MANUALLY_EDITED_APPROVED
    final_text: Mapped[str] = mapped_column(Text)
    decision_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    timestamp: Mapped[datetime.datetime] = mapped_column(
        DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc)
    )
    previous_hash: Mapped[str] = mapped_column(String(64))
    current_hash: Mapped[str] = mapped_column(String(64))

    @staticmethod
    def canonical_payload(
        sequence_number: int,
        proposal_id: str,
        decision: str,
        final_text: str,
        decision_notes: Optional[str],
        timestamp_iso: str,
        previous_hash: str,
    ) -> str:
        """Deterministic canonical JSON string for SHA-256 hash calculation."""
        # Ensure timestamp is canonical UTC Zulu format if passed as datetime
        payload = {
            "sequence_number": sequence_number,
            "proposal_id": proposal_id,
            "decision": decision,
            "final_text": final_text,
            "decision_notes": decision_notes or "",
            "timestamp": timestamp_iso,
            "previous_hash": previous_hash,
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @staticmethod
    def calculate_hash(payload_str: str) -> str:
        """Computes hex digest of SHA-256 for canonical payload string."""
        return hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
