"""
evaluation/metrics.py — Information Retrieval evaluation metrics.

Implements standard ranking evaluation metrics:
- Precision@K
- Recall@K
- Mean Reciprocal Rank (MRR)
- Normalized Discounted Cumulative Gain (nDCG@K)
"""

from __future__ import annotations

import math
from typing import Sequence


def precision_at_k(retrieved_ids: Sequence[str], relevant_ids: set[str], k: int) -> float:
    """
    Compute Precision@K.
    Proportion of retrieved items in top-K that are relevant (binary relevance).
    """
    if k <= 0:
        raise ValueError("k must be a positive integer")
    if not retrieved_ids:
        return 0.0

    top_k = retrieved_ids[:k]
    hits = sum(1 for item in top_k if item in relevant_ids)
    return hits / k


def recall_at_k(retrieved_ids: Sequence[str], relevant_ids: set[str], k: int) -> float:
    """
    Compute Recall@K.
    Proportion of total relevant items retrieved in top-K.
    If there are no relevant items for the query, returns 0.0.
    """
    if k <= 0:
        raise ValueError("k must be a positive integer")
    if not relevant_ids or not retrieved_ids:
        return 0.0

    top_k = retrieved_ids[:k]
    hits = sum(1 for item in top_k if item in relevant_ids)
    return hits / len(relevant_ids)


def reciprocal_rank(retrieved_ids: Sequence[str], relevant_ids: set[str], k: Optional[int] = None) -> float:
    """
    Compute Reciprocal Rank (RR).
    1 / rank of the first relevant item found. Returns 0.0 if none found.
    """
    items = retrieved_ids[:k] if k is not None else retrieved_ids
    for rank, item in enumerate(items, start=1):
        if item in relevant_ids:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(
    retrieved_ids: Sequence[str],
    graded_relevance: dict[str, int],
    k: int,
) -> float:
    """
    Compute Normalized Discounted Cumulative Gain at K (nDCG@K).
    Supports graded relevance (e.g. 0 = not relevant, 1 = partially, 2 = highly relevant).
    Uses standard exponential gain formulation: (2^rel - 1) / log2(rank + 1).
    """
    if k <= 0:
        raise ValueError("k must be a positive integer")
    if not retrieved_ids or not graded_relevance:
        return 0.0

    top_k = retrieved_ids[:k]

    # Compute DCG@K
    dcg = 0.0
    for rank, doc_id in enumerate(top_k, start=1):
        rel = graded_relevance.get(doc_id, 0)
        gain = (2.0 ** rel) - 1.0
        discount = math.log2(rank + 1)
        dcg += gain / discount

    # Compute Ideal DCG@K (sorted graded relevance in descending order)
    ideal_rels = sorted(graded_relevance.values(), reverse=True)[:k]
    idcg = 0.0
    for rank, rel in enumerate(ideal_rels, start=1):
        gain = (2.0 ** rel) - 1.0
        discount = math.log2(rank + 1)
        idcg += gain / discount

    if idcg == 0.0:
        return 0.0

    return dcg / idcg
