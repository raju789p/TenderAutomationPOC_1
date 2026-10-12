"""Chunk source IR and validate that a plan only references exact source ids."""

from __future__ import annotations

import re
from collections import Counter
from typing import Any

import yaml

from poc.convert.plan_schema import Plan, PlanBlock, PlanSection


_BLOCK_TYPE = {"figure": "image", "page_number": "paragraph"}


def target_for_canonical(canonical: str | None, target_config: dict[str, Any]) -> str:
    """Map a canonical section to the configured target section id."""
    if canonical:
        for section in target_config["sections"]:
            if canonical in section["accepts"]:
                return section["id"]
    return "unclassified"


def chunk_elements(elements: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Partition ordered source elements into preamble and top-level heading chunks."""
    chunks: list[dict[str, Any]] = []
    current: dict[str, Any] = {"source_heading_id": None, "elements": []}
    for element in elements:
        if element["type"] == "heading" and int(element.get("level", 1)) == 1:
            if current["elements"]:
                chunks.append(current)
            current = {"source_heading_id": element["id"], "elements": []}
        current["elements"].append(element)
    if current["elements"]:
        chunks.append(current)
    return chunks


def validate_chunk_plan(plan: Plan, chunk: dict[str, Any]) -> PlanSection:
    """Reject missing, duplicated, invented, mis-typed, or reordered source ids."""
    expected = chunk["elements"]
    if len(plan.sections) != 1:
        raise ValueError(f"expected exactly one plan section, got {len(plan.sections)}")
    section = plan.sections[0]
    if section.source_heading_id != chunk["source_heading_id"]:
        raise ValueError("source_heading_id does not match this chunk")
    expected_ids = [element["id"] for element in expected]
    actual_ids = [block.source_id for block in section.blocks]
    counts = Counter(actual_ids)
    duplicates = sorted(item for item, count in counts.items() if count > 1)
    invented = sorted(set(actual_ids) - set(expected_ids))
    missing = sorted(set(expected_ids) - set(actual_ids))
    if duplicates or invented or missing:
        raise ValueError(f"invalid element coverage; missing={missing}; duplicated={duplicates}; invented={invented}")
    index_by_id = {element["id"]: i for i, element in enumerate(expected)}
    if [index_by_id[item] for item in actual_ids] != sorted(index_by_id[item] for item in actual_ids):
        raise ValueError("source order must be preserved within the chunk")
    for block, element in zip(section.blocks, expected):
        expected_type = _BLOCK_TYPE.get(element["type"], element["type"])
        if block.block_type != expected_type:
            raise ValueError(f"block type mismatch for {block.source_id}: expected {expected_type}")
    return section


def fallback_section(chunk: dict[str, Any], classification_config: dict[str, Any], target_config: dict[str, Any]) -> PlanSection:
    """Create deterministic rule-only placement for one failed chunk."""
    headings = [e for e in chunk["elements"] if e["type"] == "heading" and int(e.get("level", 1)) == 1]
    title = headings[0].get("title", "") if headings else ""
    normalized = " ".join(title.casefold().split())
    matches = {
        rule["canonical_type"]
        for rule in classification_config.get("section_rules", [])
        if any(" ".join(str(keyword).casefold().split()) in normalized for keyword in rule["keywords"])
    }
    canonical = next(iter(matches)) if len(matches) == 1 else None
    target = target_for_canonical(canonical, target_config)
    blocks = [PlanBlock(source_id=e["id"], block_type=_BLOCK_TYPE.get(e["type"], e["type"])) for e in chunk["elements"]]
    return PlanSection(target_section=target, source_heading_id=chunk["source_heading_id"], blocks=blocks)


def renderer_assignments(sections: list[PlanSection]) -> dict[str, dict[str, Any]]:
    """Build element-id keyed targets and stable order values for the renderer."""
    assignments: dict[str, dict[str, Any]] = {}
    counters: Counter[str] = Counter()
    for section in sections:
        for block in section.blocks:
            target = section.target_section
            assignments[block.source_id] = {"target_section": target, "order_index": counters[target]}
            counters[target] += 1
    return assignments


def assemble_by_id(elements: list[dict[str, Any]], sections: list[PlanSection]) -> list[dict[str, Any]]:
    """Resolve the validated plan against IR records, retaining their exact source values."""
    by_id = {element["id"]: element for element in elements}
    planned_ids = [block.source_id for section in sections for block in section.blocks]
    if Counter(planned_ids) != Counter(by_id.keys()):
        raise ValueError("Cannot assemble plan: ids do not match the source IR exactly")
    return [by_id[source_id] for source_id in by_id]


def compare_with_rules(sections: list[PlanSection], elements: list[dict[str, Any]], classification_config: dict[str, Any], target_config: dict[str, Any]) -> list[str]:
    """List source ids whose accepted LLM destination differs from heading-rule fallback."""
    by_id = {e["id"]: e for e in elements}
    section_by_id = {block.source_id: section.target_section for section in sections for block in section.blocks}
    chunk_lookup = {e["id"]: chunk for chunk in chunk_elements(elements) for e in chunk["elements"]}
    misplaced: list[str] = []
    for source_id, element in by_id.items():
        chunk = chunk_lookup[source_id]
        rule_section = fallback_section(chunk, classification_config, target_config).target_section
        if section_by_id.get(source_id) != rule_section:
            misplaced.append(source_id)
    return misplaced

