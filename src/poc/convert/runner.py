"""C1 conversion orchestration, audit output, and cached comparison helpers."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from poc.convert.assemble import assemble_by_id, chunk_elements, compare_with_rules, renderer_assignments, validate_chunk_plan
from poc.convert.graph import plan_chunk
from poc.convert.plan_schema import Plan, PlanSection
from poc.convert.planner import MockPlanProvider, ProviderPlanAdapter, compact_planner_instructions, element_preview, make_prompt
from poc.extract import _read_config, extract_document
from poc.llm.providers import create_provider
from poc.llm.service import LLMService
from poc.llm.settings import LLMSettings, load_settings
from poc.render_docx import ROOT, render_document
from poc.verify import verify_document


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_") or "document"


def _classification_for_target(target_id: str, target_config: dict[str, Any]) -> str | None:
    for section in target_config["sections"]:
        if section["id"] == target_id:
            return section["accepts"][0] if len(section["accepts"]) == 1 else None
    return None


def _restore_matching_figure_captions(payload: dict[str, Any], root: Path) -> int:
    """Reuse saved figure descriptions only when the full source PDF hash matches."""
    saved_by_hash: dict[str, dict[str, Any]] = {}
    for doc_id in ("waterfall", "kanban"):
        path = root / "data/work" / doc_id / "elements.json"
        if not path.is_file():
            continue
        saved = json.loads(path.read_text(encoding="utf-8"))
        if saved.get("source_sha256") != payload.get("source_sha256"):
            continue
        for item in saved.get("elements", []):
            if item.get("type") == "figure" and item.get("ai_status") == "complete" and item.get("ai"):
                saved_by_hash[item.get("sha256", "")] = item["ai"]
    reused = 0
    for element in payload.get("elements", []):
        if element.get("type") == "figure" and element.get("sha256") in saved_by_hash:
            element["ai"] = saved_by_hash[element["sha256"]]
            element["ai_status"] = "complete"
            reused += 1
    return reused


def _answer_key_override_for_input(input_pdf: Path, root: Path, doc_id: str) -> dict[str, Any]:
    """Use the existing answer-key entry only for a configured source filename."""
    manifest_path = root / "config/documents.yaml"
    key_path = root / "docs/answer_key.json"
    if not manifest_path.is_file() or not key_path.is_file():
        return {doc_id: {"section_types": {}, "image_tokens": {}}}
    manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))["documents"]
    answer_key = json.loads(key_path.read_text(encoding="utf-8"))
    for item in manifest:
        if Path(item["source_file"]).name == input_pdf.name and item["doc_id"] in answer_key:
            return {doc_id: {
                "section_types": {},
                "image_tokens": answer_key[item["doc_id"]].get("image_tokens", {}),
                "target_section_types": answer_key[item["doc_id"]].get("section_types", {}),
            }}
    return {doc_id: {"section_types": {}, "image_tokens": {}}}


def _target_mapping_metrics(sections: list[PlanSection], elements: list[dict[str, Any]], answer_key: dict[str, Any], target_config: dict[str, Any]) -> dict[str, Any]:
    """Compare planned target sections with answer-key canonical targets when available."""
    expected = answer_key.get("target_section_types", answer_key.get("section_types", {}))
    headings = {str(element.get("number")): element for element in elements if element.get("type") == "heading" and int(element.get("level", 1)) == 1}
    actual = {section.source_heading_id: section.target_section for section in sections if section.source_heading_id}
    section_for_type = {canonical: target["id"] for target in target_config["sections"] for canonical in target["accepts"]}
    comparisons = []
    for number, canonical in expected.items():
        heading = headings.get(str(number))
        expected_target = section_for_type.get(canonical)
        actual_target = actual.get(heading["id"]) if heading else None
        comparisons.append({
            "element_id": heading["id"] if heading else None,
            "number": str(number), "expected_type": canonical,
            "expected_target_section": expected_target,
            "actual_target_section": actual_target,
            "correct": actual_target == expected_target,
        })
    correct = sum(item["correct"] for item in comparisons)
    return {
        "status": "measured" if comparisons else "NOT MEASURED",
        "correct": correct, "total": len(comparisons),
        "accuracy": correct / len(comparisons) if comparisons else None,
        "comparisons": comparisons,
        "note": "Target-section match; canonical subtype is not inferred when a target section accepts multiple types.",
    }


def _classification_payload(doc_id: str, elements: list[dict[str, Any]], sections: list[PlanSection], target_config: dict[str, Any]) -> dict[str, Any]:
    target_by_heading = {section.source_heading_id: section.target_section for section in sections if section.source_heading_id}
    items = []
    inherited: str | None = None
    for element in elements:
        if element.get("type") != "heading":
            continue
        if int(element.get("level", 1)) == 1:
            canonical = _classification_for_target(target_by_heading.get(element["id"], "unclassified"), target_config)
            inherited = canonical
        else:
            canonical = inherited
        item = {
            "heading_id": element["id"], "number": element.get("number"),
            "title": element.get("title", ""), "canonical_type": canonical,
            "method": "llm-plan" if element.get("level", 1) == 1 else "inherited",
            "status": "complete" if canonical else "failed",
        }
        items.append(item)
    return {"doc_id": doc_id, "items": items}


def _all_text_ids(sections: list[PlanSection]) -> list[str]:
    return [block.source_id for section in sections for block in section.blocks]


def _write_report(path: Path, *, doc_id: str, source_name: str, metrics: dict[str, Any], call_count: int, retries: int, fallbacks: list[dict[str, Any]], misplaced: list[str], saved_captions_reused: int, target_mapping: dict[str, Any]) -> None:
    lines = [
        f"# Conversion report — {source_name}", "",
        "## Verifier results", "",
        f"- Defects: {len(metrics.get('defects', []))}",
        f"- Text word recall: {metrics.get('text', {}).get('word_recall')}",
        f"- Tables matching: {metrics.get('tables', {}).get('matching_count')}/{metrics.get('tables', {}).get('expected_count')}",
        f"- Headings matched: {metrics.get('headings', {}).get('matched_count')}/{metrics.get('headings', {}).get('source_count')}",
        f"- Images preserved: {metrics.get('images', {}).get('docx_media_file_count')}/{metrics.get('images', {}).get('source_display_image_count')} (hash set equal={metrics.get('images', {}).get('set_equal')})",
        f"- Target-section mapping: {target_mapping['correct']}/{target_mapping['total']}" if target_mapping["status"] == "measured" else "- Target-section mapping: NOT MEASURED (no matching answer-key entry)",
        "- Canonical subtype mapping: NOT MEASURED (the plan schema selects target sections, some of which accept multiple canonical types)",
        "", "## Planner run", "",
        f"- Provider calls (uncached): {call_count}", f"- Planner retries: {retries}",
        f"- Fallback chunks: {len(fallbacks)}", f"- Source document id: `{doc_id}`", "",
        f"- Matching saved image captions reused: {saved_captions_reused}", "",
        "## Fallbacks", "",
    ]
    if fallbacks:
        lines.extend(f"- `{item['source_heading_id'] or 'preamble'}`: {item['reason']}" for item in fallbacks)
    else:
        lines.append("None.")
    lines.extend(["", "## Plan differences from rule baseline", "", "These ids differ from existing keyword-rule placement; this is a diagnostic comparison and not a semantic correctness verdict.", ""])
    lines.extend(f"- `{element_id}`" for element_id in misplaced) if misplaced else lines.append("None.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def convert_pdf(
    input_pdf: Path,
    out_dir: Path,
    provider_name: str = "mock",
    *,
    root: Path | None = None,
    model_override: Any | None = None,
    rule_only: bool = False,
) -> dict[str, Any]:
    """Extract, plan, validate, render, and verify one PDF without regenerating content."""
    root = root or ROOT
    input_pdf = Path(input_pdf).resolve()
    if not input_pdf.is_file():
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")
    source_hash = hashlib.sha256(input_pdf.read_bytes()).hexdigest()
    base_name = _slug(input_pdf.stem)
    doc_id = f"c1_{base_name}_{source_hash[:8]}"
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    output_path = out_dir / f"{base_name}_converted.docx"
    extraction_config = _read_config(root / "config/extraction.yaml")
    extract_document(doc_id, input_pdf, root / "data/work", extraction_config, root / "docs/challenges_log.md")
    doc_dir = root / "data/work" / doc_id
    payload = json.loads((doc_dir / "elements.json").read_text(encoding="utf-8"))
    elements = payload["elements"]
    saved_captions_reused = _restore_matching_figure_captions(payload, root)
    if saved_captions_reused:
        (doc_dir / "elements.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    target_config = yaml.safe_load((root / "config/target_format.yaml").read_text(encoding="utf-8"))
    classification_config = yaml.safe_load((root / "config/classification.yaml").read_text(encoding="utf-8"))
    instructions = compact_planner_instructions(target_config)
    chunks = chunk_elements(elements)
    outline = [
        {"id": element["id"], "title": element.get("title", "")[:100], "level": element.get("level", 1)}
        for element in elements if element.get("type") == "heading" and int(element.get("level", 1)) == 1
    ]
    call_log = out_dir / f"{base_name}_llm_calls.json"
    planner_retries = 0
    service = None
    if not rule_only and model_override is None:
        if provider_name == "mock":
            settings = LLMSettings(provider="mock", model="mock-plan-v1", api_key=None, rpm=10, max_retries=0)
            provider = MockPlanProvider()
        else:
            settings = load_settings(provider_override=provider_name, root=root)
            provider = create_provider(settings)
        service = LLMService(provider, settings, root / "data/work/llm_cache")
    sections: list[PlanSection] = []
    fallback_records = []
    chunk_diagnostics = []
    for chunk in chunks:
        ids = [element["id"] for element in chunk["elements"]]
        model = model_override
        if not rule_only and model is None:
            model = ProviderPlanAdapter(service, call_log, ids)
        state = {
            "chunk": chunk, "outline": outline, "instructions": instructions,
            "classification_config": classification_config, "target_config": target_config,
        }
        if rule_only:
            from poc.convert.assemble import fallback_section
            section = fallback_section(chunk, classification_config, target_config)
            fallback_records.append({"source_heading_id": chunk["source_heading_id"], "reason": "Mode B rule-only placement"})
            chunk_diagnostics.append({"source_heading_id": chunk["source_heading_id"], "attempts": 0, "validation_retries": 0, "fallback_used": True})
        else:
            result = plan_chunk(model, state)
            section = result["section"]
            planner_retries += max(0, int(result.get("attempts", 1)) - 1)
            chunk_diagnostics.append({
                "source_heading_id": chunk["source_heading_id"],
                "attempts": int(result.get("attempts", 1)),
                "validation_retries": max(0, int(result.get("attempts", 1)) - 1),
                "fallback_used": bool(result.get("fallback_used", False)),
            })
            if result.get("fallback_used"):
                fallback_records.append({"source_heading_id": chunk["source_heading_id"], "reason": result.get("fallback_reason", "validation failed")})
        sections.append(section)
    flattened_ids = _all_text_ids(sections)
    expected_ids = [element["id"] for element in elements]
    if Counter(flattened_ids) != Counter(expected_ids):
        raise ValueError("Combined plan does not contain every source element exactly once")
    # The LLM plan may not move source elements backwards within a target section.
    source_position = {element_id: index for index, element_id in enumerate(expected_ids)}
    per_target: dict[str, list[int]] = {}
    for section in sections:
        per_target.setdefault(section.target_section, []).extend(source_position[block.source_id] for block in section.blocks)
    order_errors = [target for target, positions in per_target.items() if positions != sorted(positions)]
    if order_errors:
        raise ValueError(f"Combined plan reordered elements within target section(s): {order_errors}")
    assignments = renderer_assignments(sections)
    assembled_elements = assemble_by_id(elements, sections)
    plan_path = out_dir / f"{base_name}_plan.json"
    plan_payload = {
        "doc_id": doc_id, "prompt_version": "c1-plan-v1", "rule_only": rule_only,
        "saved_figure_captions_reused": saved_captions_reused,
        "sections": [section.model_dump(mode="json") for section in sections],
        "chunk_diagnostics": chunk_diagnostics,
        "fallbacks": fallback_records,
    }
    plan_path.write_text(json.dumps(plan_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    class_path = doc_dir / "classification.json"
    class_path.write_text(json.dumps(_classification_payload(doc_id, elements, sections, target_config), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    ledger = render_document(doc_id, output_path=output_path, plan_assignments=assignments, source_elements=assembled_elements)
    answer_key_override = _answer_key_override_for_input(input_pdf, root, doc_id)
    verification = verify_document(doc_id, output_path, answer_key_override=answer_key_override)
    target_mapping = _target_mapping_metrics(sections, elements, answer_key_override[doc_id], target_config)
    misplaced = compare_with_rules(sections, elements, classification_config, target_config)
    provider_calls = service.stats.provider_calls if service else 0
    retries = planner_retries + (service.stats.retries if service else 0)
    verification_payload = {"doc_id": doc_id, **{key: value for key, value in verification.items() if key != "docx_file"}}
    _write_report(
        out_dir / f"{base_name}_report.md", doc_id=doc_id, source_name=input_pdf.name,
        metrics=verification_payload, call_count=provider_calls, retries=retries,
        fallbacks=fallback_records, misplaced=misplaced, saved_captions_reused=saved_captions_reused,
        target_mapping=target_mapping,
    )
    return {
        "doc_id": doc_id, "output_docx": str(output_path), "plan_path": str(plan_path),
        "report_path": str(out_dir / f"{base_name}_report.md"), "call_log": str(call_log),
        "calls": provider_calls, "retries": retries, "fallbacks": fallback_records,
        "saved_captions_reused": saved_captions_reused,
        "misplaced_ids": misplaced, "target_mapping": target_mapping,
        "ledger": ledger, "verification": verification_payload,
    }


def plan_check_first_chunk(
    input_pdf: Path,
    out_dir: Path,
    provider_name: str,
    *,
    root: Path | None = None,
) -> dict[str, Any]:
    """Make one planner request and locally validate it, without rendering a document."""
    root = root or ROOT
    input_pdf = Path(input_pdf).resolve()
    if not input_pdf.is_file():
        raise FileNotFoundError(f"Input PDF not found: {input_pdf}")
    source_hash = hashlib.sha256(input_pdf.read_bytes()).hexdigest()
    doc_id = f"c1_probe_{_slug(input_pdf.stem)}_{source_hash[:8]}"
    extract_document(
        doc_id, input_pdf, root / "data/work", _read_config(root / "config/extraction.yaml"),
        root / "docs/challenges_log.md",
    )
    payload = json.loads((root / "data/work" / doc_id / "elements.json").read_text(encoding="utf-8"))
    chunks = chunk_elements(payload["elements"])
    if not chunks:
        raise ValueError("Input PDF produced no planning chunks")
    target_config = yaml.safe_load((root / "config/target_format.yaml").read_text(encoding="utf-8"))
    settings = load_settings(provider_override=provider_name, root=root)
    provider = create_provider(settings)
    service = LLMService(provider, settings, root / "data/work/llm_cache")
    chunk = chunks[0]
    ids = [item["id"] for item in chunk["elements"]]
    adapter = ProviderPlanAdapter(service, Path(out_dir) / f"{_slug(input_pdf.stem)}_probe_llm_calls.json", ids)
    prompt = make_prompt(compact_planner_instructions(target_config)) | adapter.with_structured_output(Plan)
    outline = [
        {"id": item["id"], "title": item.get("title", "")[:100], "level": item.get("level", 1)}
        for item in payload["elements"] if item.get("type") == "heading" and int(item.get("level", 1)) == 1
    ]
    plan = prompt.invoke({
        "outline": outline,
        "chunk_json": [element_preview(item) for item in chunk["elements"]],
        "validation_errors": "none",
    })
    section = validate_chunk_plan(plan, chunk)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    plan_path = out_dir / f"{_slug(input_pdf.stem)}_first_chunk_plan.json"
    plan_path.write_text(json.dumps(section.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "plan_path": str(plan_path), "calls": service.stats.provider_calls,
        "cache_hits": service.stats.cache_hits, "source_heading_id": section.source_heading_id,
        "element_count": len(ids),
    }


def compare_all(root: Path | None = None) -> dict[str, Any]:
    """Run Mode A and rule-only Mode B on the configured originals and report verifier parity."""
    root = root or ROOT
    manifest = yaml.safe_load((root / "config/documents.yaml").read_text(encoding="utf-8"))["documents"]
    provider_name = load_settings(root=root).provider
    output_root = root / "data/output/c1_mode_comparison"
    entries: dict[str, Any] = {}
    for item in manifest:
        input_pdf = root / "data/input" / item["source_file"]
        mode_a = convert_pdf(input_pdf, output_root / "mode_a", provider_name, root=root)
        mode_b = convert_pdf(input_pdf, output_root / "mode_b", "mock", root=root, rule_only=True)
        entries[item["doc_id"]] = {
            "mode_a": _comparison_metrics(mode_a),
            "mode_b": _comparison_metrics(mode_b),
            "mode_a_calls": mode_a["calls"],
            "mode_a_retries": mode_a["retries"],
            "mode_a_fallback_chunks": len(mode_a["fallbacks"]),
        }
    payload = {
        "method": "Mode A uses the validated LLM plan; Mode B uses the existing configured keyword rules. Both are measured by the existing independent verifier.",
        "provider": provider_name,
        "documents": entries,
        "limits": [
            "2 documents only.", "The target is our own template.",
            "LLM output depends on the model and pinned prompt version.",
            "Mode A results are from the cached run produced by this command.",
        ],
    }
    metrics_path = root / "data/output/mode_comparison.json"
    metrics_path.parent.mkdir(parents=True, exist_ok=True)
    metrics_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = [
        "# Mode A / Mode B Comparison", "",
        "| Document | Mode | Text recall | Tables | Headings | Images | Target mapping | Keywords strict / normalised | Unplaced | Defects | Provider calls | Retries | Fallback chunks |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for doc_id, doc in entries.items():
        for mode in ("mode_a", "mode_b"):
            result = doc[mode]
            report.append(
                f"| {doc_id} | {mode} | {result['text_recall']} | {result['tables']} | {result['headings']} | {result['images']} | {result['target_mapping']} | {result['keywords_strict']} / {result['keywords_normalised']} | {result['unplaced']} | {result['defects']} | {doc['mode_a_calls'] if mode == 'mode_a' else 0} | {doc['mode_a_retries'] if mode == 'mode_a' else 0} | {doc['mode_a_fallback_chunks'] if mode == 'mode_a' else '—'} |"
            )
    report.extend(["", "## Limits of this evidence", "", *[f"- {entry}" for entry in payload["limits"]], ""])
    report_path = root / "docs/MODE_COMPARISON.md"
    report_path.write_text("\n".join(report), encoding="utf-8")
    return payload


def _comparison_metrics(result: dict[str, Any]) -> dict[str, Any]:
    metrics = result["verification"]
    strict = metrics.get("image_transcription", {}).get("strict", {})
    normalised = metrics.get("image_transcription", {}).get("normalised", {})
    target_mapping = result.get("target_mapping", {})
    return {
        "text_recall": metrics.get("text", {}).get("word_recall"),
        "tables": f"{metrics.get('tables', {}).get('matching_count')}/{metrics.get('tables', {}).get('expected_count')}",
        "headings": f"{metrics.get('headings', {}).get('matched_count')}/{metrics.get('headings', {}).get('source_count')}",
        "images": f"{metrics.get('images', {}).get('docx_media_file_count')}/{metrics.get('images', {}).get('source_display_image_count')}",
        "defects": len(metrics.get("defects", [])),
        "unplaced": metrics.get("ledger", {}).get("counts", {}).get("unplaced"),
        "target_mapping": f"{target_mapping.get('correct')}/{target_mapping.get('total')}" if target_mapping.get("status") == "measured" else "NOT MEASURED",
        "keywords_strict": f"{strict.get('matched')}/{strict.get('total')}",
        "keywords_normalised": f"{normalised.get('matched')}/{normalised.get('total')}",
        "verifier": metrics,
    }

