"""
evaluation/retrieval_eval.py — Reproducible evaluation comparing BM25, Dense, and Hybrid RRF retrieval.

Reports:
- Precision@5
- Recall@10
- MRR
- nDCG@10
Across 5 diverse candidate profiles and 50 manually reviewed candidate-job relevance judgments.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
import pandas as pd

from neverinvent.evaluation.metrics import (
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)
from neverinvent.jobs.job_loader import load_jobs_from_jsonl
from neverinvent.retrieval.bm25_retriever import BM25Retriever
from neverinvent.retrieval.dense_retriever import DenseRetriever
from neverinvent.retrieval.hybrid_retriever import HybridRetriever

# 5 Candidate benchmark queries
CANDIDATE_QUERIES = {
    "cand_ml_sr": (
        "Senior Machine Learning Engineer with 5+ years experience in Python, PyTorch, "
        "FAISS vector search, deep learning neural search ranking models, transformers."
    ),
    "cand_nlp_rs": (
        "NLP Research Scientist specializing in natural language processing, LLM hallucination, "
        "claim verification, factual consistency auditing, transformers, PyTorch."
    ),
    "cand_backend": (
        "Backend Systems Engineer experienced in Python, FastAPI, PostgreSQL, Redis, "
        "REST APIs, high-throughput microservices, Docker, automated testing."
    ),
    "cand_devops": (
        "DevOps Platform Infrastructure Engineer with Kubernetes, AWS, Docker, Terraform, "
        "CI/CD GitHub Actions pipelines, Prometheus monitoring."
    ),
    "cand_frontend": (
        "Frontend Software Engineer proficient in React, TypeScript, JavaScript, CSS, "
        "HTML, responsive UI design, interactive state management."
    ),
}


def load_judgments(path: str | Path) -> dict[str, dict[str, int]]:
    """
    Load judgments into structure:
    { query_id: { job_id: graded_relevance_score } }
    """
    judgments: dict[str, dict[str, int]] = {}
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            item = json.loads(line)
            qid = item["query_id"]
            jid = item["job_id"]
            rel = item["relevance"]
            if qid not in judgments:
                judgments[qid] = {}
            judgments[qid][jid] = rel
    return judgments


def evaluate_retrievers(
    jobs_path: str | Path = "data/job_postings/sample_jobs.jsonl",
    judgments_path: str | Path = "neverinvent/evaluation/datasets/retrieval_judgments.jsonl",
    output_report_path: str | Path = "neverinvent/evaluation/reports/retrieval_evaluation_report.md",
) -> dict[str, Any]:
    # 1. Load jobs
    jobs, errors = load_jobs_from_jsonl(jobs_path)
    if not jobs:
        raise ValueError(f"No jobs loaded from {jobs_path}")

    # 2. Load ground-truth judgments
    judgments = load_judgments(judgments_path)

    # 3. Initialize and fit retrievers
    bm25 = BM25Retriever()
    dense = DenseRetriever(model_name="BAAI/bge-small-en-v1.5", device="cpu")
    hybrid = HybridRetriever(bm25, dense, rrf_k=60)

    hybrid.fit(jobs)

    retrievers = {
        "BM25": lambda q: [r.job_id for r in bm25.search(q, top_k=10)],
        "Dense (BGE-small)": lambda q: [r.job_id for r in dense.search(q, top_k=10)],
        "Hybrid (RRF k=60)": lambda q: [r.job_id for r in hybrid.search_rrf(q, top_k=10)],
    }

    metrics_by_system: dict[str, list[dict[str, float]]] = {name: [] for name in retrievers}

    for qid, query_text in CANDIDATE_QUERIES.items():
        q_judgments = judgments.get(qid, {})
        # Binary relevant set (relevance >= 1)
        relevant_binary = {jid for jid, rel in q_judgments.items() if rel >= 1}

        for name, search_fn in retrievers.items():
            retrieved_ids = search_fn(query_text)

            p5 = precision_at_k(retrieved_ids, relevant_binary, k=5)
            r10 = recall_at_k(retrieved_ids, relevant_binary, k=10)
            mrr = reciprocal_rank(retrieved_ids, relevant_binary)
            ndcg10 = ndcg_at_k(retrieved_ids, q_judgments, k=10)

            metrics_by_system[name].append({
                "query_id": qid,
                "Precision@5": p5,
                "Recall@10": r10,
                "MRR": mrr,
                "nDCG@10": ndcg10,
            })

    # Aggregate means
    summary_rows = []
    for name, query_metrics in metrics_by_system.items():
        df = pd.DataFrame(query_metrics)
        summary_rows.append({
            "Retriever": name,
            "Precision@5": df["Precision@5"].mean(),
            "Recall@10": df["Recall@10"].mean(),
            "MRR": df["MRR"].mean(),
            "nDCG@10": df["nDCG@10"].mean(),
        })

    summary_df = pd.DataFrame(summary_rows)

    # Generate Markdown Report
    report_content = f"""# NeverInvent — Phase 1 Retrieval Evaluation Report

## Experimental Setup & Methodology
- **Corpus size:** {len(jobs)} job descriptions (`data/job_postings/sample_jobs.jsonl`)
- **Queries:** 5 diverse candidate profiles across ML, NLP Research, Backend, DevOps, and Frontend
- **Judgments:** 50 manually reviewed candidate-job relevance judgments (`neverinvent/evaluation/datasets/retrieval_judgments.jsonl`)
- **Graded scale:** 0 (Not relevant), 1 (Partially relevant), 2 (Highly relevant)
- **Embedding model:** `BAAI/bge-small-en-v1.5` running on CPU (FAISS IndexFlatIP)
- **Fusion method:** Reciprocal Rank Fusion (RRF, k=60)

## Benchmark Results (Averaged Across 5 Candidate Queries)

| Retriever | Precision@5 | Recall@10 | MRR | nDCG@10 |
|---|---|---|---|---|
"""
    for _, row in summary_df.iterrows():
        report_content += f"| **{row['Retriever']}** | {row['Precision@5']:.4f} | {row['Recall@10']:.4f} | {row['MRR']:.4f} | {row['nDCG@10']:.4f} |\n"

    report_content += """
## Methodological Observations & Limitations
1. **Sample Size:** 5 queries and 50 judgments provide an initial benchmark to demonstrate architecture and verify ranking logic. It is not an enterprise-scale IR evaluation.
2. **Single Annotator:** Judgments were curated by a single reviewer according to the documented rubric. Inter-annotator agreement cannot be computed.
3. **Hybrid Robustness:** Hybrid RRF combines exact lexical terminology (vital for framework/tool names like PyTorch, FAISS, Redis) with dense semantic representation (for conceptual role matching).
4. **Architectural Boundary:** Notice that retrieval scores are completely decoupled from verification. A high similarity score does NOT constitute factual evidence.
"""

    out_p = Path(output_report_path)
    out_p.parent.mkdir(parents=True, exist_ok=True)
    out_p.write_text(report_content, encoding="utf-8")

    return {
        "summary": summary_df.to_dict(orient="records"),
        "report_path": str(out_p),
    }


if __name__ == "__main__":
    res = evaluate_retrievers()
    print("Evaluation completed successfully.")
    print(json.dumps(res["summary"], indent=2))
