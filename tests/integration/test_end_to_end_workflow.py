"""
integration/test_end_to_end_workflow.py — Full end-to-end test of NeverInvent candidate workflow.

Tests:
1. Ingestion of raw candidate resume text.
2. Job retrieval and evidence-grounded skill matching.
3. Unverified proposal generation (faithful & fabricated).
4. Independent verification with claim-level evidence anchors.
5. Re-verification of candidate manual edits.
6. Approval decision recording and audit persistence.
"""

import pytest
from fastapi.testclient import TestClient

from neverinvent.api.main import app
from neverinvent.generation.models import GenerationMode, GenerationType
from neverinvent.persistence import init_db
from neverinvent.workflow.models import ApprovalDecision, ProposalStatus


@pytest.fixture(scope="module")
def client():
    init_db("sqlite:///:memory:")
    with TestClient(app) as c:
        yield c


def test_complete_neverinvent_workflow(client):
    # STEP 1: Upload and parse candidate resume
    resume_text = """Alice Smith
alice.smith@example.com | (555) 123-4567

Skills
Python, PyTorch, Kubernetes, AWS, Docker, Spark

Work Experience
Google - Senior Machine Learning Engineer
Jan 2021 - Present
- Designed search ranking models improving relevance by 18%.
- Scaled inference service handling 500ms requests.

Meta - Machine Learning Engineer
Jan 2019 - Dec 2020
- Built data processing pipelines using Python and Spark.

Education
Stanford University
B.S. in Computer Science
2015 - 2019
"""
    upload_resp = client.post("/api/resume/upload", data={"raw_text_input": resume_text})
    assert upload_resp.status_code == 200
    cid = upload_resp.json()["candidate_id"]
    profile = upload_resp.json()["profile"]
    assert profile["candidate_name"] == "Alice Smith"
    assert len(profile["skills"]) >= 5

    # STEP 2: Retrieve jobs and perform evidence-grounded match
    jobs_resp = client.get("/api/jobs")
    assert jobs_resp.status_code == 200
    jobs = jobs_resp.json()["jobs"]
    assert len(jobs) >= 1
    job_id = jobs[0]["job_id"]

    match_resp = client.post(
        "/api/jobs/match",
        json={"candidate_id": cid, "job_id": job_id},
    )
    assert match_resp.status_code == 200
    match_data = match_resp.json()["breakdown"]
    assert match_data["grounded_match_score"] > 0.0
    assert match_data["dealbreaker_result"]["passed"] is True

    # STEP 3: Generate fabricated edit (e.g. 40% vs 18%)
    fab_gen_resp = client.post(
        "/api/verify/generate",
        json={
            "candidate_id": cid,
            "job_id": job_id,
            "generation_type": GenerationType.RESUME_BULLET_SUGGESTION.value,
            "mode": GenerationMode.FABRICATED_METRIC.value,
            "target_bullet": "Designed search ranking models improving relevance by 18%.",
        },
    )
    assert fab_gen_resp.status_code == 200
    fab_proposal = fab_gen_resp.json()["proposal"]

    # STEP 4: Independent verification intercepts the fabrication!
    assert fab_proposal["status"] == ProposalStatus.CONTAINS_UNSUPPORTED.value
    assert fab_proposal["unsupported_count"] >= 1
    # Check that contradicting evidence is anchored
    unsupported_claim = next(
        r for r in fab_proposal["verification_results"] if r["final_verdict"] == "UNSUPPORTED"
    )
    assert len(unsupported_claim["contradicting_evidence"]) > 0

    # STEP 5: Candidate manual edit correcting the fabricated metric back to truthful 18%
    corrected_text = "Architected high-throughput search ranking models, improving search relevance by 18% across production clusters."
    reverify_resp = client.post(
        "/api/verify/reverify",
        json={
            "proposal_id": fab_proposal["proposal_id"],
            "candidate_id": cid,
            "edited_text": corrected_text,
        },
    )
    assert reverify_resp.status_code == 200
    reverified = reverify_resp.json()["proposal"]
    assert reverified["status"] == ProposalStatus.ALL_SUPPORTED.value
    assert reverified["unsupported_count"] == 0

    # STEP 6: Human approval action
    approve_resp = client.post(
        "/api/approve/decision",
        json={
            "proposal_id": reverified["proposal_id"],
            "decision": ApprovalDecision.MANUALLY_EDITED_APPROVED.value,
            "final_text": corrected_text,
            "notes": "Corrected 40% to documented 18% and approved.",
        },
    )
    assert approve_resp.status_code == 200
    assert approve_resp.json()["status"] == "success"

    # STEP 7: Verify immutable audit trail
    audits_resp = client.get("/api/approve/audits")
    assert audits_resp.status_code == 200
    audits = audits_resp.json()["audits"]
    assert len(audits) >= 1
    latest_audit = audits[0]
    assert latest_audit["proposal_id"] == reverified["proposal_id"]
    assert latest_audit["decision"] == ApprovalDecision.MANUALLY_EDITED_APPROVED.value
    assert "18%" in latest_audit["final_text"]
