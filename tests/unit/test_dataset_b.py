"""
tests/unit/test_dataset_b.py — Tests for Dataset B (Natural Benchmark) loader and execution.
"""

from pathlib import Path
import pytest

from neverinvent.evaluation.dataset_b import (
    NaturalEvaluationCase,
    get_benchmark_profiles,
    load_dataset_b,
)
from neverinvent.evaluation.dataset_b_eval import run_dataset_b_evaluation
from neverinvent.verification.models import Verdict


def test_dataset_b_loading_and_balance():
    """Verify Dataset B has 100 cases, valid schemas, and expected class balance."""
    cases = load_dataset_b()
    assert len(cases) == 100

    supported = [c for c in cases if c.expected_verdict == Verdict.SUPPORTED]
    unsupported = [c for c in cases if c.expected_verdict == Verdict.UNSUPPORTED]
    ambiguous = [c for c in cases if c.expected_verdict == Verdict.AMBIGUOUS]

    assert len(supported) == 40
    assert len(unsupported) == 40
    assert len(ambiguous) == 20

    # Ensure profiles exist for all candidate IDs
    profiles = get_benchmark_profiles()
    for c in cases:
        assert c.candidate_id in profiles


def test_dataset_b_evaluation_run(tmp_path):
    """Verify that dataset_b_eval runs cleanly end-to-end and computes valid metrics."""
    ds_path = Path("data/evaluation/dataset_b_natural.jsonl")
    rep_path = tmp_path / "dataset_b_report.md"

    metrics = run_dataset_b_evaluation(ds_path, rep_path)

    assert metrics["total_cases"] == 100
    assert metrics["safety_metrics"]["false_block_rate"] == 0.0
    assert metrics["safety_metrics"]["faithful_total"] == 40
    assert rep_path.exists()
