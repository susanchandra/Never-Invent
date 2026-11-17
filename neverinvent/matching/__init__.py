"""
matching package — evidence-grounded candidate-job matching and dealbreakers.
"""

from neverinvent.matching.matcher import EvidenceGroundedMatcher
from neverinvent.matching.models import (
    DealbreakerResult,
    MatchBreakdown,
    SkillMatchItem,
    SkillMatchStatus,
)

__all__ = [
    "EvidenceGroundedMatcher",
    "SkillMatchItem",
    "SkillMatchStatus",
    "DealbreakerResult",
    "MatchBreakdown",
]
