"""
workflow/diff_helper.py — Computes diff highlights (additions, removals, numeric changes).
"""

from __future__ import annotations

import difflib
import re
from typing import Optional

from neverinvent.parsing.normalizers import parse_numeric_metric
from neverinvent.workflow.models import DiffHighlight


def compute_diff(original_text: Optional[str], proposed_text: str) -> list[DiffHighlight]:
    """
    Computes differences between original and proposed text.
    Detects word additions/deletions and altered numbers.
    """
    if not original_text:
        return [DiffHighlight(kind="addition", value=proposed_text)]

    highlights: list[DiffHighlight] = []

    # 1. Check for changed numeric values
    orig_metrics = parse_numeric_metric(original_text)
    prop_metrics = parse_numeric_metric(proposed_text)

    if orig_metrics and prop_metrics:
        for p_val, p_unit, _ in prop_metrics:
            for o_val, o_unit, _ in orig_metrics:
                if p_unit == o_unit and p_val != o_val:
                    highlights.append(
                        DiffHighlight(
                            kind="changed_metric",
                            value=f"{p_val}{p_unit or ''}",
                            original_value=f"{o_val}{o_unit or ''}",
                        )
                    )

    # 2. Word-level additions and deletions
    orig_words = re.findall(r"\w+|[^\w\s]", original_text)
    prop_words = re.findall(r"\w+|[^\w\s]", proposed_text)

    matcher = difflib.SequenceMatcher(None, orig_words, prop_words)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "insert":
            inserted = " ".join(prop_words[j1:j2])
            highlights.append(DiffHighlight(kind="addition", value=inserted))
        elif tag == "delete":
            deleted = " ".join(orig_words[i1:i2])
            highlights.append(DiffHighlight(kind="deletion", value=deleted))
        elif tag == "replace":
            deleted = " ".join(orig_words[i1:i2])
            inserted = " ".join(prop_words[j1:j2])
            highlights.append(
                DiffHighlight(kind="addition", value=inserted, original_value=deleted)
            )

    return highlights
