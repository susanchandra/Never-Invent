"""
jobs/job_loader.py — Load, validate, and index job descriptions from JSONL.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Tuple
from pydantic import ValidationError

from neverinvent.jobs.models import JobDescription

logger = logging.getLogger(__name__)


class JobLoadingError(Exception):
    """Raised when job dataset file is inaccessible or completely invalid."""


def load_jobs_from_jsonl(file_path: str | Path) -> Tuple[list[JobDescription], list[dict]]:
    """
    Load job postings from a JSONL file.
    Returns:
        (valid_jobs, error_records)
    """
    path = Path(file_path).resolve()
    if not path.exists():
        raise JobLoadingError(f"Job file not found: {path}")

    valid_jobs: list[JobDescription] = []
    error_records: list[dict] = []

    with open(path, "r", encoding="utf-8") as f:
        for line_no, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                data = json.loads(stripped)
                job = JobDescription.model_validate(data)
                valid_jobs.append(job)
            except json.JSONDecodeError as err:
                logger.warning("JSON decode error at line %d: %s", line_no, err)
                error_records.append({"line_no": line_no, "error": f"JSON decode error: {err}"})
            except ValidationError as err:
                logger.warning("Validation error at line %d: %s", line_no, err)
                error_records.append({"line_no": line_no, "error": f"Schema validation error: {err.errors()}"})
            except Exception as err:
                logger.warning("Unexpected error at line %d: %s", line_no, err)
                error_records.append({"line_no": line_no, "error": str(err)})

    logger.info("Loaded %d valid jobs from %s (%d errors)", len(valid_jobs), path.name, len(error_records))
    return valid_jobs, error_records
