"""
api/routers/resume.py — Endpoints for resume upload, ingestion, and profile retrieval.
"""

from __future__ import annotations

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from neverinvent.ingestion.pdf_extractor import extract_pdf
from neverinvent.ingestion.txt_extractor import extract_txt
from neverinvent.parsing.models import CandidateProfile
from neverinvent.parsing.profile_parser import ProfileParser
from neverinvent.persistence.database import get_db_session
from neverinvent.persistence.repository import Repository

router = APIRouter(prefix="/api/resume", tags=["resume"])


MAX_UPLOAD_SIZE = 10 * 1024 * 1024  # 10 MB
CHUNK_SIZE = 1024 * 1024  # 1 MB


@router.post("/upload")
async def upload_resume(
    file: Optional[UploadFile] = File(default=None),
    raw_text_input: Optional[str] = Form(default=None),
    session: Session = Depends(get_db_session),
):
    """
    Ingest a PDF or TXT resume, extract text with provenance, parse into CandidateProfile,
    and persist in SQLite.
    Strictly enforces 10 MB ceiling via chunked streaming to prevent memory exhaustion DoS.
    """
    parser = ProfileParser()
    repo = Repository(session)

    if file is not None and file.filename:
        filename = file.filename.lower()
        suffix = Path(filename).suffix
        if suffix not in (".pdf", ".txt", ".text"):
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file format '{suffix}'. Please upload PDF or TXT.",
            )

        total_bytes = 0
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        tmp_path = tmp.name
        try:
            try:
                while True:
                    chunk = await file.read(CHUNK_SIZE)
                    if not chunk:
                        break
                    total_bytes += len(chunk)
                    if total_bytes > MAX_UPLOAD_SIZE:
                        raise HTTPException(
                            status_code=413,
                            detail="File size exceeds maximum permitted limit of 10 MB.",
                        )
                    tmp.write(chunk)
            finally:
                tmp.close()

            if suffix == ".pdf":
                raw_doc = extract_pdf(tmp_path)
            else:
                raw_doc = extract_txt(tmp_path)
        finally:
            try:
                Path(tmp_path).unlink()
            except OSError:
                pass

    elif raw_text_input and raw_text_input.strip():
        if len(raw_text_input.encode("utf-8")) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="Raw text input exceeds maximum permitted limit of 10 MB.",
            )
        # Handle direct text input
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp.write(raw_text_input)
            tmp_path = tmp.name
        try:
            raw_doc = extract_txt(tmp_path)
        finally:
            try:
                Path(tmp_path).unlink()
            except OSError:
                pass
    else:
        raise HTTPException(
            status_code=400,
            detail="Either a file (PDF/TXT) or raw_text_input must be provided.",
        )

    profile = parser.parse(raw_doc)
    cid = repo.save_candidate(profile, raw_text=raw_doc.full_text)

    return {
        "candidate_id": cid,
        "profile": profile,
        "warnings": [str(w) for w in raw_doc.warnings],
        "extracted_chars": len(raw_doc.full_text),
    }


@router.get("/{candidate_id}")
def get_candidate_profile(candidate_id: str, session: Session = Depends(get_db_session)):
    repo = Repository(session)
    profile = repo.get_candidate(candidate_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Candidate profile not found.")
    return {"candidate_id": candidate_id, "profile": profile}
