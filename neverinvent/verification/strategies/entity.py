"""
verification/strategies/entity.py — Entity verification strategy for employers, institutions, and certs.
"""

from __future__ import annotations

from neverinvent.claims.models import Claim, ClaimType, Evidence
from neverinvent.parsing.models import CandidateProfile
from neverinvent.verification.alias_registry import (
    canonicalize_company,
    canonicalize_degree,
)
from neverinvent.verification.models import StrategyResult, Verdict, VerificationStrategy


def verify_entity(claim: Claim, profile: CandidateProfile) -> StrategyResult:
    """
    Verifies EMPLOYER, EDUCATION, CERTIFICATION, and PROJECT entity claims.
    """
    matched: list[Evidence] = []
    target = (claim.subject or claim.normalized_value or claim.original_claim_text).strip().lower()

    if claim.claim_type == ClaimType.EMPLOYER:
        c_target = canonicalize_company(target)
        for i, exp in enumerate(profile.experience):
            if canonicalize_company(exp.company) == c_target or target in exp.original_company_text.lower():
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
        c_target = canonicalize_degree(target)
        for i, edu in enumerate(profile.education):
            if (
                target in edu.original_institution_text.lower()
                or (edu.degree and canonicalize_degree(edu.degree) == c_target)
                or (edu.field_of_study and target in edu.field_of_study.lower())
            ):
                matched.append(
                    Evidence(
                        evidence_id=Evidence.make_id(edu.original_institution_text, f"education[{i}]"),
                        evidence_text=f"{edu.institution} - {edu.degree or ''}",
                        source_span=edu.source_span,
                        evidence_type="education",
                        profile_field=f"education[{i}]",
                    )
                )

    elif claim.claim_type == ClaimType.CERTIFICATION:
        for i, cert in enumerate(profile.certifications):
            if target in cert.original_text.lower() or (cert.issuer and target in cert.issuer.lower()):
                matched.append(
                    Evidence(
                        evidence_id=Evidence.make_id(cert.original_text, f"certifications[{i}]"),
                        evidence_text=cert.original_text,
                        source_span=cert.source_span,
                        evidence_type="certification",
                        profile_field=f"certifications[{i}]",
                    )
                )

    elif claim.claim_type == ClaimType.PROJECT:
        for i, proj in enumerate(profile.projects):
            if target in proj.name.lower() or target in proj.original_text.lower():
                matched.append(
                    Evidence(
                        evidence_id=Evidence.make_id(proj.original_text, f"projects[{i}]"),
                        evidence_text=proj.original_text,
                        source_span=proj.source_span,
                        evidence_type="project",
                        profile_field=f"projects[{i}]",
                    )
                )

    if matched:
        return StrategyResult(
            strategy=VerificationStrategy.ENTITY,
            verdict=Verdict.SUPPORTED,
            matched_evidence=matched,
            explanation=f"Entity verified in profile: '{matched[0].evidence_text}'",
            confidence=0.95,
        )

    return StrategyResult(
        strategy=VerificationStrategy.ENTITY,
        verdict=Verdict.AMBIGUOUS,
        explanation=f"Entity '{target}' not explicitly found in profile.",
        confidence=0.5,
    )
