"""
persistence package — database setup, models, and repository.
"""

from neverinvent.persistence.database import (
    DEFAULT_DB_PATH,
    Base,
    get_db_session,
    get_engine,
    init_db,
)
from neverinvent.persistence.models import (
    ApprovalAuditRecord,
    CandidateRecord,
    JobRecord,
    ProposalRecord,
)
from neverinvent.persistence.repository import Repository

__all__ = [
    "Base",
    "get_engine",
    "init_db",
    "get_db_session",
    "DEFAULT_DB_PATH",
    "CandidateRecord",
    "JobRecord",
    "ProposalRecord",
    "ApprovalAuditRecord",
    "Repository",
]
