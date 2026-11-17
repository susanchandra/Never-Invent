"""
parsing/profile_parser.py — Conservative rule-based candidate profile extraction with full provenance.
"""

from __future__ import annotations

import re
from typing import Optional

from neverinvent.ingestion.models import RawDocument, SourceSpan
from neverinvent.parsing.models import (
    CandidateProfile,
    Certification,
    Education,
    ExtractionStatus,
    MetricClaim,
    Project,
    SkillItem,
    WorkExperience,
)
from neverinvent.parsing.normalizers import (
    calculate_duration_months,
    normalize_date,
    normalize_skill,
    parse_numeric_metric,
)


def _find_span(doc: RawDocument, subtext: str, start_search: int = 0) -> Optional[SourceSpan]:
    """Find exact occurrence of subtext in doc.full_text and return SourceSpan with page provenance."""
    idx = doc.full_text.find(subtext, start_search)
    if idx == -1:
        return None
    char_start = idx
    char_end = idx + len(subtext)
    page_span = doc.get_span_at(char_start)
    page_number = page_span.page_number if page_span else None
    return SourceSpan(
        page_number=page_number,
        char_start=char_start,
        char_end=char_end,
        text=subtext,
    )


class ProfileParser:
    """
    Conservative, deterministic resume parser.
    Never invents facts or fills in missing details.
    """

    # Section heading patterns
    SECTION_PATTERNS = {
        "experience": re.compile(r"^(?:work\s+)?experience|employment(?:\s+history)?|work\s+history", re.I | re.M),
        "education": re.compile(r"^education|academic\s+background|degrees", re.I | re.M),
        "skills": re.compile(r"^skills|technical\s+skills|core\s+competencies|technologies", re.I | re.M),
        "projects": re.compile(r"^projects|technical\s+projects|key\s+projects", re.I | re.M),
        "certifications": re.compile(r"^certifications|certificates|licenses", re.I | re.M),
    }

    EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    PHONE_PATTERN = re.compile(r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")

    MONTHS = r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
    DATE_STR = rf"(?:{MONTHS}\s+\d{{4}}|\d{{1,2}}/\d{{4}}|\b\d{{4}})"
    DATE_RANGE_PATTERN = re.compile(
        rf"({DATE_STR})\s*(?:-|–|—|to)\s*({DATE_STR}|Present|Current)",
        re.I,
    )

    def parse(self, doc: RawDocument) -> CandidateProfile:
        text = doc.full_text
        profile = CandidateProfile(
            source_document_path=doc.source_path,
            raw_text_length=len(text),
        )

        if not text.strip():
            return profile

        # Extract Email and Phone
        email_match = self.EMAIL_PATTERN.search(text)
        if email_match:
            profile.email = email_match.group(0)

        phone_match = self.PHONE_PATTERN.search(text)
        if phone_match:
            profile.phone = phone_match.group(0)

        # Extract Name from top lines
        lines = [line.strip() for line in text.splitlines() if line.strip()]
        for line in lines[:5]:
            if "@" not in line and not any(pat.match(line) for pat in self.SECTION_PATTERNS.values()):
                if len(line.split()) <= 4 and re.match(r"^[A-Za-z\s\.\'-]+$", line):
                    profile.candidate_name = line
                    break

        # Locate section boundaries
        sections: dict[str, tuple[int, int]] = {}
        matches = []
        for sec_name, pattern in self.SECTION_PATTERNS.items():
            for m in pattern.finditer(text):
                matches.append((m.start(), sec_name))
        matches.sort(key=lambda x: x[0])

        for i, (start_idx, sec_name) in enumerate(matches):
            end_idx = matches[i + 1][0] if i + 1 < len(matches) else len(text)
            sections[sec_name] = (start_idx, end_idx)

        # Extract Skills
        if "skills" in sections:
            s_start, s_end = sections["skills"]
            skills_text = text[s_start:s_end]
            first_nl = skills_text.find("\n")
            if first_nl != -1:
                skills_content = skills_text[first_nl + 1 :]
                raw_tokens = re.split(r"[,;•·|\n]+", skills_content)
                for tok in raw_tokens:
                    cleaned_tok = tok.strip()
                    if cleaned_tok and len(cleaned_tok) < 50:
                        norm = normalize_skill(cleaned_tok)
                        if norm:
                            span = _find_span(doc, cleaned_tok, start_search=s_start)
                            profile.skills.append(
                                SkillItem(
                                    name=norm,
                                    original_text=cleaned_tok,
                                    source_span=span,
                                    status=ExtractionStatus.EXPLICIT,
                                )
                            )

        # Extract Experience
        if "experience" in sections:
            e_start, e_end = sections["experience"]
            exp_text = text[e_start:e_end]
            profile.experience = self._parse_experience(doc, exp_text, e_start)

        # Extract Education
        if "education" in sections:
            ed_start, ed_end = sections["education"]
            ed_text = text[ed_start:ed_end]
            profile.education = self._parse_education(doc, ed_text, ed_start)

        # Extract Metrics across full document text
        profile.metrics = self._parse_metrics(doc)

        return profile

    def _parse_experience(self, doc: RawDocument, exp_text: str, offset: int) -> list[WorkExperience]:
        experiences: list[WorkExperience] = []
        lines = [l.strip() for l in exp_text.splitlines() if l.strip()]

        current_exp: Optional[WorkExperience] = None
        pending_header: Optional[str] = None

        for line in lines[1:]:  # skip 'Experience' header
            match = self.DATE_RANGE_PATTERN.search(line)
            if match:
                raw_start = match.group(1).strip()
                raw_end = match.group(2).strip()
                norm_start = normalize_date(raw_start)
                norm_end = normalize_date(raw_end)
                is_curr = (norm_end == "Present")
                dur = calculate_duration_months(norm_start, norm_end)

                # Determine company and title
                # Option 1: Company / title was in previous line
                # Option 2: Company / title is in same line outside date match
                line_outside_date = (line[: match.start()] + " " + line[match.end() :]).strip()
                header_candidates = []
                if pending_header:
                    header_candidates.extend(re.split(r"[,|\-–—]", pending_header))
                if line_outside_date:
                    header_candidates.extend(re.split(r"[,|\-–—]", line_outside_date))

                clean_headers = [h.strip() for h in header_candidates if h.strip()]
                company = clean_headers[0] if clean_headers else "Unknown Company"
                title = clean_headers[1] if len(clean_headers) > 1 else None

                span_text = f"{pending_header}\n{line}" if pending_header else line
                span = _find_span(doc, line, start_search=offset)

                current_exp = WorkExperience(
                    company=company,
                    original_company_text=company,
                    title=title,
                    original_title_text=title,
                    start_date=norm_start,
                    end_date=norm_end,
                    is_current=is_curr,
                    duration_months=dur,
                    responsibilities=[],
                    source_span=span,
                    status=ExtractionStatus.EXPLICIT if norm_start and norm_end else ExtractionStatus.UNCERTAIN,
                )
                experiences.append(current_exp)
                pending_header = None
            elif line.startswith(("-", "•", "*", "–")):
                if current_exp:
                    current_exp.responsibilities.append(line.lstrip("-•*– "))
            else:
                # Potential company/title line before the date line
                pending_header = line

        return experiences

    def _parse_education(self, doc: RawDocument, ed_text: str, offset: int) -> list[Education]:
        education_list = []
        lines = [l.strip() for l in ed_text.splitlines() if l.strip()]
        for line in lines[1:]:  # skip section title
            if re.search(r"\b(university|college|institute|school|bachelor|master|phd|b\.s|m\.s|b\.a|m\.a)\b", line, re.I):
                span = _find_span(doc, line, start_search=offset)
                degree_match = re.search(r"\b(b\.s\.|m\.s\.|b\.a\.|m\.a\.|ph\.d\.|bachelor['s]*|master['s]*|phd)\b", line, re.I)
                degree = degree_match.group(0) if degree_match else None
                education_list.append(
                    Education(
                        institution=line,
                        original_institution_text=line,
                        degree=degree,
                        source_span=span,
                        status=ExtractionStatus.EXPLICIT,
                    )
                )
        return education_list

    def _parse_metrics(self, doc: RawDocument) -> list[MetricClaim]:
        metrics = []
        for line in doc.full_text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            parsed_metrics = parse_numeric_metric(line_str)
            for quantity, unit, direction in parsed_metrics:
                span = _find_span(doc, line_str)
                metrics.append(
                    MetricClaim(
                        raw_metric_text=line_str,
                        quantity=quantity,
                        unit=unit,
                        direction=direction,
                        context=line_str,
                        source_span=span,
                        status=ExtractionStatus.EXPLICIT,
                    )
                )
        return metrics
