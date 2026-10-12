"""Create deterministic synthetic process-methodology PDFs and independent truth files."""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

import fitz
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
SEED = 731_905
PAGE_SIZE = (595, 842)


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _font(size: int = 14) -> ImageFont.ImageFont:
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default()


def _chart_bytes(doc_id: str, label: str, seed: int) -> bytes:
    rng = random.Random(seed)
    image = Image.new("RGB", (520, 260), "white")
    draw = ImageDraw.Draw(image)
    colors = ["#356a9a", "#e07a35", "#4f8b62", "#a95454"]
    draw.text((18, 12), label, fill="#152638", font=_font(22))
    words = ["SIGNAL", "CONTROL", "QUALITY", "FLOW"]
    for index, word in enumerate(words):
        x = 26 + index * 122
        height = 70 + rng.randrange(80)
        draw.rounded_rectangle((x, 205 - height, x + 74, 205), radius=5, fill=colors[index])
        draw.text((x - 3, 218), word, fill="#17212b", font=_font(12))
    from io import BytesIO

    buffer = BytesIO()
    image.save(buffer, format="PNG", optimize=False)
    return buffer.getvalue()


def _set_metadata(document: fitz.Document, title: str) -> None:
    metadata = document.metadata
    metadata.update({"title": title, "author": "M7 synthetic fixture generator", "subject": "Synthetic generalisation baseline", "creator": "make_m7_docs.py", "producer": "PyMuPDF", "creationDate": "D:20200101000000Z", "modDate": "D:20200101000000Z"})
    document.set_metadata(metadata)


def _text(page: fitz.Page, value: str, x: float, y: float, *, size: float = 11, color: tuple[float, float, float] = (0.12, 0.16, 0.2), font: str = "helv", width: float = 475) -> None:
    page.insert_textbox(fitz.Rect(x, y, x + width, y + 66), value, fontsize=size, fontname=font, color=color, lineheight=1.2)


def _heading(page: fitz.Page, number: str, title: str, x: float = 58, y: float = 70, *, level: int = 1, size: float | None = None, color: tuple[float, float, float] = (0.09, 0.2, 0.32), font: str = "hebo", width: float = 480) -> str:
    size = size or (18 if level == 1 else 14)
    text = f"{number} {title}"
    page.insert_textbox(fitz.Rect(x, y, x + width, y + 40), text, fontsize=size, fontname=font, color=color)
    return text


def _header_footer(page: fitz.Page, doc_id: str, page_no: int, *, color: tuple[float, float, float]) -> tuple[str, str, str]:
    header = f"{doc_id.replace('_', ' ').title()} / Internal Playbook"
    footer = "Operations Excellence Series"
    page.insert_text((44, 26), header, fontsize=8, fontname="heit", color=color)
    page.draw_line((44, 33), (551, 33), color=color, width=0.5)
    page.insert_text((44, 817), footer, fontsize=8, fontname="heit", color=color)
    page.insert_text((526, 817), str(page_no), fontsize=9, fontname="hebo", color=color)
    return header, footer, str(page_no)


def _table(page: fitz.Page, rows: list[list[str]], x: float, y: float, widths: list[float], *, ruled: bool, row_height: float = 28, color: tuple[float, float, float] = (0.15, 0.2, 0.25), font_size: float = 9) -> None:
    for r_index, row in enumerate(rows):
        for c_index, cell in enumerate(row):
            left = x + sum(widths[:c_index])
            right = left + widths[c_index]
            top = y + r_index * row_height
            bottom = top + row_height
            if ruled:
                page.draw_rect(fitz.Rect(left, top, right, bottom), color=(0.48, 0.55, 0.62), width=0.6)
            if r_index == 0:
                page.draw_rect(fitz.Rect(left, top, right, bottom), color=None, fill=(0.86, 0.9, 0.94)) if ruled else None
            page.insert_textbox(fitz.Rect(left + 5, top + 5, right - 4, bottom - 3), cell, fontsize=font_size, fontname="hebo" if r_index == 0 else "helv", color=color)


def _truth_page(text: list[str], headings: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    return {"text": "\n".join(text), "headings": headings or []}


def _source_dataset(doc_id: str, topic: str) -> dict[str, Any]:
    names = {
        "m7_a_same_style": ("Scrum", ["Delivery Intent", "Product Scope", "Sprint Mechanics", "Release Learning Objectives"]),
        "m7_b_new_style": ("Lean Portfolio", ["Value Stream Scope", "Portfolio Advantages", "Flow Evidence", "Learning Review"]),
        "m7_c_borderless_tables": ("Six Sigma", ["Variation Study", "Measurement System", "Control Plan", "Capability Review"]),
        "m7_d_two_column": ("DevOps", ["Service Flow", "Deployment Safety", "Incident Learning", "Reliability Signals"]),
        "m7_e_scanned": ("Spiral", ["Risk Resolution", "Prototype Review", "Iteration Contract", "Exit Evidence"]),
    }
    method, headings = names[doc_id]
    return {"method": method, "topic": topic, "headings": headings}


def _expected_section_type(title: str) -> str:
    """Record the expected canonical type where the existing rules clearly apply."""
    folded = title.casefold()
    for keyword, kind in (
        ("scope", "scope"), ("learning objectives", "learning_objectives"),
        ("advantages", "advantages"), ("best practices", "best_practices"),
        ("limitations", "limitations"), ("when to use", "when_to_use"),
    ):
        if keyword in folded:
            return kind
    return "unclassified"


def _make_document(doc_id: str, topic: str, destination: Path, assets_dir: Path, seed: int) -> dict[str, Any]:
    data = _source_dataset(doc_id, topic)
    method, headings = data["method"], data["headings"]
    pdf = fitz.open()
    truth_pages: list[dict[str, Any]] = []
    truth_headings: list[dict[str, Any]] = []
    truth_tables: list[dict[str, Any]] = []
    truth_images: list[dict[str, Any]] = []
    section_types: dict[str, str] = {}
    page_furniture: list[dict[str, Any]] = []
    image_words = ["SIGNAL", "CONTROL", "QUALITY", "FLOW"]
    chart = _chart_bytes(doc_id, f"{method} Evidence Loop", seed)
    assets_dir.mkdir(parents=True, exist_ok=True)
    chart_path = assets_dir / f"{doc_id}_evidence.png"
    chart_path.write_bytes(chart)
    chart_hash = _sha(chart)
    title_text = f"Project Delivery Method / {method} Operating Guide"

    # Cover page.
    page = pdf.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
    cover = ["Northstar Delivery Office", "PROJECT METHOD PLAYBOOK", method.upper(), f"{topic} | synthetic baseline edition"]
    page.insert_textbox(fitz.Rect(55, 165, 540, 280), cover[0], fontsize=13, fontname="hebo", align=1, color=(0.12, 0.24, 0.36))
    page.insert_textbox(fitz.Rect(55, 300, 540, 430), "\n".join(cover[1:]), fontsize=20, fontname="hebo", align=1, color=(0.12, 0.24, 0.36), lineheight=1.5)
    page.insert_image(fitz.Rect(185, 520, 410, 632), stream=chart)
    cover_truth = cover + image_words
    truth_pages.append(_truth_page(cover_truth))
    truth_images.append({"page": 1, "sha256": chart_hash, "expected_printed_words": image_words})

    # Contents page: intentionally resembles originals only for the same-style fixture.
    page = pdf.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
    if doc_id == "m7_b_new_style":
        header, footer, printed = _header_footer(page, doc_id, 2, color=(0.35, 0.08, 0.45))
        page_furniture.append({"page": 2, "header": header, "footer": footer, "page_number": printed})
        page.insert_textbox(fitz.Rect(64, 72, 530, 115), "ROADMAP", fontsize=25, fontname="tibo", color=(0.35, 0.08, 0.45))
        texts = ["Roadmap"]
        y = 155
        for item in headings:
            page.insert_text((82, y), item, fontsize=13, fontname="tibo", color=(0.1, 0.38, 0.35))
            texts.append(item)
            y += 36
        texts.extend([header, footer, printed])
    else:
        page.insert_text((58, 80), "Contents", fontsize=18, fontname="hebo", color=(0.1, 0.2, 0.3))
        texts = ["Contents"]
        y = 133
        for index, item in enumerate(headings, start=1):
            entry = f"{index}. {item}"
            page.insert_text((78, y), entry, fontsize=12, fontname="helv")
            texts.append(entry)
            y += 37
    truth_pages.append(_truth_page(texts))

    if doc_id == "m7_e_scanned":
        truth_images.clear()  # The final PDF contains full-page scans, not the source chart stream.
        for page_index in range(4):
            page = pdf.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
            top = _heading(page, f"{page_index + 1}", headings[page_index], size=19)
            paragraph = f"{method} teams resolve uncertainty through evidence, controlled experiments, and explicit risk review. Page {page_index + 3} describes {headings[page_index].lower()} with repeatable acceptance signals."
            _text(page, paragraph, 58, 132, size=12)
            text_items = [top, paragraph]
            heading = {"title": headings[page_index], "level": 1}
            truth_headings.append({"page": page_index + 3, **heading})
            section_types[str(page_index + 1)] = _expected_section_type(headings[page_index])
            if page_index == 1:
                page.insert_image(fitz.Rect(72, 250, 490, 460), stream=chart)
                text_items += image_words
            truth_pages.append(_truth_page(text_items, [heading]))
        # Rasterize every page to an image-only PDF, deliberately removing all text.
        raster_pdf = fitz.open()
        for page_index, original in enumerate(pdf):
            pix = original.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
            image_data = pix.tobytes("png")
            page_image = raster_pdf.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
            page_image.insert_image(page_image.rect, stream=image_data)
            truth_images.append({"page": page_index + 1, "sha256": _sha(image_data), "expected_printed_words": image_words if page_index == 3 else []})
        pdf.close()
        pdf = raster_pdf
        truth_pages = [_truth_page(page["text"].splitlines(), page.get("headings")) for page in truth_pages]
        truth_tables = []
    else:
        # New-style header/footer test and ordinary numbered heading pages.
        page_index = 2
        page = pdf.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
        page_text: list[str] = []
        h1_title = headings[0]
        h1_line = _heading(page, "1", h1_title, x=65 if doc_id == "m7_b_new_style" else 58, y=88, size=21 if doc_id == "m7_b_new_style" else 18, color=(0.46, 0.09, 0.52) if doc_id == "m7_b_new_style" else (0.09, 0.2, 0.32), font="tibo" if doc_id == "m7_b_new_style" else "hebo")
        page_text.append(h1_line)
        truth_headings.append({"page": 3, "title": h1_title, "level": 1})
        section_types["1"] = _expected_section_type(h1_title)
        h2_title = "Experiment Design" if doc_id == "m7_b_new_style" else "Evidence Inputs"
        h2_line = _heading(page, "1.1", h2_title, y=142, level=2, size=16 if doc_id == "m7_b_new_style" else 14, color=(0.1, 0.42, 0.36), font="tibo" if doc_id == "m7_b_new_style" else "hebo")
        page_text.append(h2_line)
        truth_headings.append({"page": 3, "title": h2_title, "level": 2})
        paragraph = f"{method} teams align work to {topic.lower()} goals and record evidence before advancing the work item."
        _text(page, paragraph, 58, 197, size=11 if doc_id != "m7_b_new_style" else 13, color=(0.15, 0.2, 0.25), font="helv" if doc_id != "m7_b_new_style" else "tiro")
        page_text.append(paragraph)
        bullets = ["Review the signal before changing the plan", "Keep ownership visible across handoffs"]
        for index, bullet in enumerate(bullets):
            line = f"• {bullet}"
            page.insert_text((73, 282 + 28 * index), line, fontsize=11, fontname="helv", color=(0.1, 0.2, 0.3))
            page_text.append(line)
        table_rows = [["Stage", "Evidence", "Owner"], ["Frame", "Baseline", "Lead"], ["Test", "Outcome", "Team"], ["Learn", "Decision", "Sponsor"]]
        if doc_id == "m7_b_new_style":
            pass  # Recurring furniture is added once after all pages are constructed.
        _table(page, table_rows, 58, 370, [150, 185, 125], ruled=doc_id != "m7_c_borderless_tables", color=(0.12, 0.17, 0.23))
        page_text.extend(" ".join(row) for row in table_rows)
        truth_tables.append({"page": 3, "shape": [len(table_rows), 3], "cells": table_rows})
        truth_pages.append(_truth_page(page_text, [truth_headings[-2], truth_headings[-1]]))

        # A page with a different H1/H2 to test generalized wording and numbering.
        page = pdf.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
        h1_line = _heading(page, "2", headings[1], y=88, size=20 if doc_id == "m7_b_new_style" else 18, color=(0.46, 0.09, 0.52) if doc_id == "m7_b_new_style" else (0.09, 0.2, 0.32), font="tibo" if doc_id == "m7_b_new_style" else "hebo")
        subhead = "Decision Rights" if doc_id != "m7_d_two_column" else "Column Handoff"
        h2_line = _heading(page, "2.1", subhead, y=145, level=2, size=15 if doc_id == "m7_b_new_style" else 14, color=(0.1, 0.42, 0.36), font="tibo" if doc_id == "m7_b_new_style" else "hebo")
        para1 = f"The {method} method uses {headings[1].lower()} to make the next decision observable and reversible."
        para2 = f"Teams capture context, compare evidence, and assign a named owner for the next review."
        page_text = [h1_line, h2_line]
        truth_headings.extend([{"page": 4, "title": headings[1], "level": 1}, {"page": 4, "title": subhead, "level": 2}])
        section_types["2"] = _expected_section_type(headings[1])
        if doc_id == "m7_d_two_column":
            _text(page, para1, 58, 205, size=12, width=222)
            _text(page, para2, 315, 205, size=12, width=222)
            page.draw_line((297, 200), (297, 630), color=(0.65, 0.68, 0.7), width=0.7)
            page_text += [para1, para2]
            page.insert_image(fitz.Rect(74, 390, 271, 500), stream=chart)
            caption = "Figure 1. Service signals move through a guarded deployment loop."
            page.insert_text((76, 520), caption, fontsize=9, fontname="heit")
            page.insert_text((58, 775), "1. Evidence is sampled after a stable observation window.", fontsize=8, fontname="heit")
            page_text += [caption, "1. Evidence is sampled after a stable observation window."]
            truth_images.append({"page": 4, "sha256": chart_hash, "expected_printed_words": image_words})
        else:
            _text(page, para1, 58, 205, size=11)
            _text(page, para2, 58, 255, size=11)
            page_text += [para1, para2]
        if doc_id == "m7_b_new_style":
            pass  # Recurring furniture is added once after all pages are constructed.
        truth_pages.append(_truth_page(page_text, truth_headings[-2:]))

        # The whitespace-aligned document includes a table split across pages 4–5.
        if doc_id == "m7_c_borderless_tables":
            spanning_rows = [["Control", "Measure", "Escalation"]] + [[f"Gate {i}", f"Metric {i}", f"Owner {i}"] for i in range(1, 11)]
            continuation = pdf.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
            continuation_text = "Continuation of the unruled control matrix across a page break."
            _text(continuation, continuation_text, 58, 55, size=9)
            truth_pages.append(_truth_page([continuation_text]))
            for page_no, start, stop, y in ((4, 0, 6, 520), (5, 6, len(spanning_rows), 90)):
                table_page = pdf[page_no - 1]
                part = spanning_rows[start:stop]
                _table(table_page, part, 58, y, [150, 160, 150], ruled=False, row_height=29, font_size=8)
                truth_pages[page_no - 1]["text"] += "\n" + "\n".join(" ".join(row) for row in part)
            truth_tables.append({"page": 4, "continues_on_page": 5, "shape": [len(spanning_rows), 3], "cells": spanning_rows})
        else:
            # Standard ruled table on the last page.
            page = pdf.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
            h1 = _heading(page, "3", headings[2], y=78)
            h2 = _heading(page, "3.1", "Assurance Measures", y=128, level=2)
            ptext = f"{method} records a measurable result for {headings[2].lower()} and preserves the decision context."
            _text(page, ptext, 58, 180)
            rows = [["Check", "Threshold"], ["Trace", "Evidence linked"], ["Review", "Owner assigned"], ["Close", "Action recorded"]]
            _table(page, rows, 58, 280, [220, 240], ruled=True)
            page.insert_image(fitz.Rect(170, 440, 425, 565), stream=chart)
            page_text = [h1, h2, ptext] + [" ".join(row) for row in rows] + image_words
            truth_headings += [{"page": 5, "title": headings[2], "level": 1}, {"page": 5, "title": "Assurance Measures", "level": 2}]
            section_types["3"] = _expected_section_type(headings[2])
            truth_tables.append({"page": 5, "shape": [len(rows), 2], "cells": rows})
            truth_images.append({"page": 5, "sha256": chart_hash, "expected_printed_words": image_words})
            truth_pages.append(_truth_page(page_text, truth_headings[-2:]))
            # Add a sixth page for another varied top-level title and content.
            page = pdf.new_page(width=PAGE_SIZE[0], height=PAGE_SIZE[1])
            h1 = _heading(page, "4", headings[3], y=88)
            ptext = f"A closeout record states what changed, who accepted the evidence, and what remains open in {method}."
            _text(page, ptext, 58, 145)
            truth_headings.append({"page": 6, "title": headings[3], "level": 1})
            section_types["4"] = _expected_section_type(headings[3])
            truth_pages.append(_truth_page([h1, ptext], [truth_headings[-1]]))

    if doc_id == "m7_b_new_style":
        # Add recurring page furniture on all content pages; the cover intentionally stays clean.
        for index in range(2, len(pdf)):
            header, footer, printed = _header_footer(pdf[index], doc_id, index + 1, color=(0.35, 0.08, 0.45))
            page_furniture.append({"page": index + 1, "header": header, "footer": footer, "page_number": printed})
            page_truth = truth_pages[index]
            page_truth["text"] += f"\n{header}\n{footer}\n{printed}"
    _set_metadata(pdf, title_text)
    destination.parent.mkdir(parents=True, exist_ok=True)
    pdf.save(destination, garbage=4, deflate=True, clean=True, no_new_id=True, reproducible=True)
    pdf.close()

    truth = {
        "doc_id": doc_id,
        "methodology": method,
        "source_pdf_sha256": _sha(destination.read_bytes()),
        "page_count": len(truth_pages),
        "pages": truth_pages,
        "headings": truth_headings,
        "tables": truth_tables,
        "images": truth_images,
        "section_types": section_types,
        "page_furniture": page_furniture,
    }
    return truth


def generate_all(output_root: Path | None = None) -> dict[str, str]:
    """Generate all five fixtures and truth files below output_root."""
    output_root = output_root or ROOT / "data/m7"
    inputs_dir = output_root / "inputs"
    truth_dir = output_root / "truth"
    assets_dir = output_root / "assets"
    inputs_dir.mkdir(parents=True, exist_ok=True)
    truth_dir.mkdir(parents=True, exist_ok=True)
    topics = {
        "m7_a_same_style": "Scrum Product Delivery",
        "m7_b_new_style": "Lean Portfolio Decisions",
        "m7_c_borderless_tables": "Six Sigma Quality Control",
        "m7_d_two_column": "DevOps Service Reliability",
        "m7_e_scanned": "Spiral Risk Engineering",
    }
    hashes = {}
    for index, (doc_id, topic) in enumerate(topics.items()):
        truth = _make_document(doc_id, topic, inputs_dir / f"{doc_id}.pdf", assets_dir, SEED + index)
        truth_path = truth_dir / f"{doc_id}.json"
        truth_path.write_text(json.dumps(truth, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        hashes[str(inputs_dir / f"{doc_id}.pdf")] = _sha((inputs_dir / f"{doc_id}.pdf").read_bytes())
        hashes[str(truth_path)] = _sha(truth_path.read_bytes())
    return hashes


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path, help="Fixture directory root (defaults to data/m7)")
    args = parser.parse_args()
    hashes = generate_all(args.output_root)
    for path, digest in hashes.items():
        print(f"{digest}  {path}")


if __name__ == "__main__":
    main()
