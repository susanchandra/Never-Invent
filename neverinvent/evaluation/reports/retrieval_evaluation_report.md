# NeverInvent — Phase 1 Retrieval Evaluation Report

## Experimental Setup & Methodology
- **Corpus size:** 10 job descriptions (`data/job_postings/sample_jobs.jsonl`)
- **Queries:** 5 diverse candidate profiles across ML, NLP Research, Backend, DevOps, and Frontend
- **Judgments:** 50 manually reviewed candidate-job relevance judgments (`neverinvent/evaluation/datasets/retrieval_judgments.jsonl`)
- **Graded scale:** 0 (Not relevant), 1 (Partially relevant), 2 (Highly relevant)
- **Embedding model:** `BAAI/bge-small-en-v1.5` running on CPU (FAISS IndexFlatIP)
- **Fusion method:** Reciprocal Rank Fusion (RRF, k=60)

## Benchmark Results (Averaged Across 5 Candidate Queries)

| Retriever | Precision@5 | Recall@10 | MRR | nDCG@10 |
|---|---|---|---|---|
| **BM25** | 0.6000 | 1.0000 | 1.0000 | 0.9725 |
| **Dense (BGE-small)** | 0.6400 | 1.0000 | 1.0000 | 0.9867 |
| **Hybrid (RRF k=60)** | 0.6400 | 1.0000 | 1.0000 | 0.9866 |

## Methodological Observations & Limitations
1. **Sample Size:** 5 queries and 50 judgments provide an initial benchmark to demonstrate architecture and verify ranking logic. It is not an enterprise-scale IR evaluation.
2. **Single Annotator:** Judgments were curated by a single reviewer according to the documented rubric. Inter-annotator agreement cannot be computed.
3. **Hybrid Robustness:** Hybrid RRF combines exact lexical terminology (vital for framework/tool names like PyTorch, FAISS, Redis) with dense semantic representation (for conceptual role matching).
4. **Architectural Boundary:** Notice that retrieval scores are completely decoupled from verification. A high similarity score does NOT constitute factual evidence.
