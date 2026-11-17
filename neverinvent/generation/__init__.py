"""
generation package — text proposal generation layer.
"""

from neverinvent.generation.editor import ResumeBulletEditor
from neverinvent.generation.explainer import JobMatchExplainer
from neverinvent.generation.models import (
    GenerationMode,
    GenerationRequest,
    GenerationResponse,
    GenerationType,
)
from neverinvent.generation.provider import (
    BaseGenerator,
    GenerationError,
    GroqGenerator,
    MockGenerator,
    ProviderNotConfiguredError,
)

__all__ = [
    "BaseGenerator",
    "MockGenerator",
    "GroqGenerator",
    "GenerationRequest",
    "GenerationResponse",
    "GenerationType",
    "GenerationMode",
    "GenerationError",
    "ProviderNotConfiguredError",
    "JobMatchExplainer",
    "ResumeBulletEditor",
]
