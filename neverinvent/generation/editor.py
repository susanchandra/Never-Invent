"""
generation/editor.py — Resume bullet suggestion service.

Produces unverified tailored resume bullet suggestions.
All proposed edits must pass through atomic claim extraction and verification.
"""

from __future__ import annotations

from typing import Optional

from neverinvent.generation.models import (
    GenerationMode,
    GenerationRequest,
    GenerationResponse,
    GenerationType,
)
from neverinvent.generation.provider import BaseGenerator, MockGenerator
from neverinvent.jobs.models import JobDescription
from neverinvent.parsing.models import CandidateProfile


class ResumeBulletEditor:
    """Generates unverified bullet point suggestions tailored to a target job."""

    def __init__(self, generator: Optional[BaseGenerator] = None):
        self.generator = generator or MockGenerator()

    def suggest_bullet(
        self,
        candidate_profile: CandidateProfile,
        job_description: JobDescription,
        target_bullet: str,
        mode: GenerationMode = GenerationMode.FAITHFUL,
    ) -> GenerationResponse:
        """
        Produce a tailored bullet suggestion for the target role.
        """
        req = GenerationRequest(
            candidate_profile=candidate_profile,
            job_description=job_description,
            generation_type=GenerationType.RESUME_BULLET_SUGGESTION,
            mode=mode,
            target_bullet=target_bullet,
        )
        return self.generator.generate(req)
