"""
verification package — independent deterministic claim verification engine.
"""

from neverinvent.verification.models import (
    StrategyResult,
    Verdict,
    VerificationResult,
    VerificationStrategy,
)
from neverinvent.verification.verifier import ALL_STRATEGIES, ClaimVerifier

__all__ = [
    "Verdict",
    "VerificationStrategy",
    "StrategyResult",
    "VerificationResult",
    "ClaimVerifier",
    "ALL_STRATEGIES",
]
