"""
Unit tests for verification evaluation metrics and evaluation runner.
"""

from pathlib import Path
import pytest

from neverinvent.claims.models import Claim, ClaimType
from neverinvent.evaluation.fabrication_dataset import (
    FabricationCase,
    generate_dataset_a,
    get_standard_evaluation_profile,
)
from neverinvent.evaluation.llm_judge import LLMJudge
from neverinvent.evaluation.verification_eval import run_evaluation
from neverinvent.evaluation.verification_metrics import (
    ambiguity_rate,
    compute_confusion_matrix,
    f1_score,
    fabrication_detection_precision,
    fabrication_detection_recall,
    false_block_rate,
)
from neverinvent.verification.models import StrategyResult, Verdict, VerificationResult, VerificationStrategy


def test_verification_metrics_calculation():
    # 2 fabricated (1 predicted UNSUPPORTED = TP, 1 predicted AMBIGUOUS = FN)
    # 2 faithful (2 predicted SUPPORTED = TN, 0 predicted UNSUPPORTED = 0 FP)
    cases = [
        FabricationCase(
            case_id="1",
            fabrication_type="test",
            claim_type=ClaimType.SKILL,
            test_claim_text="t1",
            source_evidence="e1",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            rationale="r1",
        ),
        FabricationCase(
            case_id="2",
            fabrication_type="test",
            claim_type=ClaimType.SKILL,
            test_claim_text="t2",
            source_evidence="e2",
            expected_verdict=Verdict.UNSUPPORTED,
            is_fabricated=True,
            rationale="r2",
        ),
        FabricationCase(
            case_id="3",
            fabrication_type="test",
            claim_type=ClaimType.SKILL,
            test_claim_text="t3",
            source_evidence="e3",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            rationale="r3",
        ),
        FabricationCase(
            case_id="4",
            fabrication_type="test",
            claim_type=ClaimType.SKILL,
            test_claim_text="t4",
            source_evidence="e4",
            expected_verdict=Verdict.SUPPORTED,
            is_fabricated=False,
            rationale="r4",
        ),
    ]

    dummy_claim = Claim(
        claim_id="d1",
        original_claim_text="d",
        normalized_value="d",
        claim_type=ClaimType.SKILL,
        extraction_method="test",
        source_text="d",
    )

    results = [
        VerificationResult(
            claim=dummy_claim,
            final_verdict=Verdict.UNSUPPORTED,
            primary_strategy=VerificationStrategy.EXACT_MATCH,
            rationale="",
        ),
        VerificationResult(
            claim=dummy_claim,
            final_verdict=Verdict.AMBIGUOUS,
            primary_strategy=VerificationStrategy.EVIDENCE_SUFFICIENCY,
            rationale="",
        ),
        VerificationResult(
            claim=dummy_claim,
            final_verdict=Verdict.SUPPORTED,
            primary_strategy=VerificationStrategy.EXACT_MATCH,
            rationale="",
        ),
        VerificationResult(
            claim=dummy_claim,
            final_verdict=Verdict.SUPPORTED,
            primary_strategy=VerificationStrategy.EXACT_MATCH,
            rationale="",
        ),
    ]

    prec = fabrication_detection_precision(results, cases)
    rec = fabrication_detection_recall(results, cases)
    f1 = f1_score(prec, rec)
    fbr = false_block_rate(results, cases)
    amb = ambiguity_rate(results)

    assert prec == 1.0  # 1 TP, 0 FP -> 1.0
    assert rec == 0.5   # 1 TP / 2 expected unsupported -> 0.5
    assert abs(f1 - (2 * 1.0 * 0.5 / 1.5)) < 1e-4
    assert fbr == 0.0   # 0 faithful claims blocked
    assert amb == 0.25  # 1 / 4 claims ambiguous

    cm = compute_confusion_matrix(results, cases)
    assert cm["UNSUPPORTED"]["UNSUPPORTED"] == 1
    assert cm["UNSUPPORTED"]["AMBIGUOUS"] == 1
    assert cm["SUPPORTED"]["SUPPORTED"] == 2


def test_llm_judge_unconfigured():
    judge = LLMJudge(api_key=None)
    assert not judge.is_configured
    dummy_claim = Claim(
        claim_id="d1",
        original_claim_text="d",
        normalized_value="d",
        claim_type=ClaimType.SKILL,
        extraction_method="test",
        source_text="d",
    )
    profile = get_standard_evaluation_profile()
    res = judge.evaluate_claim(dummy_claim, profile)
    assert res.is_available is False
    assert res.verdict == Verdict.AMBIGUOUS


def test_run_evaluation_pipeline(tmp_path: Path):
    dataset_file = tmp_path / "test_dataset.jsonl"
    report_file = tmp_path / "test_report.md"

    res = run_evaluation(dataset_file, report_file)
    assert "precision" in res
    assert "recall" in res
    assert "f1" in res
    assert "ablation" in res
    assert report_file.exists()
    content = report_file.read_text(encoding="utf-8")
    assert "Executive Summary" in content
    assert "Confusion Matrix" in content
    assert "Ablation Study" in content
