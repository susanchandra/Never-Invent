"""
verification/strategies/exact_match.py — Exact verbatim string match strategy.
"""

from __future__ import annotations

from neverinvent.claims.models import Claim, Evidence
from neverinvent.parsing.models import CandidateProfile
from neverinvent.verification.evidence_extractor import get_profile_evidence
from neverinvent.verification.models import StrategyResult, Verdict, VerificationStrategy


def verify_exact_match(claim: Claim, profile: CandidateProfile) -> StrategyResult:
    """
    Checks whether the exact claim text appears verbatim in candidate evidence.
    """
    target = claim.original_claim_text.strip()
    if not target:
        return StrategyResult(
            strategy=VerificationStrategy.EXACT_MATCH,
            verdict=Verdict.AMBIGUOUS,
            explanation="Empty claim text cannot be verified by exact match.",
            confidence=0.0,
        )

    evidence_items = get_profile_evidence(profile)
    matched: list[Evidence] = []

    for ev in evidence_items:
        # Check if target appears verbatim or as a whole word/phrase in evidence
        if target.lower() == ev.evidence_text.strip().lower() or target in ev.evidence_text:
            matched.append(ev)

    if matched:
        return StrategyResult(
            strategy=VerificationStrategy.EXACT_MATCH,
            verdict=Verdict.SUPPORTED,
            matched_evidence=matched,
            explanation=f"Found exact match in resume evidence: '{matched[0].evidence_text}'",
            confidence=1.0,
        )

    return StrategyResult(
        strategy=VerificationStrategy.EXACT_MATCH,
        verdict=Verdict.AMBIGUOUS,
        explanation="No exact verbatim match found in resume evidence.",
        confidence=0.5,
    )
