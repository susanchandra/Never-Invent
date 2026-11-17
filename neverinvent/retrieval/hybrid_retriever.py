"""
retrieval/hybrid_retriever.py — Score fusion combining BM25 and Dense Retrieval.
"""

from __future__ import annotations

from typing import Optional
from neverinvent.jobs.models import JobDescription
from neverinvent.retrieval.bm25_retriever import BM25Retriever
from neverinvent.retrieval.dense_retriever import DenseRetriever
from neverinvent.retrieval.models import RetrievalMethod, RetrievalResult


class HybridRetriever:
    """
    Hybrid retriever that coordinates BM25 and Dense retrievers.
    Supports:
    1. Reciprocal Rank Fusion (RRF) - robust, parameter-free.
    2. Linear score interpolation with min-max normalization.
    """

    def __init__(
        self,
        bm25_retriever: BM25Retriever,
        dense_retriever: DenseRetriever,
        rrf_k: int = 60,
    ):
        self.bm25 = bm25_retriever
        self.dense = dense_retriever
        self.rrf_k = rrf_k
        self.jobs_by_id: dict[str, JobDescription] = {}

    def fit(self, jobs: list[JobDescription]) -> None:
        """Fit both underlying retrievers on the same job corpus."""
        self.jobs_by_id = {j.job_id: j for j in jobs}
        self.bm25.fit(jobs)
        self.dense.fit(jobs)

    def search_rrf(self, query: str, top_k: int = 10, candidate_pool_k: int = 30) -> list[RetrievalResult]:
        """
        Reciprocal Rank Fusion (RRF):
        score(d) = sum_{m in {bm25, dense}} 1 / (rrf_k + rank_m(d))
        """
        if not query or not query.strip():
            return []

        bm25_results = self.bm25.search(query, top_k=candidate_pool_k)
        dense_results = self.dense.search(query, top_k=candidate_pool_k)

        if not bm25_results and not dense_results:
            return []

        scores: dict[str, float] = {}

        for res in bm25_results:
            scores[res.job_id] = scores.get(res.job_id, 0.0) + (1.0 / (self.rrf_k + res.rank))

        for res in dense_results:
            scores[res.job_id] = scores.get(res.job_id, 0.0) + (1.0 / (self.rrf_k + res.rank))

        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results: list[RetrievalResult] = []
        for rank, (job_id, score) in enumerate(sorted_items[:top_k], start=1):
            results.append(
                RetrievalResult(
                    job_id=job_id,
                    rank=rank,
                    score=float(score),
                    method=RetrievalMethod.HYBRID_RRF,
                    job=self.jobs_by_id.get(job_id),
                )
            )

        return results

    def search_linear(
        self,
        query: str,
        top_k: int = 10,
        bm25_weight: float = 0.5,
        dense_weight: float = 0.5,
        candidate_pool_k: int = 30,
    ) -> list[RetrievalResult]:
        """
        Linear score fusion with min-max normalization:
        score(d) = bm25_weight * norm(bm25) + dense_weight * norm(dense)
        """
        if not query or not query.strip():
            return []

        bm25_results = self.bm25.search(query, top_k=candidate_pool_k)
        dense_results = self.dense.search(query, top_k=candidate_pool_k)

        if not bm25_results and not dense_results:
            return []

        # Min-max normalization helper
        def _normalize(results: list[RetrievalResult]) -> dict[str, float]:
            if not results:
                return {}
            raw_scores = [r.score for r in results]
            min_s, max_s = min(raw_scores), max(raw_scores)
            if max_s == min_s:
                return {r.job_id: 1.0 for r in results}
            return {r.job_id: (r.score - min_s) / (max_s - min_s) for r in results}

        norm_bm25 = _normalize(bm25_results)
        norm_dense = _normalize(dense_results)

        all_ids = set(norm_bm25.keys()) | set(norm_dense.keys())
        scores: dict[str, float] = {}

        for jid in all_ids:
            s_bm25 = norm_bm25.get(jid, 0.0)
            s_dense = norm_dense.get(jid, 0.0)
            scores[jid] = (bm25_weight * s_bm25) + (dense_weight * s_dense)

        sorted_items = sorted(scores.items(), key=lambda x: x[1], reverse=True)

        results: list[RetrievalResult] = []
        for rank, (job_id, score) in enumerate(sorted_items[:top_k], start=1):
            results.append(
                RetrievalResult(
                    job_id=job_id,
                    rank=rank,
                    score=float(score),
                    method=RetrievalMethod.HYBRID_LINEAR,
                    job=self.jobs_by_id.get(job_id),
                )
            )

        return results
