"""
config.py — Application-wide settings loaded from environment / .env file.

All secrets (API keys) are excluded from source control via .gitignore.
Never hardcode secrets here. Use .env.example as the documented template.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    NeverInvent application settings.

    Values are loaded from:
    1. Environment variables (highest priority)
    2. .env file in project root
    3. Defaults defined here
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",   # ignore unknown env vars silently
    )

    # --- Application ---
    app_env: str = "development"
    log_level: str = "INFO"

    # --- Database ---
    database_url: str = "sqlite:///./neverinvent.db"

    # --- Embedding model ---
    # Pinned model name. Change with care — affects FAISS index compatibility.
    embedding_model_name: str = "BAAI/bge-small-en-v1.5"
    # Set to False to force CPU even when CUDA is available.
    # Leave True to use GPU when available (faster embedding during development).
    use_gpu_if_available: bool = True

    # --- Retrieval ---
    bm25_k1: float = 1.5
    bm25_b: float = 0.75
    # RRF parameter (k=60 is the standard default from the original RRF paper)
    rrf_k: int = 60

    # --- Optional: Groq API (Phase 2+, not required for Phase 1) ---
    groq_api_key: str = ""

    # --- Paths ---
    # Resolved at runtime relative to config.py location
    @property
    def project_root(self) -> Path:
        return Path(__file__).parent.resolve()

    @property
    def data_dir(self) -> Path:
        return self.project_root / "data"

    @property
    def sample_resumes_dir(self) -> Path:
        return self.data_dir / "sample_resumes"

    @property
    def job_postings_dir(self) -> Path:
        return self.data_dir / "job_postings"

    @property
    def evaluation_datasets_dir(self) -> Path:
        return self.project_root / "neverinvent" / "evaluation" / "datasets"

    @property
    def evaluation_reports_dir(self) -> Path:
        return self.project_root / "neverinvent" / "evaluation" / "reports"


# Module-level singleton — import this everywhere.
# Tests may override individual fields by passing kwargs to Settings().
settings = Settings()
