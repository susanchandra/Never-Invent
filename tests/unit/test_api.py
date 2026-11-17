"""
Unit and integration tests for FastAPI backend endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from neverinvent.api.main import app
from neverinvent.generation.models import GenerationMode, GenerationType
from neverinvent.jobs.models import JobDescription, JobSource
from neverinvent.persistence import init_db
from neverinvent.workflow.models import ApprovalDecision, ProposalStatus


@pytest.fixture(scope="module")
def client():
    # Use memory or default test sqlite
    init_db("sqlite:///:memory:")
    with TestClient(app) as c:
        yield c


def test_healthcheck(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"
    assert data["service"] == "NeverInvent"


def test_resume_upload_and_retrieve(client):
    resume_text = """Alice Smith
alice.smith@example.com | (555) 123-4567

Skills
Python, PyTorch, Kubernetes, AWS

Work Experience
Google - Senior Machine Learning Engineer
Jan 2021 - Present
- Designed search ranking models improving relevance by 18%.
- Scaled inference service handling 500ms requests.

Education
Stanford University
B.S. in Computer Science
2015 - 2019
"""
    # Test upload via form text input
    resp = client.post("/api/resume/upload", data={"raw_text_input": resume_text})
    assert resp.status_code == 200
    data = resp.json()
    assert "candidate_id" in data
    cid = data["candidate_id"]
    assert data["profile"]["candidate_name"] == "Alice Smith"

    # Test get profile
    get_resp = client.get(f"/api/resume/{cid}")
    assert get_resp.status_code == 200
    assert get_resp.json()["profile"]["candidate_name"] == "Alice Smith"


def test_jobs_list_search_match(client):
    # 1. List jobs
    list_resp = client.get("/api/jobs")
    assert list_resp.status_code == 200
    jobs = list_resp.json()["jobs"]
    assert len(jobs) >= 1
    job_id = jobs[0]["job_id"]

    # 2. Search jobs
    search_resp = client.post(
        "/api/jobs/search",
        json={"query": "Machine Learning Engineer", "method": "bm25", "top_k": 3},
    )
    assert search_resp.status_code == 200
    assert len(search_resp.json()["results"]) >= 1

    # 3. Match candidate against job
    # First get candidate id from earlier test
    up_resp = client.post(
        "/api/resume/upload",
        data={"raw_text_input": "Alice Smith\nSkills\nPython, PyTorch\nWork Experience\nGoogle\nJan 2021 - Present\n- Built models.\n"},
    )
    cid = up_resp.json()["candidate_id"]

    match_resp = client.post(
        "/api/jobs/match",
        json={"candidate_id": cid, "job_id": job_id},
    )
    assert match_resp.status_code == 200
    breakdown = match_resp.json()["breakdown"]
    assert "grounded_match_score" in breakdown
    assert "dealbreaker_result" in breakdown


def test_verification_generation_and_approval_flow(client):
    # Upload Alice profile
    up_resp = client.post(
        "/api/resume/upload",
        data={
            "raw_text_input": (
                "Alice Smith\nSkills\nPython, PyTorch\n"
                "Work Experience\nGoogle\nJan 2021 - Present\n"
                "- Designed search ranking models improving relevance by 18%.\n"
            )
        },
    )
    cid = up_resp.json()["candidate_id"]
    job_id = client.get("/api/jobs").json()["jobs"][0]["job_id"]

    # 1. Generate faithful proposal
    faithful_resp = client.post(
        "/api/verify/generate",
        json={
            "candidate_id": cid,
            "job_id": job_id,
            "generation_type": "resume_bullet_suggestion",
            "mode": "faithful",
            "target_bullet": "Designed search ranking models improving relevance by 18%.",
        },
    )
    assert faithful_resp.status_code == 200
    f_prop = faithful_resp.json()["proposal"]
    assert f_prop["status"] == ProposalStatus.ALL_SUPPORTED.value

    # 2. Generate fabricated proposal (inflated metric: 40%)
    fab_resp = client.post(
        "/api/verify/generate",
        json={
            "candidate_id": cid,
            "job_id": job_id,
            "generation_type": "resume_bullet_suggestion",
            "mode": "fabricated_metric",
            "target_bullet": "Designed search ranking models improving relevance by 18%.",
        },
    )
    assert fab_resp.status_code == 200
    fab_prop = fab_resp.json()["proposal"]
    assert fab_prop["status"] == ProposalStatus.CONTAINS_UNSUPPORTED.value
    assert fab_prop["unsupported_count"] >= 1

    # 3. Manual Edit Re-verification
    # User corrects fabricated proposal
    reverify_resp = client.post(
        "/api/verify/reverify",
        json={
            "proposal_id": fab_prop["proposal_id"],
            "candidate_id": cid,
            "edited_text": "Engineered search ranking models improving relevance by 18%.",
        },
    )
    assert reverify_resp.status_code == 200
    rev_prop = reverify_resp.json()["proposal"]
    assert rev_prop["status"] == ProposalStatus.ALL_SUPPORTED.value

    # 4. Human Approval
    appr_resp = client.post(
        "/api/approve/decision",
        json={
            "proposal_id": rev_prop["proposal_id"],
            "decision": ApprovalDecision.MANUALLY_EDITED_APPROVED.value,
            "final_text": rev_prop["proposed_text"],
            "notes": "Verified and accepted by candidate.",
        },
    )
    assert appr_resp.status_code == 200
    assert appr_resp.json()["status"] == "success"

    # 5. Check Audit Log
    audits_resp = client.get("/api/approve/audits")
    assert audits_resp.status_code == 200
    audits = audits_resp.json()["audits"]
    assert len(audits) >= 1
    assert audits[0]["decision"] == ApprovalDecision.MANUALLY_EDITED_APPROVED.value
