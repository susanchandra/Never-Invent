"""
Unit tests for retrieval modules (BM25, Dense, Hybrid RRF).
"""

import pytest
from neverinvent.jobs.models import JobDescription, JobSource
from neverinvent.retrieval import (
    BM25Retriever,
    DenseRetriever,
    HybridRetriever,
    RetrievalMethod,
)


@pytest.fixture
def sample_jobs() -> list[JobDescription]:
    return [
        JobDescription(
            job_id="job_ml",
            title="Senior Machine Learning Engineer",
            normalized_title="machine learning engineer",
            company="AI Corp",
            raw_description="Deep learning models, PyTorch, FAISS vector indexing and transformers.",
            required_skills=["python", "pytorch", "faiss"],
            source_type=JobSource.SYNTHETIC,
        ),
        JobDescription(
            job_id="job_web",
            title="Frontend React Developer",
            normalized_title="frontend engineer",
            company="WebTech",
            raw_description="Building modern accessible user interfaces with React and TypeScript.",
            required_skills=["react", "typescript", "css"],
            source_type=JobSource.SYNTHETIC,
        ),
        JobDescription(
            job_id="job_devops",
            title="Platform & DevOps Engineer",
            normalized_title="devops engineer",
            company="CloudScale",
            raw_description="Kubernetes cluster management on AWS with Terraform and Docker.",
            required_skills=["kubernetes", "docker", "aws"],
            source_type=JobSource.SYNTHETIC,
        ),
    ]


def test_bm25_empty_handling():
    retriever = BM25Retriever()
    assert retriever.search("python") == []
    assert retriever.search("") == []


def test_bm25_ranking(sample_jobs):
    retriever = BM25Retriever()
    retriever.fit(sample_jobs)

    # Empty query check
    assert retriever.search("") == []
    assert retriever.search("   ") == []

    # Search for ML skills
    results = retriever.search("PyTorch FAISS machine learning")
    assert len(results) > 0
    top = results[0]
    assert top.job_id == "job_ml"
    assert top.rank == 1
    assert top.method == RetrievalMethod.BM25
    assert top.job is not None

    # Search for React skills
    react_res = retriever.search("React TypeScript")
    assert react_res[0].job_id == "job_web"


def test_dense_retriever_cpu(sample_jobs):
    # Explicitly test CPU execution
    dense = DenseRetriever(model_name="BAAI/bge-small-en-v1.5", device="cpu")
    dense.fit(sample_jobs)

    assert dense.search("") == []

    # Semantic search with synonymous phrasing not present literally in title
    results = dense.search("neural network embeddings and vector similarity", top_k=2)
    assert len(results) > 0
    assert results[0].job_id == "job_ml"
    assert results[0].method == RetrievalMethod.DENSE
    assert results[0].score > 0.0


def test_hybrid_rrf_fusion(sample_jobs):
    bm25 = BM25Retriever()
    dense = DenseRetriever(model_name="BAAI/bge-small-en-v1.5", device="cpu")
    hybrid = HybridRetriever(bm25, dense, rrf_k=60)
    hybrid.fit(sample_jobs)

    results = hybrid.search_rrf("Kubernetes AWS Docker infrastructure", top_k=3)
    assert len(results) > 0
    assert results[0].job_id == "job_devops"
    assert results[0].rank == 1
    assert results[0].method == RetrievalMethod.HYBRID_RRF


def test_hybrid_linear_fusion(sample_jobs):
    bm25 = BM25Retriever()
    dense = DenseRetriever(model_name="BAAI/bge-small-en-v1.5", device="cpu")
    hybrid = HybridRetriever(bm25, dense)
    hybrid.fit(sample_jobs)

    results = hybrid.search_linear("Frontend TypeScript interfaces", top_k=2)
    assert len(results) > 0
    assert results[0].job_id == "job_web"
    assert results[0].method == RetrievalMethod.HYBRID_LINEAR
