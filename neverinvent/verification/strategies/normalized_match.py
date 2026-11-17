"""
verification/strategies/normalized_match.py — Case, whitespace, and punctuation normalized match.
"""

from __future__ import annotations

import re

from neverinvent.claims.models import Claim, Evidence
from neverinvent.parsing.models import CandidateProfile
from neverinvent.verification.evidence_extractor import get_profile_evidence
from neverinvent.verification.models import StrategyResult, Verdict, VerificationStrategy


def _normalize_str(s: str) -> str:
    cleaned = s.lower().strip()
    cleaned = re.sub(r"[\s\-_,\.;:\(\)\[\]]+", " ", cleaned)
    return cleaned.strip()


def verify_normalized_match(claim: Claim, profile: CandidateProfile) -> StrategyResult:
    """
    Checks whether normalized claim value matches normalized evidence text.
    """
    target = _normalize_str(claim.normalized_value or claim.original_claim_text)
    if not target:
        return StrategyResult(
            strategy=VerificationStrategy.NORMALIZED_MATCH,
            verdict=Verdict.AMBIGUOUS,
            explanation="Empty normalized claim text.",
            confidence=0.0,
        )

    evidence_items = get_profile_evidence(profile)
    matched: list[Evidence] = []

    pattern = re.compile(rf"(?:^|\s){re.escape(target)}(?:\s|$)")
    for ev in evidence_items:
        norm_ev = _normalize_str(ev.evidence_text)
        if target == norm_ev or bool(pattern.search(norm_ev)):
            matched.append(ev)

    if matched:
        return StrategyResult(
            strategy=VerificationStrategy.NORMALIZED_MATCH,
            verdict=Verdict.SUPPORTED,
            matched_evidence=matched,
            explanation=f"Found normalized match in resume evidence: '{matched[0].evidence_text}'",
            confidence=0.95,
        )

    return StrategyResult(
        strategy=VerificationStrategy.NORMALIZED_MATCH,
        verdict=Verdict.AMBIGUOUS,
        explanation="No normalized match found in resume evidence.",
        confidence=0.5,
    )
