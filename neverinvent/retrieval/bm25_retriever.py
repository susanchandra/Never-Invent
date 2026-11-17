"""
retrieval/bm25_retriever.py — Lexical retrieval using BM25Okapi.
"""

from __future__ import annotations

import re
from typing import Optional
from rank_bm25 import BM25Okapi

from neverinvent.jobs.models import JobDescription
from neverinvent.retrieval.models import RetrievalMethod, RetrievalResult


def tokenize(text: str) -> list[str]:
    """Tokenize and normalize text for BM25 matching."""
    if not text:
        return []
    cleaned = re.sub(r"[^\w\s]", " ", text.lower())
    return [tok for tok in cleaned.split() if len(tok) > 1]


class BM25Retriever:
    """
    Lexical BM25 retriever for job descriptions.
    """

    def __init__(self, k1: float = 1.5, b: float = 0.75):
        self.k1 = k1
        self.b = b
        self.jobs: list[JobDescription] = []
        self.job_ids: list[str] = []
        self.tokenized_corpus: list[list[str]] = []
        self.bm25: Optional[BM25Okapi] = None

    def fit(self, jobs: list[JobDescription]) -> None:
        """Index the provided list of jobs."""
        self.jobs = list(jobs)
        self.job_ids = [j.job_id for j in self.jobs]
        self.tokenized_corpus = [tokenize(j.get_searchable_text()) for j in self.jobs]

        if self.tokenized_corpus:
            self.bm25 = BM25Okapi(self.tokenized_corpus, k1=self.k1, b=self.b)
        else:
            self.bm25 = None

    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """
        Search corpus with BM25.
        Returns empty list if query is empty or corpus is empty.
        """
        if not query or not query.strip() or self.bm25 is None or not self.jobs:
            return []

        tokens = tokenize(query)
        if not tokens:
            return []

        scores = self.bm25.get_scores(tokens)

        # Sort indices by descending score
        scored_indices = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
        results: list[RetrievalResult] = []

        for rank, (idx, score) in enumerate(scored_indices[:top_k], start=1):
            results.append(
                RetrievalResult(
                    job_id=self.job_ids[idx],
                    rank=rank,
                    score=float(score),
                    method=RetrievalMethod.BM25,
                    job=self.jobs[idx],
                )
            )

        return results
