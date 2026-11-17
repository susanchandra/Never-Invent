"""
workflow/pipeline.py — End-to-end verification and proposal assembly pipeline.

Design contracts:
- Routes every generated proposal through atomic claim extraction and verification.
- Re-verifies every manual edit prior to approval.
- Preserves verbatim evidence anchors and source spans.
- Flags unsupported claims prominently without suppressing them.
- Disallows silent acceptance of extractions that yield zero claims.
"""

from __future__ import annotations

import datetime
from typing import Optional

from neverinvent.claims.extractor import ClaimExtractor
from neverinvent.claims.models import Claim, ClaimType
from neverinvent.generation.models import GenerationType
from neverinvent.parsing.models import CandidateProfile, ExtractionStatus
from neverinvent.verification.models import Verdict, VerificationResult
from neverinvent.verification.verifier import ClaimVerifier
from neverinvent.workflow.diff_helper import compute_diff
from neverinvent.workflow.models import (
    ApprovalDecision,
    ProposalStatus,
    VerifiedProposal,
)


class VerificationPipeline:
    """Orchestrates claim extraction, independent verification, and proposal packaging."""

    def __init__(
        self,
        extractor: Optional[ClaimExtractor] = None,
        verifier: Optional[ClaimVerifier] = None,
    ):
        self.extractor = extractor or ClaimExtractor()
        self.verifier = verifier or ClaimVerifier()

    def process_proposal(
        self,
        proposed_text: str,
        candidate_profile: CandidateProfile,
        original_text: Optional[str] = None,
        generation_type: GenerationType = GenerationType.RESUME_BULLET_SUGGESTION,
        provider: str = "mock",
        model_name: str = "default",
    ) -> VerifiedProposal:
        """
        Extract claims, verify each against the candidate profile, compute diff, and package.
        """
        warnings: list[str] = []
        clean_text = proposed_text.strip()
        proposal_id = VerifiedProposal.make_id(clean_text, generation_type)

        # 1. Atomic claim extraction
        claims = self.extractor.extract(clean_text)

        # Safety check: if no claims extracted, do not silently accept
        if not claims:
            warnings.append(
                "No typed atomic claims detected in proposal. Flagged for mandatory human review."
            )
            fallback_claim = Claim(
                claim_id=Claim.make_id(clean_text, ClaimType.RESPONSIBILITY),
                original_claim_text=clean_text,
                normalized_value=clean_text.lower()[:100],
                claim_type=ClaimType.RESPONSIBILITY,
                extraction_method="fallback_unparsed",
                extraction_confidence=ExtractionStatus.UNCERTAIN,
                source_text=clean_text,
            )
            claims = [fallback_claim]

        # 2. Independent Verification
        results: list[VerificationResult] = [
            self.verifier.verify(c, candidate_profile) for c in claims
        ]

        # 3. Status determination
        sup_cnt = sum(1 for r in results if r.final_verdict == Verdict.SUPPORTED)
        unsup_cnt = sum(1 for r in results if r.final_verdict == Verdict.UNSUPPORTED)
        amb_cnt = sum(1 for r in results if r.final_verdict == Verdict.AMBIGUOUS)

        if unsup_cnt > 0:
            status = ProposalStatus.CONTAINS_UNSUPPORTED
        elif amb_cnt > 0:
            status = ProposalStatus.CONTAINS_AMBIGUOUS
        elif sup_cnt > 0:
            status = ProposalStatus.ALL_SUPPORTED
        else:
            status = ProposalStatus.EXTRACTION_WARNING

        # 4. Diff calculation
        diffs = compute_diff(original_text, clean_text)

        return VerifiedProposal(
            proposal_id=proposal_id,
            generation_type=generation_type,
            original_text=original_text,
            proposed_text=clean_text,
            provider=provider,
            model_name=model_name,
            claims=claims,
            verification_results=results,
            status=status,
            supported_count=sup_cnt,
            unsupported_count=unsup_cnt,
            ambiguous_count=amb_cnt,
            requires_human_review=True,  # All proposals require human review before approval
            warnings=warnings,
            diff_highlights=diffs,
            decision=ApprovalDecision.PENDING,
        )

    def reverify_manual_edit(
        self,
        original_proposal: VerifiedProposal,
        edited_text: str,
        candidate_profile: CandidateProfile,
    ) -> VerifiedProposal:
        """
        Re-verifies user-modified text before approval is committed.
        """
        reverified = self.process_proposal(
            proposed_text=edited_text,
            candidate_profile=candidate_profile,
            original_text=original_proposal.original_text,
            generation_type=original_proposal.generation_type,
            provider="manual_user_edit",
            model_name="human",
        )
        return reverified
