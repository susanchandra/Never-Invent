"""
matching/matcher.py — Evidence-grounded candidate-job matcher and dealbreaker engine.

Design contracts:
- Reuses CandidateProfile and JobDescription without modifying them.
- Separates required skills from preferred skills.
- Reuses canonical skill aliases from verification.alias_registry.
- Strict provenance: every supported requirement attaches an inspectable Evidence reference.
- Deterministic dealbreaker evaluation. Missing resume fields are not assumed ineligible.
- Grounded match score is calculated with an explicit, documented formula:
    score = (supported_required / max(1, total_required)) * 0.70
          + (supported_preferred / max(1, total_preferred)) * 0.30
"""

from __future__ import annotations

from typing import Optional

from neverinvent.claims.models import Evidence
from neverinvent.jobs.models import JobDescription
from neverinvent.matching.models import (
    DealbreakerResult,
    MatchBreakdown,
    SkillMatchItem,
    SkillMatchStatus,
)
from neverinvent.parsing.models import CandidateProfile
from neverinvent.parsing.normalizers import calculate_duration_months
from neverinvent.verification.alias_registry import canonicalize_degree, canonicalize_skill
from neverinvent.verification.strategies.temporal import _calculate_total_calendar_months


class EvidenceGroundedMatcher:
    """
    Evaluates candidate eligibility and skill coverage against a job description.
    """

    def __init__(self, min_required_skill_ratio: float = 0.0):
        self.min_required_skill_ratio = min_required_skill_ratio

    def match(
        self, candidate_profile: CandidateProfile, job_description: JobDescription
    ) -> MatchBreakdown:
        """
        Evaluate candidate evidence against job requirements.
        """
        # 1. Match Required Skills
        req_items: list[SkillMatchItem] = []
        for req_skill in job_description.required_skills:
            item = self._match_skill(req_skill, candidate_profile, is_required=True)
            req_items.append(item)

        # 2. Match Preferred Skills
        pref_items: list[SkillMatchItem] = []
        for pref_skill in job_description.preferred_skills:
            item = self._match_skill(pref_skill, candidate_profile, is_required=False)
            pref_items.append(item)

        # Counts
        sup_req = sum(1 for i in req_items if i.status == SkillMatchStatus.SUPPORTED)
        tot_req = len(req_items)
        sup_pref = sum(1 for i in pref_items if i.status == SkillMatchStatus.SUPPORTED)
        tot_pref = len(pref_items)

        # Calculate explicitly defined match score with empty category normalization
        if tot_req > 0 and tot_pref > 0:
            req_ratio = sup_req / tot_req
            pref_ratio = sup_pref / tot_pref
            score = round(req_ratio * 0.70 + pref_ratio * 0.30, 4)
        elif tot_req > 0 and tot_pref == 0:
            req_ratio = sup_req / tot_req
            pref_ratio = 0.0
            score = round(req_ratio * 1.00, 4)
        elif tot_req == 0 and tot_pref > 0:
            req_ratio = 0.0
            pref_ratio = sup_pref / tot_pref
            score = round(pref_ratio * 1.00, 4)
        else:
            req_ratio = 0.0
            pref_ratio = 0.0
            score = 0.0

        # 3. Evaluate Dealbreakers
        dealbreaker = self._evaluate_dealbreakers(candidate_profile, job_description, req_ratio)

        if tot_req == 0 and tot_pref == 0:
            explanation = (
                "Insufficient job information: Job description specifies no required or preferred skills. "
                f"Grounded Match Score: 0.0%. Dealbreaker Status: {'PASSED' if dealbreaker.passed else 'FAILED'}."
            )
        else:
            explanation = (
                f"Candidate matches {sup_req}/{tot_req} required skills and {sup_pref}/{tot_pref} "
                f"preferred skills. Grounded Match Score: {score * 100:.1f}%. "
                f"Dealbreaker Status: {'PASSED' if dealbreaker.passed else 'FAILED'}."
            )

        return MatchBreakdown(
            job_id=job_description.job_id,
            job_title=job_description.title,
            company=job_description.company,
            required_skills_match=req_items,
            preferred_skills_match=pref_items,
            dealbreaker_result=dealbreaker,
            supported_required_count=sup_req,
            total_required_count=tot_req,
            supported_preferred_count=sup_pref,
            total_preferred_count=tot_pref,
            grounded_match_score=score,
            explanation=explanation,
        )

    def _match_skill(
        self, skill_name: str, profile: CandidateProfile, is_required: bool
    ) -> SkillMatchItem:
        canon_target = canonicalize_skill(skill_name)

        for i, s in enumerate(profile.skills):
            if (
                canonicalize_skill(s.name) == canon_target
                or canonicalize_skill(s.original_text) == canon_target
            ):
                ev = Evidence(
                    evidence_id=Evidence.make_id(s.original_text, f"skills[{i}]"),
                    evidence_text=s.original_text,
                    source_span=s.source_span,
                    evidence_type="skill",
                    profile_field=f"skills[{i}]",
                )
                return SkillMatchItem(
                    skill_name=skill_name,
                    is_required=is_required,
                    status=SkillMatchStatus.SUPPORTED,
                    supporting_evidence=ev,
                )

        return SkillMatchItem(
            skill_name=skill_name,
            is_required=is_required,
            status=SkillMatchStatus.MISSING,
            supporting_evidence=None,
        )

    def _evaluate_dealbreakers(
        self,
        profile: CandidateProfile,
        job: JobDescription,
        required_skill_ratio: float,
    ) -> DealbreakerResult:
        checked: list[str] = []
        failed: list[str] = []

        # 1. Experience Duration Dealbreaker
        if job.min_years_experience is not None:
            checked.append(f"min_years_experience >= {job.min_years_experience}")
            total_months, has_experience_data = _calculate_total_calendar_months(profile.experience)

            # Only fail if experience is affirmatively documented and below requirement
            if has_experience_data:
                years = total_months / 12.0
                if years + 0.5 < job.min_years_experience:
                    failed.append(
                        f"Documented experience ({years:.1f} years) is below required minimum ({job.min_years_experience} years)."
                    )

        # 2. Minimum Education Level
        if job.education_level:
            checked.append(f"education_level >= {job.education_level}")
            req_degree = canonicalize_degree(job.education_level)
            cand_degrees = [
                canonicalize_degree(e.degree) for e in profile.education if e.degree
            ]
            if cand_degrees and req_degree not in cand_degrees:
                # Degree hierarchy check: if candidate has higher degree, accept
                # Simple hierarchy: doctorate > master of science > bachelor of science
                hierarchy = {
                    "bachelor of science": 1,
                    "master of science": 2,
                    "doctor of philosophy": 3,
                }
                cand_max = max((hierarchy.get(d, 0) for d in cand_degrees), default=0)
                req_level = hierarchy.get(req_degree, 0)
                if req_level > 0 and cand_max < req_level:
                    failed.append(
                        f"Documented education does not meet required {job.education_level}."
                    )

        # 3. Minimum Required Skill Coverage Dealbreaker
        if self.min_required_skill_ratio > 0.0:
            checked.append(f"required_skill_coverage >= {self.min_required_skill_ratio * 100:.0f}%")
            if required_skill_ratio < self.min_required_skill_ratio:
                failed.append(
                    f"Required skill coverage ({required_skill_ratio * 100:.1f}%) is below minimum threshold ({self.min_required_skill_ratio * 100:.0f}%)."
                )

        return DealbreakerResult(
            passed=len(failed) == 0,
            failed_reasons=failed,
            checked_criteria=checked,
        )
