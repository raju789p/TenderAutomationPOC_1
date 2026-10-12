"""Validated JSON generation with rate limiting, retries, and result caching."""

from __future__ import annotations

import hashlib
import json
import random
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Type

from pydantic import BaseModel, ValidationError

from poc.llm.providers import LLMProvider, ProviderError
from poc.llm.settings import LLMSettings


PROMPT_VERSION = "m3-v1"


class QuotaLimitError(RuntimeError):
    """Raised when the provider reports a daily or account quota limit."""


class InvalidProviderOutput(RuntimeError):
    """Raised after the initial response and one repair response fail validation."""


@dataclass
class ServiceStats:
    provider_calls: int = 0
    cache_hits: int = 0
    repair_calls: int = 0
    retries: int = 0


class LLMService:
    """Provider wrapper that caches only schema-valid JSON results."""

    def __init__(self, provider: LLMProvider, settings: LLMSettings, cache_dir: Path, sleep=time.sleep, jitter=random.uniform):
        self.provider = provider
        self.settings = settings
        self.cache_dir = cache_dir
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.stats = ServiceStats()
        self._sleep = sleep
        self._jitter = jitter
        self._last_request: float | None = None

    def _cache_path(self, prompt: str, image: bytes | None) -> Path:
        image_hash = hashlib.sha256(image).hexdigest() if image is not None else ""
        model = self.provider.model_for(image is not None)
        material = "\0".join((self.provider.name, model, PROMPT_VERSION, prompt, image_hash))
        digest = hashlib.sha256(material.encode("utf-8")).hexdigest()
        return self.cache_dir / f"{digest}.json"

    def _rate_limit(self) -> None:
        if self.provider.name == "mock" or self._last_request is None:
            self._last_request = time.monotonic()
            return
        interval = 60.0 / self.settings.rpm
        wait = interval - (time.monotonic() - self._last_request)
        if wait > 0:
            self._sleep(wait)
        self._last_request = time.monotonic()

    def _call(self, prompt: str, schema: Type[BaseModel], image: bytes | None, mime: str | None) -> dict[str, Any]:
        for attempt in range(self.settings.max_retries + 1):
            self._rate_limit()
            self.stats.provider_calls += 1
            try:
                return self.provider.generate_json(prompt, schema, image, mime)
            except ProviderError as error:
                if error.quota:
                    raise QuotaLimitError("Provider quota limit reached") from None
                retryable = error.status_code == 429 or (error.status_code is not None and 500 <= error.status_code <= 599)
                if not retryable or attempt >= self.settings.max_retries:
                    raise
                self.stats.retries += 1
                ceiling = min(60.0, 2.0**attempt)
                self._sleep(self._jitter(0.0, ceiling))
        raise AssertionError("unreachable retry state")

    def generate_validated(
        self,
        prompt: str,
        schema: Type[BaseModel],
        image: bytes | None = None,
        mime: str | None = None,
    ) -> tuple[BaseModel, bool]:
        """Return a schema-valid value and whether it came from cache."""
        cache_path = self._cache_path(prompt, image)
        if cache_path.is_file():
            try:
                cached = json.loads(cache_path.read_text(encoding="utf-8"))
                result = schema.model_validate(cached)
            except (ValidationError, json.JSONDecodeError):
                # Corrupt or old cache entries are ignored and replaced only after valid generation.
                pass
            else:
                self.stats.cache_hits += 1
                return result, True

        try:
            raw = self._call(prompt, schema, image, mime)
            result = schema.model_validate(raw)
        except (ValueError, ValidationError) as first_error:
            self.stats.repair_calls += 1
            repair_prompt = (
                f"{prompt}\n\nYour previous response did not validate. Correct it and return JSON only. "
                f"Validation error: {first_error}"
            )
            try:
                raw = self._call(repair_prompt, schema, image, mime)
                result = schema.model_validate(raw)
            except (ValueError, ValidationError) as second_error:
                raise InvalidProviderOutput("Initial and repair outputs failed schema validation") from second_error

        cache_path.write_text(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return result, False
