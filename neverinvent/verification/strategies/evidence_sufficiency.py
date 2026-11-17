"""
verification/strategies/evidence_sufficiency.py — Evidence sufficiency check.

Determines whether sufficient grounding evidence exists in the resume profile.
Under strict closed-world check for explicit sections (such as candidate skills list
or formal education), if an entity is completely absent from a comprehensive list,
it flags it accordingly. Otherwise, missing evidence defaults to AMBIGUOUS.
"""

from __future__ import annotations

from neverinvent.claims.models import Claim, ClaimType, Evidence
from neverinvent.parsing.models import CandidateProfile
from neverinvent.verification.alias_registry import canonicalize_company, canonicalize_skill
from neverinvent.verification.models import StrategyResult, Verdict, VerificationStrategy


def verify_evidence_sufficiency(
    claim: Claim,
    profile: CandidateProfile,
    strict_closed_world: bool = True,
) -> StrategyResult:
    """
    Evaluates evidence sufficiency for a claim.

    When strict_closed_world is True:
    - SKILL claims: if candidate profile has an explicit skills section and the skill
      is completely absent, returns UNSUPPORTED (invented skill).
    - Other claims without evidence return AMBIGUOUS (requiring human review).
    """
    target = (claim.normalized_value or claim.original_claim_text).strip().lower()

    if strict_closed_world and claim.claim_type == ClaimType.SKILL:
        if profile.skills:  # Profile has documented skills
            canon_target = canonicalize_skill(target)
            known_skills = {canonicalize_skill(s.name) for s in profile.skills} | {
                canonicalize_skill(s.original_text) for s in profile.skills
            }
            if canon_target not in known_skills:
                return StrategyResult(
                    strategy=VerificationStrategy.EVIDENCE_SUFFICIENCY,
                    verdict=Verdict.UNSUPPORTED,
                    explanation=(
                        f"Skill '{claim.original_claim_text}' is completely absent from "
                        f"the candidate's documented skills inventory ({len(profile.skills)} skills listed)."
                    ),
                    confidence=0.90,
                )

    return StrategyResult(
        strategy=VerificationStrategy.EVIDENCE_SUFFICIENCY,
        verdict=Verdict.AMBIGUOUS,
        explanation=f"Insufficient resume evidence to verify claim '{claim.original_claim_text}'.",
        confidence=0.5,
    )
