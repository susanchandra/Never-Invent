"""
jobs/models.py — Job Description schema with provenance and normalized requirements.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class JobSource(str, Enum):
    SYNTHETIC = "synthetic"
    PUBLIC_DATASET = "public_dataset"
    MANUALLY_CURATED = "manually_curated"


class JobDescription(BaseModel):
    """
    Standard schema for a normalized job posting.
    Preserves original full text while exposing structured queryable fields.
    """
    job_id: str = Field(description="Unique identifier for the job posting")
    title: str = Field(description="Original job title")
    normalized_title: str = Field(description="Canonical normalized job title")
    company: str = Field(description="Hiring company name")
    location: Optional[str] = Field(default=None, description="Location or Remote")
    is_remote: bool = False
    raw_description: str = Field(description="Verbatim full job posting text")
    responsibilities: list[str] = Field(default_factory=list, description="Extracted bullet points of responsibilities")
    required_skills: list[str] = Field(default_factory=list, description="Must-have technical and domain skills")
    preferred_skills: list[str] = Field(default_factory=list, description="Nice-to-have skills")
    min_years_experience: Optional[int] = Field(default=None, ge=0, description="Minimum years of experience required")
    education_level: Optional[str] = Field(default=None, description="Minimum degree required, e.g. B.S., M.S.")
    source_type: JobSource = Field(default=JobSource.SYNTHETIC, description="Origin of the posting")
    source_reference: Optional[str] = Field(default=None, description="URL, dataset name, or license notice")

    def get_searchable_text(self) -> str:
        """
        Produce a unified representation for lexical and dense indexing.
        """
        req_str = ", ".join(self.required_skills)
        pref_str = ", ".join(self.preferred_skills)
        resp_str = " ".join(self.responsibilities)
        return f"{self.title} at {self.company}. Location: {self.location or 'Unspecified'}. Required Skills: {req_str}. Preferred Skills: {pref_str}. Responsibilities: {resp_str}. Details: {self.raw_description}"
