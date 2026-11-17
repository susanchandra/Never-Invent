"""
api/main.py — FastAPI application entry point for NeverInvent.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from neverinvent.api.routers import approval, jobs, resume, verification
from neverinvent.persistence.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


import os

# Configured trusted CORS origins (strict when credentials allowed)
_DEFAULT_ORIGINS = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
_env_origins = os.getenv("CORS_ORIGINS")
ALLOWED_ORIGINS = [o.strip() for o in _env_origins.split(",")] if _env_origins else _DEFAULT_ORIGINS

app = FastAPI(
    title="NeverInvent API",
    description="Evidence-Grounded Resume Intelligence & Independent Claim Verification Engine",
    version="0.3.0",
    lifespan=lifespan,
)

# Enable CORS strictly for trusted origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Include routers
app.include_router(resume.router)
app.include_router(jobs.router)
app.include_router(verification.router)
app.include_router(approval.router)


@app.get("/health")
def healthcheck():
    return {
        "status": "healthy",
        "service": "NeverInvent",
        "version": "0.3.0",
        "architecture": "decoupled_deterministic_verification",
    }


# Frontend static files mounting
FRONTEND_DIR = Path("frontend")
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

    @app.get("/")
    def serve_frontend_root():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(index_file)
        return {"message": "NeverInvent API is running. Frontend index.html not found."}
