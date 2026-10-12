"""Run the existing extractor, renderer, and verifier on the isolated M7 set."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]


def _rule(title: str, rules: dict[str, Any]) -> str | None:
    normalized = " ".join(title.casefold().split())
    matches = {
        item["canonical_type"]
        for item in rules["section_rules"]
        if any(" ".join(keyword.casefold().split()) in normalized for keyword in item["keywords"])
    }
    return next(iter(matches)) if len(matches) == 1 else None


def _classifications(payload: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    """Apply only configured rules and parent inheritance; unknowns remain absent/unclassified."""
    records: list[dict[str, Any]] = []
    parent_types: dict[str, str] = {}
    for element in payload["elements"]:
        if element["type"] != "heading":
            continue
        number = element.get("number") or ""
        if element["level"] == 1:
            canonical = _rule(element["title"], config)
            if canonical:
                parent_types[number.split(".", 1)[0]] = canonical
        else:
            canonical = parent_types.get(number.split(".", 1)[0])
        if canonical:
            records.append({
                "heading_id": element["id"], "number": number, "title": element["title"],
                "canonical_type": canonical, "method": "rule", "status": "complete",
            })
    return records


def run_all(root: Path = ROOT) -> dict[str, Any]:
    """Run the baseline pipeline in a M7-only runtime and output directory."""
    base = root / "data/m7"
    runtime = base / "runtime"
    work_root = runtime / "data/work"
    output_root = base / "output"
    (runtime / "config").mkdir(parents=True, exist_ok=True)
    (runtime / "docs").mkdir(parents=True, exist_ok=True)
    work_root.mkdir(parents=True, exist_ok=True)
    output_root.mkdir(parents=True, exist_ok=True)
    for filename in ("extraction.yaml", "classification.yaml", "target_format.yaml"):
        shutil.copyfile(root / "config" / filename, runtime / "config" / filename)
    shutil.copyfile(root / "config" / "classification.yaml", runtime / "config/classification.yaml")
    manifest = yaml.safe_load((root / "config/documents_m7.yaml").read_text(encoding="utf-8"))["documents"]
    docs_for_key: dict[str, Any] = {}
    truths: dict[str, dict[str, Any]] = {}
    for item in manifest:
        doc_id = item["doc_id"]
        truth = json.loads((base / "truth" / f"{doc_id}.json").read_text(encoding="utf-8"))
        truths[doc_id] = truth
        docs_for_key[doc_id] = {
            "section_types": truth["section_types"],
            "image_tokens": {f"fixture_{i + 1}": [] for i, _ in enumerate(truth["images"])},
        }
    (runtime / "docs/answer_key.json").write_text(json.dumps(docs_for_key, indent=2) + "\n", encoding="utf-8")
    (runtime / "docs/challenges_log.md").write_text("# M7 runtime challenges\n", encoding="utf-8")

    import poc.extract as extractor
    import poc.render_docx as renderer
    import poc.verify as verifier

    renderer.ROOT = runtime
    verifier.ROOT = runtime
    extraction_config = yaml.safe_load((runtime / "config/extraction.yaml").read_text(encoding="utf-8"))
    classification_config = yaml.safe_load((runtime / "config/classification.yaml").read_text(encoding="utf-8"))
    statuses: dict[str, dict[str, Any]] = {}
    for item in manifest:
        doc_id = item["doc_id"]
        source = base / "inputs" / Path(item["source_file"]).name
        try:
            extracted = extractor.extract_document(doc_id, source, work_root, extraction_config, runtime / "docs/challenges_log.md")
            elements_path = work_root / doc_id / "elements.json"
            payload = json.loads(elements_path.read_text(encoding="utf-8"))
            classified = _classifications(payload, classification_config)
            class_path = work_root / doc_id / "classification.json"
            class_path.write_text(json.dumps({"doc_id": doc_id, "items": classified}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
            rendered = renderer.render_document(doc_id, output_root / f"{doc_id}.docx")
            verified = verifier.verify_document(doc_id, output_root / f"{doc_id}.docx")
            statuses[doc_id] = {
                "status": "complete", "extraction": extracted,
                "classification_count": len(classified), "render": rendered,
                "verification": verified,
            }
        except Exception as error:  # Baseline records crashes as evidence and continues.
            statuses[doc_id] = {"status": "crashed", "crash": f"{type(error).__name__}: {error}"}
    (output_root / "m7_pipeline.json").write_text(
        json.dumps({"documents": statuses}, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    return {"root": root, "manifest": manifest, "truths": truths, "statuses": statuses}


if __name__ == "__main__":
    summary = run_all()
    for doc_id, result in summary["statuses"].items():
        print(f"{doc_id}: {result['status']}")
        if result["status"] == "crashed":
            print(result["crash"])
