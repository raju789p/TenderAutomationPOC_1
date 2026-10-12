"""Render extracted and enriched IR documents into deterministic decision briefs."""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import yaml
from docx import Document as WordDocument
from docx.enum.table import WD_CELL_VERTICAL_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[2]
LOGGER = logging.getLogger(__name__)


def _text(element: dict[str, Any]) -> str:
    """Return an element's source text without altering its content."""
    if element["type"] in {"paragraph", "bullet"}:
        return "".join(span["text"] for span in element.get("spans", []))
    if element["type"] == "heading":
        return element.get("title", "")
    if element["type"] == "page_number":
        return element.get("value", "")
    return ""


def _normalized(value: str) -> str:
    """Collapse whitespace for generated navigational labels only."""
    return " ".join(value.split())


def _target_sections(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {canonical: section for section in config["sections"] for canonical in section["accepts"]}


def _set_run(run: Any, *, bold: bool | None = None, italic: bool | None = None) -> None:
    if bold is not None:
        run.bold = bold
    if italic is not None:
        run.italic = italic


def _add_spans(paragraph: Any, spans: list[dict[str, Any]]) -> None:
    for span in spans:
        text = "".join(char for char in span["text"] if not 0xE000 <= ord(char) <= 0xF8FF)
        run = paragraph.add_run(text)
        _set_run(run, bold=span.get("bold", False), italic=span.get("italic", False))


def _set_table_pagination(table: Any, header_rows: int) -> None:
    """Repeat configured header rows and prevent individual rows splitting."""
    for index, row in enumerate(table.rows):
        tr_properties = row._tr.get_or_add_trPr()
        if tr_properties.find(qn("w:cantSplit")) is None:
            tr_properties.append(OxmlElement("w:cantSplit"))
        if index < header_rows and tr_properties.find(qn("w:tblHeader")) is None:
            header = OxmlElement("w:tblHeader")
            header.set(qn("w:val"), "true")
            tr_properties.append(header)


def _add_source_table(document: Any, element: dict[str, Any]) -> None:
    rows = element["rows"]
    if not rows:
        return
    cols = max((len(row) for row in rows), default=0)
    if not cols:
        return
    table = document.add_table(rows=len(rows), cols=cols)
    table.style = "Table Grid"
    _set_table_pagination(table, element.get("header_rows", 0))
    for r_idx, row in enumerate(rows):
        for c_idx in range(cols):
            cell = table.cell(r_idx, c_idx)
            cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER
            cell.text = row[c_idx] if c_idx < len(row) else ""
            if r_idx < element.get("header_rows", 0):
                for run in cell.paragraphs[0].runs:
                    run.bold = True
                shading = cell._tc.get_or_add_tcPr()
                fill = OxmlElement("w:shd")
                fill.set(qn("w:fill"), "D9EAF7")
                shading.append(fill)


def _add_figure(document: Any, element: dict[str, Any], doc_dir: Path, figure_number: int, generated_label: str) -> None:
    image_file = doc_dir / element["image_path"]
    if not image_file.is_file():
        raise FileNotFoundError(f"Display image is missing for {element['id']}: {image_file}")
    image_p = document.add_paragraph()
    image_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    image_p.paragraph_format.keep_with_next = True
    image_p.add_run().add_picture(str(image_file), width=Inches(6))
    label = document.add_paragraph()
    label.alignment = WD_ALIGN_PARAGRAPH.CENTER
    label.paragraph_format.keep_with_next = bool(element.get("ai", {}).get("caption") if element.get("ai") else False)
    label.add_run(f"Figure {figure_number}").bold = True
    caption = element.get("ai", {}).get("caption") if element.get("ai") else None
    if caption:
        p = document.add_paragraph()
        p.paragraph_format.keep_together = True
        p.add_run(f"{generated_label} {caption}")


def _make_deterministic(path: Path) -> None:
    """Rewrite ZIP metadata so two identical renders have identical bytes."""
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".docx", delete=False) as temp:
        temp_path = Path(temp.name)
    try:
        with zipfile.ZipFile(path, "r") as source, zipfile.ZipFile(temp_path, "w", zipfile.ZIP_DEFLATED) as target:
            for name in sorted(source.namelist()):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                info.external_attr = 0o600 << 16
                target.writestr(info, source.read(name))
        temp_path.replace(path)
    finally:
        temp_path.unlink(missing_ok=True)


def render_document(
    doc_id: str,
    output_path: Path | None = None,
    *,
    plan_assignments: dict[str, dict[str, Any]] | None = None,
    source_elements: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Render one source IR and persist dispositions plus placement ledger."""
    config = yaml.safe_load((ROOT / "config/target_format.yaml").read_text())
    doc_dir = ROOT / "data/work" / doc_id
    source_path = doc_dir / "elements.json"
    payload = json.loads(source_path.read_text())
    elements = source_elements if source_elements is not None else payload["elements"]
    class_data = json.loads((doc_dir / "classification.json").read_text())
    classifications = {item["heading_id"]: item for item in class_data["items"]}
    section_by_type = _target_sections(config)
    section_by_id = {item["id"]: item for item in config["sections"]}
    labels_before_tables: set[str] = set()
    paragraphs_after_tables: set[str] = set()
    for index, source_element in enumerate(elements):
        if source_element["type"] == "paragraph":
            following = next((e for e in elements[index + 1:] if e["type"] != "page_number"), None)
            if following and following["type"] == "table":
                labels_before_tables.add(source_element["id"])
        if source_element["type"] == "table" and source_element.get("role") != "toc":
            following = next((e for e in elements[index + 1:] if e["type"] != "page_number"), None)
            if following and following["type"] == "paragraph":
                paragraphs_after_tables.add(following["id"])

    word = WordDocument()
    word.core_properties.title = f"{payload['doc_id'].title()} — Decision Brief"
    word.core_properties.subject = "Generated from extracted source elements"
    word.core_properties.author = "Tender Automation POC"
    word.core_properties.created = word.core_properties.modified = __import__("datetime").datetime(2000, 1, 1)
    word.styles["Normal"].font.name = "Arial"
    word.styles["Normal"].font.size = Pt(10)
    footer = word.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer.add_run("Page ")
    page_field = __import__("docx.oxml", fromlist=["OxmlElement"]).OxmlElement("w:fldSimple")
    page_field.set(__import__("docx.oxml.ns", fromlist=["qn"]).qn("w:instr"), "PAGE")
    footer._p.append(page_field)

    counts = {"placed": 0, "regenerated": 0, "unplaced": 0, "pending": 0}
    placement: dict[str, dict[str, Any]] = {}
    order_counter: dict[str, int] = {}
    current_section: str | None = None
    heading_target: dict[str, str] = {}
    last_h1_target: str | None = None

    # Build source section membership using the nearest preceding classified heading.
    for element in elements:
        planned_target = (plan_assignments or {}).get(element["id"], {}).get("target_section")
        if element["type"] == "heading":
            decision = classifications.get(element["id"])
            if plan_assignments is not None and planned_target:
                target = planned_target
                heading_target[element["id"]] = target
                if element.get("level") == 1:
                    last_h1_target = target
                current_section = target
            elif decision:
                target = section_by_type[decision["canonical_type"]]["id"]
                heading_target[element["id"]] = target
                if element.get("level") == 1:
                    last_h1_target = target
                current_section = target
            else:
                current_section = last_h1_target
        elif element["role"] == "body" and current_section is None:
            current_section = last_h1_target

    # Cover block preserves source lines and includes the source cover figure.
    cover_lines = payload.get("cover_lines", [])
    title = word.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run(cover_lines[0] if cover_lines else doc_id.upper()).bold = True
    for line in cover_lines[1:]:
        p = word.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run(line)
    cover_elements = [e for e in elements if e.get("role") == "cover"]
    figure_number = 0
    for element in cover_elements:
        if element["type"] == "figure":
            figure_number += 1
            _add_figure(word, element, doc_dir, figure_number, config["generated_label"])
            element["disposition"] = "placed"
            placement[element["id"]] = {"target_section": "cover", "order_index": 0}
        elif element["type"] == "paragraph":
            element["disposition"] = "placed"
            placement[element["id"]] = {"target_section": "cover", "order_index": len(placement)}
    word.add_page_break()

    # A static contents list is the configured fallback to a Word TOC field.
    toc_title = word.add_heading("Contents", level=1)
    toc_title.paragraph_format.keep_with_next = True
    for element in elements:
        if element["type"] == "paragraph" and _normalized(_text(element)).casefold() == "contents":
            element["disposition"] = "regenerated"
            placement[element["id"]] = {"target_section": "contents", "order_index": 0}
    for section in config["sections"]:
        p = word.add_paragraph(section["title"])
        p.paragraph_format.left_indent = Inches(0.2)

    # Render target sections in config order; source order is retained within each section.
    render_targets = list(config["sections"])
    if plan_assignments is not None:
        render_targets.append({"id": "unclassified", "title": "Unclassified Source Content", "accepts": []})
    for target in render_targets:
        word.add_page_break()
        word.add_heading(target["title"], level=1)
        current = target["id"]
        order_counter[current] = 0
        for element in elements:
            if element.get("role") == "cover":
                continue
            etype = element["type"]
            if etype == "table" and element.get("role") == "toc":
                element["disposition"] = "regenerated"
                placement[element["id"]] = {"target_section": "contents", "order_index": len(placement)}
                continue
            if etype == "page_number":
                element["disposition"] = "regenerated"
                placement[element["id"]] = {"target_section": "page_numbers", "order_index": len(placement)}
                continue
            if etype == "paragraph" and _normalized(_text(element)).casefold() == "contents":
                continue
            if etype == "heading":
                destination = heading_target.get(element["id"])
                if destination != current:
                    continue
                # Keep title verbatim; omit the number field/prefix in the rendered subheading.
                word.add_heading(element["title"], level=2 if element.get("level") == 1 else 3)
            else:
                destination = current_section
                # Resolve destination from preceding source heading by scanning source order.
                if plan_assignments is not None:
                    destination = plan_assignments.get(element["id"], {}).get("target_section")
                else:
                    destination = _element_target(elements, classifications, section_by_type, element["id"])
                if destination != current:
                    continue
                if etype == "paragraph":
                    paragraph = word.add_paragraph()
                    _add_spans(paragraph, element.get("spans", []))
                    if element["id"] in labels_before_tables or element.get("is_label"):
                        paragraph.paragraph_format.keep_with_next = True
                    if element["id"] in paragraphs_after_tables:
                        paragraph.paragraph_format.space_before = Pt(8)
                elif etype == "bullet":
                    paragraph = word.add_paragraph(style="List Bullet")
                    _add_spans(paragraph, element.get("spans", []))
                elif etype == "table":
                    _add_source_table(word, element)
                    # A paragraph lead-in with is_label remains just before the table in source order.
                elif etype == "figure":
                    figure_number += 1
                    _add_figure(word, element, doc_dir, figure_number, config["generated_label"])
                else:
                    continue
            if element["id"] not in placement:
                element["disposition"] = "placed"
                placement[element["id"]] = {"target_section": current, "order_index": order_counter[current]}
                order_counter[current] += 1

    # Appendix 1: AI-labelled figure index (generated content is not a source element).
    word.add_page_break()
    word.add_heading(config["appendices"][0]["title"], level=1)
    word.add_paragraph("Structure inside images may be lost in transcription.")
    figures = [e for e in elements if e["type"] == "figure"]
    index_table = word.add_table(rows=1, cols=6)
    index_table.style = "Table Grid"
    index_headers = [
        "AI-generated figure id",
        "AI-generated source page",
        "AI-generated hash prefix",
        "AI-generated caption",
        "AI-generated transcribed text",
        "AI-generated source part hashes",
    ]
    for cell, value in zip(index_table.rows[0].cells, index_headers):
        cell.text = value
        for run in cell.paragraphs[0].runs:
            run.bold = True
    for figure in figures:
        ai = figure.get("ai") or {}
        part_hashes = [part.get("sha256", "") for part in figure.get("parts", [])]
        display_hash = figure.get("sha256", "")
        row = index_table.add_row()
        values = [
            figure["id"],
            str(figure["page"]),
            display_hash[:12],
            ai.get("caption", "[missing enrichment result]"),
            " | ".join(ai.get("transcribed_text", [])) or "[none]",
            ", ".join(part_hashes) or display_hash,
        ]
        for cell, value in zip(row.cells, values):
            cell.text = value
    _set_table_pagination(index_table, 1)

    # Appendix 2 records original numbering and target mapping; numbering is omitted from headings.
    word.add_page_break()
    word.add_heading(config["appendices"][1]["title"], level=1)
    source_map_rows: list[dict[str, Any]] = []
    for element in elements:
        if element["type"] != "heading":
            continue
        decision = classifications.get(element["id"], {})
        target_id = heading_target.get(element["id"], "unmapped")
        source_map_rows.append({"element_id": element["id"], "number": element.get("number"), "title": element["title"], "target_section": target_id})
        word.add_paragraph(f"{element['id']}: source number {element.get('number') or '[none]'}; title {element['title']}; target {section_by_id[target_id]['title'] if target_id in section_by_id else target_id}")

    # Appendix 3 must be empty; every source element is placed or explicitly regenerated.
    unplaced = [element for element in elements if element.get("disposition") == "unplaced"]
    word.add_page_break()
    word.add_heading(config["appendices"][2]["title"], level=1)
    if unplaced:
        for element in unplaced:
            word.add_paragraph(f"{element['id']}: {_text(element)}")

    for element in elements:
        counts[element.get("disposition", "pending")] += 1
    if output_path is None:
        output_path = ROOT / "data/output" / f"{doc_id}_decision_brief.docx"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    word.save(output_path)
    _make_deterministic(output_path)

    payload["elements"] = elements
    source_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    ledger = {
        "doc_id": doc_id,
        "output_file": str(output_path.relative_to(ROOT)) if output_path.is_relative_to(ROOT) else str(output_path),
        "placements": placement,
        "source_map": source_map_rows,
        "disposition_counts": counts,
        "unplaced_ids": [element["id"] for element in unplaced],
    }
    (doc_dir / "placement.json").write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + "\n")
    return ledger


def _element_target(elements: list[dict[str, Any]], classifications: dict[str, dict[str, Any]], section_by_type: dict[str, dict[str, Any]], element_id: str) -> str | None:
    """Find the nearest preceding classified heading's destination for an element."""
    current: str | None = None
    for candidate in elements:
        if candidate["type"] == "heading":
            decision = classifications.get(candidate["id"])
            if decision:
                current = section_by_type[decision["canonical_type"]]["id"]
        if candidate["id"] == element_id:
            return current
    return current


def render_all() -> list[dict[str, Any]]:
    """Render both configured source documents and optionally create visual review renders."""
    ledgers = [render_document(doc_id) for doc_id in ("waterfall", "kanban")]
    soffice = shutil.which("soffice")
    if not soffice:
        challenges = ROOT / "docs/challenges_log.md"
        existing = challenges.read_text() if challenges.exists() else ""
        if "## LibreOffice visual review skipped" not in existing:
            with challenges.open("a") as log:
                log.write("\n## LibreOffice visual review skipped\n- Where: M4 DOCX visual comparison.\n- Frequency: 2 documents.\n- What happened: `soffice` was not installed/on PATH.\n- Action: Skipped PDF conversion and PNG page renders as directed.\n- Residual risk: Human must compare DOCX files directly with the source PDFs.\n")
        LOGGER.info("LibreOffice not installed; skipped PDF and PNG review renders")
    else:
        review_dir = ROOT / "data/output/review"
        review_dir.mkdir(parents=True, exist_ok=True)
        for doc_id in ("waterfall", "kanban"):
            docx_path = ROOT / "data/output" / f"{doc_id}_decision_brief.docx"
            subprocess.run([soffice, "--headless", "--convert-to", "pdf", "--outdir", str(review_dir), str(docx_path)], check=True, capture_output=True, text=True)
            pdf_path = review_dir / f"{doc_id}_decision_brief.pdf"
            try:
                import fitz
                pdf = fitz.open(pdf_path)
                for index, page in enumerate(pdf):
                    pix = page.get_pixmap(dpi=100, alpha=False)
                    pix.save(review_dir / f"{doc_id}_p{index + 1:03d}.png")
            except Exception as exc:
                LOGGER.warning("Could not render review PNGs for %s: %s", doc_id, exc)
    return ledgers
