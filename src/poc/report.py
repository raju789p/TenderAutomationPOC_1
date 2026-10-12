"""Generate the architect-facing accuracy report from verifier metrics."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]


def _percent(value: float | None) -> str:
    return "NOT MEASURED" if value is None else f"{value * 100:.2f}%"


def _ratio(matched: int, total: int) -> str:
    return f"{matched}/{total} ({_percent(matched / total if total else None)})"


def results_table(metrics: dict[str, Any]) -> str:
    """Return the results table with every reported measurement sourced from metrics."""
    header = "| Document | Text recall | Tables | Headings | Images | Composites | Mapping accuracy | Image keywords strict | Image keywords normalised | Placed / regenerated / unplaced | Defects |"
    separator = "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"
    lines = [header, separator]
    documents = metrics["documents"]
    for doc_id, item in documents.items():
        text = item["text"]
        tables = item["tables"]
        headings = item["headings"]
        images = item["images"]
        composites = images["composites"]
        mapping = item["mapping"]
        keywords = item["image_transcription"]
        ledger = item["ledger"]["counts"]
        lines.append(
            f"| {doc_id} | {_percent(text['word_recall'])} | {tables['matching_count']}/{tables['expected_count']} | "
            f"{headings['matched_count']}/{headings['source_count']} | {images['docx_media_file_count']}/{images['source_display_image_count']} | "
            f"{sum(entry['matches'] for entry in composites)}/{len(composites)} | {_ratio(mapping['correct'], mapping['total'])} | "
            f"{keywords['strict']['matched']}/{keywords['strict']['total']} | {keywords['normalised']['matched']}/{keywords['normalised']['total']} | "
            f"{ledger['placed']} / {ledger['regenerated']} / {ledger['unplaced']} | {len(item['defects'])} |"
        )
    overall = metrics["overall"]
    text, tables, headings = overall["text"], overall["tables"], overall["headings"]
    images, mapping, keywords, ledger = overall["images"], overall["mapping"], overall["image_transcription"], overall["ledger"]
    lines.append(
        f"| Overall | {_percent(text['word_recall'])} | {tables['matching_count']}/{tables['expected_count']} | "
        f"{headings['matched']}/{headings['total']} | {images['docx_media_file_count']}/{images['source_display_image_count']} | "
        f"{images['composites_matching']}/{images['composites_rebuilt']} | {_ratio(mapping['correct'], mapping['total'])} | "
        f"{keywords['strict']['matched']}/{keywords['strict']['total']} | {keywords['normalised']['matched']}/{keywords['normalised']['total']} | "
        f"{ledger['placed']} / {ledger['regenerated']} / {ledger['unplaced']} | {overall['defect_count']} |"
    )
    return "\n".join(lines)


def generate_accuracy_report(metrics: dict[str, Any]) -> str:
    """Build the complete accuracy report using only verifier-produced measurements."""
    overall = metrics["overall"]
    corruptions = [
        "delete a table row", "swap one image", "change one paragraph word", "delete one paragraph",
        "change a heading title", "move a section out of order", "insert a private-use character",
    ]
    return "\n".join([
        "# Accuracy Report", "",
        "## Goal and method", "",
        "Measure whether two source PDFs are preserved in our configured Word template. The deterministic workflow is extract → intermediate representation (IR) → target template → render → independent verification. AI-generated image descriptions are saved enrichment metadata; the document conversion itself uses extracted source content.", "",
        "## Results", "", results_table(metrics), "",
        f"Heading coverage: {overall['headings']['matched']}/{overall['headings']['total']} ({_percent(overall['headings']['accuracy'])}); contents topics represented as headings: {overall['contents']['matched']}/{overall['contents']['total']}.",
        f"Composite rebuilds matched: {overall['images']['composites_matching']}/{overall['images']['composites_rebuilt']}. Image keyword recall is **indicative; measures keyword presence only**: strict {_ratio(overall['image_transcription']['strict']['matched'], overall['image_transcription']['strict']['total'])}; normalised {_ratio(overall['image_transcription']['normalised']['matched'], overall['image_transcription']['normalised']['total'])}.",
        "", "## What the verifier checks", "",
        "The independent DOCX verifier checks source-word recall and excess words, table shape and whitespace-normalised cell equality, heading titles and levels, display-image media hashes and counts, composite rebuilds from exact parts, placement order, contents topics, section mapping, the disposition ledger, and private-use Unicode characters. The offline corruption suite verifies detection of: " + "; ".join(corruptions) + ".",
        "", "## Limits of this evidence", "",
        "- Only two source documents were measured.",
        "- The target is our own configured template, not an external organisation's approved template.",
        "- Image keyword recall is indicative only: it measures selected keyword presence, not full transcription accuracy.",
        "- Text inside images cannot be verified automatically against a complete human transcription.",
        "- Layout still needs human visual review against the source PDFs.",
        "- The contents list is static and has no page numbers.",
        "- Results come from the deterministic pipeline, not from an LLM-generated conversion.",
        "", "## Known issues", "",
        "One AI-generated caption named **Skógafoss**, a place name not supported by the source image. This is a caption hallucination risk. The planned prompt rule is: **describe only what is visible; no place, person or brand names**. Existing saved AI outputs are preserved; no new model request was made for this report.",
        "", "Image keyword metrics do not evaluate that caption claim; human review remains necessary.", "",
    ])


def generate_summary(metrics: dict[str, Any]) -> str:
    """Build a compact project summary, deriving its five result lines from metrics."""
    overall = metrics["overall"]
    text, tables, mapping = overall["text"], overall["tables"], overall["mapping"]
    images, keywords, ledger = overall["images"], overall["image_transcription"], overall["ledger"]
    return "\n".join([
        "# Project Summary", "",
        "## What we built", "",
        "An offline-capable pipeline that extracts two PDFs into a structured intermediate representation, enriches figures from saved AI results, renders decision briefs in the configured Word template, and independently verifies the DOCX outputs.", "",
        "## Accuracy in five lines", "",
        f"- Source text word recall: {_percent(text['word_recall'])}; missing={text['missing_word_count']}, excess={text['excess_word_count']}.",
        f"- Tables: {tables['matching_count']}/{tables['expected_count']} shape and cell matches.",
        f"- Display images: {images['docx_media_file_count']}/{images['source_display_image_count']}; composites rebuilt={images['composites_matching']}/{images['composites_rebuilt']}.",
        f"- Section mapping: {_ratio(mapping['correct'], mapping['total'])}; image keywords indicative strict={keywords['strict']['matched']}/{keywords['strict']['total']}, normalised={keywords['normalised']['matched']}/{keywords['normalised']['total']}.",
        f"- Ledger: placed={ledger['placed']}, regenerated={ledger['regenerated']}, unplaced={ledger['unplaced']}; defects={overall['defect_count']}.",
        "", "## Top five challenges", "",
        "1. Table extraction fragmented ruled cells; the line-based strategy and configured tolerances restored expected shapes.",
        "2. Table-overlap suppression initially dropped adjacent bold text; per-line suppression plus word-conservation checks fixed it.",
        "3. PDF image streams split logical figures; exact fragment bytes are retained and composites are rebuilt and checked.",
        "4. Gemini could not be reached from the sandbox; the human completed enrichment and the saved results were reused offline.",
        "5. An AI caption named unsupported place Skógafoss; the planned prompt rule will restrict descriptions to visible content and avoid names.",
        "", "## What is not proven", "",
        "Evidence covers two documents and our own template only. Image keyword presence is indicative, image transcription is not fully checked, and layout requires human visual comparison. The contents list is static and has no page numbers.",
        "", "## Next steps", "",
        "Have the architect review the generated DOCX and visual comparison, approve the accuracy evidence, and update the image prompt with the visible-content/no-names rule before any future real enrichment run.", "",
    ])


def write_accuracy_report(metrics_path: Path | None = None, output_path: Path | None = None) -> str:
    """Write the generated report from the supplied or standard metrics file."""
    metrics_path = metrics_path or ROOT / "data/output/metrics.json"
    output_path = output_path or ROOT / "docs/accuracy_report.md"
    report = generate_accuracy_report(json.loads(metrics_path.read_text(encoding="utf-8")))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report, encoding="utf-8")
    return report


def write_summary(metrics_path: Path | None = None, output_path: Path | None = None) -> str:
    """Write the concise project summary from the verifier metrics."""
    metrics_path = metrics_path or ROOT / "data/output/metrics.json"
    output_path = output_path or ROOT / "docs/SUMMARY.md"
    summary = generate_summary(json.loads(metrics_path.read_text(encoding="utf-8")))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(summary, encoding="utf-8")
    return summary
