"""
Unit tests for jobs module.
"""

from pathlib import Path
import pytest

from neverinvent.jobs import JobDescription, JobLoadingError, JobSource, load_jobs_from_jsonl


def test_job_description_model():
    job = JobDescription(
        job_id="test_01",
        title="ML Engineer",
        normalized_title="machine learning engineer",
        company="AI Corp",
        raw_description="Build search models with PyTorch.",
        required_skills=["python", "pytorch"],
        preferred_skills=["faiss"],
        source_type=JobSource.SYNTHETIC,
    )
    assert job.job_id == "test_01"
    searchable = job.get_searchable_text()
    assert "ML Engineer" in searchable
    assert "python, pytorch" in searchable
    assert "faiss" in searchable


def test_load_jobs_valid_file():
    jobs_path = Path("data/job_postings/sample_jobs.jsonl")
    jobs, errors = load_jobs_from_jsonl(jobs_path)
    assert len(jobs) == 10
    assert len(errors) == 0
    assert jobs[0].job_id == "job_001"
    assert "python" in jobs[0].required_skills


def test_load_jobs_with_errors(tmp_path: Path):
    corrupt_file = tmp_path / "mixed_jobs.jsonl"
    corrupt_file.write_text(
        '{"job_id": "j1", "title": "Dev", "normalized_title": "dev", "company": "Co", "raw_description": "text"}\n'
        'INVALID JSON LINE\n'
        '{"job_id": "j2", "title": 123, "normalized_title": "dev"}\n',  # missing required fields like company
        encoding="utf-8",
    )
    jobs, errors = load_jobs_from_jsonl(corrupt_file)
    assert len(jobs) == 1
    assert len(errors) == 2
    assert errors[0]["line_no"] == 2
    assert errors[1]["line_no"] == 3


def test_load_jobs_missing_file():
    with pytest.raises(JobLoadingError):
        load_jobs_from_jsonl("non_existent_jobs.jsonl")
