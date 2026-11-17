"""
evaluation/fabrication_dataset.py — Builder and loader for Dataset A (controlled injected fabrications).

Covers 10 distinct fabrication categories with balanced faithful and fabricated cases:
1. invented_skill
2. metric_inflation
3. percentage_change
4. invented_employer
5. project_ownership
6. duration_exaggeration
7. date_alteration
8. invented_degree
9. quantity_alteration
10. unsupported_responsibility
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Optional
from pydantic import BaseModel, Field

from neverinvent.claims.models import Claim, ClaimType
from neverinvent.parsing.models import (
    CandidateProfile,
    Education,
    MetricClaim,
    SkillItem,
    WorkExperience,
)
from neverinvent.verification.models import Verdict


class FabricationCase(BaseModel):
    case_id: str
    fabrication_type: str
    claim_type: ClaimType
    test_claim_text: str
    source_evidence: str
    expected_verdict: Verdict
    is_fabricated: bool
    rationale: str
    numeric_value: Optional[float] = None
    unit: Optional[str] = None
    temporal_start: Optional[str] = None
    temporal_end: Optional[str] = None


def get_standard_evaluation_profile() -> CandidateProfile:
    """Canonical test profile (Alice Smith) matching Phase 1 parsed profile."""
    return CandidateProfile(
        candidate_name="Alice Smith",
        email="alice.smith@example.com",
        phone="(555) 123-4567",
        skills=[
            SkillItem(name="python", original_text="Python"),
            SkillItem(name="pytorch", original_text="PyTorch"),
            SkillItem(name="kubernetes", original_text="Kubernetes"),
            SkillItem(name="amazon web services", original_text="AWS"),
            SkillItem(name="faiss", original_text="FAISS"),
            SkillItem(name="docker", original_text="Docker"),
            SkillItem(name="spark", original_text="Spark"),
        ],
        experience=[
            WorkExperience(
                company="Google",
                original_company_text="Google",
                title="Senior Machine Learning Engineer",
                original_title_text="Senior Machine Learning Engineer",
                start_date="2021-01",
                end_date="Present",
                is_current=True,
                duration_months=70,  # to Nov 2026
                responsibilities=[
                    "Designed search ranking models improving relevance by 18%.",
                    "Scaled inference service handling 500ms requests.",
                ],
            ),
            WorkExperience(
                company="Meta",
                original_company_text="Meta",
                title="Machine Learning Engineer",
                original_title_text="Machine Learning Engineer",
                start_date="2019-01",
                end_date="2020-12",
                is_current=False,
                duration_months=23,
                responsibilities=["Built data processing pipelines using Python and Spark."],
            ),
        ],
        education=[
            Education(
                institution="Stanford University",
                original_institution_text="Stanford University",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                start_date="2015-01",
                end_date="2019-01",
            )
        ],
        metrics=[
            MetricClaim(
                raw_metric_text="improving relevance by 18%",
                quantity=18.0,
                unit="%",
                direction="increase",
                context="Designed search ranking models improving relevance by 18%.",
            ),
            MetricClaim(
                raw_metric_text="handling 500ms requests",
                quantity=500.0,
                unit="ms",
                direction=None,
                context="Scaled inference service handling 500ms requests.",
            ),
        ],
    )


def generate_dataset_a() -> list[FabricationCase]:
    """Generates 50 controlled evaluation cases (5 per category across 10 categories)."""
    cases: list[FabricationCase] = [
        # 1. invented_skill (3 fabricated, 2 faithful)
        FabricationCase(
            case_id="skill_01",
            fabrication_type="invented_skill",
            claim_type=ClaimType.SKILL,
            test_claim_text="Proficient in Rust programming.",
            source_evidence="Skills: Python, PyTorch, Kubernetes, AWS, FAISS, Docker, Spark",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            rationale="Rust is not in the candidate's documented skills.",
        ),
        FabricationCase(
            case_id="skill_02",
            fabrication_type="invented_skill",
            claim_type=ClaimType.SKILL,
            test_claim_text="Extensive experience with Solidity and blockchain.",
            source_evidence="Skills: Python, PyTorch, Kubernetes, AWS, FAISS, Docker, Spark",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            rationale="Solidity is not in the candidate's documented skills.",
        ),
        FabricationCase(
            case_id="skill_03",
            fabrication_type="invented_skill",
            claim_type=ClaimType.SKILL,
            test_claim_text="Skilled in Julia data pipelines.",
            source_evidence="Skills: Python, PyTorch, Kubernetes, AWS, FAISS, Docker, Spark",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            rationale="Julia is not in candidate skills.",
        ),
        FabricationCase(
            case_id="skill_04_faithful",
            fabrication_type="invented_skill",
            claim_type=ClaimType.SKILL,
            test_claim_text="Proficient in Python.",
            source_evidence="Skills: Python",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            rationale="Python is explicitly listed in skills.",
        ),
        FabricationCase(
            case_id="skill_05_faithful",
            fabrication_type="invented_skill",
            claim_type=ClaimType.SKILL,
            test_claim_text="Experienced with PyTorch and deep learning.",
            source_evidence="Skills: PyTorch",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            rationale="PyTorch is explicitly listed in skills.",
        ),

        # 2. metric_inflation (3 fabricated, 2 faithful)
        FabricationCase(
            case_id="metric_01",
            fabrication_type="metric_inflation",
            claim_type=ClaimType.METRIC,
            test_claim_text="Improved search relevance by 40%.",
            source_evidence="Designed search ranking models improving relevance by 18%.",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            numeric_value=40.0,
            unit="%",
            rationale="Inflated metric from documented 18% to 40%.",
        ),
        FabricationCase(
            case_id="metric_02",
            fabrication_type="metric_inflation",
            claim_type=ClaimType.METRIC,
            test_claim_text="Boosted search relevance by 85%.",
            source_evidence="Designed search ranking models improving relevance by 18%.",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            numeric_value=85.0,
            unit="%",
            rationale="Inflated metric from documented 18% to 85%.",
        ),
        FabricationCase(
            case_id="metric_03",
            fabrication_type="metric_inflation",
            claim_type=ClaimType.METRIC,
            test_claim_text="Optimized inference service down to 50ms requests.",
            source_evidence="Scaled inference service handling 500ms requests.",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            numeric_value=50.0,
            unit="ms",
            rationale="Altered latency from 500ms to 50ms.",
        ),
        FabricationCase(
            case_id="metric_04_faithful",
            fabrication_type="metric_inflation",
            claim_type=ClaimType.METRIC,
            test_claim_text="Improved search relevance by 18%.",
            source_evidence="Designed search ranking models improving relevance by 18%.",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            numeric_value=18.0,
            unit="%",
            rationale="Matches exact documented metric of 18%.",
        ),
        FabricationCase(
            case_id="metric_05_faithful",
            fabrication_type="metric_inflation",
            claim_type=ClaimType.METRIC,
            test_claim_text="Handled 500ms requests at scale.",
            source_evidence="Scaled inference service handling 500ms requests.",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            numeric_value=500.0,
            unit="ms",
            rationale="Matches exact documented metric of 500ms.",
        ),

        # 3. percentage_change (3 fabricated, 2 faithful)
        FabricationCase(
            case_id="pct_01",
            fabrication_type="percentage_change",
            claim_type=ClaimType.METRIC,
            test_claim_text="Decreased error rate by 35%.",
            source_evidence="improving relevance by 18%",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            numeric_value=35.0,
            unit="%",
            rationale="Invented percentage metric.",
        ),
        FabricationCase(
            case_id="pct_02",
            fabrication_type="percentage_change",
            claim_type=ClaimType.METRIC,
            test_claim_text="Improved relevance by 25%.",
            source_evidence="improving relevance by 18%",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            numeric_value=25.0,
            unit="%",
            rationale="Subtly changed 18% to 25%.",
        ),
        FabricationCase(
            case_id="pct_03",
            fabrication_type="percentage_change",
            claim_type=ClaimType.METRIC,
            test_claim_text="Cut costs by 50%.",
            source_evidence="improving relevance by 18%",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            numeric_value=50.0,
            unit="%",
            rationale="Invented 50% cost cut metric.",
        ),
        FabricationCase(
            case_id="pct_04_faithful",
            fabrication_type="percentage_change",
            claim_type=ClaimType.METRIC,
            test_claim_text="Achieved an 18% increase in relevance.",
            source_evidence="improving relevance by 18%",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            numeric_value=18.0,
            unit="%",
            rationale="Matches 18% improvement.",
        ),
        FabricationCase(
            case_id="pct_05_faithful",
            fabrication_type="percentage_change",
            claim_type=ClaimType.METRIC,
            test_claim_text="Enhanced model relevance by 18%.",
            source_evidence="improving relevance by 18%",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            numeric_value=18.0,
            unit="%",
            rationale="Matches 18% improvement.",
        ),

        # 4. invented_employer (3 fabricated, 2 faithful)
        FabricationCase(
            case_id="emp_01",
            fabrication_type="invented_employer",
            claim_type=ClaimType.EMPLOYER,
            test_claim_text="Worked at Netflix as a lead engineer.",
            source_evidence="Experience: Google, Meta",
            expected_verdict=Verdict.AMBIGUOUS,
            is_fabricated=True,
            rationale="Netflix is not in documented experience; absence is ambiguous.",
        ),
        FabricationCase(
            case_id="emp_02",
            fabrication_type="invented_employer",
            claim_type=ClaimType.EMPLOYER,
            test_claim_text="Employed by Uber Technologies.",
            source_evidence="Experience: Google, Meta",
            expected_verdict=Verdict.AMBIGUOUS,
            is_fabricated=True,
            rationale="Uber is not in documented experience.",
        ),
        FabricationCase(
            case_id="emp_03",
            fabrication_type="invented_employer",
            claim_type=ClaimType.EMPLOYER,
            test_claim_text="Worked at OpenAI on LLMs.",
            source_evidence="Experience: Google, Meta",
            expected_verdict=Verdict.AMBIGUOUS,
            is_fabricated=True,
            rationale="OpenAI is not documented.",
        ),
        FabricationCase(
            case_id="emp_04_faithful",
            fabrication_type="invented_employer",
            claim_type=ClaimType.EMPLOYER,
            test_claim_text="Worked at Google as a Senior Machine Learning Engineer.",
            source_evidence="Google - Senior Machine Learning Engineer",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            rationale="Google tenure is documented.",
        ),
        FabricationCase(
            case_id="emp_05_faithful",
            fabrication_type="invented_employer",
            claim_type=ClaimType.EMPLOYER,
            test_claim_text="Employed at Meta from 2019 to 2020.",
            source_evidence="Meta - Machine Learning Engineer Jan 2019 - Dec 2020",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            rationale="Meta tenure is documented.",
        ),

        # 5. project_ownership (3 fabricated, 2 faithful)
        FabricationCase(
            case_id="proj_01",
            fabrication_type="project_ownership",
            claim_type=ClaimType.JOB_TITLE,
            test_claim_text="Served as VP of Engineering at Google.",
            source_evidence="Google - Senior Machine Learning Engineer",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            rationale="VP title contradicts documented Senior Engineer role.",
        ),
        FabricationCase(
            case_id="proj_02",
            fabrication_type="project_ownership",
            claim_type=ClaimType.JOB_TITLE,
            test_claim_text="Chief Technology Officer at Google.",
            source_evidence="Google - Senior Machine Learning Engineer",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            rationale="CTO title contradicts documented role.",
        ),
        FabricationCase(
            case_id="proj_03",
            fabrication_type="project_ownership",
            claim_type=ClaimType.JOB_TITLE,
            test_claim_text="Director of Machine Learning at Meta.",
            source_evidence="Meta - Machine Learning Engineer",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            rationale="Director title contradicts documented Machine Learning Engineer role.",
        ),
        FabricationCase(
            case_id="proj_04_faithful",
            fabrication_type="project_ownership",
            claim_type=ClaimType.JOB_TITLE,
            test_claim_text="Senior Machine Learning Engineer at Google.",
            source_evidence="Google - Senior Machine Learning Engineer",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            rationale="Matches exact documented title.",
        ),
        FabricationCase(
            case_id="proj_05_faithful",
            fabrication_type="project_ownership",
            claim_type=ClaimType.JOB_TITLE,
            test_claim_text="Machine Learning Engineer at Meta.",
            source_evidence="Meta - Machine Learning Engineer",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            rationale="Matches exact documented title.",
        ),

        # 6. duration_exaggeration (3 fabricated, 2 faithful)
        FabricationCase(
            case_id="dur_01",
            fabrication_type="duration_exaggeration",
            claim_type=ClaimType.DURATION,
            test_claim_text="Has over 15 years of experience in ML.",
            source_evidence="Experience: 2019-2026 (~7.8 years total)",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            numeric_value=15.0,
            unit="years",
            rationale="Claimed 15 years exceeds documented experience.",
        ),
        FabricationCase(
            case_id="dur_02",
            fabrication_type="duration_exaggeration",
            claim_type=ClaimType.DURATION,
            test_claim_text="20 years of experience in software engineering.",
            source_evidence="Graduated 2019; total experience ~8 years",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            numeric_value=20.0,
            unit="years",
            rationale="Claimed 20 years greatly exceeds experience.",
        ),
        FabricationCase(
            case_id="dur_03",
            fabrication_type="duration_exaggeration",
            claim_type=ClaimType.DURATION,
            test_claim_text="12 years of experience building pipelines.",
            source_evidence="Total experience ~8 years",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            numeric_value=12.0,
            unit="years",
            rationale="Claimed 12 years exceeds documented experience.",
        ),
        FabricationCase(
            case_id="dur_04_faithful",
            fabrication_type="duration_exaggeration",
            claim_type=ClaimType.DURATION,
            test_claim_text="Over 5 years of experience in machine learning.",
            source_evidence="Google (2021-Present, ~5.8 yrs) + Meta (2 yrs)",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            numeric_value=5.0,
            unit="years",
            rationale="Documented experience (~7.8 years) supports >5 years.",
        ),
        FabricationCase(
            case_id="dur_05_faithful",
            fabrication_type="duration_exaggeration",
            claim_type=ClaimType.DURATION,
            test_claim_text="2 years of experience at Meta.",
            source_evidence="Meta Jan 2019 - Dec 2020 (23 months)",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            numeric_value=2.0,
            unit="years",
            rationale="Meta tenure is 23 months (~2 years).",
        ),

        # 7. date_alteration (3 fabricated, 2 faithful)
        FabricationCase(
            case_id="date_01",
            fabrication_type="date_alteration",
            claim_type=ClaimType.DATE,
            test_claim_text="Employed at Meta from Jan 2014 to Dec 2017.",
            source_evidence="Meta: Jan 2019 - Dec 2020",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            temporal_start="2014-01",
            temporal_end="2017-12",
            rationale="Dates contradict actual documented Meta dates (2019-2020).",
        ),
        FabricationCase(
            case_id="date_02",
            fabrication_type="date_alteration",
            claim_type=ClaimType.DATE,
            test_claim_text="Joined Google in Jan 2016.",
            source_evidence="Google: Jan 2021 - Present",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            temporal_start="2016-01",
            rationale="Start date contradicts documented 2021 start date at Google.",
        ),
        FabricationCase(
            case_id="date_03",
            fabrication_type="date_alteration",
            claim_type=ClaimType.DATE,
            test_claim_text="Worked at Meta from Jan 2015 to Dec 2018.",
            source_evidence="Meta: Jan 2019 - Dec 2020",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            temporal_start="2015-01",
            temporal_end="2018-12",
            rationale="Dates contradict actual Meta tenure.",
        ),
        FabricationCase(
            case_id="date_04_faithful",
            fabrication_type="date_alteration",
            claim_type=ClaimType.DATE,
            test_claim_text="Joined Google in Jan 2021.",
            source_evidence="Google: Jan 2021 - Present",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            temporal_start="2021-01",
            rationale="Matches documented Google start date.",
        ),
        FabricationCase(
            case_id="date_05_faithful",
            fabrication_type="date_alteration",
            claim_type=ClaimType.DATE,
            test_claim_text="Worked at Meta from Jan 2019 to Dec 2020.",
            source_evidence="Meta: Jan 2019 - Dec 2020",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            temporal_start="2019-01",
            temporal_end="2020-12",
            rationale="Matches documented Meta tenure.",
        ),

        # 8. invented_degree (3 fabricated, 2 faithful)
        FabricationCase(
            case_id="deg_01",
            fabrication_type="invented_degree",
            claim_type=ClaimType.EDUCATION,
            test_claim_text="Holds a PhD in Computer Science from MIT.",
            source_evidence="Stanford University B.S. in Computer Science",
            expected_verdict=Verdict.AMBIGUOUS,
            is_fabricated=True,
            rationale="PhD from MIT not documented; absence requires human review.",
        ),
        FabricationCase(
            case_id="deg_02",
            fabrication_type="invented_degree",
            claim_type=ClaimType.EDUCATION,
            test_claim_text="Completed Master of Science in Artificial Intelligence at Berkeley.",
            source_evidence="Stanford University B.S. in Computer Science",
            expected_verdict=Verdict.AMBIGUOUS,
            is_fabricated=True,
            rationale="M.S. from Berkeley is not documented.",
        ),
        FabricationCase(
            case_id="deg_03",
            fabrication_type="invented_degree",
            claim_type=ClaimType.EDUCATION,
            test_claim_text="Earned an MBA from Harvard Business School.",
            source_evidence="Stanford University B.S. in Computer Science",
            expected_verdict=Verdict.AMBIGUOUS,
            is_fabricated=True,
            rationale="MBA is not documented.",
        ),
        FabricationCase(
            case_id="deg_04_faithful",
            fabrication_type="invented_degree",
            claim_type=ClaimType.EDUCATION,
            test_claim_text="Holds a Bachelor of Science in Computer Science from Stanford University.",
            source_evidence="Stanford University B.S. in Computer Science",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            rationale="Matches documented degree and university.",
        ),
        FabricationCase(
            case_id="deg_05_faithful",
            fabrication_type="invented_degree",
            claim_type=ClaimType.EDUCATION,
            test_claim_text="Graduated from Stanford University with a degree in Computer Science.",
            source_evidence="Stanford University B.S. in Computer Science",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            rationale="Matches documented institution and major.",
        ),

        # 9. quantity_alteration (3 fabricated, 2 faithful)
        FabricationCase(
            case_id="qty_01",
            fabrication_type="quantity_alteration",
            claim_type=ClaimType.QUANTITY,
            test_claim_text="Scaled service handling 50ms latency.",
            source_evidence="Scaled inference service handling 500ms requests.",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            numeric_value=50.0,
            unit="ms",
            rationale="Altered latency from 500ms to 50ms.",
        ),
        FabricationCase(
            case_id="qty_02",
            fabrication_type="quantity_alteration",
            claim_type=ClaimType.QUANTITY,
            test_claim_text="Handled 2000ms service requests.",
            source_evidence="Scaled inference service handling 500ms requests.",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            numeric_value=2000.0,
            unit="ms",
            rationale="Altered 500ms to 2000ms.",
        ),
        FabricationCase(
            case_id="qty_03",
            fabrication_type="quantity_alteration",
            claim_type=ClaimType.QUANTITY,
            test_claim_text="Improved search ranking by 55%.",
            source_evidence="Designed search ranking models improving relevance by 18%.",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            numeric_value=55.0,
            unit="%",
            rationale="Altered 18% to 55%.",
        ),
        FabricationCase(
            case_id="qty_04_faithful",
            fabrication_type="quantity_alteration",
            claim_type=ClaimType.QUANTITY,
            test_claim_text="Engineered services handling 500ms requests.",
            source_evidence="Scaled inference service handling 500ms requests.",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            numeric_value=500.0,
            unit="ms",
            rationale="Matches 500ms documented metric.",
        ),
        FabricationCase(
            case_id="qty_05_faithful",
            fabrication_type="quantity_alteration",
            claim_type=ClaimType.QUANTITY,
            test_claim_text="Improved relevance by 18%.",
            source_evidence="improving relevance by 18%",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            numeric_value=18.0,
            unit="%",
            rationale="Matches 18% documented metric.",
        ),

        # 10. unsupported_responsibility (3 fabricated, 2 faithful)
        FabricationCase(
            case_id="resp_01",
            fabrication_type="unsupported_responsibility",
            claim_type=ClaimType.RESPONSIBILITY,
            test_claim_text="Negotiated multimillion-dollar vendor contracts across enterprise divisions.",
            source_evidence="Responsibilities at Google: Search models, inference scaling",
            expected_verdict=Verdict.AMBIGUOUS,
            is_fabricated=True,
            rationale="Vendor negotiation not in resume; requires human review.",
        ),
        FabricationCase(
            case_id="resp_02",
            fabrication_type="unsupported_responsibility",
            claim_type=ClaimType.RESPONSIBILITY,
            test_claim_text="Managed iOS mobile app deployment to App Store.",
            source_evidence="Responsibilities at Google & Meta: Search models, Spark pipelines",
            expected_verdict=Verdict.AMBIGUOUS,
            is_fabricated=True,
            rationale="Mobile app deployment not documented.",
        ),
        FabricationCase(
            case_id="resp_03",
            fabrication_type="unsupported_responsibility",
            claim_type=ClaimType.RESPONSIBILITY,
            test_claim_text="Conducted financial audits and compliance reviews.",
            source_evidence="Responsibilities at Google & Meta: ML engineering",
            expected_verdict=Verdict.AMBIGUOUS,
            is_fabricated=True,
            rationale="Financial audits not documented.",
        ),
        FabricationCase(
            case_id="resp_04_faithful",
            fabrication_type="unsupported_responsibility",
            claim_type=ClaimType.RESPONSIBILITY,
            test_claim_text="Designed search ranking models improving relevance by 18%.",
            source_evidence="Designed search ranking models improving relevance by 18%.",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            rationale="Exact match with documented responsibility.",
        ),
        FabricationCase(
            case_id="resp_05_faithful",
            fabrication_type="unsupported_responsibility",
            claim_type=ClaimType.RESPONSIBILITY,
            test_claim_text="Built data processing pipelines using Python and Spark.",
            source_evidence="Built data processing pipelines using Python and Spark.",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            rationale="Exact match with documented responsibility.",
        ),
    ]
    return cases


def save_dataset_a(output_path: Path) -> None:
    """Save Dataset A to JSONL."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cases = generate_dataset_a()
    with open(output_path, "w", encoding="utf-8") as f:
        for c in cases:
            f.write(c.model_dump_json() + "\n")


def load_dataset_a(path: Path) -> list[FabricationCase]:
    """Load Dataset A from JSONL."""
    if not path.exists():
        save_dataset_a(path)
    cases: list[FabricationCase] = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                cases.append(FabricationCase.model_validate_json(line))
    return cases
