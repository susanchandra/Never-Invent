"""
Unit tests for evaluation metrics.
"""

import math
import pytest
from neverinvent.evaluation.metrics import (
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    reciprocal_rank,
)


def test_precision_at_k():
    retrieved = ["doc1", "doc2", "doc3", "doc4"]
    relevant = {"doc1", "doc3"}

    assert precision_at_k(retrieved, relevant, k=2) == 0.5  # 1/2
    assert precision_at_k(retrieved, relevant, k=4) == 0.5  # 2/4
    assert precision_at_k(retrieved, relevant, k=1) == 1.0  # 1/1
    assert precision_at_k([], relevant, k=5) == 0.0

    with pytest.raises(ValueError):
        precision_at_k(retrieved, relevant, k=0)


def test_recall_at_k():
    retrieved = ["doc1", "doc2", "doc3", "doc4"]
    relevant = {"doc1", "doc3", "doc5", "doc6"}  # 4 total relevant

    assert recall_at_k(retrieved, relevant, k=2) == 0.25  # 1 out of 4
    assert recall_at_k(retrieved, relevant, k=4) == 0.5   # 2 out of 4
    assert recall_at_k(retrieved, set(), k=2) == 0.0


def test_reciprocal_rank():
    assert reciprocal_rank(["doc1", "doc2", "doc3"], {"doc1"}) == 1.0
    assert reciprocal_rank(["doc2", "doc1", "doc3"], {"doc1"}) == 0.5
    assert reciprocal_rank(["doc2", "doc3", "doc1"], {"doc1"}) == 1.0 / 3.0
    assert reciprocal_rank(["doc2", "doc3", "doc4"], {"doc1"}) == 0.0


def test_ndcg_at_k_perfect():
    retrieved = ["docA", "docB", "docC"]
    graded = {"docA": 2, "docB": 1, "docC": 0}
    # Perfect order should yield 1.0
    assert math.isclose(ndcg_at_k(retrieved, graded, k=3), 1.0, rel_tol=1e-5)


def test_ndcg_at_k_suboptimal():
    # Suboptimal order: docB (rel 1) ranked before docA (rel 2)
    retrieved = ["docB", "docA", "docC"]
    graded = {"docA": 2, "docB": 1, "docC": 0}

    dcg = ((2**1 - 1) / math.log2(2)) + ((2**2 - 1) / math.log2(3))
    idcg = ((2**2 - 1) / math.log2(2)) + ((2**1 - 1) / math.log2(3))
    expected_ndcg = dcg / idcg

    score = ndcg_at_k(retrieved, graded, k=3)
    assert math.isclose(score, expected_ndcg, rel_tol=1e-5)
    assert score < 1.0
