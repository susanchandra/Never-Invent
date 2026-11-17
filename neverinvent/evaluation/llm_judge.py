"""
evaluation/llm_judge.py — LLM-as-judge baseline using Groq (Llama-3.1-8b-instant).

Design contracts:
- Strictly optional evaluation baseline.
- Never called by the core verification pipeline.
- If GROQ_API_KEY is not set or groq is unavailable, gracefully raises or reports NOT AVAILABLE without failing unit tests.
"""

from __future__ import annotations

import os
from typing import Optional

from pydantic import BaseModel, Field

from neverinvent.claims.models import Claim
from neverinvent.parsing.models import CandidateProfile
from neverinvent.verification.models import Verdict


class LLMJudgeResult(BaseModel):
    claim_id: str
    verdict: Verdict
    rationale: str
    is_available: bool = True
    error_message: Optional[str] = None


class LLMJudge:
    """LLM-as-judge comparator for verification evaluation."""

    def __init__(self, api_key: Optional[str] = None, model: str = "llama-3.1-8b-instant"):
        self.api_key = api_key or os.getenv("GROQ_API_KEY")
        self.model = model

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def evaluate_claim(self, claim: Claim, profile: CandidateProfile) -> LLMJudgeResult:
        if not self.is_configured:
            return LLMJudgeResult(
                claim_id=claim.claim_id,
                verdict=Verdict.AMBIGUOUS,
                rationale="GROQ_API_KEY not configured. LLM judge unavailable.",
                is_available=False,
                error_message="GROQ_API_KEY environment variable missing.",
            )

        try:
            from groq import Groq

            client = Groq(api_key=self.api_key)
            prompt = (
                f"Candidate Evidence:\n"
                f"Name: {profile.candidate_name}\n"
                f"Skills: {', '.join(s.name for s in profile.skills)}\n"
                f"Experience: {[{'company': e.company, 'title': e.title, 'start': e.start_date, 'end': e.end_date} for e in profile.experience]}\n\n"
                f"Claim to verify:\n"
                f"Text: '{claim.original_claim_text}'\n"
                f"Type: {claim.claim_type.value}\n\n"
                f"Task: Classify this claim as exactly one of: SUPPORTED, UNSUPPORTED, AMBIGUOUS.\n"
                f"Return JSON: {{\"verdict\": \"SUPPORTED|UNSUPPORTED|AMBIGUOUS\", \"rationale\": \"...\"}}"
            )
            resp = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model=self.model,
                temperature=0.0,
            )
            content = resp.choices[0].message.content or ""
            # parse verdict
            verdict = Verdict.AMBIGUOUS
            if "SUPPORTED" in content and "UNSUPPORTED" not in content:
                verdict = Verdict.SUPPORTED
            elif "UNSUPPORTED" in content:
                verdict = Verdict.UNSUPPORTED

            return LLMJudgeResult(
                claim_id=claim.claim_id,
                verdict=verdict,
                rationale=content[:200],
                is_available=True,
            )
        except Exception as e:
            return LLMJudgeResult(
                claim_id=claim.claim_id,
                verdict=Verdict.AMBIGUOUS,
                rationale=f"LLM call failed: {e}",
                is_available=False,
                error_message=str(e),
            )
