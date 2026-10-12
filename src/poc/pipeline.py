"""Offline, idempotent orchestration for the M6 demonstration."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import yaml

from poc.extract import extract_all
from poc.render_docx import ROOT, render_all
from poc.verify import verify_all
from poc.report import write_accuracy_report, write_summary

LOGGER = logging.getLogger(__name__)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _reuse_saved_enrichment(root: Path, snapshots: dict[str, dict[str, Any]]) -> dict[str, int]:
    """Restore matching saved AI results and classifications without loading settings or providers."""
    counts = {"figures_reused": 0, "figures_missing": 0, "classifications_reused": 0, "classifications_missing": 0}
    rules = yaml.safe_load((root / "config/classification.yaml").read_text(encoding="utf-8"))
    for doc_id, snapshot in snapshots.items():
        doc_dir = root / "data/work" / doc_id
        elements_path = doc_dir / "elements.json"
        document = _read_json(elements_path)
        old_elements = {element["id"]: element for element in snapshot.get("elements", [])}
        for element in document["elements"]:
            previous = old_elements.get(element["id"])
            if element["type"] == "figure":
                if previous and previous.get("sha256") == element.get("sha256") and previous.get("ai") and previous.get("ai_status") == "complete":
                    element["ai"] = previous["ai"]
                    element["ai_status"] = "complete"
                    element["ai_error"] = None
                    counts["figures_reused"] += 1
                else:
                    element["ai"] = None
                    element["ai_status"] = "failed"
                    element["ai_error"] = "No matching saved enrichment result; provider calls disabled in M6 run"
                    counts["figures_missing"] += 1
        elements_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

        old_classification_path = doc_dir / "classification.json"
        old_classifications = {}
        if old_classification_path.is_file():
            old_classifications = {
                item["heading_id"]: item
                for item in _read_json(old_classification_path).get("items", [])
            }
        items: list[dict[str, Any]] = []
        inherited: dict[str, str] = {}
        for element in document["elements"]:
            if element["type"] != "heading":
                continue
            previous = old_classifications.get(element["id"])
            if previous and previous.get("title") == element["title"] and previous.get("number") == element.get("number") and previous.get("status") == "complete":
                result = dict(previous)
                counts["classifications_reused"] += 1
            else:
                number = element.get("number") or ""
                if element.get("level", 1) > 1:
                    parent = number.split(".", 1)[0]
                    canonical = inherited.get(parent)
                    method = "rule"
                else:
                    normalized = " ".join(element["title"].casefold().split())
                    matches = {
                        rule["canonical_type"]
                        for rule in rules["section_rules"]
                        if any(" ".join(keyword.casefold().split()) in normalized for keyword in rule["keywords"])
                    }
                    canonical = next(iter(matches)) if len(matches) == 1 else None
                    method = "rule"
                    if canonical:
                        inherited[number.split(".", 1)[0]] = canonical
                if element.get("level", 1) > 1 and canonical:
                    result = {"heading_id": element["id"], "number": element.get("number"), "title": element["title"], "canonical_type": canonical, "method": "rule", "status": "complete"}
                elif element.get("level", 1) == 1 and canonical:
                    result = {"heading_id": element["id"], "number": element.get("number"), "title": element["title"], "canonical_type": canonical, "method": method, "status": "complete"}
                else:
                    result = {"heading_id": element["id"], "number": element.get("number"), "title": element["title"], "canonical_type": None, "method": method, "status": "failed", "error": "No saved classification or unambiguous configured rule; provider calls disabled in M6 run"}
                    counts["classifications_missing"] += 1
            if result.get("status") == "complete" and element.get("level", 1) == 1:
                inherited[element.get("number", "").split(".", 1)[0]] = result["canonical_type"]
            items.append(result)
        old_classification_path.write_text(json.dumps({"doc_id": doc_id, "items": items}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return counts


def run_all(provider_name: str, root: Path = ROOT) -> dict[str, Any]:
    """Run extraction through reporting with saved enrichment only and zero provider calls."""
    documents_config = yaml.safe_load((root / "config/documents.yaml").read_text(encoding="utf-8"))["documents"]
    snapshots = {}
    for item in documents_config:
        elements_path = root / "data/work" / item["doc_id"] / "elements.json"
        snapshots[item["doc_id"]] = _read_json(elements_path) if elements_path.is_file() else {"elements": []}
    LOGGER.info("Extracting configured documents; enrichment is cache-only (provider=%s, calls=0)", provider_name)
    extract_all(root=root)
    reuse = _reuse_saved_enrichment(root, snapshots)
    LOGGER.info("Saved enrichment reused: %d figures; missing=%d; classifications missing=%d", reuse["figures_reused"], reuse["figures_missing"], reuse["classifications_missing"])
    render_all()
    verified = verify_all()
    write_accuracy_report(root / "data/output/metrics.json", root / "docs/accuracy_report.md")
    write_summary(root / "data/output/metrics.json", root / "docs/SUMMARY.md")
    documents = []
    for doc_id, metrics in verified["documents"].items():
        counts = metrics["ledger"]["counts"]
        documents.append({"doc_id": doc_id, "placed": counts["placed"], "regenerated": counts["regenerated"], "unplaced": counts["unplaced"], "defects": len(metrics["defects"])})
    overall = verified["overall"]
    return {
        "documents": documents,
        "overall": {
            "placed": overall["ledger"]["placed"],
            "regenerated": overall["ledger"]["regenerated"],
            "unplaced": overall["ledger"]["unplaced"],
            "defects": overall["defect_count"],
        },
        "enrichment": reuse,
        "provider_calls": 0,
    }
