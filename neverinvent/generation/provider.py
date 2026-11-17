"""
generation/provider.py — Provider abstraction, MockGenerator, and optional GroqGenerator.

Design contracts:
- Abstract interface: BaseGenerator.
- Deterministic MockGenerator supports faithful and controlled fabrication modes.
- Optional GroqGenerator with configurable model, temperature, and prompt.
- Never commits or leaks API keys.
- Output text is untrusted; never verified by the generator.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from typing import Optional

from neverinvent.generation.models import (
    GenerationMode,
    GenerationRequest,
    GenerationResponse,
    GenerationType,
)


class GenerationError(Exception):
    """Raised when text generation fails."""


class ProviderNotConfiguredError(GenerationError):
    """Raised when an optional provider lacks credentials or libraries."""


class BaseGenerator(ABC):
    """Abstract interface for all generation providers."""

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResponse:
        """Generate text proposal based on candidate profile and job description."""
        raise NotImplementedError


class MockGenerator(BaseGenerator):
    """
    Deterministic mock generator for tests, benchmarks, and offline demonstrations.
    Produces predictable outputs matching each GenerationMode.
    """

    def __init__(self, model_name: str = "mock-generator-v1"):
        self.model_name = model_name

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        cand_name = request.candidate_profile.candidate_name or "Candidate"
        job_title = request.job_description.title
        skills_str = ", ".join(s.name for s in request.candidate_profile.skills[:5])

        prompt_used = (
            f"Generate {request.generation_type.value} for {cand_name} targeting {job_title}. "
            f"Mode: {request.mode.value}."
        )

        if request.generation_type == GenerationType.JOB_MATCH_EXPLANATION:
            if request.mode == GenerationMode.FAITHFUL:
                text = (
                    f"{cand_name} is a strong match for {job_title}. "
                    f"Proficient in {skills_str or 'Python'} with documented experience in search models "
                    f"and distributed systems."
                )
            elif request.mode == GenerationMode.FABRICATED_METRIC:
                text = (
                    f"{cand_name} is an exceptional fit for {job_title}, having improved search relevance "
                    f"by 40% and scaled infrastructure across high-throughput services."
                )
            elif request.mode == GenerationMode.INVENTED_SKILL:
                text = (
                    f"{cand_name} matches {job_title} requirements. "
                    f"Proficient in Rust programming and distributed consensus architecture."
                )
            elif request.mode == GenerationMode.AMBIGUOUS_CLAIM:
                text = (
                    f"{cand_name} is suitable for {job_title}. "
                    f"Holds a Master of Science in Artificial Intelligence from Berkeley."
                )
            else:
                text = f"{cand_name} demonstrates strong relevant background for {job_title}."

        else:  # RESUME_BULLET_SUGGESTION
            orig = request.target_bullet or "Designed search ranking models improving relevance by 18%."
            if request.mode == GenerationMode.FAITHFUL:
                text = (
                    f"Engineered and deployed search ranking models using Python and PyTorch, "
                    f"improving search relevance by 18%."
                )
            elif request.mode == GenerationMode.FABRICATED_METRIC:
                text = (
                    f"Architected high-throughput search ranking models, improving search relevance "
                    f"by 40% across production clusters."
                )
            elif request.mode == GenerationMode.INVENTED_SKILL:
                text = (
                    f"Built resilient low-latency microservices in Rust and Docker, "
                    f"optimizing query routing."
                )
            elif request.mode == GenerationMode.AMBIGUOUS_CLAIM:
                text = (
                    f"Led cross-functional enterprise alignment initiatives, negotiating "
                    f"multimillion-dollar vendor contracts across engineering divisions."
                )
            else:
                text = f"Improved execution: {orig}"

        return GenerationResponse(
            generated_text=text,
            generation_type=request.generation_type,
            provider="mock",
            model_name=self.model_name,
            prompt_used=prompt_used,
            mode=request.mode,
            metadata={"deterministic": True},
        )


class GroqGenerator(BaseGenerator):
    """
    Optional live generator using Groq cloud API (e.g. Llama-3.1-8b-instant).
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: str = "llama-3.1-8b-instant",
        temperature: float = 0.2,
    ):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model_name = model_name
        self.temperature = temperature

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(self, request: GenerationRequest) -> GenerationResponse:
        if not self.is_configured:
            raise ProviderNotConfiguredError(
                "GROQ_API_KEY is not configured. Please supply an API key or use MockGenerator."
            )

        try:
            from groq import Groq
        except ImportError as exc:
            raise ProviderNotConfiguredError(
                "The 'groq' package is not installed. Install it or use MockGenerator."
            ) from exc

        cand = request.candidate_profile
        job = request.job_description

        # Construct strictly grounded system & user prompts
        system_prompt = (
            "You are an assistant for NeverInvent, a claim-grounded resume intelligence system. "
            "CRITICAL REQUIREMENT: Use ONLY factual evidence supplied in the candidate profile. "
            "Do NOT invent skills, employers, dates, metrics, or degrees. "
            "Write concise, professional resume statements."
        )

        user_prompt = (
            f"Candidate Name: {cand.candidate_name}\n"
            f"Skills: {', '.join(s.name for s in cand.skills)}\n"
            f"Experience: {[{'company': e.company, 'title': e.title, 'start': e.start_date, 'end': e.end_date, 'responsibilities': e.responsibilities} for e in cand.experience]}\n"
            f"Target Job: {job.title} at {job.company or 'Company'}\n"
            f"Required Skills: {job.required_skills}\n"
            f"Task: Generate a {request.generation_type.value}.\n"
        )
        if request.target_bullet:
            user_prompt += f"Original bullet to refine: '{request.target_bullet}'\n"

        client = Groq(api_key=self.api_key)
        try:
            resp = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                model=self.model_name,
                temperature=self.temperature,
                max_tokens=250,
            )
            text = (resp.choices[0].message.content or "").strip()
        except Exception as e:
            raise GenerationError(f"Groq API call failed: {e}") from e

        return GenerationResponse(
            generated_text=text,
            generation_type=request.generation_type,
            provider="groq",
            model_name=self.model_name,
            prompt_used=user_prompt,
            mode=request.mode,
            metadata={"temperature": self.temperature},
        )
