"""
verification/evidence_extractor.py — Extracts structured Evidence items from a CandidateProfile.
"""

from __future__ import annotations

from neverinvent.claims.models import Evidence
from neverinvent.parsing.models import CandidateProfile


def get_profile_evidence(profile: CandidateProfile) -> list[Evidence]:
    """
    Extracts all grounded Evidence objects from the candidate profile.
    """
    evidence_list: list[Evidence] = []

    # 1. Skills
    for i, s in enumerate(profile.skills):
        evidence_list.append(
            Evidence(
                evidence_id=Evidence.make_id(s.original_text, f"skills[{i}]"),
                evidence_text=s.original_text,
                source_span=s.source_span,
                evidence_type="skill",
                profile_field=f"skills[{i}]",
            )
        )

    # 2. Experience
    for i, exp in enumerate(profile.experience):
        evidence_list.append(
            Evidence(
                evidence_id=Evidence.make_id(exp.original_company_text, f"experience[{i}].company"),
                evidence_text=exp.original_company_text,
                source_span=exp.source_span,
                evidence_type="company",
                profile_field=f"experience[{i}].company",
            )
        )
        if exp.original_title_text:
            evidence_list.append(
                Evidence(
                    evidence_id=Evidence.make_id(exp.original_title_text, f"experience[{i}].title"),
                    evidence_text=exp.original_title_text,
                    source_span=exp.source_span,
                    evidence_type="job_title",
                    profile_field=f"experience[{i}].title",
                )
            )
        for j, resp in enumerate(exp.responsibilities):
            evidence_list.append(
                Evidence(
                    evidence_id=Evidence.make_id(resp, f"experience[{i}].responsibilities[{j}]"),
                    evidence_text=resp,
                    source_span=exp.source_span,
                    evidence_type="responsibility",
                    profile_field=f"experience[{i}].responsibilities[{j}]",
                )
            )

    # 3. Education
    for i, edu in enumerate(profile.education):
        evidence_list.append(
            Evidence(
                evidence_id=Evidence.make_id(edu.original_institution_text, f"education[{i}].institution"),
                evidence_text=edu.original_institution_text,
                source_span=edu.source_span,
                evidence_type="institution",
                profile_field=f"education[{i}].institution",
            )
        )
        if edu.degree:
            evidence_list.append(
                Evidence(
                    evidence_id=Evidence.make_id(edu.degree, f"education[{i}].degree"),
                    evidence_text=edu.degree,
                    source_span=edu.source_span,
                    evidence_type="degree",
                    profile_field=f"education[{i}].degree",
                )
            )

    # 4. Certifications
    for i, cert in enumerate(profile.certifications):
        evidence_list.append(
            Evidence(
                evidence_id=Evidence.make_id(cert.original_text, f"certifications[{i}]"),
                evidence_text=cert.original_text,
                source_span=cert.source_span,
                evidence_type="certification",
                profile_field=f"certifications[{i}]",
            )
        )

    # 5. Projects
    for i, proj in enumerate(profile.projects):
        evidence_list.append(
            Evidence(
                evidence_id=Evidence.make_id(proj.original_text, f"projects[{i}]"),
                evidence_text=proj.original_text,
                source_span=proj.source_span,
                evidence_type="project",
                profile_field=f"projects[{i}]",
            )
        )

    # 6. Metrics
    for i, m in enumerate(profile.metrics):
        evidence_list.append(
            Evidence(
                evidence_id=Evidence.make_id(m.raw_metric_text, f"metrics[{i}]"),
                evidence_text=m.raw_metric_text,
                source_span=m.source_span,
                evidence_type="metric",
                profile_field=f"metrics[{i}]",
            )
        )

    return evidence_list
