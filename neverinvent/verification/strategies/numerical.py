"""
verification/strategies/numerical.py — Numerical and quantitative verification strategy.

Checks metrics, quantities, percentages, and units against profile evidence.
Detects metric inflation, altered values, and unit mismatches.
"""

from __future__ import annotations

import math
import re
from typing import Optional

from neverinvent.claims.models import Claim, ClaimType, Evidence
from neverinvent.parsing.models import CandidateProfile
from neverinvent.verification.models import StrategyResult, Verdict, VerificationStrategy

_GENERIC_STOP_WORDS = {
    "the", "a", "an", "and", "or", "in", "by", "of", "to", "for", "with", "at", "from", "on", "into", "across",
    "improved", "improving", "improve",
    "increased", "increasing", "increase",
    "reduced", "reducing", "reduce",
    "decreased", "decreasing", "decrease",
    "scaled", "scaling", "scale",
    "boosted", "boosting", "boost",
    "achieved", "achieving", "achieve",
    "delivered", "delivering", "deliver",
    "handling", "handled", "handle",
    "up", "down", "more", "than", "over", "about", "approx",
}


def verify_numerical(claim: Claim, profile: CandidateProfile) -> StrategyResult:
    """
    Verifies numerical claims (METRIC, QUANTITY) against CandidateProfile metrics.
    """
    if claim.claim_type not in (ClaimType.METRIC, ClaimType.QUANTITY) and claim.numeric_value is None:
        return StrategyResult(
            strategy=VerificationStrategy.NUMERICAL,
            verdict=Verdict.AMBIGUOUS,
            explanation="Not a numerical claim.",
            confidence=0.5,
        )

    val = claim.numeric_value
    if val is None:
        return StrategyResult(
            strategy=VerificationStrategy.NUMERICAL,
            verdict=Verdict.AMBIGUOUS,
            explanation="Numerical claim has no parsed numeric value.",
            confidence=0.5,
        )

    unit = (claim.unit or "").lower().rstrip("s")
    matched: list[Evidence] = []
    contradicting: list[Evidence] = []

    # Check each metric in CandidateProfile
    for i, m in enumerate(profile.metrics):
        m_unit = (m.unit or "").lower().rstrip("s")
        same_unit = (unit == m_unit) or (not unit and not m_unit)

        # Build evidence item
        ev = Evidence(
            evidence_id=Evidence.make_id(m.raw_metric_text, f"metrics[{i}]"),
            evidence_text=m.raw_metric_text,
            source_span=m.source_span,
            evidence_type="metric",
            profile_field=f"metrics[{i}]",
        )

        if math.isclose(val, m.quantity, rel_tol=1e-3, abs_tol=1e-3) and same_unit:
            matched.append(ev)
        else:
            # Check if there is contextual overlap indicating this is an altered/inflated version
            claim_ctx = (claim.source_text or claim.original_claim_text).lower()
            ev_ctx = m.context.lower()
            
            # Extract non-generic content words
            words_claim = set(re.findall(r"\b[a-zA-Z]{3,}\b", claim_ctx)) - _GENERIC_STOP_WORDS
            words_ev = set(re.findall(r"\b[a-zA-Z]{3,}\b", ev_ctx)) - _GENERIC_STOP_WORDS
            overlap = words_claim.intersection(words_ev)
            
            # Non-generic domain context must overlap to constitute a true contradiction
            if len(overlap) >= 2 or (len(overlap) >= 1 and same_unit):
                contradicting.append(ev)

    if matched:
        return StrategyResult(
            strategy=VerificationStrategy.NUMERICAL,
            verdict=Verdict.SUPPORTED,
            matched_evidence=matched,
            explanation=f"Found matching numerical metric in profile: {matched[0].evidence_text}",
            confidence=1.0,
        )

    if contradicting:
        return StrategyResult(
            strategy=VerificationStrategy.NUMERICAL,
            verdict=Verdict.UNSUPPORTED,
            contradicting_evidence=contradicting,
            explanation=(
                f"Numerical value {val}{unit} contradicts documented metric: "
                f"'{contradicting[0].evidence_text}'"
            ),
            confidence=0.95,
        )

    return StrategyResult(
        strategy=VerificationStrategy.NUMERICAL,
        verdict=Verdict.AMBIGUOUS,
        explanation=f"No matching or contradicting metric of value {val}{unit} found in profile.",
        confidence=0.5,
    )
