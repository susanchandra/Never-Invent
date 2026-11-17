"""
parsing/normalizers.py — Normalization helpers for skills, dates, metrics, and entities.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Optional, Tuple
import dateparser


# Common canonical skill alias mapping
SKILL_ALIASES = {
    "py": "python",
    "python3": "python",
    "python 3": "python",
    "js": "javascript",
    "ts": "typescript",
    "reactjs": "react",
    "react.js": "react",
    "nodejs": "node.js",
    "node": "node.js",
    "golang": "go",
    "k8s": "kubernetes",
    "postgres": "postgresql",
    "tf": "tensorflow",
    "torch": "pytorch",
    "aws": "amazon web services",
    "gcp": "google cloud platform",
    "azure": "microsoft azure",
    "scikit": "scikit-learn",
    "sklearn": "scikit-learn",
    "ml": "machine learning",
    "dl": "deep learning",
    "nlp": "natural language processing",
    "cv": "computer vision",
    "llm": "large language models",
    "llms": "large language models",
}


def normalize_skill(raw_skill: str) -> str:
    """
    Normalize skill string: trim, lowercase, strip trailing punctuation, map aliases.
    """
    if not raw_skill:
        return ""
    cleaned = raw_skill.strip().lower()
    cleaned = re.sub(r"[\(\)\[\]\{\},;]+", " ", cleaned).strip()
    return SKILL_ALIASES.get(cleaned, cleaned)


def normalize_date(raw_date_str: str) -> Optional[str]:
    """
    Normalize raw date string into 'YYYY-MM' format.
    Returns 'Present' for ongoing roles.
    Returns None if date cannot be parsed with certainty.
    """
    if not raw_date_str:
        return None

    cleaned = raw_date_str.strip()
    if re.search(r"\b(present|current|now|ongoing|today)\b", cleaned, re.IGNORECASE):
        return "Present"

    # Try explicit Year-only match first (e.g. "2021")
    year_match = re.match(r"^(\d{4})$", cleaned)
    if year_match:
        return f"{year_match.group(1)}-01"

    # Try dateparser
    dt = dateparser.parse(
        cleaned,
        settings={"PREFER_DAY_OF_MONTH": "first", "RETURN_AS_TIMEZONE_AWARE": False},
    )
    if dt:
        return dt.strftime("%Y-%m")

    return None


def calculate_duration_months(start_date_str: Optional[str], end_date_str: Optional[str]) -> Optional[int]:
    """
    Calculate duration in months between two YYYY-MM dates.
    If end_date_str is 'Present', uses current date (2026-11 per prompt environment).
    Returns None if either date is missing, invalid, or end is before start.
    """
    if not start_date_str or not end_date_str:
        return None

    try:
        start_year, start_month = map(int, start_date_str.split("-")[:2])
    except (ValueError, AttributeError):
        return None

    if end_date_str.lower() in ("present", "current", "now"):
        # Fixed reference date from environment: Nov 2026
        end_year, end_month = 2026, 11
    else:
        try:
            end_year, end_month = map(int, end_date_str.split("-")[:2])
        except (ValueError, AttributeError):
            return None

    months = (end_year - start_year) * 12 + (end_month - start_month)
    if months < 0:
        return None
    return months


def parse_numeric_metric(text: str) -> list[Tuple[float, Optional[str], Optional[str]]]:
    """
    Find metric values in text, e.g. '40%', '$1.2M', '500ms', '3x', '100+ users'.
    Returns list of (quantity, unit, direction).
    """
    results = []
    # Pattern 1: Percentages (e.g. 40%, 15.5%)
    for m in re.finditer(r"(\b\d+(?:\.\d+)?)\s*%", text):
        val = float(m.group(1))
        direction = "decrease" if re.search(r"\b(reduced|cut|decreased|dropped|saved|slashed)\b", text[:m.start()], re.I) else (
            "increase" if re.search(r"\b(increased|grew|boosted|improved|scaled|raised)\b", text[:m.start()], re.I) else None
        )
        results.append((val, "%", direction))

    # Pattern 2: Currency (e.g. $500K, $2.5M, $100,000)
    for m in re.finditer(r"\$\s*(\d+(?:\.\d+)?)\s*([KkMmBb])?", text):
        base = float(m.group(1))
        multiplier = 1.0
        suffix = (m.group(2) or "").upper()
        if suffix == "K":
            multiplier = 1_000.0
        elif suffix == "M":
            multiplier = 1_000_000.0
        elif suffix == "B":
            multiplier = 1_000_000_000.0
        val = base * multiplier
        results.append((val, "$", "total"))

    # Pattern 3: Speed / latency (e.g. 50ms, 2s, 3x)
    for m in re.finditer(r"(\b\d+(?:\.\d+)?)\s*(ms|s|sec|seconds|x)\b", text, re.I):
        val = float(m.group(1))
        unit = m.group(2).lower()
        direction = "speedup" if unit == "x" else None
        results.append((val, unit, direction))

    return results
