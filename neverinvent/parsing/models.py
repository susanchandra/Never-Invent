"""
parsing/models.py — Structured candidate profile models with provenance.

Design contracts:
- Preserves original verbatim text separately from normalized values.
- Every extracted field links back to a SourceSpan.
- Missing information remains None; never inferred as certain.
- Uncertain fields carry an ExtractionStatus.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field

from neverinvent.ingestion.models import SourceSpan


class ExtractionStatus(str, Enum):
    EXPLICIT = "explicit"       # Directly found in resume text with clear anchor
    UNCERTAIN = "uncertain"     # Heuristically extracted; ambiguous boundary
    UNRESOLVED = "unresolved"   # Detected presence but couldn't parse structured value


class ProvenancedValue(BaseModel):
    """Base class for any extracted value that traces back to the raw document."""
    original_text: str = Field(description="Verbatim text from resume")
    normalized_value: str = Field(description="Normalized canonical form")
    source_span: Optional[SourceSpan] = Field(default=None, description="Exact location in source document")
    status: ExtractionStatus = Field(default=ExtractionStatus.EXPLICIT)


class SkillItem(BaseModel):
    name: str = Field(description="Normalized skill name")
    original_text: str = Field(description="Verbatim text from resume")
    source_span: Optional[SourceSpan] = None
    category: Optional[str] = Field(default=None, description="e.g. language, framework, cloud, tool")
    status: ExtractionStatus = ExtractionStatus.EXPLICIT


class WorkExperience(BaseModel):
    company: str = Field(description="Normalized employer/company name")
    original_company_text: str = Field(description="Verbatim company text")
    title: Optional[str] = Field(default=None, description="Normalized job title")
    original_title_text: Optional[str] = None
    start_date: Optional[str] = Field(default=None, description="ISO date or YYYY-MM if known")
    end_date: Optional[str] = Field(default=None, description="ISO date or YYYY-MM or 'Present'")
    is_current: bool = False
    duration_months: Optional[int] = Field(default=None, description="Computed only when start and end are unambiguous")
    responsibilities: list[str] = Field(default_factory=list, description="Extracted bullet points / responsibilities")
    source_span: Optional[SourceSpan] = None
    status: ExtractionStatus = ExtractionStatus.EXPLICIT


class Education(BaseModel):
    institution: str = Field(description="University / college / school")
    original_institution_text: str
    degree: Optional[str] = Field(default=None, description="e.g. B.S., M.S., Ph.D.")
    field_of_study: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    source_span: Optional[SourceSpan] = None
    status: ExtractionStatus = ExtractionStatus.EXPLICIT


class Certification(BaseModel):
    name: str
    original_text: str
    issuer: Optional[str] = None
    issue_date: Optional[str] = None
    source_span: Optional[SourceSpan] = None
    status: ExtractionStatus = ExtractionStatus.EXPLICIT


class MetricClaim(BaseModel):
    """Numerical metric or quantitative achievement in resume (e.g., 'reduced latency by 40%')."""
    raw_metric_text: str
    quantity: float
    unit: Optional[str] = None  # '%', 'ms', 'users', '$', etc.
    direction: Optional[str] = None  # 'increase', 'decrease', 'total'
    context: str = Field(description="Sentence / bullet containing the metric")
    source_span: Optional[SourceSpan] = None
    status: ExtractionStatus = ExtractionStatus.EXPLICIT


class Project(BaseModel):
    name: str
    original_text: str
    description: Optional[str] = None
    technologies: list[str] = Field(default_factory=list)
    source_span: Optional[SourceSpan] = None
    status: ExtractionStatus = ExtractionStatus.EXPLICIT


class CandidateProfile(BaseModel):
    """
    Structured candidate profile strictly grounded in raw document evidence.
    """
    candidate_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    summary: Optional[str] = None
    skills: list[SkillItem] = Field(default_factory=list)
    experience: list[WorkExperience] = Field(default_factory=list)
    education: list[Education] = Field(default_factory=list)
    certifications: list[Certification] = Field(default_factory=list)
    projects: list[Project] = Field(default_factory=list)
    metrics: list[MetricClaim] = Field(default_factory=list)
    source_document_path: Optional[str] = None
    raw_text_length: int = 0
