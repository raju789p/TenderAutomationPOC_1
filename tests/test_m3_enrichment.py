"""Offline M3 provider, classification, cache, and reliability tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from poc.enrich import ImagePayload, classify_heading, enrich_document
from poc.extract import extract_document
from poc.llm.providers import MockProvider
from poc.llm.service import LLMService, QuotaLimitError
from poc.llm.settings import LLMSettings
from poc.models import Document, Heading


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {"waterfall": "WaterFall_PM_Documentation 1.pdf", "kanban": "Kanban_PM_Final 2.pdf"}
MOCK_SETTINGS = LLMSettings(provider="mock", model="mock", api_key=None, rpm=100, max_retries=1)


@pytest.fixture(scope="module")
def enriched_workspace(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, MockProvider, LLMService, dict[str, dict]]:
    root = tmp_path_factory.mktemp("m3")
    work_root = root / "work"
    challenge_log = root / "challenges_log.md"
    challenge_log.write_text("# Challenges log\n", encoding="utf-8")
    extraction_config = yaml.safe_load((ROOT / "config" / "extraction.yaml").read_text(encoding="utf-8"))
    classification_config = yaml.safe_load((ROOT / "config" / "classification.yaml").read_text(encoding="utf-8"))
    provider = MockProvider(ROOT / "tests" / "fixtures" / "mock_llm.json")
    service = LLMService(provider, MOCK_SETTINGS, root / "cache")
    results = {}
    for doc_id, filename in SOURCES.items():
        extract_document(doc_id, ROOT / "data" / "input" / filename, work_root, extraction_config, challenge_log)
        results[doc_id] = enrich_document(
            doc_id, work_root, ROOT, MOCK_SETTINGS, provider, service, classification_config,
        )
    return work_root, provider, service, results


def test_all_twenty_level_one_headings_use_rules_and_subsections_inherit(enriched_workspace) -> None:
    work_root, _, _, results = enriched_workspace
    key = json.loads((ROOT / "docs" / "answer_key.json").read_text(encoding="utf-8"))
    for doc_id in SOURCES:
        expected = key[doc_id]["section_types"]
        classification = json.loads((work_root / doc_id / "classification.json").read_text(encoding="utf-8"))["items"]
        document = Document.model_validate_json((work_root / doc_id / "elements.json").read_text(encoding="utf-8"))
        heading_by_id = {element.id: element for element in document.elements if isinstance(element, Heading)}
        level_one = [item for item in classification if heading_by_id[item["heading_id"]].level == 1]
        assert len(level_one) == 10
        assert all(item["method"] == "rule" and item["status"] == "complete" for item in classification)
        assert all(item["canonical_type"] == expected[item["number"]] for item in level_one)
        for item in classification:
            heading = heading_by_id[item["heading_id"]]
            if heading.level > 1:
                assert item["canonical_type"] == expected[heading.number.split(".", 1)[0]]
                assert item["inherited_from"] == heading.number.split(".", 1)[0]
        assert results[doc_id]["classification"] == {"rule": len(classification), "llm": 0, "failed": 0}
    assert sum(results[doc_id]["classification"]["rule"] for doc_id in SOURCES) >= 20


def test_figures_enrich_and_second_run_is_all_cache_hits(enriched_workspace) -> None:
    work_root, provider, service, results = enriched_workspace
    assert sum(result["figures"] for result in results.values()) == 8
    assert sum(result["figures_complete"] for result in results.values()) == 8
    calls_after_first_run = provider.calls
    assert calls_after_first_run == 8
    assert service.stats.cache_hits == 0

    classification_config = yaml.safe_load((ROOT / "config" / "classification.yaml").read_text(encoding="utf-8"))
    second_results = {
        doc_id: enrich_document(
            doc_id, work_root, ROOT, MOCK_SETTINGS, provider, service, classification_config,
        )
        for doc_id in SOURCES
    }
    assert provider.calls == calls_after_first_run
    assert sum(result["provider_calls"] for result in second_results.values()) == 0
    assert sum(result["cache_hits"] for result in second_results.values()) == 8
    for doc_id in SOURCES:
        document = Document.model_validate_json((work_root / doc_id / "elements.json").read_text(encoding="utf-8"))
        assert all(figure.ai_status == "complete" and figure.ai is not None for figure in document.elements if figure.type == "figure")


def test_unknown_heading_uses_mock_llm_then_cache(tmp_path: Path) -> None:
    provider = MockProvider(ROOT / "tests" / "fixtures" / "mock_llm.json")
    service = LLMService(provider, MOCK_SETTINGS, tmp_path / "cache")
    config = yaml.safe_load((ROOT / "config" / "classification.yaml").read_text(encoding="utf-8"))
    prompt = (ROOT / "src" / "poc" / "prompts" / "classification.txt").read_text(encoding="utf-8").strip()
    heading = Heading(
        id="mock-p001-001", doc_id="mock", page=1, bbox=(0, 0, 100, 20),
        role="body", level=1, number="11", title="A New Unmapped Heading",
    )
    first = classify_heading(heading, config, service, prompt, {})
    second = classify_heading(heading, config, service, prompt, {})
    assert first["method"] == second["method"] == "llm"
    assert first["canonical_type"] == "core_concept"
    assert provider.calls == 1
    assert service.stats.cache_hits == 1


def _service_with_fixture(tmp_path: Path, responses: list[dict], kind: str = "classification", retries: int = 1):
    fixture = tmp_path / "mock.json"
    fixture.write_text(json.dumps({kind: {"responses": responses}}), encoding="utf-8")
    provider = MockProvider(fixture)
    settings = LLMSettings("mock", "mock", None, 100, retries)
    service = LLMService(provider, settings, tmp_path / "cache", sleep=lambda _: None, jitter=lambda low, high: 0)
    return provider, service


def test_transient_429_retries_and_valid_output_is_cached(tmp_path: Path) -> None:
    provider, service = _service_with_fixture(tmp_path, [
        {"mock_error": {"status_code": 429}}, {"canonical_type": "scope"},
    ])
    result, cached = service.generate_validated("title only", __import__("poc.models", fromlist=["HeadingClassification"]).HeadingClassification)
    assert result.canonical_type == "scope"
    assert not cached
    assert provider.calls == 2 and service.stats.retries == 1


def test_invalid_json_shape_gets_one_repair_retry(tmp_path: Path) -> None:
    provider, service = _service_with_fixture(tmp_path, [{"unexpected": "value"}, {"canonical_type": "scope"}])
    from poc.models import HeadingClassification

    result, _ = service.generate_validated("title only", HeadingClassification)
    assert result.canonical_type == "scope"
    assert provider.calls == 2 and service.stats.repair_calls == 1


def test_quota_limit_stops_retrying(tmp_path: Path) -> None:
    provider, service = _service_with_fixture(
        tmp_path, [{"mock_error": {"status_code": 429, "quota": True}}], kind="image",
    )
    with pytest.raises(QuotaLimitError):
        service.generate_validated("image prompt", ImagePayload, b"image", "image/png")
    assert provider.calls == 1


def test_image_payload_rejects_multiple_caption_sentences() -> None:
    with pytest.raises(ValueError):
        ImagePayload.model_validate({
            "kind": "diagram", "caption": "First. Second.",
            "transcribed_text": [], "uncertain": False,
        })
