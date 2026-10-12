"""Load LLM settings from process environment and the project .env file."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass(frozen=True)
class LLMSettings:
    provider: str
    model: str
    api_key: str | None
    rpm: int
    max_retries: int
    groq_vision_model: str | None = None


def load_settings(provider_override: str | None = None, root: Path | None = None) -> LLMSettings:
    """Load settings without logging or exposing any credential values."""
    project_root = root or Path.cwd()
    load_dotenv(dotenv_path=project_root / ".env", override=False)
    provider = (provider_override or os.getenv("LLM_PROVIDER", "mock")).strip().lower()
    if provider not in {"mock", "gemini", "groq"}:
        raise ValueError("LLM_PROVIDER must be mock, gemini, or groq")
    if provider == "gemini":
        model = os.getenv("GEMINI_MODEL", "").strip()
        api_key = os.getenv("GEMINI_API_KEY", "").strip()
        required = [("GEMINI_MODEL", model), ("GEMINI_API_KEY", api_key)]
    elif provider == "groq":
        model = os.getenv("GROQ_MODEL", "").strip()
        api_key = os.getenv("GROQ_API_KEY", "").strip()
        required = [("GROQ_MODEL", model), ("GROQ_API_KEY", api_key)]
    else:
        model = "mock"
        api_key = None
        required = []
    missing = [name for name, value in required if not value]
    if missing:
        raise ValueError("Missing required environment variable(s): " + ", ".join(missing))
    rpm = _positive_env("LLM_RPM", 10)
    retries = _positive_env("LLM_MAX_RETRIES", 5, allow_zero=True)
    return LLMSettings(
        provider=provider,
        model=model,
        api_key=api_key,
        rpm=rpm,
        max_retries=retries,
        groq_vision_model=os.getenv("GROQ_VISION_MODEL", "").strip() or None,
    )


def _positive_env(name: str, default: int, allow_zero: bool = False) -> int:
    raw = os.getenv(name, str(default)).strip()
    try:
        value = int(raw)
    except ValueError as error:
        raise ValueError(f"{name} must be an integer") from error
    if value < (0 if allow_zero else 1):
        raise ValueError(f"{name} must be {'non-negative' if allow_zero else 'positive'}")
    return value
