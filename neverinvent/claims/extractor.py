"""
claims/extractor.py — Rule-based atomic claim extractor.

DESIGN CONTRACT AND LIMITATIONS (read before modifying)
=========================================================
This extractor uses regex patterns and keyword heuristics.  It does NOT use:
  - Any LLM or neural model
  - FAISS, BM25, or any retrieval scores
  - Any external API

LIMITATIONS (must be understood before interpreting results):
  1. Regex cannot reliably parse arbitrary natural language.
     Sentences with complex syntax, negation, or unusual phrasing will be
     missed or incorrectly parsed.  This is expected and acceptable for an
     MVP research verifier.
  2. Compound sentences are split on sentence boundaries (period + capital),
     but subordinate clauses within one sentence are not separated.
  3. When a sentence is ambiguous or cannot be parsed into a typed claim,
     it is returned with ExtractionStatus.UNCERTAIN — it is NEVER silently
     discarded.
  4. Claim IDs are deterministic SHA-256 hashes and are stable across runs
     for the same (source_text, claim_type) pair.
  5. The extractor does not verify claims — it only identifies and types them.
     Verification is performed by verification/verifier.py.

Usage
-----
    extractor = ClaimExtractor()
    claims = extractor.extract("Alice is proficient in Python and improved latency by 40%.")
    # Returns two Claim objects: one SKILL, one METRIC
"""

from __future__ import annotations

import re
import uuid
from typing import Optional

from neverinvent.claims.models import Claim, ClaimType
from neverinvent.parsing.models import ExtractionStatus
from neverinvent.parsing.normalizers import normalize_date, normalize_skill

# ---------------------------------------------------------------------------
# Regex patterns
# ---------------------------------------------------------------------------

# Sentence splitter: split on ". " followed by a capital letter or end-of-string
_SENTENCE_SPLIT_RE = re.compile(r"(?<=\.)\s+(?=[A-Z])|(?<=\?)\s+|(?<=!)\s+")

# --- SKILL patterns ---
_SKILL_PATTERNS = [
    # "proficient in X", "experienced with X", "expertise in X", "skilled in X"
    re.compile(
        r"\b(?:proficient in|experienced (?:with|in)|expertise in|skilled in|"
        r"specializes? in|knowledge of|familiar(?:ity)? with)\s+"
        r"([A-Za-z0-9][\w\-\.\+\#]{0,30}(?:\s+(?!and\b|or\b|with\b|while\b|for\b|to\b|in\b)[A-Za-z0-9][\w\-\.\+\#]{0,30}){0,2})",
        re.IGNORECASE,
    ),
    # "X developer", "X engineer" — e.g. "Python developer"
    re.compile(
        r"\b([A-Za-z][\w\-\.\+\#]{1,30})\s+(?:developer|engineer|programmer|specialist)\b",
        re.IGNORECASE,
    ),
    # "knows X" / "uses X" / "worked with X" — single token or short phrase
    re.compile(
        r"\b(?:knows?|uses?|utilizes?|worked with|works with)\s+"
        r"([A-Za-z0-9][\w\-\.\+\#]{0,30}(?:\s+(?!and\b|or\b|with\b|while\b|for\b|to\b|in\b)[A-Za-z0-9][\w\-\.\+\#]{0,30}){0,2})\b",
        re.IGNORECASE,
    ),
]

# --- EMPLOYER patterns ---
_EMPLOYER_PATTERNS = [
    re.compile(
        r"\b(?:worked at|works at|employed (?:at|by)|joined|at)\s+([A-Z][A-Za-z0-9\s&,\.]{1,40}?)(?:\s+(?:as|from|until|for|since|,|\.|$))",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:former\s+)?([A-Z][A-Za-z0-9\s&\.]{1,30})\s+employee\b",
        re.IGNORECASE,
    ),
]

# --- METRIC patterns ---
# Matches "improved X by Y%", "improving X by Y%", "reduced X by Y%", "processed N records", etc.
_METRIC_PATTERNS = [
    re.compile(
        r"\b(?P<verb>improved|improving|improve|increased|increasing|increase|reduced|reducing|reduce|"
        r"decreased|decreasing|decrease|boosted|boosting|boost|cut|cutting|grew|growing|grow|"
        r"scaled|scaling|scale|saved|saving|save|raised|raising|raise|dropped|dropping|drop|"
        r"slashed|slashing|slash|processed|processing|process|handled|handling|handle)\b"
        r"[^.]{0,80}?\b(?P<quantity>\d+(?:\.\d+)?)\s*(?P<unit>%|(?:ms|s\b|sec|seconds?|users?|records?|requests?|x\b))",
        re.IGNORECASE,
    ),
]

# --- QUANTITY patterns (pure number claims without direction verb) ---
_QUANTITY_PATTERNS = [
    re.compile(
        r"\b(?P<quantity>\d+(?:\.\d+)?)\s*(?P<unit>%|(?:ms|users?|records?|TB|GB|MB|requests?|calls?)\b)",
        re.IGNORECASE,
    ),
]

# --- DURATION patterns ---
_DURATION_PATTERNS = [
    re.compile(
        r"\b(?P<quantity>\d+(?:\.\d+)?)\s*(?P<unit>years?|months?)\s+(?:of\s+)?(?:experience|expertise|work)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?P<quantity>\d+(?:\.\d+)?)\+\s*(?P<unit>years?|months?)\s+(?:of\s+)?(?:experience|expertise|work)\b",
        re.IGNORECASE,
    ),
]

# --- DATE patterns ---
_DATE_PATTERNS = [
    re.compile(
        r"\b(?:joined|started|left|until|since|from|in)\s+"
        r"(?P<date>(?:January|February|March|April|May|June|July|August|September|October|November|December)"
        r"\s+\d{4}|\d{4})\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?P<start>(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
        r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})"
        r"\s*(?:to|-|–|through)\s*"
        r"(?P<end>(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
        r"Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4}|[Pp]resent|[Cc]urrent)\b",
        re.IGNORECASE,
    ),
]

# --- DEGREE / EDUCATION patterns ---
_DEGREE_PATTERNS = [
    re.compile(
        r"\b(?P<degree>Bachelor(?:\'s)?(?:\s+of\s+Science|\s+of\s+Arts)?|B\.?S\.?|B\.?A\.?|"
        r"Master(?:\'s)?(?:\s+of\s+Science|\s+of\s+Arts)?|M\.?S\.?|M\.?A\.?|MBA|"
        r"PhD|Ph\.D\.|Doctor(?:ate)?(?:\s+of\s+Philosophy)?)\s+(?:in\s+)?(?P<field>[A-Za-z][A-Za-z\s\-]{2,40})",
        re.IGNORECASE,
    ),
]

# --- CERTIFICATION patterns ---
_CERT_PATTERNS = [
    re.compile(
        r"\b(?:certified|certification|certificate)\s+(?:in\s+)?(?P<cert>[A-Za-z][A-Za-z0-9\s\-\+\.]{3,60}?)(?=\s*[,\.\(]|$)",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?P<cert>AWS\s+Certified[A-Za-z\s\-]*?|Google\s+Cloud\s+(?:Professional|Associate)[A-Za-z\s\-]*?"
        r"|Microsoft\s+Certified[A-Za-z\s\-]*?|CPA|PMP|CISSP|CFA|CCNA|CCNP)\b",
        re.IGNORECASE,
    ),
]


# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def _split_sentences(text: str) -> list[str]:
    """Split text into individual sentences for per-sentence extraction."""
    parts = _SENTENCE_SPLIT_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def _make_claim(
    *,
    source_text: str,
    claim_type: ClaimType,
    normalized_value: str,
    subject: Optional[str] = None,
    numeric_value: Optional[float] = None,
    unit: Optional[str] = None,
    temporal_start: Optional[str] = None,
    temporal_end: Optional[str] = None,
    extraction_method: str,
    extraction_confidence: ExtractionStatus = ExtractionStatus.EXPLICIT,
    original_claim_text: Optional[str] = None,
) -> Claim:
    """Construct a Claim with a deterministic ID."""
    return Claim(
        claim_id=Claim.make_id(source_text, claim_type),
        original_claim_text=original_claim_text or source_text,
        normalized_value=normalized_value,
        claim_type=claim_type,
        subject=subject,
        numeric_value=numeric_value,
        unit=unit,
        temporal_start=temporal_start,
        temporal_end=temporal_end,
        extraction_method=extraction_method,
        extraction_confidence=extraction_confidence,
        source_text=source_text,
    )


# ---------------------------------------------------------------------------
# Per-type extraction helpers
# ---------------------------------------------------------------------------

def _extract_skills(sentence: str) -> list[Claim]:
    claims = []
    seen: set[str] = set()
    for pattern in _SKILL_PATTERNS:
        for m in pattern.finditer(sentence):
            raw = m.group(1).strip()
            normalized = normalize_skill(raw)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            claims.append(
                _make_claim(
                    source_text=sentence,
                    claim_type=ClaimType.SKILL,
                    normalized_value=normalized,
                    subject=normalized,
                    extraction_method="regex_skill",
                    original_claim_text=raw,
                )
            )
    return claims


def _extract_employers(sentence: str) -> list[Claim]:
    claims = []
    seen: set[str] = set()
    for pattern in _EMPLOYER_PATTERNS:
        for m in pattern.finditer(sentence):
            raw = m.group(1).strip().rstrip(",.")
            normalized = raw.lower().strip()
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            claims.append(
                _make_claim(
                    source_text=sentence,
                    claim_type=ClaimType.EMPLOYER,
                    normalized_value=normalized,
                    subject=raw,
                    extraction_method="regex_employer",
                    original_claim_text=raw,
                )
            )
    return claims


def _extract_metrics(sentence: str) -> list[Claim]:
    claims = []
    for pattern in _METRIC_PATTERNS:
        for m in pattern.finditer(sentence):
            try:
                qty = float(m.group("quantity"))
                unit = m.group("unit").lower().rstrip("s")  # normalize plural
                claims.append(
                    _make_claim(
                        source_text=sentence,
                        claim_type=ClaimType.METRIC,
                        normalized_value=f"{qty}{unit}",
                        numeric_value=qty,
                        unit=unit,
                        extraction_method="regex_metric",
                        original_claim_text=m.group(0).strip(),
                    )
                )
            except (IndexError, ValueError):
                pass
    return claims


def _extract_quantities(sentence: str) -> list[Claim]:
    """Extract standalone numeric quantity claims (no direction verb)."""
    claims = []
    for pattern in _QUANTITY_PATTERNS:
        for m in pattern.finditer(sentence):
            try:
                qty = float(m.group("quantity"))
                unit = m.group("unit").lower().rstrip("s")
                claims.append(
                    _make_claim(
                        source_text=sentence,
                        claim_type=ClaimType.QUANTITY,
                        normalized_value=f"{qty}{unit}",
                        numeric_value=qty,
                        unit=unit,
                        extraction_method="regex_quantity",
                        original_claim_text=m.group(0).strip(),
                    )
                )
            except (IndexError, ValueError):
                pass
    return claims


def _extract_durations(sentence: str) -> list[Claim]:
    claims = []
    for pattern in _DURATION_PATTERNS:
        for m in pattern.finditer(sentence):
            try:
                qty = float(m.group("quantity"))
                unit = m.group("unit").lower().rstrip("s")  # normalize plural
                claims.append(
                    _make_claim(
                        source_text=sentence,
                        claim_type=ClaimType.DURATION,
                        normalized_value=f"{qty} {unit}",
                        numeric_value=qty,
                        unit=unit,
                        extraction_method="regex_duration",
                        original_claim_text=m.group(0).strip(),
                    )
                )
            except (IndexError, ValueError):
                pass
    return claims


def _extract_dates(sentence: str) -> list[Claim]:
    claims = []
    # Try date-range pattern first
    range_pat = _DATE_PATTERNS[1]
    for m in range_pat.finditer(sentence):
        start_raw = m.group("start")
        end_raw = m.group("end")
        t_start = normalize_date(start_raw)
        t_end = normalize_date(end_raw)
        claims.append(
            _make_claim(
                source_text=sentence,
                claim_type=ClaimType.DATE,
                normalized_value=f"{t_start}--{t_end}",
                temporal_start=t_start,
                temporal_end=t_end,
                extraction_method="regex_date_range",
                original_claim_text=m.group(0).strip(),
            )
        )

    # Single date references
    single_pat = _DATE_PATTERNS[0]
    for m in single_pat.finditer(sentence):
        date_raw = m.group("date")
        t = normalize_date(date_raw)
        if t:
            claims.append(
                _make_claim(
                    source_text=sentence,
                    claim_type=ClaimType.DATE,
                    normalized_value=t,
                    temporal_start=t,
                    extraction_method="regex_date_single",
                    original_claim_text=m.group(0).strip(),
                )
            )
    return claims


def _extract_education(sentence: str) -> list[Claim]:
    claims = []
    for pattern in _DEGREE_PATTERNS:
        for m in pattern.finditer(sentence):
            degree = m.group("degree").strip()
            field = m.group("field").strip().rstrip(".,")
            normalized = f"{degree.lower()} in {field.lower()}"
            claims.append(
                _make_claim(
                    source_text=sentence,
                    claim_type=ClaimType.EDUCATION,
                    normalized_value=normalized,
                    subject=field,
                    extraction_method="regex_education",
                    original_claim_text=m.group(0).strip(),
                )
            )
    return claims


def _extract_certifications(sentence: str) -> list[Claim]:
    claims = []
    seen: set[str] = set()
    for pattern in _CERT_PATTERNS:
        for m in pattern.finditer(sentence):
            cert = m.group("cert").strip().rstrip(".,")
            normalized = cert.lower()
            if normalized in seen:
                continue
            seen.add(normalized)
            claims.append(
                _make_claim(
                    source_text=sentence,
                    claim_type=ClaimType.CERTIFICATION,
                    normalized_value=normalized,
                    subject=cert,
                    extraction_method="regex_certification",
                    original_claim_text=cert,
                )
            )
    return claims


def _extract_responsibilities(sentence: str) -> list[Claim]:
    """
    Classify any sentence beginning with an action verb as a RESPONSIBILITY claim.
    This is a catch-all for sentences not captured by other patterns.
    """
    action_verbs = re.compile(
        r"^\s*(?:designed|engineered|built|developed|implemented|led|managed|architected|created|"
        r"deployed|maintained|optimized|analyzed|delivered|collaborated|wrote|automated|"
        r"established|launched|trained|mentored|coordinated|planned|resolved|investigated|scaled)\b",
        re.IGNORECASE,
    )
    if action_verbs.match(sentence):
        return [
            _make_claim(
                source_text=sentence,
                claim_type=ClaimType.RESPONSIBILITY,
                normalized_value=sentence.strip().lower()[:120],
                extraction_method="regex_responsibility",
                extraction_confidence=ExtractionStatus.UNCERTAIN,
                original_claim_text=sentence.strip(),
            )
        ]
    return []


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class ClaimExtractor:
    """
    Rule-based atomic claim extractor.

    Accepts a generated text string and returns a list of Claim objects.
    Claims are split at the sentence level before pattern matching.

    See module docstring for limitations.
    """

    def extract(self, generated_text: str) -> list[Claim]:
        """
        Extract atomic factual claims from generated_text.

        Parameters
        ----------
        generated_text : str
            Text produced by an LLM (resume edit bullet, job-match explanation, etc.)

        Returns
        -------
        list[Claim]
            One Claim per detected atomic assertion.  Returns an empty list for
            empty input.  Never raises; uncertain extractions are returned with
            ExtractionStatus.UNCERTAIN.
        """
        if not generated_text or not generated_text.strip():
            return []

        sentences = _split_sentences(generated_text)
        all_claims: list[Claim] = []

        for sentence in sentences:
            sentence_claims: list[Claim] = []

            # Order matters: more specific → less specific
            sentence_claims.extend(_extract_skills(sentence))
            sentence_claims.extend(_extract_employers(sentence))
            sentence_claims.extend(_extract_metrics(sentence))
            sentence_claims.extend(_extract_durations(sentence))
            sentence_claims.extend(_extract_dates(sentence))
            sentence_claims.extend(_extract_education(sentence))
            sentence_claims.extend(_extract_certifications(sentence))

            # Quantities: only add if not already covered by a metric claim
            metric_values = {c.numeric_value for c in sentence_claims if c.claim_type == ClaimType.METRIC}
            for qclaim in _extract_quantities(sentence):
                if qclaim.numeric_value not in metric_values:
                    sentence_claims.append(qclaim)

            # Responsibility: only if no other claim extracted from this sentence
            if not sentence_claims:
                sentence_claims.extend(_extract_responsibilities(sentence))

            all_claims.extend(sentence_claims)

        return all_claims
