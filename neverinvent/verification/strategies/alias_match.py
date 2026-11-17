"""
verification/strategies/alias_match.py — Canonical alias match strategy for skills, companies, and degrees.
"""

from __future__ import annotations

from neverinvent.claims.models import Claim, ClaimType, Evidence
from neverinvent.parsing.models import CandidateProfile
from neverinvent.verification.alias_registry import (
    canonicalize_company,
    canonicalize_degree,
    canonicalize_skill,
)
from neverinvent.verification.evidence_extractor import get_profile_evidence
from neverinvent.verification.models import StrategyResult, Verdict, VerificationStrategy


def verify_alias_match(claim: Claim, profile: CandidateProfile) -> StrategyResult:
    """
    Checks if canonical form of claim matches canonical form of profile evidence.
    """
    matched: list[Evidence] = []
    target = claim.normalized_value or claim.original_claim_text

    if claim.claim_type == ClaimType.SKILL:
        canon_claim = canonicalize_skill(target)
        for i, s in enumerate(profile.skills):
            if canonicalize_skill(s.name) == canon_claim or canonicalize_skill(s.original_text) == canon_claim:
                matched.append(
                    Evidence(
                        evidence_id=Evidence.make_id(s.original_text, f"skills[{i}]"),
                        evidence_text=s.original_text,
                        source_span=s.source_span,
                        evidence_type="skill",
                        profile_field=f"skills[{i}]",
                    )
                )

    elif claim.claim_type == ClaimType.EMPLOYER:
        canon_claim = canonicalize_company(target)
        for i, exp in enumerate(profile.experience):
            if canonicalize_company(exp.company) == canon_claim or canonicalize_company(exp.original_company_text) == canon_claim:
                matched.append(
                    Evidence(
                        evidence_id=Evidence.make_id(exp.original_company_text, f"experience[{i}].company"),
                        evidence_text=exp.original_company_text,
                        source_span=exp.source_span,
                        evidence_type="company",
                        profile_field=f"experience[{i}].company",
                    )
                )

    elif claim.claim_type == ClaimType.EDUCATION:
        canon_claim = canonicalize_degree(target)
        for i, edu in enumerate(profile.education):
            if edu.degree and canonicalize_degree(edu.degree) == canon_claim:
                matched.append(
                    Evidence(
                        evidence_id=Evidence.make_id(edu.degree, f"education[{i}].degree"),
                        evidence_text=edu.degree,
                        source_span=edu.source_span,
                        evidence_type="degree",
                        profile_field=f"education[{i}].degree",
                    )
                )

    if matched:
        return StrategyResult(
            strategy=VerificationStrategy.ALIAS_MATCH,
            verdict=Verdict.SUPPORTED,
            matched_evidence=matched,
            explanation=f"Found canonical alias match in resume evidence: '{matched[0].evidence_text}'",
            confidence=0.95,
        )

    return StrategyResult(
        strategy=VerificationStrategy.ALIAS_MATCH,
        verdict=Verdict.AMBIGUOUS,
        explanation="No canonical alias match found in resume evidence.",
        confidence=0.5,
    )
