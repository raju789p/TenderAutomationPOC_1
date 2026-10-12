"""Gemini, Groq, and offline mock implementations of the JSON provider."""

from __future__ import annotations

import base64
import json
import re
from pathlib import Path
from typing import Any, Protocol, Type
from urllib.parse import urlsplit, urlunsplit

from pydantic import BaseModel

from poc.llm.settings import LLMSettings


def sanitize_provider_message(message: str) -> str:
    """Remove credentials and URL query strings from provider-supplied text."""
    value = str(message)
    value = re.sub(r"(?i)Bearer\s+[A-Za-z0-9._~+/-]+=*", "Bearer [REDACTED]", value)
    value = re.sub(
        r"(?i)(api[_ -]?key|x-goog-api-key|authorization|access[_ -]?token|token|\bkey)([\"']?\s*[:=]\s*[\"']?)[^\s,\"'}]+",
        r"\1\2[REDACTED]", value,
    )
    value = re.sub(r"AIza[A-Za-z0-9_-]{20,}", "[REDACTED]", value)
    value = re.sub(
        r"https?://[^\s\"'<>]+",
        lambda match: _without_query(match.group(0)), value,
    )
    return value[:2000]


def _without_query(url: str) -> str:
    """Strip query and fragment components from a URL safely."""
    try:
        parts = urlsplit(url)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))
    except ValueError:
        return "[URL]"


def _api_message(error: Exception) -> str:
    """Extract the API's own message where available without exposing raw headers."""
    direct = getattr(error, "message", None)
    if isinstance(direct, str) and direct:
        return direct
    response = getattr(error, "response", None)
    json_method = getattr(response, "json", None)
    if callable(json_method):
        try:
            body = json_method()
            if isinstance(body, dict):
                nested = body.get("error", body)
                if isinstance(nested, dict) and isinstance(nested.get("message"), str):
                    return nested["message"]
        except Exception:
            pass
    raw = str(error)
    match = re.search(r"['\"]message['\"]\s*:\s*['\"]([^'\"]+)['\"]", raw)
    return match.group(1) if match else raw


def _provider_schema(schema: Type[BaseModel]) -> Any:
    """Select a provider-safe override when a Pydantic model declares one."""
    override = getattr(schema, "gemini_response_schema", None)
    return override() if callable(override) else schema


class LLMProvider(Protocol):
    """Common structured-generation interface."""

    name: str
    model: str

    def model_for(self, image: bool = False) -> str:
        """Return the configured model selected for this request type."""

    def generate_json(self, prompt: str, schema: Type[BaseModel], image: bytes | None = None, mime: str | None = None) -> dict[str, Any]:
        """Generate JSON conforming to the supplied Pydantic schema."""


class ProviderError(RuntimeError):
    """Sanitized provider failure metadata used by retry policy."""

    def __init__(self, message: str, status_code: int | None = None, quota: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.quota = quota


def _response_dict(text: str) -> dict[str, Any]:
    try:
        value = json.loads(text)
    except (TypeError, json.JSONDecodeError) as error:
        raise ValueError("Provider returned invalid JSON") from error
    if not isinstance(value, dict):
        raise ValueError("Provider JSON must be an object")
    return value


def _provider_failure(error: Exception) -> ProviderError:
    status = getattr(error, "status_code", None)
    if status is None:
        status = getattr(error, "code", None)
    try:
        status = int(status) if status is not None else None
    except (ValueError, TypeError):
        status = None
    api_message = sanitize_provider_message(_api_message(error))
    quota = any(term in api_message.casefold() for term in ("quota", "resource exhausted", "daily limit", "billing limit"))
    prefix = f"Provider quota limit reached (HTTP {status})" if quota and status else "Provider quota limit reached" if quota else f"Provider request failed (HTTP {status})" if status else "Provider request failed"
    return ProviderError(f"{prefix}: {api_message}", status_code=status, quota=quota)


class GeminiProvider:
    """Gemini JSON generation using the Google Gen AI SDK."""

    name = "gemini"

    def __init__(self, settings: LLMSettings):
        from google import genai

        self.model = settings.model
        self._client = genai.Client(api_key=settings.api_key)

    def model_for(self, image: bool = False) -> str:
        return self.model

    def generate_json(self, prompt: str, schema: Type[BaseModel], image: bytes | None = None, mime: str | None = None) -> dict[str, Any]:
        from google.genai import types

        content: list[Any] = [prompt]
        if image is not None:
            content.append(types.Part.from_bytes(data=image, mime_type=mime or "image/png"))
        try:
            response = self._client.models.generate_content(
                model=self.model,
                contents=content,
                config=types.GenerateContentConfig(
                    temperature=0,
                    response_mime_type="application/json",
                    response_schema=_provider_schema(schema),
                ),
            )
            return _response_dict(response.text or "")
        except (ValueError, ProviderError):
            raise
        except Exception as error:
            raise _provider_failure(error) from None


class GroqProvider:
    """Groq JSON generation; vision is restricted to a configured vision model."""

    name = "groq"

    def __init__(self, settings: LLMSettings):
        from groq import Groq

        self.model = settings.model
        self.vision_model = settings.groq_vision_model
        self._client = Groq(api_key=settings.api_key)

    def model_for(self, image: bool = False) -> str:
        if image and not self.vision_model:
            raise ProviderError("Groq vision requires GROQ_VISION_MODEL")
        return self.vision_model if image and self.vision_model else self.model

    def generate_json(self, prompt: str, schema: Type[BaseModel], image: bytes | None = None, mime: str | None = None) -> dict[str, Any]:
        model = self.model_for(image is not None)
        content: Any = prompt
        if image is not None:
            encoded = base64.b64encode(image).decode("ascii")
            content = [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime or 'image/png'};base64,{encoded}"}},
            ]
        try:
            response = self._client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": content}],
                temperature=0,
                response_format={"type": "json_object"},
            )
            return _response_dict(response.choices[0].message.content or "")
        except (ValueError, ProviderError):
            raise
        except Exception as error:
            raise _provider_failure(error) from None


class MockProvider:
    """Deterministic, offline provider with fixture-backed responses."""

    name = "mock"
    model = "mock"

    def __init__(self, fixture_path: Path | None = None):
        self.calls = 0
        self._indices = {"classification": 0, "image": 0}
        path = fixture_path or Path(__file__).resolve().parents[3] / "tests" / "fixtures" / "mock_llm.json"
        self._fixture = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}

    def model_for(self, image: bool = False) -> str:
        return self.model

    def generate_json(self, prompt: str, schema: Type[BaseModel], image: bytes | None = None, mime: str | None = None) -> dict[str, Any]:
        self.calls += 1
        kind = "image" if image is not None else "classification"
        fixture = self._fixture.get(kind, {})
        responses = fixture.get("responses", [])
        index = self._indices[kind]
        self._indices[kind] += 1
        response = responses[index] if index < len(responses) else fixture.get("default")
        if isinstance(response, dict) and "mock_error" in response:
            error = response["mock_error"]
            raise ProviderError(
                "Mock provider error",
                status_code=error.get("status_code"),
                quota=bool(error.get("quota", False)),
            )
        if response is None:
            if kind == "image":
                response = {
                    "kind": "other",
                    "caption": "Mock placeholder; no source image semantics were inferred.",
                    "transcribed_text": [],
                    "uncertain": True,
                }
            else:
                response = {"canonical_type": "core_concept"}
        return dict(response)


def create_provider(settings: LLMSettings, fixture_path: Path | None = None) -> LLMProvider:
    """Construct the selected provider without exposing credentials."""
    if settings.provider == "gemini":
        return GeminiProvider(settings)
    if settings.provider == "groq":
        return GroqProvider(settings)
    return MockProvider(fixture_path=fixture_path)
