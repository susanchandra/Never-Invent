"""
retrieval/dense_retriever.py — Dense semantic retrieval using BGE-small and FAISS.
"""

from __future__ import annotations

import logging
from typing import Optional
import faiss
import numpy as np

from neverinvent.jobs.models import JobDescription
from neverinvent.retrieval.models import RetrievalMethod, RetrievalResult

logger = logging.getLogger(__name__)


class DenseRetriever:
    """
    Dense vector retriever using BGE-small embeddings and FAISS index.
    Fully supports CPU execution as required by architectural constraints.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-small-en-v1.5",
        device: str = "cpu",
    ):
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.device = device
        logger.info("Initializing DenseRetriever with model=%s on device=%s", model_name, device)
        self.model = SentenceTransformer(model_name, device=device)
        self.jobs: list[JobDescription] = []
        self.job_ids: list[str] = []
        self.index: Optional[faiss.IndexFlatIP] = None
        self.dimension: Optional[int] = None

    def fit(self, jobs: list[JobDescription], batch_size: int = 32) -> None:
        """
        Embed all job descriptions and build FAISS index.
        """
        self.jobs = list(jobs)
        self.job_ids = [j.job_id for j in self.jobs]

        if not self.jobs:
            self.index = None
            return

        texts = [j.get_searchable_text() for j in self.jobs]
        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,  # normalize for cosine similarity via IndexFlatIP
        )
        embeddings = np.array(embeddings, dtype=np.float32)

        self.dimension = embeddings.shape[1]
        self.index = faiss.IndexFlatIP(self.dimension)
        self.index.add(embeddings)
        logger.info("FAISS index built with %d vectors of dimension %d", len(self.jobs), self.dimension)

    def search(self, query: str, top_k: int = 10) -> list[RetrievalResult]:
        """
        Query the FAISS index with dense representation.
        """
        if not query or not query.strip() or self.index is None or not self.jobs:
            return []

        # BGE query instruction prefix recommended by BGE authors for retrieval
        bge_query = f"Represent this sentence for searching relevant passages: {query.strip()}"
        q_emb = self.model.encode([bge_query], normalize_embeddings=True)
        q_emb = np.array(q_emb, dtype=np.float32)

        k = min(top_k, len(self.jobs))
        scores, indices = self.index.search(q_emb, k)

        results: list[RetrievalResult] = []
        for rank, (idx, score) in enumerate(zip(indices[0], scores[0]), start=1):
            if idx < 0 or idx >= len(self.jobs):
                continue
            results.append(
                RetrievalResult(
                    job_id=self.job_ids[idx],
                    rank=rank,
                    score=float(score),
                    method=RetrievalMethod.DENSE,
                    job=self.jobs[idx],
                )
            )

        return results
