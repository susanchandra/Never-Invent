"""
persistence/repository.py — Data access layer for profiles, jobs, proposals, and audit records.
"""

from __future__ import annotations

import datetime
import json
import uuid
from typing import Optional

from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from neverinvent.jobs.models import JobDescription
from neverinvent.parsing.models import CandidateProfile
from neverinvent.persistence.models import (
    ApprovalAuditRecord,
    CandidateRecord,
    JobRecord,
    ProposalRecord,
)
from neverinvent.workflow.models import ApprovalDecision, VerifiedProposal


class Repository:
    """Lightweight repository encapsulating database operations."""

    def __init__(self, session: Session):
        self.session = session

    # 1. Candidate Profiles
    def save_candidate(
        self, profile: CandidateProfile, raw_text: str = "", candidate_id: Optional[str] = None
    ) -> str:
        cid = candidate_id or f"cand_{uuid.uuid4().hex[:12]}"
        rec = self.session.get(CandidateRecord, cid)
        profile_json = profile.model_dump_json()

        if rec is None:
            rec = CandidateRecord(
                id=cid,
                candidate_name=profile.candidate_name,
                email=profile.email,
                raw_text=raw_text,
                profile_json=profile_json,
            )
            self.session.add(rec)
        else:
            rec.candidate_name = profile.candidate_name
            rec.email = profile.email
            rec.raw_text = raw_text
            rec.profile_json = profile_json

        self.session.commit()
        return cid

    def get_candidate(self, candidate_id: str) -> Optional[CandidateProfile]:
        rec = self.session.get(CandidateRecord, candidate_id)
        if not rec:
            return None
        return CandidateProfile.model_validate_json(rec.profile_json)

    # 2. Jobs
    def save_job(self, job: JobDescription) -> str:
        rec = self.session.get(JobRecord, job.job_id)
        job_json = job.model_dump_json()

        if rec is None:
            rec = JobRecord(
                job_id=job.job_id,
                title=job.title,
                company=job.company,
                raw_description=job.raw_description,
                job_json=job_json,
            )
            self.session.add(rec)
        else:
            rec.title = job.title
            rec.company = job.company
            rec.raw_description = job.raw_description
            rec.job_json = job_json

        self.session.commit()
        return job.job_id

    def get_job(self, job_id: str) -> Optional[JobDescription]:
        rec = self.session.get(JobRecord, job_id)
        if not rec:
            return None
        return JobDescription.model_validate_json(rec.job_json)

    def list_jobs(self) -> list[JobDescription]:
        stmt = select(JobRecord).order_by(JobRecord.created_at.desc())
        records = self.session.scalars(stmt).all()
        return [JobDescription.model_validate_json(r.job_json) for r in records]

    # 3. Verified Proposals
    def save_proposal(
        self,
        proposal: VerifiedProposal,
        candidate_id: str = "default_candidate",
        job_id: str = "default_job",
    ) -> str:
        rec = self.session.get(ProposalRecord, proposal.proposal_id)
        proposal_json = proposal.model_dump_json()

        if rec is None:
            rec = ProposalRecord(
                proposal_id=proposal.proposal_id,
                candidate_id=candidate_id,
                job_id=job_id,
                generation_type=proposal.generation_type.value,
                original_text=proposal.original_text,
                proposed_text=proposal.proposed_text,
                provider=proposal.provider,
                model_name=proposal.model_name,
                status=proposal.status.value,
                supported_count=proposal.supported_count,
                unsupported_count=proposal.unsupported_count,
                ambiguous_count=proposal.ambiguous_count,
                proposal_json=proposal_json,
            )
            self.session.add(rec)
        else:
            rec.proposed_text = proposal.proposed_text
            rec.status = proposal.status.value
            rec.supported_count = proposal.supported_count
            rec.unsupported_count = proposal.unsupported_count
            rec.ambiguous_count = proposal.ambiguous_count
            rec.proposal_json = proposal_json

        self.session.commit()
        return proposal.proposal_id

    def get_proposal(self, proposal_id: str) -> Optional[VerifiedProposal]:
        rec = self.session.get(ProposalRecord, proposal_id)
        if not rec:
            return None
        return VerifiedProposal.model_validate_json(rec.proposal_json)

    # 4. Approval Auditing & Hash Chaining
    def record_approval(
        self,
        proposal_id: str,
        decision: ApprovalDecision,
        final_text: str,
        notes: Optional[str] = None,
    ) -> ApprovalAuditRecord:
        """
        Records human approval decision into an append-only, SHA-256 hash-chained audit ledger.
        Each record cryptographically binds the sequence number, proposal ID, decision,
        final text, notes, timestamp, and previous block hash.
        """
        # Find latest block to determine sequence and previous hash
        latest_stmt = (
            select(ApprovalAuditRecord)
            .order_by(desc(ApprovalAuditRecord.sequence_number))
            .limit(1)
        )
        latest = self.session.scalars(latest_stmt).first()

        if latest is not None:
            sequence_number = latest.sequence_number + 1
            previous_hash = latest.current_hash
        else:
            sequence_number = 1
            previous_hash = "GENESIS_BLOCK_0000000000000000000000000000000000000000000000000000"

        ts = datetime.datetime.now(datetime.timezone.utc)
        ts_str = ts.strftime("%Y-%m-%dT%H:%M:%SZ")
        payload = ApprovalAuditRecord.canonical_payload(
            sequence_number=sequence_number,
            proposal_id=proposal_id,
            decision=decision.value,
            final_text=final_text,
            decision_notes=notes,
            timestamp_iso=ts_str,
            previous_hash=previous_hash,
        )
        current_hash = ApprovalAuditRecord.calculate_hash(payload)

        audit = ApprovalAuditRecord(
            sequence_number=sequence_number,
            proposal_id=proposal_id,
            decision=decision.value,
            final_text=final_text,
            decision_notes=notes,
            timestamp=ts,
            previous_hash=previous_hash,
            current_hash=current_hash,
        )
        self.session.add(audit)

        # Update proposal state if exists
        rec = self.session.get(ProposalRecord, proposal_id)
        if rec:
            prop = VerifiedProposal.model_validate_json(rec.proposal_json)
            prop.decision = decision
            prop.decision_notes = notes
            prop.decision_timestamp = ts_str
            rec.proposal_json = prop.model_dump_json()

        self.session.commit()
        return audit

    def list_approvals(self) -> list[dict]:
        stmt = select(ApprovalAuditRecord).order_by(desc(ApprovalAuditRecord.sequence_number))
        records = self.session.scalars(stmt).all()
        return [
            {
                "id": r.id,
                "sequence_number": r.sequence_number,
                "proposal_id": r.proposal_id,
                "decision": r.decision,
                "final_text": r.final_text,
                "decision_notes": r.decision_notes,
                "timestamp": r.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if r.timestamp else None,
                "previous_hash": r.previous_hash,
                "current_hash": r.current_hash,
            }
            for r in records
        ]

    def verify_audit_chain(self) -> tuple[bool, Optional[str]]:
        """
        Validates the entire audit log hash chain.
        Verifies:
        1. Monotonically increasing sequence numbers starting at 1.
        2. Correct cryptographic previous_hash linkage across records.
        3. Canonical payload hash matching stored current_hash (detects payload tampering).
        Returns (is_valid, error_message).
        """
        stmt = select(ApprovalAuditRecord).order_by(ApprovalAuditRecord.sequence_number.asc())
        records = self.session.scalars(stmt).all()

        if not records:
            return True, None

        expected_seq = 1
        expected_prev_hash = "GENESIS_BLOCK_0000000000000000000000000000000000000000000000000000"

        for rec in records:
            if rec.sequence_number != expected_seq:
                return False, (
                    f"Sequence gap detected: expected #{expected_seq}, found #{rec.sequence_number} "
                    f"(record id={rec.id}). Indicates record deletion or reordering."
                )

            if rec.previous_hash != expected_prev_hash:
                return False, (
                    f"Broken hash link at sequence #{rec.sequence_number}: stored previous_hash "
                    f"'{rec.previous_hash}' does not match expected hash '{expected_prev_hash}'."
                )

            # Recompute canonical hash
            ts_str = rec.timestamp.strftime("%Y-%m-%dT%H:%M:%SZ") if rec.timestamp else ""
            recomputed_payload = ApprovalAuditRecord.canonical_payload(
                sequence_number=rec.sequence_number,
                proposal_id=rec.proposal_id,
                decision=rec.decision,
                final_text=rec.final_text,
                decision_notes=rec.decision_notes,
                timestamp_iso=ts_str,
                previous_hash=rec.previous_hash,
            )
            recomputed_hash = ApprovalAuditRecord.calculate_hash(recomputed_payload)

            if rec.current_hash != recomputed_hash:
                return False, (
                    f"Tampered record detected at sequence #{rec.sequence_number}: "
                    f"stored current_hash '{rec.current_hash}' != recomputed '{recomputed_hash}'. "
                    f"Payload content was modified post-finalization."
                )

            expected_seq += 1
            expected_prev_hash = rec.current_hash

        return True, None
