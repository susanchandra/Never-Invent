# NeverInvent — Demonstration & Verification Guide

**System Version:** NeverInvent v1.0 (Research Prototype)  
**Tagline:** Verify AI-generated claims. Stop fabricated resume information.  
**Notice:** All candidate names, employers, contact details, and job descriptions used in these demonstrations are **100% synthetic** benchmarks constructed for empirical AI evaluation.

---

## 1. Quick Start & Environment Setup

### 1.1 Start the Application Server

```bash
# Clone the repository
git clone https://github.com/susanchandra/Never-Invent.git
cd Never-Invent

# Install Python dependencies (Python 3.10+ recommended)
pip install -r requirements.txt

# Start the FastAPI server and UI
uvicorn neverinvent.api.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser to: **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

### 1.2 Verify the Test Suite

NeverInvent includes 74 comprehensive tests (adversarial security audits, unit tests, audit integrity tests, Dataset B evaluation pipeline, and integration pipelines):

```bash
# Run the fast unit and adversarial audit suite (~5 seconds, no model downloads)
pytest tests/adversarial/ tests/unit/test_audit_integrity.py tests/unit/test_matching.py \
       tests/unit/test_claims.py tests/unit/test_verification.py tests/unit/test_dataset_b.py \
       tests/unit/test_persistence.py -v

# Run the complete test suite (~90 seconds, includes dense BGE-small embeddings)
pytest tests/ -v
```

---

## 2. Interactive Five-Scenario Verification (CLI & API Walkthrough)

Below are the 5 core demonstration scenarios with exact, tested `curl` commands demonstrating NeverInvent's factual verification and governance invariants.

---

### Scenario 1: Faithful Generation & Successful Approval

**Goal:** Demonstrate that truthful candidate claims extracted from the resume are verified as `SUPPORTED` and approved without false friction.

```bash
# 1. Ingest synthetic candidate resume
curl -X POST "http://127.0.0.1:8000/api/resume/upload" \
  -F "file=@data/sample_resumes/alice_smith_synthetic.txt"

# Response returns: {"candidate_id": "cand_...", "skills_count": 8, "experience_count": 3}
```

```bash
# 2. Generate a faithful resume bullet proposal
curl -X POST "http://127.0.0.1:8000/api/verify/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_id": "cand_benchmark_alice",
    "job_id": "job_staff_mle",
    "generation_type": "resume_bullet_suggestion",
    "mode": "faithful",
    "provider": "mock"
  }'
```

**Expected JSON Response:**
```json
{
  "proposal_id": "prop_...",
  "status": "ALL_SUPPORTED",
  "supported_count": 3,
  "unsupported_count": 0,
  "ambiguous_count": 0,
  "claims": [
    {
      "claim_type": "SKILL",
      "value": "PyTorch",
      "verdict": "SUPPORTED",
      "evidence_citation": "Page 1, chars 142-149: 'PyTorch'"
    }
  ]
}
```

```bash
# 3. Record candidate approval
curl -X POST "http://127.0.0.1:8000/api/approve/decision" \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_id": "<PROPOSAL_ID_FROM_STEP_2>",
    "decision": "approved",
    "final_text": "<PROPOSED_TEXT_FROM_STEP_2>"
  }'
```

---

### Scenario 2: Quantitative Metric Inflation Interception & Approval Block

**Goal:** Demonstrate that an LLM attempting to inflate an 18% improvement to 40% is caught by the numerical verifier, flagged as `UNSUPPORTED`, and strictly blocked from human approval.

```bash
# 1. Generate a proposal with fabricated metric inflation
curl -X POST "http://127.0.0.1:8000/api/verify/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_id": "cand_benchmark_alice",
    "job_id": "job_staff_mle",
    "generation_type": "resume_bullet_suggestion",
    "mode": "fabricated_metric",
    "provider": "mock"
  }'
```

**Expected JSON Response:**
```json
{
  "proposal_id": "prop_...",
  "status": "CONTAINS_UNSUPPORTED",
  "supported_count": 2,
  "unsupported_count": 1,
  "ambiguous_count": 0,
  "claims": [
    {
      "claim_type": "METRIC",
      "value": "40%",
      "verdict": "UNSUPPORTED",
      "rationale": "Numerical value 40% contradicts documented evidence 18% in the same context.",
      "evidence_citation": "Contradicting source span: 'improved latency by 18%'"
    }
  ]
}
```

```bash
# 2. Attempt to bypass the gate and approve the fabricated proposal (MUST FAIL)
curl -X POST "http://127.0.0.1:8000/api/approve/decision" \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_id": "<PROPOSAL_ID_FROM_STEP_1>",
    "decision": "approved",
    "final_text": "Reduced inference latency by 40% using TensorRT."
  }'
```

**Expected HTTP 400 Bad Request Response:**
```json
{
  "detail": "Cannot approve a proposal containing UNSUPPORTED claims. Prohibited by verification integrity rules."
}
```

```bash
# 3. Properly reject the fabricated proposal
curl -X POST "http://127.0.0.1:8000/api/approve/decision" \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_id": "<PROPOSAL_ID_FROM_STEP_1>",
    "decision": "rejected",
    "final_text": "Reduced inference latency by 40% using TensorRT.",
    "notes": "Rejected: candidate achieved 18% latency reduction, not 40%."
  }'
```

---

### Scenario 3: Substring Collision Defense (Java vs. JavaScript)

**Goal:** Prove that naive substring matching vulnerabilities are prevented by regex word-boundary anchors. Claiming proficiency in `Java` when the candidate's resume only lists `JavaScript` does **not** match.

```bash
# Check skill verification with word boundaries
curl -X POST "http://127.0.0.1:8000/api/verify/generate" \
  -H "Content-Type: application/json" \
  -d '{
    "candidate_id": "cand_benchmark_alice",
    "job_id": "job_backend_engineer",
    "generation_type": "resume_bullet_suggestion",
    "mode": "invented_skill",
    "provider": "mock"
  }'
```

**System Behavior:**  
- The candidate possesses `JavaScript`. The proposal claims `Java`.
- The Normalized Match strategy applies `\bJava\b`, which fails to match `JavaScript`.
- Verdict: `UNSUPPORTED` (or `AMBIGUOUS`), protecting hiring teams from false skill matches.

---

### Scenario 4: Manual Edit, Forced Re-Verification, and Approval

**Goal:** Prove that if a user manually modifies proposed text, any prior verification token is invalidated, requiring fresh atomic claim extraction and verification.

```bash
# 1. Candidate manually fixes the inflated 40% metric back to 18%
curl -X POST "http://127.0.0.1:8000/api/verify/reverify" \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_id": "<PROPOSAL_ID_FROM_SCENARIO_2>",
    "candidate_id": "cand_benchmark_alice",
    "edited_text": "Optimized transformer inference latency by 18% across 4 A100 GPUs."
  }'
```

**Expected JSON Response:**
```json
{
  "proposal_id": "prop_...",
  "status": "ALL_SUPPORTED",
  "supported_count": 2,
  "unsupported_count": 0,
  "ambiguous_count": 0
}
```

```bash
# 2. Approve the re-verified text
curl -X POST "http://127.0.0.1:8000/api/approve/decision" \
  -H "Content-Type: application/json" \
  -d '{
    "proposal_id": "<PROPOSAL_ID_FROM_STEP_1>",
    "decision": "manually_edited_approved",
    "final_text": "Optimized transformer inference latency by 18% across 4 A100 GPUs."
  }'
```

---

### Scenario 5: Tamper-Evident Audit Trail Inspection

**Goal:** Inspect the durable audit log to confirm every approval and rejection is recorded with full provenance, timestamps, decision states, and cryptographic hash-chain integrity.

```bash
# Retrieve all audit records with chain validity status
curl -X GET "http://127.0.0.1:8000/api/approve/audits"
```

**Expected JSON Response:**
```json
[
  {
    "audit_id": "audit_842a...",
    "proposal_id": "prop_...",
    "candidate_id": "cand_benchmark_alice",
    "decision": "manually_edited_approved",
    "final_text": "Optimized transformer inference latency by 18% across 4 A100 GPUs.",
    "notes": null,
    "created_at": "2026-11-18T02:10:00Z",
    "chain_valid": true,
    "chain_error": null
  },
  {
    "audit_id": "audit_193b...",
    "proposal_id": "prop_...",
    "candidate_id": "cand_benchmark_alice",
    "decision": "rejected",
    "final_text": "Reduced inference latency by 40% using TensorRT.",
    "notes": "Rejected: candidate achieved 18% latency reduction, not 40%.",
    "chain_valid": true,
    "chain_error": null
  }
]
```

```bash
# Explicitly verify the full SHA-256 hash chain integrity
curl -X GET "http://127.0.0.1:8000/api/approve/verify-chain"
```

**Expected JSON Response (tamper-free chain):**
```json
{
  "chain_valid": true,
  "record_count": 2,
  "chain_error": null
}
```

**If tampering is detected**, the response includes:
```json
{
  "chain_valid": false,
  "record_count": 2,
  "chain_error": "Hash mismatch at sequence 1: expected abc123... got xyz789..."
}
```

> **Limitation:** The SHA-256 hash chain detects payload tampering, record deletion, and reordering. It does not prevent full-chain rewriting by an attacker with direct database write access — it makes such manipulation detectable during the next verification call.

---

## 3. Web UI Visual Tour (5 Tabs)

If exploring via the web interface at `http://127.0.0.1:8000`:

1. **Tab 1: Candidate Profile**  
   - Click **"Load Benchmark Profile (Alice Smith)"** or upload any PDF/TXT resume.
   - Inspect parsed skills, employers, calendar durations, and highlighted source text spans.

2. **Tab 2: Job Match**  
   - Select a target role (e.g., *Staff Machine Learning Engineer*).
   - View the **70/30 skill match breakdown**, dealbreaker checks, and explicit evidence citations for required skills.

3. **Tab 3: Edit & Generation**  
   - Toggle demonstration modes: *1. Faithful*, *2. Fabricated Metric*, *3. Invented Skill*, *4. Ambiguous Fact*.
   - Click **"Generate & Verify Proposal"**.

4. **Tab 4: Claim Verification**  
   - Inspect colored verdict badges:
     - 🟢 **SUPPORTED**: Grounded in resume source text.
     - 🔴 **UNSUPPORTED**: Fabricated or contradicted metric/date/skill.
     - 🟡 **AMBIGUOUS**: Missing evidence requiring human review.
   - Test the manual editor: edit text, click **"Re-Verify"**, then **"Approve"**.

5. **Tab 5: Approval Audit**  
   - Review historical decisions and tamper-evident audit logs.
