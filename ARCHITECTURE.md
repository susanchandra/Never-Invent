# Architecture & System Design — NeverInvent

**Tagline:** Verify AI-generated claims. Stop fabricated resume information.  
**System Version:** NeverInvent v1.0 (Research Prototype)

---

## 1. Core Architectural Principle

> **Fundamental Invariant:**  
> The claim verification engine must be strictly decoupled from the text generation model.  
> The generator may propose text; it must **never** decide whether its own claims are true.

This separation is not an implementation preference—it is the foundational research requirement. In an LLM-based workflow, self-verification suffers from autoregressive confirmation bias. By enforcing a deterministic, rule-grounded verifier with zero LLM dependencies, NeverInvent achieves reproducible, auditable, sub-millisecond factual verification with zero hallucination.

---

## 2. System Architecture Overview

```mermaid
flowchart TB
    subgraph Client["Client Layer"]
        UI["Interactive Web UI\nHTML5 / Vanilla JS / CSS3\n5-Tab Responsive Interface"]
    end

    subgraph API["API Gateway (FastAPI)"]
        RouterResume["/api/resume\nUpload, Parse, Profile Extraction"]
        RouterJobs["/api/jobs\nIndex, Ingest, List Postings"]
        RouterMatch["/api/matching\nBM25 + BGE-small + RRF Fusion"]
        RouterVerify["/api/verify\nExtraction & 8-Strategy Verification"]
        RouterApprove["/api/approve\nTamper-Proof Audit & Approval Gate"]
    end

    subgraph CoreEngine["Core Processing Pipelines"]
        subgraph Pipeline1["1. Ingestion & Provenance"]
            PDF["PyMuPDF / Text Extractor"] --> RawDoc["RawDocument\nSource Text + Character Spans"]
            RawDoc --> Parser["Heuristic Profile Parser"]
            Parser --> Profile["CandidateProfile\nSkills, Roles, Metrics, Dates, Spans"]
        end

        subgraph Pipeline2["2. Hybrid Retrieval & Match"]
            JobCorpus["Job Posting Corpus"] --> BM25["BM25 Lexical Index"]
            JobCorpus --> Dense["BGE-small FAISS Index"]
            Profile --> Query["Candidate Query Vector"]
            Query --> BM25
            Query --> Dense
            BM25 & Dense --> RRF["Reciprocal Rank Fusion\n(k = 60)"]
            RRF --> MatchScore["EvidenceGroundedMatcher\n70/30 Skill Scoring + Dealbreakers"]
        end

        subgraph Pipeline3["3. Generation & Claim Extraction"]
            GenLayer["Generator Protocol\n(Deterministic Mock / Groq API)"] --> Proposal["Proposed Resume Edit / Explanation"]
            Proposal --> Extractor["Atomic Claim Extractor\nType, Entity, Metric, Temporal"]
            Extractor --> ClaimsList["List of Atomic Claims"]
        end

        subgraph Pipeline4["4. Independent Verification Engine"]
            ClaimsList --> Verifier["ClaimVerifier\n(8 Deterministic Strategies)"]
            Profile -.->|Evidence Bundle| Verifier
            RawDoc -.->|Source Spans| Verifier
            Verifier --> Verdicts["Claim Verdicts\nSUPPORTED / UNSUPPORTED / AMBIGUOUS"]
        end
    end

    subgraph Governance["5. Governance & Human Approval Gate"]
        Verdicts --> Gate{"Integrity Gate"}
        Gate -- Has UNSUPPORTED --> RejectOnly["Approval Prohibited (400 Bad Request)\nUser Rejection Required"]
        Gate -- Has AMBIGUOUS --> Override["Manual Review Required\nOverride Justification Logged"]
        Gate -- ALL SUPPORTED --> ApproveOK["Approval Permitted"]
        ApproveOK & Override --> AuditDB[("SQLite Persistence\nAudit Records & Cryptographic Hashes")]
    end

    UI <===>|HTTP REST / JSON| API
    RouterResume --> Pipeline1
    RouterJobs & RouterMatch --> Pipeline2
    RouterVerify --> Pipeline3 & Pipeline4
    RouterApprove --> Governance
```

---

## 3. Trust Boundary Analysis

NeverInvent operates with strict trust boundaries to prevent fabricated claims from leaking into verified records:

```mermaid
flowchart LR
    subgraph Untrusted["UNTRUSTED ZONE"]
        U1["Uploaded Files\n(PDF/TXT)"]
        U2["LLM Generations\n(Groq/Mock Prompts)"]
        U3["Manual User Edits\n(Client-side Text)"]
    end

    subgraph Boundary["SECURITY & INTEGRITY BOUNDARY"]
        B1["10MB Chunked Ceiling\nPath Traversal Neutralization"]
        B2["Mandatory Claim Extraction\n& Multi-Strategy Verification"]
        B3["Freshness Check:\nSubmitted Text === Verified Text"]
    end

    subgraph Trusted["TRUSTED ZONE"]
        T1["RawDocument & SourceSpans\n(Immutable Source of Truth)"]
        T2["CandidateProfile\n(Structured Grounding)"]
        T3["Deterministic Verifier\n(Zero Generative Parameters)"]
        T4["Audit Log\n(Tamper-Evident Stored Decisions)"]
    end

    U1 -->|Sanitization & Size Limit| B1 --> T1 & T2
    U2 -->|Forced Extraction| B2 --> T3
    U3 -->|Invalidate & Re-verify| B3 --> T3
    T3 --> T4
```

### Trust Boundary Invariants:
1. **Generative LLM is Untrusted:** No output from an LLM is ever written to verified storage or presented as verified fact without passing through the independent claim verifier.
2. **User Input is Untrusted:** Any manual edits made to a proposed bullet immediately invalidate prior verification tokens. The backend rejects stale verification IDs and requires re-extracting and re-verifying the edited text.
3. **Source Evidence is Immutable:** The `RawDocument` and extracted `CandidateProfile` created upon resume upload serve as the read-only grounding baseline.

---

## 4. Ingestion & Provenance Architecture

```mermaid
sequenceDiagram
    autonumber
    actor User
    participant API as Resume Router
    participant Ingest as PDF/Text Ingestion
    participant Parser as Profile Parser
    participant DB as SQLite Storage

    User->>API: POST /api/resume/upload (PDF/TXT)
    API->>API: Enforce 10MB file limit & sanitize filename
    API->>Ingest: Extract text & character byte offsets
    Ingest-->>API: RawDocument (full text + SourceSpans)
    API->>Parser: Extract structured entities with exact span citations
    Parser-->>API: CandidateProfile (skills, employers, dates, metrics)
    API->>DB: Persist RawDocument + CandidateProfile
    API-->>User: HTTP 200 (candidate_id, summary statistics)
```

Every extracted datum in `CandidateProfile` maintains:
- `original_text`: Verbatim string as it appeared in the resume.
- `source_span`: Tuple `(char_start, char_end, page_number)`.
- `normalized_value`: Standardized representation (lowercase, ISO date, float metric).

---

## 5. Claim Verification Pipeline

```mermaid
flowchart TD
    ClaimInput["Atomic Claim\n(Type, Subject, Predicate, Object, Value)"] --> StratCheck{Strategy Dispatch}

    StratCheck --> S1["1. Exact Match Strategy\nVerbatim substring in RawDocument?"]
    S1 -- Yes --> V_Supp["Verdict: SUPPORTED\nConfidence: 1.0"]
    S1 -- No --> S2["2. Normalized Match Strategy\nRegex word-boundary \\b match?"]

    S2 -- Yes --> V_Supp
    S2 -- No --> S3["3. Alias Match Strategy\nBidirectional tech alias dictionary?"]

    S3 -- Yes --> V_Supp
    S3 -- No --> S4["4. Numerical Match Strategy\nMagnitude check, 5% tolerance,\ncontext word overlap?"]

    S4 -- Value Exceeds Bound --> V_Unsupp["Verdict: UNSUPPORTED\nContradiction Detected"]
    S4 -- Within Bound --> V_Supp
    S4 -- Context Mismatch --> S5["5. Temporal Match Strategy\nCalendar months tenure calculation,\noverlapping job interval merging?"]

    S5 -- Exceeds Total Tenure --> V_Unsupp
    S5 -- Within Tenure --> V_Supp
    S5 -- Non-Temporal --> S6["6. Entity Match Strategy\nDegree / Employer in profile?"]

    S6 -- Unknown Entity --> S7["7. Contradiction Detection\nSeniority elevation (Junior -> Lead)?"]

    S7 -- Confirmed Contradiction --> V_Unsupp
    S7 -- No Contradiction --> S8["8. Sufficiency Strategy\nAbsence of evidence != Proof of absence"]

    S8 --> V_Ambig["Verdict: AMBIGUOUS\nEscalate for Human Review"]
```

---

## 6. Approval & Governance State Machine

```mermaid
stateDiagram-v2
    [*] --> Generated: Proposal Created
    Generated --> Extracted: Atomic Claims Parsed
    Extracted --> Verified: Verifier Computes Verdicts

    state Verified {
        [*] --> CheckStatus
        CheckStatus --> ALL_SUPPORTED: All claims SUPPORTED
        CheckStatus --> CONTAINS_AMBIGUOUS: ≥1 AMBIGUOUS, 0 UNSUPPORTED
        CheckStatus --> CONTAINS_UNSUPPORTED: ≥1 UNSUPPORTED
    }

    CONTAINS_UNSUPPORTED --> Rejected: Candidate Rejects Proposal
    CONTAINS_UNSUPPORTED --> Blocked: Attempted Approve (HTTP 400 Forbidden)
    Blocked --> CONTAINS_UNSUPPORTED

    CONTAINS_AMBIGUOUS --> Rejected: Candidate Rejects
    CONTAINS_AMBIGUOUS --> ApprovedOverride: Human Overrides with Rationale
    CONTAINS_AMBIGUOUS --> ManuallyEdited: Candidate Modifies Text

    ALL_SUPPORTED --> Approved: Direct Approval
    ALL_SUPPORTED --> Rejected: Candidate Declines
    ALL_SUPPORTED --> ManuallyEdited: Candidate Modifies Text

    ManuallyEdited --> Extracted: Forced Re-Extraction & Verification
    Approved --> [*]: Audit Record Persisted
    ApprovedOverride --> [*]: Audit Record Persisted
    Rejected --> [*]: Audit Record Persisted
```

---

## 7. Module Directory Structure & Responsibilities

| Directory | Core Responsibility | Key Invariants |
|---|---|---|
| `neverinvent/ingestion/` | Raw text and span extraction from PDF/TXT documents. | Never modifies source content; records character spans for every token. |
| `neverinvent/parsing/` | Converts raw text into structured `CandidateProfile`. | Never guesses or fabricates missing fields; leaves unknown values as `None`. |
| `neverinvent/retrieval/` | Lexical (BM25), Dense (BGE-small), and Hybrid (RRF) search. | Decoupled from verification; retrieval score does not constitute factual proof. |
| `neverinvent/matching/` | Evaluates candidate fit against job requirements. | 70/30 required vs preferred skill weighting; dealbreaker enforcement. |
| `neverinvent/generation/` | Pluggable text generator (Mock / Groq LLM API). | Generates unverified proposals; completely isolated from verifier. |
| `neverinvent/claims/` | Extracts atomic factual claims from generated text. | Rule-based extraction; does not assign verdicts. |
| `neverinvent/verification/` | 8-strategy deterministic verification engine. | Zero LLM calls; sub-millisecond latency; outputs SUPPORTED/UNSUPPORTED/AMBIGUOUS. |
| `neverinvent/workflow/` | Proposal lifecycle, review states, and audit tracking. | Strictly enforces approval gates and prevents duplicate or stale approvals. |
| `neverinvent/persistence/` | SQLAlchemy models and SQLite storage layer. | Relational integrity for profiles, jobs, proposals, and audit records. |
| `neverinvent/api/` | Thin FastAPI router exposing typed REST endpoints. | Pydantic request/response validation; 10MB payload ceiling; CORS protection. |
| `frontend/` | Vanilla JS, HTML5, CSS3 user interface. | Zero external framework dependencies; clean 5-tab responsive workflow. |
| `neverinvent/evaluation/` | Empirical benchmarks for retrieval and claim verification. | Reproducible evaluation suites with zero hardcoded results. |

---

## 8. Key Architectural Decisions (ADR Summary)

| Decision | Alternative Considered | Justification |
|---|---|---|
| **Deterministic Verifier** | LLM-as-a-Judge | LLM-as-a-judge is non-deterministic, hallucinates, suffers from prompt drift, adds $1000\times$ latency (~1500ms vs 0.56ms), and incurs API cost. Deterministic rules are audit-traceable and fast. |
| **Three-Class Taxonomy** | Binary (True / False) | Real resumes contain incomplete, paraphrased, or unprovable claims. Forcing binary classification leads to high False Block Rates on legitimate candidates. `AMBIGUOUS` safely escalates to human review. |
| **Calendar Months Merging** | Simple Year/Month Subtraction | Concurrent employment across multiple roles artificially inflates total tenure if durations are summed naively. Interval merging computes true calendar experience. |
| **Reciprocal Rank Fusion** | Linear Score Combination | RRF ($k=60$) does not require score normalization across disparate scales (BM25 unbounded vs cosine $[-1, 1]$) and exhibits superior ranking robustness. |
| **Vanilla Frontend** | React / Next.js / Vue | Avoids multi-gigabyte node_modules and complex build toolchains. The project focus is Applied AI research and verification systems engineering. |
| **SQLite + SQLAlchemy** | PostgreSQL / Microservices | Zero external infrastructure overhead; fully self-contained repository; instantaneous setup for peer review and interview demonstration. |
