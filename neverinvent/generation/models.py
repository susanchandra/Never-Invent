"""
generation/models.py — Data contracts and schemas for the generation layer.

Design contracts:
- The generator produces UNVERIFIED text proposals.
- It NEVER decides whether its own statements are true.
- All outputs must pass through claim extraction and independent verification.
- Output models clearly track prompt, provider, and model used.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, Field

from neverinvent.jobs.models import JobDescription
from neverinvent.parsing.models import CandidateProfile


class GenerationType(str, Enum):
    JOB_MATCH_EXPLANATION = "job_match_explanation"
    RESUME_BULLET_SUGGESTION = "resume_bullet_suggestion"


class GenerationMode(str, Enum):
    """Preset generation behaviors, especially useful for deterministic demoing & testing."""
    FAITHFUL = "faithful"
    FABRICATED_METRIC = "fabricated_metric"
    INVENTED_SKILL = "invented_skill"
    AMBIGUOUS_CLAIM = "ambiguous_claim"


class GenerationRequest(BaseModel):
    candidate_profile: CandidateProfile
    job_description: JobDescription
    generation_type: GenerationType
    mode: GenerationMode = GenerationMode.FAITHFUL
    target_role: Optional[str] = None
    target_bullet: Optional[str] = Field(
        default=None,
        description="Original bullet to tailor/improve if generation_type is RESUME_BULLET_SUGGESTION.",
    )


class GenerationResponse(BaseModel):
    model_config = {"protected_namespaces": ()}

    generated_text: str = Field(description="Raw generated text proposal (unverified).")
    generation_type: GenerationType
    provider: str = Field(description="Name of the generation provider (e.g. 'mock', 'groq').")
    model_name: str = Field(description="Model identifier.")
    prompt_used: str = Field(description="Full prompt sent to the generator.")
    mode: GenerationMode
    metadata: dict[str, Any] = Field(default_factory=dict)
