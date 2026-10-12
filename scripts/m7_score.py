"""Score the untouched M7 baseline against generator-owned ground truth."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
TOKEN = re.compile(r"[\w]+(?:['’][\w]+)*", re.UNICODE)


def _tokens(text: str) -> list[str]:
    return [word.casefold() for word in TOKEN.findall(text)]


def _normal(text: str) -> str:
    return " ".join(text.split()).casefold()


def _element_text(element: dict[str, Any]) -> str:
    kind = element["type"]
    if kind == "heading":
        return " ".join(piece for piece in (element.get("number"), element.get("title")) if piece)
    if kind in {"paragraph", "bullet"}:
        return "".join(span["text"] for span in element.get("spans", []))
    if kind == "table":
        return " ".join(cell for row in element.get("rows", []) for cell in row)
    if kind == "page_number":
        return element.get("value", "")
    return ""


def _table_signature(rows: list[list[str]]) -> tuple[tuple[str, ...], ...]:
    return tuple(tuple(_normal(cell) for cell in row) for row in rows)


def _failure(category: str, doc_id: str, detail: str, cause: str, disposition: str) -> dict[str, str]:
    return {"document": doc_id, "category": category, "detail": detail, "likely_root_cause": cause, "recommended_scope": disposition}


def _score_document(doc_id: str, truth: dict[str, Any], status: dict[str, Any], root: Path) -> dict[str, Any]:
    runtime = root / "data/m7/runtime"
    work_dir = runtime / "data/work" / doc_id
    extraction_path = work_dir / "elements.json"
    failures: list[dict[str, str]] = []
    if status.get("status") != "complete" or not extraction_path.is_file():
        crash = status.get("crash", "No extraction output was produced")
        return {
            "status": "crashed", "crash": crash, "expected_pages": truth["page_count"],
            "text": {"status": "NOT MEASURED", "reason": "Pipeline crashed before producing elements.json."},
            "headings": {"matched": 0, "expected": len(truth["headings"])},
            "tables": {"matched": 0, "expected": len(truth["tables"])},
            "images": {"actual_count": 0, "expected_count": len(truth["images"]), "hash_matches": 0},
            "mapping": {"correct": 0, "total": len(truth["section_types"])},
            "ledger": {"unplaced": None, "pending": None}, "header_footer_leakage": {"leaked": True},
            "failures": [_failure("crash", doc_id, crash, "The existing extraction/render path raised before completing; inspect the exception and the relevant extractor or renderer call path.", "generic fix or configuration change, after review")],
        }

    payload = json.loads(extraction_path.read_text(encoding="utf-8"))
    elements = payload["elements"]
    expected_text = Counter(_tokens("\n".join(page["text"] for page in truth["pages"])))
    actual_text = Counter(_tokens(" ".join(_element_text(element) for element in elements)))
    missing = expected_text - actual_text
    excess = actual_text - expected_text
    text = {
        "status": "no text extracted" if not actual_text else "measured",
        "expected_words": sum(expected_text.values()), "extracted_words": sum(actual_text.values()),
        "recalled_words": sum((expected_text & actual_text).values()),
        "recall": sum((expected_text & actual_text).values()) / sum(expected_text.values()) if expected_text else None,
        "missing_word_count": sum(missing.values()), "missing_words": dict(missing),
        "excess_word_count": sum(excess.values()), "excess_words": dict(excess),
    }

    expected_headings = Counter((item["level"], _normal(item["title"])) for item in truth["headings"])
    found_headings = Counter((element.get("level"), _normal(element.get("title", ""))) for element in elements if element["type"] == "heading")
    heading_matches = sum((expected_headings & found_headings).values())
    missing_headings = list((expected_headings - found_headings).elements())
    extra_headings = list((found_headings - expected_headings).elements())

    expected_tables = [_table_signature(item["cells"]) for item in truth["tables"]]
    found_tables = [_table_signature(element["rows"]) for element in elements if element["type"] == "table"]
    table_match_flags = []
    unused = list(found_tables)
    for expected in expected_tables:
        index = next((i for i, actual in enumerate(unused) if actual == expected), None)
        table_match_flags.append(index is not None)
        if index is not None:
            unused.pop(index)
    table_shape_matches = sum(
        any(len(actual) == len(expected) and all(len(actual_row) == len(expected_row) for actual_row, expected_row in zip(actual, expected)) for actual in found_tables)
        for expected in expected_tables
    )

    expected_image_hashes = Counter(item["sha256"] for item in truth["images"])
    figures = [element for element in elements if element["type"] == "figure"]
    actual_image_hashes = Counter(element["sha256"] for element in figures)
    image_matches = sum((expected_image_hashes & actual_image_hashes).values())
    expected_mapping = truth["section_types"]
    class_path = work_dir / "classification.json"
    classifications = json.loads(class_path.read_text(encoding="utf-8")).get("items", []) if class_path.is_file() else []
    actual_mapping = {item["number"]: item["canonical_type"] for item in classifications if "." not in str(item.get("number", ""))}
    expected_top_headings = [item for item in truth["headings"] if item["level"] == 1]
    mapping_comparisons = []
    for index, (number, expected) in enumerate(expected_mapping.items()):
        expected_heading = expected_top_headings[index] if index < len(expected_top_headings) else None
        detected = next((element for element in elements if element["type"] == "heading" and expected_heading and element["level"] == 1 and _normal(element["title"]) == _normal(expected_heading["title"])), None)
        actual = actual_mapping.get(str(detected.get("number"))) if detected else None
        actual = actual or ("unclassified" if detected else "not_extracted")
        mapping_comparisons.append({"number": number, "expected": expected, "actual": actual, "correct": actual == expected})
    mapping_correct = sum(item["correct"] for item in mapping_comparisons)
    dispositions = Counter(element.get("disposition", "pending") for element in elements)

    body_items = [element for element in elements if element["type"] in {"heading", "paragraph", "bullet"}]
    body_by_page: dict[int, list[str]] = {}
    for element in body_items:
        body_by_page.setdefault(element["page"], []).append(_normal(_element_text(element)))
    leaked_headers: list[dict[str, Any]] = []
    leaked_page_numbers: list[dict[str, Any]] = []
    page_number_elements = {(element["page"], str(element.get("value", ""))) for element in elements if element["type"] == "page_number"}
    for furniture in truth.get("page_furniture", []):
        page_no = furniture["page"]
        body = body_by_page.get(page_no, [])
        for field in ("header", "footer"):
            value = _normal(furniture[field])
            if any(value and value in item for item in body):
                leaked_headers.append({"page": page_no, "field": field, "text": furniture[field]})
        printed = str(furniture["page_number"])
        if any(item == printed for item in body) and (page_no, printed) not in page_number_elements:
            leaked_page_numbers.append({"page": page_no, "value": printed})

    verifier_metrics = status.get("verification", {})
    failures.extend(_derive_failures(doc_id, text, heading_matches, len(truth["headings"]), missing_headings, extra_headings,
                                    table_match_flags, len(truth["tables"]), len(found_tables), image_matches,
                                    len(truth["images"]), len(figures), mapping_correct, len(mapping_comparisons),
                                    dispositions, leaked_headers, leaked_page_numbers, truth))
    if text["status"] == "no text extracted":
        text["note"] = "no text extracted"
    return {
        "status": "complete", "source_pdf_sha256": truth["source_pdf_sha256"],
        "page_count": payload["page_count"], "expected_page_count": truth["page_count"],
        "text": text,
        "headings": {"matched": heading_matches, "expected": len(truth["headings"]), "actual": sum(found_headings.values()), "expected_items": truth["headings"], "actual_items": [{"page": element["page"], "title": element["title"], "level": element["level"], "number": element.get("number")} for element in elements if element["type"] == "heading"], "missing": missing_headings, "extra": extra_headings},
        "tables": {"shape_matches": table_shape_matches, "cell_matches": sum(table_match_flags), "expected": len(expected_tables), "actual": len(found_tables), "matches": table_match_flags, "expected_tables": [{"shape": table["shape"], "cells": table["cells"]} for table in truth["tables"]], "actual_tables": [{"element_id": element["id"], "page": element["page"], "shape": [len(element["rows"]), max((len(row) for row in element["rows"]), default=0)], "cells": element["rows"]} for element in elements if element["type"] == "table"]},
        "images": {"actual_count": len(figures), "expected_count": len(truth["images"]), "count_match": len(figures) == len(truth["images"]), "hash_matches": image_matches, "expected_hashes": dict(expected_image_hashes), "actual_hashes": dict(actual_image_hashes), "printed_words_expected": [word for image in truth["images"] for word in image["expected_printed_words"]], "printed_words_ocr_status": "NOT MEASURED — no OCR or image transcription was run"},
        "mapping": {"correct": mapping_correct, "total": len(mapping_comparisons), "accuracy": mapping_correct / len(mapping_comparisons) if mapping_comparisons else None, "comparisons": mapping_comparisons},
        "ledger": {"placed": dispositions["placed"], "regenerated": dispositions["regenerated"], "unplaced": dispositions["unplaced"], "pending": dispositions["pending"]},
        "header_footer_leakage": {"header_or_footer_leaks": leaked_headers, "page_number_leaks": leaked_page_numbers, "leaked": bool(leaked_headers or leaked_page_numbers)},
        "existing_verifier": {"defect_count": len(verifier_metrics.get("defects", [])), "defects": verifier_metrics.get("defects", []), "text_recall": verifier_metrics.get("text", {}).get("word_recall"), "table_matches": verifier_metrics.get("tables", {}).get("matching_count"), "image_hash_set_equal": verifier_metrics.get("images", {}).get("set_equal")},
        "failures": failures,
    }


def _derive_failures(doc_id: str, text: dict[str, Any], heading_matches: int, heading_expected: int,
                     missing_headings: list[Any], extra_headings: list[Any], table_flags: list[bool],
                     table_expected: int, table_actual: int, image_matches: int, image_expected: int,
                     image_actual: int, mapping_correct: int, mapping_total: int, dispositions: Counter[str],
                     leaked_headers: list[dict[str, Any]], leaked_pages: list[dict[str, Any]], truth: dict[str, Any]) -> list[dict[str, str]]:
    failures = []
    if text["missing_word_count"] or text["excess_word_count"]:
        failures.append(_failure("text", doc_id, f"Missing {text['missing_word_count']} words and excess {text['excess_word_count']} words.", "`src/poc/extract.py` builds text elements from PyMuPDF text blocks and line spans; `config/extraction.yaml` supplies the heading and bullet heuristics. Image-only text has no OCR path.", "generic extractor or configuration change; OCR is out of scope"))
    if heading_matches != heading_expected or missing_headings or extra_headings:
        if text["status"] == "no text extracted":
            cause = "`src/poc/extract.py` reads page text with PyMuPDF; these pages contain only raster images, so no heading text reaches the numbered-heading detector. OCR is out of scope."
            scope = "OCR is out of scope; no baseline fix applied"
        else:
            cause = "`src/poc/extract.py` numbered-heading detection is controlled by `config/extraction.yaml` (`heading.numbered_pattern`, `minimum_font_size_pt`); alternate wording/typography can fall through as paragraphs."
            scope = "generic heading detector improvement or document-specific configuration, measured only"
        failures.append(_failure("headings", doc_id, f"Matched {heading_matches}/{heading_expected}; missing={missing_headings}; extra={extra_headings}.", cause, scope))
    if table_actual != table_expected or not all(table_flags):
        failures.append(_failure("tables", doc_id, f"Cell-exact matches {sum(table_flags)}/{table_expected}; extracted {table_actual} tables.", "`src/poc/extract.py` calls pdfplumber `find_tables`; `config/extraction.yaml` selects the lines strategy and fixed snap/join tolerances, which cannot detect whitespace-aligned tables reliably or join split-page fragments.", "generic table detection/joining or configuration change, measured only"))
    if image_actual != image_expected or image_matches != image_expected:
        failures.append(_failure("images", doc_id, f"Image count {image_actual}/{image_expected}; exact hash matches {image_matches}/{image_expected}.", "`src/poc/extract.py` hashes extracted image streams; PDF image re-encoding and full-page rasterization can change byte identity relative to generator source bytes.", "generic provenance/hash handling or configuration change, measured only"))
    if mapping_correct != mapping_total:
        failures.append(_failure("section_mapping", doc_id, f"Correct {mapping_correct}/{mapping_total} expected top-level classifications.", "`src/poc/enrich.py` applies keyword rules from `config/classification.yaml`; the baseline runner deliberately skips LLM fallback, so unknown wording stays unclassified.", "classification configuration or generic rule coverage; no LLM used"))
    if dispositions["unplaced"] or dispositions["pending"]:
        failures.append(_failure("ledger", doc_id, f"Unplaced={dispositions['unplaced']}; pending={dispositions['pending']}.", "`src/poc/render_docx.py` places content only under a preceding heading with a canonical target section; unmatched headings leave elements without a destination.", "generic renderer or classification coverage; measured without fixes"))
    if leaked_headers or leaked_pages:
        failures.append(_failure("header_footer_leakage", doc_id, f"Header/footer leaks={leaked_headers}; page-number leaks={leaked_pages}.", "`config/extraction.yaml` classifies only isolated digit spans near the page bottom; `src/poc/extract.py` otherwise processes repeated furniture as ordinary page text.", "generic header/footer detection or configuration change"))
    if not any(image["expected_printed_words"] for image in truth["images"]):
        pass
    return failures


def _render_report(metrics: dict[str, Any]) -> str:
    documents = metrics["documents"]
    rows = ["| Document | Pages | Text recall | Headings | Tables shape/cells | Images count/hash | Mapping accuracy | Unplaced / pending | Verifier defects | Crashes | Header/footer leaks |", "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for doc_id, item in documents.items():
        recall = item["text"].get("recall")
        recall_text = "no text extracted" if item["text"].get("status") == "no text extracted" else "NOT MEASURED" if recall is None else f"{recall:.1%}"
        rows.append(f"| {doc_id} | {item.get('page_count', '—')}/{item.get('expected_page_count', '—')} | {recall_text} | {item['headings']['matched']}/{item['headings']['expected']} | {item['tables']['shape_matches']}/{item['tables']['expected']} shape; {item['tables']['cell_matches']}/{item['tables']['expected']} cells | {item['images']['actual_count']}/{item['images']['expected_count']}; {item['images']['hash_matches']}/{item['images']['expected_count']} hashes | {item['mapping']['correct']}/{item['mapping']['total']} | {item['ledger']['unplaced']} / {item['ledger']['pending']} | {item.get('existing_verifier', {}).get('defect_count', 'NOT MEASURED')} | {int(item['status'] == 'crashed')} | {len(item['header_footer_leakage'].get('header_or_footer_leaks', [])) + len(item['header_footer_leakage'].get('page_number_leaks', []))} |")
    failures = [failure for item in documents.values() for failure in item.get("failures", [])]
    verifier_causes = {
        "placement_ledger_mismatch": ("`src/poc/render_docx.py` does not create exactly one placement entry per extracted source element in this baseline.", "generic ledger/rendering change"),
        "pending_disposition": ("`src/poc/render_docx.py` places content under recognized target sections; unresolved headings leave dependent source elements pending.", "generic renderer or classification coverage change"),
        "table_count_mismatch": ("`src/poc/extract.py` uses pdfplumber line-based table detection configured in `config/extraction.yaml`; borderless and split-page grids exceed that strategy.", "generic table detection or configuration change"),
        "table_shape_mismatch": ("`src/poc/extract.py` table extraction relies on line geometry and configured snap/join tolerances in `config/extraction.yaml`.", "generic table detection or configuration change"),
        "heading_missing_or_wrong_level": ("`src/poc/extract.py` heading recognition uses numbered-heading and font-size heuristics in `config/extraction.yaml`; raster pages have no text layer.", "generic heading detection/configuration change; OCR is out of scope"),
        "image_set_or_count_mismatch": ("`src/poc/extract.py` extracts image streams while `src/poc/render_docx.py` embeds placed figures; source images may be omitted or normalized.", "generic image extraction/rendering or provenance change"),
        "image_relationship_mismatch": ("`src/poc/render_docx.py` creates inline image relationships from placed figure elements; the resulting package lacks the full source display-image set.", "generic image placement change"),
        "image_placement_mismatch": ("`src/poc/render_docx.py` emits figures in target-section placement order, which can diverge from source order.", "generic figure ordering/placement change"),
        "source_order_violation": ("`src/poc/render_docx.py` groups source elements by target section, changing their original relative order in this case.", "generic renderer ordering change"),
        "text_missing": ("`src/poc/render_docx.py` places extracted text under recognized target headings; unresolved or misclassified headings leave source words out.", "generic renderer/classification change"),
        "text_excess": ("The verifier's generated-text allowlist does not cover some renderer-generated appendix metadata or fallback labels emitted by `src/poc/render_docx.py`.", "generic generated-text accounting or renderer change"),
        "mapping_mismatch": ("`src/poc/enrich.py` applies keyword rules in `config/classification.yaml`; M7 intentionally made no LLM fallback calls.", "classification configuration or generic rule coverage change"),
    }
    verifier_findings = []
    for doc_id, item in documents.items():
        grouped: Counter[str] = Counter(d.get("code", "unknown") for d in item.get("existing_verifier", {}).get("defects", []))
        for code, count in sorted(grouped.items()):
            cause, scope = verifier_causes.get(code, ("Inspect the exact defect records in `data/m7/output/m7_metrics.json` and the associated extractor or renderer path.", "generic change after reviewing the recorded evidence"))
            verifier_findings.append(f"### {doc_id} — verifier `{code}` ({count})\n\n- Likely root cause: {cause}\n- Scope: {scope}\n")
    worked = []
    for doc_id, item in documents.items():
        recall = item["text"].get("recall")
        recall_text = "no text extracted" if item["text"].get("status") == "no text extracted" else "NOT MEASURED" if recall is None else f"{recall:.1%}"
        worked.append(f"{doc_id}: text recall {recall_text}, {item['headings']['matched']}/{item['headings']['expected']} headings, {item['images']['actual_count']} extracted figures.")
    lines = [
        "# M7 Generalisation Report", "", "## Baseline results", "", *rows, "",
        "## What worked", "", *[f"- {entry}" for entry in worked], "",
        "The unchanged extraction, rendering, and verification functions completed where noted; no provider or network calls were made. Exact hashes and per-document details are in `data/m7/output/m7_metrics.json`.", "",
        "## What broke and likely root causes", "",
    ]
    if failures:
        for failure in failures:
            lines.extend([f"### {failure['document']} — {failure['category']}", "", f"- Observed: {failure['detail']}", f"- Likely root cause: {failure['likely_root_cause']}", f"- Scope: {failure['recommended_scope']}", ""])
    else:
        lines.append("No measured failures.")
    lines.extend([
        "## Existing verifier findings by defect code", "",
        "These counts come from the unchanged M5 verifier. They are listed separately from ground-truth scoring because the categories overlap.", "",
        *verifier_findings, "",
        "## Image text", "",
        "Printed words inside images are recorded in each truth file. OCR and LLM transcription were not run, so recognition of those words is NOT MEASURED.", "",
        "## Header, footer, and page-number leakage", "",
    ])
    for doc_id, item in documents.items():
        leak = item["header_footer_leakage"]
        lines.append(f"- {doc_id}: header/footer leaked into body={bool(leak.get('header_or_footer_leaks'))}; page-number leaked into body={bool(leak.get('page_number_leaks'))}.")
    lines.extend([
        "", "## Limits of this evidence", "",
        f"These are synthetic documents made by the same team and model that built the pipeline. They are cleaner and less messy than real documents, so they are a floor on risk, not a guarantee. The set samples only {metrics['summary']['documents']} constructed layouts and does not represent the range of publishers, scans, encodings, or document quality found in production.", "",
    ])
    return "\n".join(lines)


def score_all(root: Path = ROOT) -> dict[str, Any]:
    """Compare M7 pipeline outputs with source-owned truth and write metrics/report."""
    base = root / "data/m7"
    pipeline = json.loads((base / "output/m7_pipeline.json").read_text(encoding="utf-8"))
    documents = {}
    for doc_id, status in pipeline["documents"].items():
        truth = json.loads((base / "truth" / f"{doc_id}.json").read_text(encoding="utf-8"))
        documents[doc_id] = _score_document(doc_id, truth, status, root)
    metrics = {"stage": "M7 baseline", "network_calls": 0, "llm_calls": 0, "documents": documents,
               "summary": {"documents": len(documents), "crashes": sum(item["status"] == "crashed" for item in documents.values()),
                           "failures": sum(len(item.get("failures", [])) for item in documents.values())}}
    output = base / "output/m7_metrics.json"
    output.write_text(json.dumps(metrics, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = root / "docs/M7_GENERALISATION_REPORT.md"
    report_path.write_text(_render_report(metrics), encoding="utf-8")
    _append_challenges(root / "docs/challenges_log.md", metrics)
    return metrics


def _append_challenges(path: Path, metrics: dict[str, Any]) -> None:
    """Record each baseline failure once, preserving the measured outcome."""
    content = path.read_text(encoding="utf-8") if path.exists() else "# Challenges log\n"
    additions = []
    for doc_id, item in metrics["documents"].items():
        for failure in item.get("failures", []):
            heading = f"## M7 baseline — {doc_id}: {failure['category']}"
            if heading in content:
                continue
            additions.extend([
                heading,
                f"- Where: M7 synthetic document `{doc_id}`.",
                "- Frequency: 1 baseline document.",
                f"- Symptom: {failure['detail']}.",
                f"- Root cause: {failure['likely_root_cause']}.",
                "- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.",
                f"- Residual risk: {failure['recommended_scope']}.",
                "",
            ])
            content += "\n" + "\n".join(additions)
            additions.clear()
        grouped: Counter[str] = Counter(d.get("code", "unknown") for d in item.get("existing_verifier", {}).get("defects", []))
        for code, count in sorted(grouped.items()):
            heading = f"## M7 verifier baseline — {doc_id}: {code}"
            if heading in content:
                continue
            content += "\n" + "\n".join([
                heading,
                f"- Where: M7 synthetic document `{doc_id}`; existing verifier output in `data/m7/output/m7_metrics.json`.",
                f"- Frequency: {count} verifier defect record(s).",
                f"- Symptom: The unchanged verifier emitted `{code}`.",
                "- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.",
                "- Action: Recorded as baseline measurement; no pipeline fix was applied.",
                "- Residual risk: This defect remains and shows the baseline's measured generalisation limit.",
                "",
            ])
    if content and not content.endswith("\n"):
        content += "\n"
    path.write_text(content, encoding="utf-8")


if __name__ == "__main__":
    result = score_all()
    print(f"Scored {result['summary']['documents']} documents; crashes={result['summary']['crashes']}; failure categories={result['summary']['failures']}")
