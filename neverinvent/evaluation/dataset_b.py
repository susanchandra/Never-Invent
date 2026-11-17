"""
neverinvent/evaluation/dataset_b.py — Dataset B (Natural Benchmark) loader and definitions.

Dataset B provides 100 realistic, natural model-generated candidate claims across
5 diverse candidate backgrounds and real-world job roles.

Dataset Properties:
- Total Cases: 100
- Class Distribution:
    - 40 Faithful Claims (SUPPORTED)
    - 40 Fabricated Claims (UNSUPPORTED: inflation, invented skills, dates, degrees)
    - 20 Ambiguous / Partially Grounded Claims (AMBIGUOUS: soft skills, scope unprovable from resume)
- Annotation Protocol:
    Annotated following a strict 3-tier evidence rubric:
    1. SUPPORTED: Every factual entity, metric, date, or title is explicitly present in candidate source record.
    2. UNSUPPORTED: Directly contradicted by source evidence, or claims an unearned credential/skill in a closed-world domain.
    3. AMBIGUOUS: Plausible or partially aligned, but cannot be definitively confirmed from the resume text alone.
- Disclosure:
    Annotated by a single evaluator according to the documented guidelines.
    Dataset was frozen prior to evaluation; no verifier rules were tuned against Dataset B.
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


class NaturalEvaluationCase(BaseModel):
    case_id: str
    candidate_id: str
    claim_type: ClaimType
    claim_text: str
    extracted_claim_value: str
    source_evidence: str
    expected_verdict: Verdict
    annotation_rationale: str
    annotation_notes: Optional[str] = None
    annotator: str = "manual_expert_review"


def get_benchmark_profiles() -> dict[str, CandidateProfile]:
    """Returns canonical candidate profiles for Dataset B evaluation."""
    alice = CandidateProfile(
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
                end_date="present",
                duration_months=46,
                is_current=True,
                description="Designed search ranking models improving relevance by 18%. Scaled inference service handling 500ms requests.",
            ),
            WorkExperience(
                company="Meta",
                original_company_text="Meta",
                title="Machine Learning Engineer",
                original_title_text="Machine Learning Engineer",
                start_date="2019-01",
                end_date="2020-12",
                duration_months=24,
                is_current=False,
                description="Built data processing pipelines using Python and Spark.",
            ),
        ],
        education=[
            Education(
                institution="Stanford University",
                original_institution_text="Stanford University",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                start_date="2015-09",
                end_date="2019-06",
            )
        ],
        metrics=[
            MetricClaim(
                raw_metric_text="18%",
                quantity=18.0,
                unit="%",
                direction="increase",
                context="improving relevance by 18%",
            ),
            MetricClaim(
                raw_metric_text="500ms",
                quantity=500.0,
                unit="ms",
                direction="total",
                context="handling 500ms requests",
            ),
        ],
    )

    bob = CandidateProfile(
        candidate_name="Bob Jones",
        email="bob.jones@example.com",
        phone="(555) 234-5678",
        skills=[
            SkillItem(name="python", original_text="Python"),
            SkillItem(name="go", original_text="Go"),
            SkillItem(name="kafka", original_text="Kafka"),
            SkillItem(name="postgresql", original_text="PostgreSQL"),
            SkillItem(name="redis", original_text="Redis"),
            SkillItem(name="grpc", original_text="gRPC"),
        ],
        experience=[
            WorkExperience(
                company="Stripe",
                original_company_text="Stripe",
                title="Backend Software Engineer",
                original_title_text="Backend Software Engineer",
                start_date="2020-03",
                end_date="present",
                duration_months=56,
                is_current=True,
                description="Architected high-throughput ledger service processing 10,000 transactions per second with 99.99% uptime.",
            ),
            WorkExperience(
                company="Square",
                original_company_text="Square",
                title="Software Engineer",
                original_title_text="Software Engineer",
                start_date="2018-06",
                end_date="2020-02",
                duration_months=20,
                is_current=False,
                description="Built REST APIs in Python and PostgreSQL.",
            ),
        ],
        education=[
            Education(
                institution="University of Washington",
                original_institution_text="University of Washington",
                degree="Bachelor of Science",
                field_of_study="Computer Engineering",
                start_date="2014-09",
                end_date="2018-05",
            )
        ],
        metrics=[
            MetricClaim(
                raw_metric_text="10,000 transactions per second",
                quantity=10000.0,
                unit="tps",
                direction="total",
                context="processing 10,000 transactions per second",
            ),
            MetricClaim(
                raw_metric_text="99.99%",
                quantity=99.99,
                unit="%",
                direction="total",
                context="with 99.99% uptime",
            ),
        ],
    )

    carol = CandidateProfile(
        candidate_name="Carol Danvers",
        email="carol.danvers@example.com",
        phone="(555) 345-6789",
        skills=[
            SkillItem(name="kubernetes", original_text="Kubernetes"),
            SkillItem(name="terraform", original_text="Terraform"),
            SkillItem(name="amazon web services", original_text="AWS"),
            SkillItem(name="docker", original_text="Docker"),
            SkillItem(name="datadog", original_text="Datadog"),
            SkillItem(name="linux", original_text="Linux"),
            SkillItem(name="bash", original_text="Bash"),
        ],
        experience=[
            WorkExperience(
                company="Datadog",
                original_company_text="Datadog",
                title="DevOps Engineer",
                original_title_text="DevOps Engineer",
                start_date="2021-06",
                end_date="present",
                duration_months=41,
                is_current=True,
                description="Managed 15 Kubernetes clusters on AWS using Terraform. Reduced deployment time by 35%.",
            )
        ],
        education=[
            Education(
                institution="Carnegie Mellon University",
                original_institution_text="Carnegie Mellon University",
                degree="Bachelor of Science",
                field_of_study="Information Systems",
                start_date="2017-09",
                end_date="2021-05",
            )
        ],
        metrics=[
            MetricClaim(
                raw_metric_text="15",
                quantity=15.0,
                unit="clusters",
                direction="total",
                context="Managed 15 Kubernetes clusters",
            ),
            MetricClaim(
                raw_metric_text="35%",
                quantity=35.0,
                unit="%",
                direction="decrease",
                context="Reduced deployment time by 35%",
            ),
        ],
    )

    david = CandidateProfile(
        candidate_name="David Lee",
        email="david.lee@example.com",
        phone="(555) 456-7890",
        skills=[
            SkillItem(name="pytorch", original_text="PyTorch"),
            SkillItem(name="transformers", original_text="HuggingFace Transformers"),
            SkillItem(name="nlp", original_text="Natural Language Processing"),
            SkillItem(name="python", original_text="Python"),
            SkillItem(name="wandb", original_text="Weights & Biases"),
        ],
        experience=[
            WorkExperience(
                company="AI Research Lab",
                original_company_text="AI Research Lab",
                title="Research Scientist",
                original_title_text="Research Scientist",
                start_date="2022-01",
                end_date="present",
                duration_months=34,
                is_current=True,
                description="Fine-tuned 7B parameter open-source LLMs on proprietary instruction datasets. Authored 3 conference papers.",
            )
        ],
        education=[
            Education(
                institution="UC Berkeley",
                original_institution_text="UC Berkeley",
                degree="Master of Science",
                field_of_study="Computer Science",
                start_date="2020-08",
                end_date="2022-05",
            )
        ],
        metrics=[
            MetricClaim(
                raw_metric_text="7B",
                quantity=7.0,
                unit="B",
                direction="total",
                context="7B parameter open-source LLMs",
            ),
            MetricClaim(
                raw_metric_text="3",
                quantity=3.0,
                unit="papers",
                direction="total",
                context="Authored 3 conference papers",
            ),
        ],
    )

    elena = CandidateProfile(
        candidate_name="Elena Rostova",
        email="elena.rostova@example.com",
        phone="(555) 567-8901",
        skills=[
            SkillItem(name="react", original_text="React"),
            SkillItem(name="typescript", original_text="TypeScript"),
            SkillItem(name="next.js", original_text="Next.js"),
            SkillItem(name="graphql", original_text="GraphQL"),
            SkillItem(name="tailwind css", original_text="Tailwind CSS"),
        ],
        experience=[
            WorkExperience(
                company="Airbnb",
                original_company_text="Airbnb",
                title="Frontend Software Engineer",
                original_title_text="Frontend Software Engineer",
                start_date="2021-03",
                end_date="present",
                duration_months=44,
                is_current=True,
                description="Spearheaded migration of checkout funnel to Next.js and TypeScript, decreasing page load time by 28%.",
            )
        ],
        education=[
            Education(
                institution="University of Michigan",
                original_institution_text="University of Michigan",
                degree="Bachelor of Science",
                field_of_study="Computer Science",
                start_date="2016-09",
                end_date="2020-12",
            )
        ],
        metrics=[
            MetricClaim(
                raw_metric_text="28%",
                quantity=28.0,
                unit="%",
                direction="decrease",
                context="decreasing page load time by 28%",
            )
        ],
    )

    return {
        "alice": alice,
        "bob": bob,
        "carol": carol,
        "david": david,
        "elena": elena,
    }


def load_dataset_b(filepath: Optional[str] = None) -> list[NaturalEvaluationCase]:
    """Loads Dataset B cases from jsonl file."""
    if filepath is None:
        p = Path(__file__).resolve().parent.parent.parent / "data" / "evaluation" / "dataset_b_natural.jsonl"
    else:
        p = Path(filepath)

    if not p.exists():
        raise FileNotFoundError(f"Dataset B file not found at: {p}")

    cases = []
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                cases.append(NaturalEvaluationCase.model_validate_json(line))
    return cases
