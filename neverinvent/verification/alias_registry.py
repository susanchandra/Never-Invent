"""
verification/alias_registry.py — Canonical alias mapping registry for skills, companies, and degrees.
"""

from __future__ import annotations

from neverinvent.parsing.normalizers import SKILL_ALIASES

# Comprehensive skills alias mapping
VERIFICATION_SKILL_ALIASES = dict(SKILL_ALIASES)
VERIFICATION_SKILL_ALIASES.update({
    "py": "python",
    "python3": "python",
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
    "bge-small": "bge-small",
    "bge": "bge-small",
    "faiss-cpu": "faiss",
    "faiss": "faiss",
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
})

# Company aliases (canonical lowercase)
COMPANY_ALIASES = {
    "google": "google",
    "google llc": "google",
    "google inc": "google",
    "alphabet": "google",
    "meta": "meta",
    "meta platforms": "meta",
    "facebook": "meta",
    "amazon": "amazon",
    "amazon.com": "amazon",
    "aws": "amazon web services",
    "microsoft": "microsoft",
    "msft": "microsoft",
    "apple": "apple",
    "apple inc": "apple",
    "netflix": "netflix",
}

# Degree aliases
DEGREE_ALIASES = {
    "bs": "bachelor of science",
    "b.s.": "bachelor of science",
    "bachelor of science": "bachelor of science",
    "bachelor's": "bachelor of science",
    "bachelors": "bachelor of science",
    "ms": "master of science",
    "m.s.": "master of science",
    "master of science": "master of science",
    "master's": "master of science",
    "masters": "master of science",
    "phd": "doctor of philosophy",
    "ph.d.": "doctor of philosophy",
    "doctorate": "doctor of philosophy",
}


def canonicalize_skill(skill: str) -> str:
    cleaned = skill.strip().lower()
    return VERIFICATION_SKILL_ALIASES.get(cleaned, cleaned)


def canonicalize_company(company: str) -> str:
    cleaned = company.strip().lower().rstrip(".,")
    return COMPANY_ALIASES.get(cleaned, cleaned)


def canonicalize_degree(degree: str) -> str:
    cleaned = degree.strip().lower().rstrip(".,")
    return DEGREE_ALIASES.get(cleaned, cleaned)
