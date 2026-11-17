"""
generation/explainer.py — Job-match explanation service.

Produces unverified match explanation proposals for candidate-job pairs.
All outputs must be routed to verification before being shown to users.
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
from neverinvent.retrieval.models import RetrievalResult


class JobMatchExplainer:
    """Generates unverified candidate-job match explanation text."""

    def __init__(self, generator: Optional[BaseGenerator] = None):
        self.generator = generator or MockGenerator()

    def explain_match(
        self,
        candidate_profile: CandidateProfile,
        job_description: JobDescription,
        retrieval_result: Optional[RetrievalResult] = None,
        mode: GenerationMode = GenerationMode.FAITHFUL,
    ) -> GenerationResponse:
        """
        Produce a proposed explanation of why the candidate fits the job.
        """
        req = GenerationRequest(
            candidate_profile=candidate_profile,
            job_description=job_description,
            generation_type=GenerationType.JOB_MATCH_EXPLANATION,
            mode=mode,
        )
        return self.generator.generate(req)
