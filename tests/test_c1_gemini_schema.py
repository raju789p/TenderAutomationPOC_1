"""Offline checks for the Gemini-safe planner request and local strictness."""

from __future__ import annotations

from pydantic import ValidationError
import pytest

from poc.convert.plan_schema import Plan, gemini_plan_schema
from poc.llm.providers import _provider_failure, _provider_schema, sanitize_provider_message


FORBIDDEN = {"$defs", "$ref", "anyOf", "oneOf", "enum", "additionalProperties", "default", "title"}


def _keys(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from _keys(item)
    elif isinstance(value, list):
        for item in value:
            yield from _keys(item)


def test_gemini_provider_schema_is_flat_and_uses_plain_strings():
    sent_schema = _provider_schema(Plan)
    assert sent_schema == gemini_plan_schema()
    assert not (FORBIDDEN & set(_keys(sent_schema)))
    assert sent_schema["properties"]["sections"]["items"]["properties"]["target_section"] == {"type": "STRING"}
    block = sent_schema["properties"]["sections"]["items"]["properties"]["blocks"]["items"]
    assert block["properties"]["block_type"] == {"type": "STRING"}


def test_sanitizer_removes_credentials_and_url_query_strings():
    result = sanitize_provider_message(
        "bad key=secret123 X-goog-api-key:anothersecret "
        "https://example.test/path?key=querysecret&token=alsobad"
    )
    assert "secret123" not in result
    assert "anothersecret" not in result
    assert "querysecret" not in result and "alsobad" not in result
    assert "https://example.test/path" in result


def test_provider_error_keeps_sanitized_api_message_and_status():
    class FakeHTTPError(Exception):
        status_code = 400
        message = "Invalid schema; token=secret-value"

    error = _provider_failure(FakeHTTPError())
    assert error.status_code == 400
    assert "Invalid schema" in str(error)
    assert "secret-value" not in str(error)
    assert "HTTP 400" in str(error)


@pytest.mark.parametrize("field,value", [("target_section", "invented"), ("block_type", "chart")])
def test_local_plan_schema_still_rejects_invalid_values(field, value):
    block = {"source_id": "p1", "block_type": "paragraph"}
    section = {"target_section": "A_overview", "source_heading_id": "h1", "blocks": [block]}
    if field == "target_section":
        section[field] = value
    else:
        block[field] = value
    with pytest.raises(ValidationError):
        Plan.model_validate({"sections": [section]})
