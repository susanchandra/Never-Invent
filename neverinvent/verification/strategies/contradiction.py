"""
verification/strategies/contradiction.py — Explicit contradiction detection strategy.

Detects contradictory claims against documented candidate profile records:
- Contradictory job titles (e.g. claiming "VP of Engineering" or "Chief Architect" when documented title is "Senior Machine Learning Engineer")
- Contradictory project ownership
- Direct conflicts with documented facts
"""

from __future__ import annotations

import re

from neverinvent.claims.models import Claim, ClaimType, Evidence
from neverinvent.parsing.models import CandidateProfile
from neverinvent.verification.alias_registry import canonicalize_company
from neverinvent.verification.models import StrategyResult, Verdict, VerificationStrategy


_SENIORITY_HIERARCHY = {
    "intern": 1,
    "junior": 2,
    "associate": 2,
    "mid": 3,
    "senior": 4,
    "staff": 5,
    "principal": 6,
    "lead": 5,
    "manager": 5,
    "director": 7,
    "vp": 8,
    "vice president": 8,
    "head of": 7,
    "cto": 9,
    "cio": 9,
    "ceo": 9,
}


def verify_contradiction(claim: Claim, profile: CandidateProfile) -> StrategyResult:
    """
    Checks if a claim directly contradicts documented facts in the candidate profile.
    """
    contradicting: list[Evidence] = []
    text = (claim.source_text or claim.original_claim_text).lower()

    # 1. Job Title Contradiction (e.g. claiming VP / Director / Chief Architect when profile says Senior Engineer)
    if claim.claim_type in (ClaimType.JOB_TITLE, ClaimType.RESPONSIBILITY):
        for i, exp in enumerate(profile.experience):
            c_norm = canonicalize_company(exp.company)
            if c_norm in text or exp.original_company_text.lower() in text:
                doc_title = (exp.title or exp.original_title_text or "").lower()
                # Check for extreme seniority inflation
                if any(k in text for k in ["vp", "vice president", "director", "chief", "cto", "head of"]):
                    if not any(k in doc_title for k in ["vp", "vice president", "director", "chief", "cto", "head of"]):
                        contradicting.append(
                            Evidence(
                                evidence_id=Evidence.make_id(doc_title, f"experience[{i}].title"),
                                evidence_text=f"Documented role at {exp.company}: '{doc_title}'",
                                source_span=exp.source_span,
                                evidence_type="job_title",
                                profile_field=f"experience[{i}].title",
                            )
                        )

    # 2. Project ownership contradiction (claiming to be sole creator/founder of a team employer project)
    if claim.claim_type == ClaimType.PROJECT:
        if "founded" in text or "sole creator" in text or "co-founder" in text:
            for i, proj in enumerate(profile.projects):
                if proj.name.lower() in text:
                    contradicting.append(
                        Evidence(
                            evidence_id=Evidence.make_id(proj.original_text, f"projects[{i}]"),
                            evidence_text=proj.original_text,
                            source_span=proj.source_span,
                            evidence_type="project",
                            profile_field=f"projects[{i}]",
                        )
                    )

    if contradicting:
        return StrategyResult(
            strategy=VerificationStrategy.CONTRADICTION,
            verdict=Verdict.UNSUPPORTED,
            contradicting_evidence=contradicting,
            explanation=f"Claim explicitly contradicts documented resume facts: {contradicting[0].evidence_text}",
            confidence=0.95,
        )

    return StrategyResult(
        strategy=VerificationStrategy.CONTRADICTION,
        verdict=Verdict.AMBIGUOUS,
        explanation="No explicit contradiction detected with documented facts.",
        confidence=0.5,
    )
