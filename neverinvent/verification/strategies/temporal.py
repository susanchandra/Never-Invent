"""
verification/strategies/temporal.py — Temporal verification strategy for dates and durations.

Checks start/end dates, total experience duration, and role tenures.
Detects duration exaggeration and date alterations.
"""

from __future__ import annotations

import re
from typing import Optional

from neverinvent.claims.models import Claim, ClaimType, Evidence
from neverinvent.parsing.models import CandidateProfile
from neverinvent.parsing.normalizers import calculate_duration_months, normalize_date
from neverinvent.verification.alias_registry import canonicalize_company
from neverinvent.verification.models import StrategyResult, Verdict, VerificationStrategy


def _parse_month_index(date_str: Optional[str]) -> Optional[int]:
    if not date_str:
        return None
    if str(date_str).strip().lower() in ("present", "current", "now", "ongoing"):
        return 2026 * 12 + 11
    try:
        parts = str(date_str).strip().split("-")
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        return year * 12 + month
    except (ValueError, IndexError):
        return None


def _calculate_total_calendar_months(experiences: list) -> tuple[int, bool]:
    """
    Calculate total unique calendar months of experience by merging overlapping intervals.
    Prevents double-counting concurrent roles.
    """
    intervals: list[tuple[int, int]] = []
    has_any = False
    undated_months = 0

    for exp in experiences:
        s_idx = _parse_month_index(exp.start_date)
        e_idx = _parse_month_index(exp.end_date)
        if s_idx is not None and e_idx is not None and e_idx >= s_idx:
            intervals.append((s_idx, e_idx))
            has_any = True
        elif exp.duration_months is not None and exp.duration_months > 0:
            undated_months += exp.duration_months
            has_any = True

    if not intervals:
        return undated_months, has_any

    # Merge overlapping or contiguous calendar intervals
    intervals.sort(key=lambda x: x[0])
    merged = [list(intervals[0])]
    for s, e in intervals[1:]:
        prev_s, prev_e = merged[-1]
        if s <= prev_e + 1:  # overlapping or contiguous
            merged[-1][1] = max(prev_e, e)
        else:
            merged.append([s, e])

    # Each interval [s, e] covers (e - s + 1) calendar months
    total_months = sum((e - s + 1) for s, e in merged) + undated_months
    return total_months, has_any


def verify_temporal(claim: Claim, profile: CandidateProfile) -> StrategyResult:
    """
    Verifies DATE and DURATION claims against CandidateProfile work experience.
    """
    if claim.claim_type not in (ClaimType.DATE, ClaimType.DURATION):
        return StrategyResult(
            strategy=VerificationStrategy.TEMPORAL,
            verdict=Verdict.AMBIGUOUS,
            explanation="Not a temporal claim.",
            confidence=0.5,
        )

    matched: list[Evidence] = []
    contradicting: list[Evidence] = []

    # Case 1: DURATION claim (e.g. "5 years of experience" or "10 years")
    if claim.claim_type == ClaimType.DURATION and claim.numeric_value is not None:
        qty = claim.numeric_value
        unit = (claim.unit or "").lower()
        claimed_months = qty * 12.0 if "year" in unit else qty

        # Compute merged calendar duration across all candidate roles
        total_months, has_calculated_any = _calculate_total_calendar_months(profile.experience)

        if has_calculated_any:
            # If claimed duration exceeds total documented experience by more than 12 months,
            # it is an exaggeration
            if claimed_months > total_months + 12:
                # Build contradicting evidence
                for i, exp in enumerate(profile.experience):
                    text = f"{exp.company}: {exp.start_date} to {exp.end_date} ({exp.duration_months or 'unknown'} months)"
                    contradicting.append(
                        Evidence(
                            evidence_id=Evidence.make_id(text, f"experience[{i}]"),
                            evidence_text=text,
                            source_span=exp.source_span,
                            evidence_type="duration",
                            profile_field=f"experience[{i}]",
                        )
                    )
                return StrategyResult(
                    strategy=VerificationStrategy.TEMPORAL,
                    verdict=Verdict.UNSUPPORTED,
                    contradicting_evidence=contradicting,
                    explanation=(
                        f"Claimed duration {qty} {unit} (~{claimed_months:.0f} months) significantly "
                        f"exceeds total documented experience ({total_months} months)."
                    ),
                    confidence=0.95,
                )
            elif abs(claimed_months - total_months) <= 12 or claimed_months <= total_months:
                for i, exp in enumerate(profile.experience):
                    matched.append(
                        Evidence(
                            evidence_id=Evidence.make_id(exp.company, f"experience[{i}]"),
                            evidence_text=f"{exp.company}: {exp.start_date} to {exp.end_date}",
                            source_span=exp.source_span,
                            evidence_type="duration",
                            profile_field=f"experience[{i}]",
                        )
                    )
                return StrategyResult(
                    strategy=VerificationStrategy.TEMPORAL,
                    verdict=Verdict.SUPPORTED,
                    matched_evidence=matched,
                    explanation=f"Claimed duration {qty} {unit} is consistent with documented experience ({total_months} months).",
                    confidence=0.90,
                )

    # Case 2: DATE claim (e.g. start/end dates for a specific employer)
    if claim.claim_type == ClaimType.DATE:
        claim_start = claim.temporal_start
        claim_end = claim.temporal_end

        # Check if an employer is mentioned in the claim context
        context_text = (claim.source_text or claim.original_claim_text).lower()

        for i, exp in enumerate(profile.experience):
            c_norm = canonicalize_company(exp.company)
            orig_norm = exp.original_company_text.lower()

            if c_norm in context_text or orig_norm in context_text:
                exp_text = f"{exp.company}: {exp.start_date} - {exp.end_date}"
                ev = Evidence(
                    evidence_id=Evidence.make_id(exp_text, f"experience[{i}]"),
                    evidence_text=exp_text,
                    source_span=exp.source_span,
                    evidence_type="date",
                    profile_field=f"experience[{i}]",
                )

                # If start date is specified and differs from resume start date
                if claim_start and exp.start_date:
                    if claim_start == exp.start_date:
                        matched.append(ev)
                    else:
                        contradicting.append(ev)

                # If end date is specified and differs
                if claim_end and exp.end_date:
                    if claim_end == exp.end_date:
                        matched.append(ev)
                    else:
                        contradicting.append(ev)

        if matched and not contradicting:
            return StrategyResult(
                strategy=VerificationStrategy.TEMPORAL,
                verdict=Verdict.SUPPORTED,
                matched_evidence=matched,
                explanation=f"Dates match resume tenure: {matched[0].evidence_text}",
                confidence=1.0,
            )

        if contradicting:
            return StrategyResult(
                strategy=VerificationStrategy.TEMPORAL,
                verdict=Verdict.UNSUPPORTED,
                contradicting_evidence=contradicting,
                explanation=f"Claimed dates contradict documented tenure: {contradicting[0].evidence_text}",
                confidence=0.95,
            )

    return StrategyResult(
        strategy=VerificationStrategy.TEMPORAL,
        verdict=Verdict.AMBIGUOUS,
        explanation="Date or duration claim cannot be conclusively verified against documented experience.",
        confidence=0.5,
    )
