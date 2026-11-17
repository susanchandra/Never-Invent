"""
verification/verifier.py — Main verification orchestrator.

Design contracts:
- Checks a Claim against a CandidateProfile using independent deterministic strategies.
- Evaluates strategies in priority order:
    1. Exact Match
    2. Normalized Match
    3. Alias Match
    4. Numerical Check
    5. Temporal Check
    6. Entity Check
    7. Contradiction Check
    8. Evidence Sufficiency
- Zero dependencies on retrieval or generation modules.
- Latency tracked per verification call in milliseconds.
- Ambiguous claims or uncertain extractions require human review.
"""

from __future__ import annotations

import time
from typing import Optional

from neverinvent.claims.models import Claim
from neverinvent.parsing.models import CandidateProfile, ExtractionStatus
from neverinvent.verification.models import (
    StrategyResult,
    Verdict,
    VerificationResult,
    VerificationStrategy,
)
from neverinvent.verification.strategies.alias_match import verify_alias_match
from neverinvent.verification.strategies.contradiction import verify_contradiction
from neverinvent.verification.strategies.entity import verify_entity
from neverinvent.verification.strategies.evidence_sufficiency import verify_evidence_sufficiency
from neverinvent.verification.strategies.exact_match import verify_exact_match
from neverinvent.verification.strategies.normalized_match import verify_normalized_match
from neverinvent.verification.strategies.numerical import verify_numerical
from neverinvent.verification.strategies.temporal import verify_temporal


ALL_STRATEGIES = [
    VerificationStrategy.EXACT_MATCH,
    VerificationStrategy.NORMALIZED_MATCH,
    VerificationStrategy.ALIAS_MATCH,
    VerificationStrategy.NUMERICAL,
    VerificationStrategy.TEMPORAL,
    VerificationStrategy.ENTITY,
    VerificationStrategy.CONTRADICTION,
    VerificationStrategy.EVIDENCE_SUFFICIENCY,
]


class ClaimVerifier:
    """
    Independent deterministic claim verifier.

    Evaluates atomic factual claims against grounded candidate profile evidence.
    """

    def __init__(
        self,
        enabled_strategies: Optional[list[VerificationStrategy]] = None,
        strict_closed_world_skills: bool = True,
    ):
        self.enabled_strategies = enabled_strategies or list(ALL_STRATEGIES)
        self.strict_closed_world_skills = strict_closed_world_skills

    def verify(self, claim: Claim, profile: CandidateProfile) -> VerificationResult:
        """
        Verify a single atomic claim against a candidate profile.
        """
        start_time = time.perf_counter()
        strategy_results: list[StrategyResult] = []

        conclusive_res: Optional[StrategyResult] = None

        # Execute enabled strategies in order
        for strat in self.enabled_strategies:
            res: Optional[StrategyResult] = None

            if strat == VerificationStrategy.EXACT_MATCH:
                res = verify_exact_match(claim, profile)
            elif strat == VerificationStrategy.NORMALIZED_MATCH:
                res = verify_normalized_match(claim, profile)
            elif strat == VerificationStrategy.ALIAS_MATCH:
                res = verify_alias_match(claim, profile)
            elif strat == VerificationStrategy.NUMERICAL:
                res = verify_numerical(claim, profile)
            elif strat == VerificationStrategy.TEMPORAL:
                res = verify_temporal(claim, profile)
            elif strat == VerificationStrategy.ENTITY:
                res = verify_entity(claim, profile)
            elif strat == VerificationStrategy.CONTRADICTION:
                res = verify_contradiction(claim, profile)
            elif strat == VerificationStrategy.EVIDENCE_SUFFICIENCY:
                res = verify_evidence_sufficiency(
                    claim, profile, strict_closed_world=self.strict_closed_world_skills
                )

            if res:
                strategy_results.append(res)
                # If conclusive (SUPPORTED or UNSUPPORTED), take as primary
                if res.verdict in (Verdict.SUPPORTED, Verdict.UNSUPPORTED) and conclusive_res is None:
                    conclusive_res = res
                    break

        latency_ms = (time.perf_counter() - start_time) * 1000.0

        if conclusive_res:
            final_verdict = conclusive_res.verdict
            primary_strategy = conclusive_res.strategy
            rationale = conclusive_res.explanation
            matched = conclusive_res.matched_evidence
            contradicting = conclusive_res.contradicting_evidence
        else:
            final_verdict = Verdict.AMBIGUOUS
            primary_strategy = (
                strategy_results[-1].strategy
                if strategy_results
                else VerificationStrategy.EVIDENCE_SUFFICIENCY
            )
            rationale = "No strategy could conclusively verify or refute the claim with available evidence."
            matched = []
            contradicting = []

        requires_human_review = (
            final_verdict == Verdict.AMBIGUOUS
            or claim.extraction_confidence != ExtractionStatus.EXPLICIT
        )

        return VerificationResult(
            claim=claim,
            final_verdict=final_verdict,
            primary_strategy=primary_strategy,
            all_strategy_results=strategy_results,
            matched_evidence=matched,
            contradicting_evidence=contradicting,
            rationale=rationale,
            requires_human_review=requires_human_review,
            latency_ms=latency_ms,
        )

    def verify_many(
        self, claims: list[Claim], profile: CandidateProfile
    ) -> list[VerificationResult]:
        """Verify multiple claims against a candidate profile sequentially."""
        return [self.verify(c, profile) for c in claims]
