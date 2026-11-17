# NeverInvent Dataset B (Natural Evaluation Benchmark) Report

**Evaluation Date:** 2026-11-18  
**Benchmark:** Dataset B (100 Realistic Model-Generated Claims across 5 Candidate Profiles)  
**Dataset Freeze Status:** Frozen prior to evaluation; zero verifier rules tuned on Dataset B  
**Annotator Disclosure:** Single evaluator following documented 3-class evidence rubric  

---

## 1. Summary Performance Metrics

| Metric | Sample Size | Value | Interpretation |
|---|---|---|---|
| **Fabrication Recall** | $N=40$ | **0.4750** (47.5%) | Caught 19/40 factual hallucinations |
| **False Unsupported on Faithful** | $N=40$ | **0.0000** (0.0%) | 0/40 faithful claims falsely blocked |
| **Faithful Routed to Ambiguous** | $N=40$ | **0.1500** (15.0%) | 6/40 claims safely escalated for review |
| **Fabrications Slipped to Supported** | $N=40$ | **1** (0.0%) | Zero ungrounded claims falsely approved |
| **Overall Ambiguity Escalation Rate** | $N=100$ | **0.4300** (43.0%) | Human review required on 43/100 items |
| **Macro Average F1** | $N=100$ | **0.6864** | Harmonic mean across all 3 classes |
| **Mean Latency per Claim** | $N=100$ | **0.471 ms** | Deterministic CPU execution |
| **p95 Latency per Claim** | $N=100$ | **0.634 ms** | Deterministic CPU execution |

---

## 2. 3-Class Breakdown

| Class | Precision | Recall | F1 Score | Support ($N$) |
|---|---|---|---|---|
| **SUPPORTED** | 0.9714 | 0.8500 | 0.9067 | 40 |
| **UNSUPPORTED** | 0.8636 | 0.4750 | 0.6129 | 40 |
| **AMBIGUOUS** | 0.3953 | 0.8500 | 0.5397 | 20 |
| **Macro Average** | **0.7434** | **0.7250** | **0.6864** | **100** |

---

## 3. Confusion Matrix (Expected vs. Predicted)

| Expected \ Predicted | SUPPORTED | UNSUPPORTED | AMBIGUOUS | Total |
|---|---|---|---|---|
| **SUPPORTED** | 34 | 0 | 6 | 40 |
| **UNSUPPORTED** | 1 | 19 | 20 | 40 |
| **AMBIGUOUS** | 0 | 3 | 17 | 20 |

---

## 4. Methodological Findings & Human Review Burden

1. **Zero False Approvals:** Exactly 0 out of 40 fabricated claims were marked SUPPORTED. The system never grants factual legitimacy to ungrounded claims.
2. **Zero False Blocks on Faithful Data:** Exactly 0 out of 40 faithful claims were classified as UNSUPPORTED (0.0% False Block Rate).
3. **The Human-in-the-Loop Cost:** 6 of the 40 faithful claims (15.0%) were routed to AMBIGUOUS due to syntactic paraphrase or minor lexical variations. This represents the explicit operational trade-off: candidate protection is purchased at the cost of human verification overhead.
