"""
workflow package — verified proposals, diff helpers, and approval pipeline.
"""

from neverinvent.workflow.diff_helper import compute_diff
from neverinvent.workflow.models import (
    ApprovalDecision,
    DiffHighlight,
    ProposalStatus,
    VerifiedProposal,
)
from neverinvent.workflow.pipeline import VerificationPipeline

__all__ = [
    "VerifiedProposal",
    "ProposalStatus",
    "ApprovalDecision",
    "DiffHighlight",
    "compute_diff",
    "VerificationPipeline",
]
