# NeverInvent Phase 2: Claim Verification Research Evaluation Report

**Date:** 2026-11-18  
**Benchmark:** Dataset A (Controlled Synthetic Fabrications & Faithful Counterparts)  
**Total Evaluation Cases:** 50 (Balanced across 10 fabrication categories)  

---

## 1. Executive Summary & Core Results

| Metric | Measured Value | Target / Baseline |
|---|---|---|
| **Fabrication Detection Precision** | **1.0000** | >= 0.8500 |
| **Fabrication Detection Recall** | **0.9048** | >= 0.8500 |
| **F1 Score** | **0.9500** | >= 0.8500 |
| **False Block Rate (on Faithful)** | **0.0000** | <= 0.0500 |
| **Ambiguity Rate (Escalated)** | **0.3000** | ~0.2000 |
| **Mean Latency per Claim** | **0.563 ms** | < 10.000 ms |
| **p95 Latency per Claim** | **0.822 ms** | < 25.000 ms |

> [!IMPORTANT]
> **Zero False Blocks Achieved:** Faithful candidate claims are never wrongly classified as UNSUPPORTED.
> Incomplete or uncertain claims are escalated as `AMBIGUOUS` for human review rather than being silently rejected.

---

## 2. 3-Class Evaluation Breakdown (SUPPORTED, UNSUPPORTED, AMBIGUOUS)

| Class | Precision | Recall | F1 Score | Support |
|---|---|---|---|---|
| **SUPPORTED** | 1.0000 | 0.8000 | 0.8889 | 20 |
| **UNSUPPORTED** | 1.0000 | 0.9048 | 0.9500 | 21 |
| **AMBIGUOUS** | 0.6000 | 1.0000 | 0.7500 | 9 |
| **Macro Average** | **0.8667** | **0.9016** | **0.8630** | 50 |

---

## 3. Confusion Matrix (Expected vs Predicted Verdict)

| Expected \ Predicted | SUPPORTED | UNSUPPORTED | AMBIGUOUS | Total |
|---|---|---|---|---|
| **SUPPORTED** | 16 | 0 | 4 | 20 |
| **UNSUPPORTED** | 0 | 19 | 2 | 21 |
| **AMBIGUOUS** | 0 | 0 | 9 | 9 |

---

## 4. Per-Category Performance Breakdown

| Category | Cases | Correct | Accuracy | Precision | Recall | F1 |
|---|---|---|---|---|---|---|
| `date_alteration` | 5 | 5 | 1.00 | 1.00 | 1.00 | 1.00 |
| `duration_exaggeration` | 5 | 5 | 1.00 | 1.00 | 1.00 | 1.00 |
| `invented_degree` | 5 | 3 | 0.60 | 1.00 | 1.00 | 1.00 |
| `invented_employer` | 5 | 5 | 1.00 | 1.00 | 1.00 | 1.00 |
| `invented_skill` | 5 | 5 | 1.00 | 1.00 | 1.00 | 1.00 |
| `metric_inflation` | 5 | 5 | 1.00 | 1.00 | 1.00 | 1.00 |
| `percentage_change` | 5 | 3 | 0.60 | 1.00 | 0.33 | 0.50 |
| `project_ownership` | 5 | 3 | 0.60 | 1.00 | 1.00 | 1.00 |
| `quantity_alteration` | 5 | 5 | 1.00 | 1.00 | 1.00 | 1.00 |
| `unsupported_responsibility` | 5 | 5 | 1.00 | 1.00 | 1.00 | 1.00 |

---

## 5. Ablation Study: Strategy Contribution Analysis

To quantify the individual contribution of each verification module, we evaluated the system under 6 incremental conditions:

| Condition | Enabled Strategies | Precision | Recall | F1 | False Block Rate | Ambiguity Rate |
|---|---|---|---|---|---|---|
| **1. Exact Match Only** | `1_exact_only` | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.9000 |
| **2. Exact + Normalized** | `2_exact_norm` | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.8800 |
| **3. Exact + Norm + Alias** | `3_exact_norm_alias` | 1.0000 | 0.0000 | 0.0000 | 0.0000 | 0.8800 |
| **4. + Numeric & Temporal** | `4_add_numeric_temporal` | 1.0000 | 0.6190 | 0.7647 | 0.0000 | 0.4200 |
| **5. + Entity & Contradiction** | `5_add_entity_contradiction` | 1.0000 | 0.7619 | 0.8649 | 0.0000 | 0.3600 |
| **6. Full System (All 8)** | `6_full_system` | 1.0000 | 0.9048 | 0.9500 | 0.0000 | 0.3000 |

### Key Insights from Ablation:
1. **Exact match alone** achieves high precision but fails to catch inflated metrics, date shifts, and aliases.
2. **Numerical and Temporal strategies** provide the single largest boost in fabrication detection recall, identifying quantitative inflation.
3. **Contradiction and Evidence Sufficiency** prevent invented skills and senior role exaggerations from slipping through as ambiguous.
4. **Deterministic execution** eliminates the latency and non-determinism of generative LLM evaluation, running in under 1ms per claim on commodity hardware.

---

## 6. Dataset B (Natural LLM Outputs) & LLM-as-Judge Baseline Status

- **Dataset B Status:** Awaiting LLM generation API key (`GROQ_API_KEY`) for live model sampling. Deterministic verifier is fully operational independent of external APIs.
- **LLM Baseline:** Standardized prompt template available; ready to benchmark once external credentials are provided.
