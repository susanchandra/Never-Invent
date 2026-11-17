"""
Unit tests for generation layer (provider abstraction, mock generator, explainer, editor).
"""

import pytest

from neverinvent.generation import (
    GenerationMode,
    GenerationRequest,
    GenerationResponse,
    GenerationType,
    GroqGenerator,
    JobMatchExplainer,
    MockGenerator,
    ProviderNotConfiguredError,
    ResumeBulletEditor,
)
from neverinvent.jobs.models import JobDescription, JobSource
from neverinvent.parsing.models import CandidateProfile, SkillItem, WorkExperience


@pytest.fixture
def sample_candidate() -> CandidateProfile:
    return CandidateProfile(
        candidate_name="Alice Smith",
        skills=[SkillItem(name="python", original_text="Python")],
        experience=[
            WorkExperience(
                company="Google",
                original_company_text="Google",
                title="Senior ML Engineer",
                start_date="2021-01",
                end_date="Present",
                responsibilities=["Designed search ranking models improving relevance by 18%."],
            )
        ],
    )


@pytest.fixture
def sample_job() -> JobDescription:
    return JobDescription(
        job_id="job_001",
        title="Staff Machine Learning Engineer",
        normalized_title="staff machine learning engineer",
        company="Tech Corp",
        raw_description="Build search models.",
        required_skills=["python", "pytorch"],
        preferred_skills=["kubernetes"],
        source_type=JobSource.SYNTHETIC,
    )


def test_mock_generator_faithful_explanation(sample_candidate, sample_job):
    gen = MockGenerator()
    req = GenerationRequest(
        candidate_profile=sample_candidate,
        job_description=sample_job,
        generation_type=GenerationType.JOB_MATCH_EXPLANATION,
        mode=GenerationMode.FAITHFUL,
    )
    resp = gen.generate(req)
    assert isinstance(resp, GenerationResponse)
    assert "Alice Smith" in resp.generated_text
    assert "Staff Machine Learning Engineer" in resp.generated_text
    assert resp.provider == "mock"
    assert resp.mode == GenerationMode.FAITHFUL


def test_mock_generator_controlled_modes(sample_candidate, sample_job):
    gen = MockGenerator()

    # Fabricated metric mode
    req_metric = GenerationRequest(
        candidate_profile=sample_candidate,
        job_description=sample_job,
        generation_type=GenerationType.RESUME_BULLET_SUGGESTION,
        mode=GenerationMode.FABRICATED_METRIC,
    )
    resp_metric = gen.generate(req_metric)
    assert "40%" in resp_metric.generated_text

    # Invented skill mode
    req_skill = GenerationRequest(
        candidate_profile=sample_candidate,
        job_description=sample_job,
        generation_type=GenerationType.JOB_MATCH_EXPLANATION,
        mode=GenerationMode.INVENTED_SKILL,
    )
    resp_skill = gen.generate(req_skill)
    assert "Rust" in resp_skill.generated_text

    # Ambiguous claim mode
    req_amb = GenerationRequest(
        candidate_profile=sample_candidate,
        job_description=sample_job,
        generation_type=GenerationType.JOB_MATCH_EXPLANATION,
        mode=GenerationMode.AMBIGUOUS_CLAIM,
    )
    resp_amb = gen.generate(req_amb)
    assert "Berkeley" in resp_amb.generated_text


def test_explainer_and_editor_services(sample_candidate, sample_job):
    explainer = JobMatchExplainer()
    exp_resp = explainer.explain_match(sample_candidate, sample_job)
    assert exp_resp.generation_type == GenerationType.JOB_MATCH_EXPLANATION

    editor = ResumeBulletEditor()
    ed_resp = editor.suggest_bullet(
        sample_candidate,
        sample_job,
        target_bullet="Designed search ranking models improving relevance by 18%.",
    )
    assert ed_resp.generation_type == GenerationType.RESUME_BULLET_SUGGESTION


def test_groq_generator_unconfigured(sample_candidate, sample_job):
    groq_gen = GroqGenerator(api_key=None)
    assert not groq_gen.is_configured
    dummy_req = GenerationRequest(
        candidate_profile=sample_candidate,
        job_description=sample_job,
        generation_type=GenerationType.JOB_MATCH_EXPLANATION,
    )
    with pytest.raises(ProviderNotConfiguredError):
        groq_gen.generate(dummy_req)
