"""Rule-first classification and cached AI enrichment for extracted documents."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ValidationError, field_validator

from poc.llm.providers import LLMProvider, ProviderError, create_provider
from poc.llm.service import InvalidProviderOutput, LLMService, QuotaLimitError
from poc.llm.settings import LLMSettings, load_settings
from poc.models import Document, Figure, Heading, HeadingClassification, ImageDescription

LOGGER = logging.getLogger(__name__)


class ImagePayload(BaseModel):
    """Provider-facing image fields, before provenance metadata is attached."""

    kind: Literal["photo", "diagram", "chart", "screenshot", "other"]
    caption: str
    transcribed_text: list[str]
    uncertain: bool

    @field_validator("caption")
    @classmethod
    def require_single_sentence(cls, value: str) -> str:
        return ImageDescription.validate_one_sentence(value)


def _read_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _prompt(root: Path, name: str) -> str:
    return (root / "src" / "poc" / "prompts" / name).read_text(encoding="utf-8").strip()


def _rule_match(title: str, config: dict[str, Any]) -> str | None:
    normalized = " ".join(title.casefold().split())
    matches = {
        rule["canonical_type"]
        for rule in config["section_rules"]
        if any(" ".join(keyword.casefold().split()) in normalized for keyword in rule["keywords"])
    }
    if len(matches) > 1:
        raise ValueError(f"Classification rules conflict for heading title: {title}")
    return next(iter(matches)) if matches else None


def classify_heading(
    heading: Heading,
    config: dict[str, Any],
    service: LLMService,
    prompt_template: str,
    inherited_types: dict[str, str],
) -> dict[str, Any]:
    """Classify one heading by rule, parent inheritance, then LLM fallback."""
    if heading.level > 1:
        parent_number = (heading.number or "").split(".", maxsplit=1)[0]
        if parent_number not in inherited_types:
            return {
                "heading_id": heading.id,
                "number": heading.number,
                "title": heading.title,
                "canonical_type": None,
                "method": "rule",
                "status": "failed",
                "error": "Parent section has no classification",
            }
        return {
            "heading_id": heading.id,
            "number": heading.number,
            "title": heading.title,
            "canonical_type": inherited_types[parent_number],
            "method": "rule",
            "status": "complete",
            "inherited_from": parent_number,
        }

    matched = _rule_match(heading.title, config)
    method = "rule"
    try:
        if matched is None:
            method = "llm"
            result, _ = service.generate_validated(prompt_template.format(title=heading.title), HeadingClassification)
            matched = result.canonical_type
        section_number = (heading.number or "").split(".", maxsplit=1)[0]
        inherited_types[section_number] = matched
        return {
            "heading_id": heading.id,
            "number": heading.number,
            "title": heading.title,
            "canonical_type": matched,
            "method": method,
            "status": "complete",
        }
    except (QuotaLimitError, ProviderError, InvalidProviderOutput, ValidationError) as error:
        return {
            "heading_id": heading.id,
            "number": heading.number,
            "title": heading.title,
            "canonical_type": None,
            "method": method,
            "status": "failed",
            "error": str(error),
        }


def _save_document(document: Document, output_path: Path) -> None:
    output_path.write_text(document.model_dump_json(indent=2), encoding="utf-8")


def enrich_document(
    doc_id: str,
    work_root: Path,
    project_root: Path,
    settings: LLMSettings,
    provider: LLMProvider,
    service: LLMService,
    classification_config: dict[str, Any],
    quota_already_hit: bool = False,
) -> dict[str, Any]:
    """Classify headings and enrich figures, saving after every durable result."""
    calls_before = service.stats.provider_calls
    hits_before = service.stats.cache_hits
    repairs_before = service.stats.repair_calls
    retries_before = service.stats.retries
    document_root = work_root / doc_id
    elements_path = document_root / "elements.json"
    document = Document.model_validate_json(elements_path.read_text(encoding="utf-8"))
    headings = [element for element in document.elements if isinstance(element, Heading)]
    classification_prompt = _prompt(project_root, "classification.txt")
    inherited_types: dict[str, str] = {}
    classifications = [
        classify_heading(item, classification_config, service, classification_prompt, inherited_types)
        for item in headings
    ]
    classification_path = document_root / "classification.json"
    classification_path.write_text(
        json.dumps({"doc_id": doc_id, "items": classifications}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    image_prompt = _prompt(project_root, "image_description.txt")
    figures = [element for element in document.elements if isinstance(element, Figure)]
    quota_hit = quota_already_hit
    failed_figures: list[str] = []
    for index, figure in enumerate(figures):
        if quota_hit:
            figure.ai = None
            figure.ai_status = "failed"
            figure.ai_error = "Real provider calls stopped after quota limit"
            failed_figures.append(figure.id)
            continue
        image_path = document_root / figure.image_path
        image_bytes = image_path.read_bytes()
        try:
            result, _ = service.generate_validated(image_prompt, ImagePayload, image_bytes, figure.mime)
            figure.ai = ImageDescription(
                kind=result.kind,
                caption=result.caption,
                transcribed_text=result.transcribed_text,
                uncertain=result.uncertain,
                provider=provider.name,
                model=provider.model_for(image=True),
                prompt_version="m3-v1",
            )
            figure.ai_status = "complete"
            figure.ai_error = None
        except QuotaLimitError:
            quota_hit = True
            figure.ai = None
            figure.ai_status = "failed"
            figure.ai_error = "Provider quota limit reached; stopped further real calls"
            failed_figures.append(figure.id)
            LOGGER.warning("Provider quota limit reached for %s; remaining real calls stopped", doc_id)
        except (ProviderError, InvalidProviderOutput, ValidationError, OSError) as error:
            figure.ai = None
            figure.ai_status = "failed"
            figure.ai_error = str(error)
            failed_figures.append(figure.id)
        _save_document(document, elements_path)
        # Keep progress durable, including all results cached before a quota or item failure.
        classification_path.write_text(
            json.dumps({"doc_id": doc_id, "items": classifications}, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    _save_document(document, elements_path)
    classification_summary = {
        "rule": sum(item["method"] == "rule" and item["status"] == "complete" for item in classifications),
        "llm": sum(item["method"] == "llm" and item["status"] == "complete" for item in classifications),
        "failed": sum(item["status"] != "complete" for item in classifications),
    }
    return {
        "doc_id": doc_id,
        "headings": len(headings),
        "classification": classification_summary,
        "figures": len(figures),
        "figures_complete": sum(figure.ai_status == "complete" for figure in figures),
        "figures_failed": failed_figures,
        "quota_hit": quota_hit,
        "cache_hits": service.stats.cache_hits - hits_before,
        "provider_calls": service.stats.provider_calls - calls_before,
        "repair_calls": service.stats.repair_calls - repairs_before,
        "retries": service.stats.retries - retries_before,
        "classification_path": str(classification_path),
    }


def enrich_all(
    root: Path | None = None,
    provider_override: str | None = None,
    provider: LLMProvider | None = None,
    settings: LLMSettings | None = None,
) -> list[dict[str, Any]]:
    """Enrich all extracted documents using cached provider results."""
    project_root = root or Path.cwd()
    settings = settings or load_settings(provider_override, project_root)
    provider_instance = provider or create_provider(settings, project_root / "tests" / "fixtures" / "mock_llm.json")
    service = LLMService(provider_instance, settings, project_root / "data" / "work" / "llm_cache")
    documents_cfg = _read_yaml(project_root / "config" / "documents.yaml")["documents"]
    classification_config = _read_yaml(project_root / "config" / "classification.yaml")
    results = []
    quota_hit = False
    for item in documents_cfg:
        result = enrich_document(
            item["doc_id"], project_root / "data" / "work", project_root,
            settings, provider_instance, service, classification_config,
            quota_already_hit=quota_hit,
        )
        results.append(result)
        if result["quota_hit"]:
            quota_hit = True
            # Later documents are still persisted with explicit failed image statuses;
            # enrich_document receives quota_already_hit and makes no provider calls.
    return results


def check_connection(root: Path | None = None, provider_override: str | None = None) -> tuple[bool, str]:
    """Send one harmless text-plus-tiny-image request and return status and model only."""
    from io import BytesIO

    from PIL import Image

    project_root = root or Path.cwd()
    settings = load_settings(provider_override, project_root)
    provider = create_provider(settings)
    buffer = BytesIO()
    Image.new("RGB", (2, 2), color=(255, 255, 255)).save(buffer, format="PNG")
    prompt = "Reply with JSON {\"ok\": true} to confirm that this text and tiny image were received."

    class CheckResult(BaseModel):
        ok: bool

    try:
        result = provider.generate_json(prompt, CheckResult, buffer.getvalue(), "image/png")
        return bool(CheckResult.model_validate(result).ok), provider.model_for(image=True)
    except Exception:
        return False, provider.model_for(image=True)
