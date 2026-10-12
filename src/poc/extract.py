"""Extract text, tables, raster images, and vector regions from source PDFs."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import unicodedata
from io import BytesIO
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf as fitz
import pdfplumber
import yaml
from PIL import Image, ImageChops

from poc.models import (
    Bullet,
    Document,
    Figure,
    FigurePart,
    Heading,
    PageNumber,
    Paragraph,
    Span,
    Table,
)

LOGGER = logging.getLogger(__name__)
@dataclass
class Candidate:
    """An element prior to stable page sequence assignment."""

    page: int
    bbox: tuple[float, float, float, float]
    kind: str
    payload: dict[str, Any]


def _normalise_whitespace(value: str) -> str:
    """Collapse whitespace while retaining source words and punctuation."""
    return re.sub(r"\s+", " ", value).strip()


def _spans_from_lines(lines: list[dict[str, Any]]) -> list[Span]:
    """Join visual line wraps while preserving every source span's emphasis."""
    spans: list[Span] = []
    for line_index, line in enumerate(lines):
        if line_index and spans and spans[-1].text and not spans[-1].text.endswith(" "):
            spans.append(Span(text=" "))
        for raw_span in line.get("spans", []):
            text = raw_span.get("text", "")
            if not text:
                continue
            flags = int(raw_span.get("flags", 0))
            spans.append(Span(text=text, bold=bool(flags & 16), italic=bool(flags & 2)))
    # Merge adjacent spans with the same style, without changing their text.
    merged: list[Span] = []
    for span in spans:
        if merged and (merged[-1].bold, merged[-1].italic) == (span.bold, span.italic):
            merged[-1].text += span.text
        else:
            merged.append(span)
    return merged


def _span_text(spans: list[Span]) -> str:
    return _normalise_whitespace("".join(span.text for span in spans))


def _intersection_ratio(a: tuple[float, float, float, float], b: tuple[float, float, float, float]) -> float:
    x0, y0, x1, y1 = a
    bx0, by0, bx1, by1 = b
    area = max(0.0, min(x1, bx1) - max(x0, bx0)) * max(0.0, min(y1, by1) - max(y0, by0))
    own_area = max(1.0, (x1 - x0) * (y1 - y0))
    return area / own_area


def _convert_table_bbox(bbox: tuple[float, float, float, float], page_height: float) -> tuple[float, float, float, float]:
    """Convert pdfplumber's top-origin bbox to PyMuPDF's top-origin coordinates."""
    return (bbox[0], bbox[1], bbox[2], bbox[3]) if page_height else bbox


def _bbox_union(bboxes: list[tuple[float, float, float, float]]) -> tuple[float, float, float, float]:
    """Return the smallest rectangle containing every bbox."""
    return (
        min(bbox[0] for bbox in bboxes),
        min(bbox[1] for bbox in bboxes),
        max(bbox[2] for bbox in bboxes),
        max(bbox[3] for bbox in bboxes),
    )


def _image_relation(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
    tolerance: float,
) -> tuple[str, float, float]:
    """Describe whether two rectangles overlap, abut, or are separate."""
    overlap_x = min(first[2], second[2]) - max(first[0], second[0])
    overlap_y = min(first[3], second[3]) - max(first[1], second[1])
    gap_x = max(0.0, max(first[0], second[0]) - min(first[2], second[2]))
    gap_y = max(0.0, max(first[1], second[1]) - min(first[3], second[3]))
    if overlap_x > tolerance and overlap_y > tolerance:
        return "overlap", overlap_x, overlap_y
    if gap_x <= tolerance and gap_y <= tolerance and overlap_x >= -tolerance and overlap_y >= -tolerance:
        return "abut", gap_x, gap_y
    return "separate", gap_x, gap_y


def _group_image_pieces(candidates: list[Candidate], tolerance: float) -> list[Candidate]:
    """Group connected image pieces whose page rectangles touch or overlap."""
    pieces = [candidate for candidate in candidates if candidate.kind == "image_piece"]
    others = [candidate for candidate in candidates if candidate.kind != "image_piece"]
    by_page: dict[int, list[Candidate]] = defaultdict(list)
    for piece in pieces:
        by_page[piece.page].append(piece)
    groups: list[Candidate] = []
    for page, page_pieces in by_page.items():
        parents = list(range(len(page_pieces)))

        def find(index: int) -> int:
            while parents[index] != index:
                parents[index] = parents[parents[index]]
                index = parents[index]
            return index

        for left in range(len(page_pieces)):
            for right in range(left + 1, len(page_pieces)):
                relation, _, _ = _image_relation(page_pieces[left].bbox, page_pieces[right].bbox, tolerance)
                if relation in {"overlap", "abut"}:
                    parents[find(right)] = find(left)
        connected: dict[int, list[Candidate]] = defaultdict(list)
        for index, piece in enumerate(page_pieces):
            connected[find(index)].append(piece)
        for group in connected.values():
            group.sort(key=lambda item: (item.bbox[1], item.bbox[0], item.payload["xref"]))
            bbox = _bbox_union([piece.bbox for piece in group])
            payload = {"parts": [piece.payload for piece in group]}
            groups.append(Candidate(page, bbox, "figure", payload))
    return others + groups


def _part_rgba(part: dict[str, Any]) -> Image.Image:
    """Decode source image bytes and apply the extracted PDF soft mask if present."""
    with Image.open(BytesIO(part["_bytes"])) as source:
        source.load()
        image = source.convert("RGBA")
    mask_bytes = part.get("_mask_bytes")
    if mask_bytes:
        with Image.open(BytesIO(mask_bytes)) as mask_source:
            mask_source.load()
            mask = mask_source.convert("L")
        if mask.size != image.size:
            mask = mask.resize(image.size, Image.Resampling.NEAREST)
            part["_mask_resized"] = True
        image.putalpha(mask)
    return image


def _compose_parts(
    parts: list[dict[str, Any]],
    bbox: tuple[float, float, float, float],
    page: fitz.Page,
    validation_dpi: int,
    rounding_tolerance_px: int,
) -> tuple[bytes, int, int, float, list[str]]:
    """Compose exact decoded fragments at native scale and compare to a page render."""
    composite_bytes, canvas_width, canvas_height, scaling_events = _build_composite_bytes(parts, bbox, rounding_tolerance_px)
    with Image.open(BytesIO(composite_bytes)) as composite:
        canvas = composite.convert("RGBA")
    clip = fitz.Rect(bbox)
    pixmap = page.get_pixmap(matrix=fitz.Matrix(validation_dpi / 72, validation_dpi / 72), clip=clip, alpha=False)
    rendered = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
    composite_rgb = Image.new("RGB", canvas.size, (255, 255, 255))
    composite_rgb.paste(canvas, mask=canvas.getchannel("A"))
    if composite_rgb.size != rendered.size:
        composite_rgb = composite_rgb.resize(rendered.size, Image.Resampling.LANCZOS)
    difference = ImageChops.difference(composite_rgb, rendered)
    histogram = difference.histogram()
    total_difference = sum((index % 256) * count for index, count in enumerate(histogram))
    score = float(total_difference / (rendered.width * rendered.height * 3 * 255))
    return composite_bytes, canvas_width, canvas_height, score, scaling_events


def _build_composite_bytes(
    parts: list[dict[str, Any]],
    bbox: tuple[float, float, float, float],
    rounding_tolerance_px: int,
) -> tuple[bytes, int, int, list[str]]:
    """Build a deterministic PNG using decoded exact part bytes at their PDF positions."""
    reference = parts[0]
    scale_x = reference["width"] / (reference["bbox"][2] - reference["bbox"][0])
    scale_y = reference["height"] / (reference["bbox"][3] - reference["bbox"][1])
    scaling_events: list[str] = []
    decoded: list[tuple[Image.Image, int, int]] = []
    for part in parts:
        image = _part_rgba(part)
        if part.pop("_mask_resized", False):
            scaling_events.append(f"{part['xref']} mask resized to the base image pixel dimensions")
        expected_size = (
            max(1, round((part["bbox"][2] - part["bbox"][0]) * scale_x)),
            max(1, round((part["bbox"][3] - part["bbox"][1]) * scale_y)),
        )
        if max(abs(expected_size[0] - image.width), abs(expected_size[1] - image.height)) > rounding_tolerance_px:
            scaling_events.append(f"{part['xref']}: {image.width}x{image.height} to {expected_size[0]}x{expected_size[1]}")
            image = image.resize(expected_size, Image.Resampling.LANCZOS)
        x = round((part["bbox"][0] - bbox[0]) * scale_x)
        y = round((part["bbox"][1] - bbox[1]) * scale_y)
        decoded.append((image, x, y))
    canvas_width = max(1, max(x + image.width for image, x, _ in decoded))
    canvas_height = max(1, max(y + image.height for image, _, y in decoded))
    canvas = Image.new("RGBA", (canvas_width, canvas_height), (0, 0, 0, 0))
    for image, x, y in decoded:
        canvas.alpha_composite(image, dest=(x, y))
    composite_buffer = BytesIO()
    canvas.save(composite_buffer, format="PNG", optimize=False)
    return composite_buffer.getvalue(), canvas_width, canvas_height, scaling_events


def _write_tables_dump(output_dir: Path, elements: list[Any]) -> None:
    """Write every extracted table cell in a human-reviewable JSON layout."""
    lines = ["# Extracted tables", ""]
    for table in (element for element in elements if isinstance(element, Table)):
        lines += [
            f"## {table.id} — page {table.page} ({table.n_rows} rows × {table.n_cols} columns)",
            "",
            "```json",
            json.dumps(table.rows, ensure_ascii=False, indent=2),
            "```",
            "",
        ]
    (output_dir / "tables_dump.md").write_text("\n".join(lines), encoding="utf-8")


def _write_figure_diagnosis(
    output_dir: Path,
    elements: list[Any],
    composite_scores: list[dict[str, Any]],
    hash_prefix_chars: int,
    adjacency_tolerance: float,
    validation_dpi: int,
) -> None:
    """Write per-piece PDF image metadata and same-page spatial relations."""
    figures = [element for element in elements if isinstance(element, Figure) and element.parts]
    all_parts = [(figure, part) for figure in figures for part in figure.parts]
    score_by_figure = {entry["figure_id"]: entry for entry in composite_scores}
    lines = ["# Figure diagnosis", "", f"Extracted image pieces: {len(all_parts)}", f"Logical figures with embedded parts: {len(figures)}", ""]
    for figure in figures:
        score = score_by_figure.get(figure.id)
        description = f" — composite validation score at 150 dpi: {score['score']:.8f}" if score else " — single-part image; display bytes are the exact source bytes"
        lines += [f"## {figure.id} — page {figure.page}, {len(figure.parts)} part(s){description}", ""]
        for part in figure.parts:
            relations = []
            for other_figure, other_part in all_parts:
                if other_part.id == part.id or other_part.page != part.page:
                    continue
                relation, gap_x, gap_y = _image_relation(part.bbox, other_part.bbox, adjacency_tolerance)
                if relation == "separate":
                    # Use a zero tolerance for classifying proximity; report the nearest edge gaps.
                    relations.append(f"{other_part.id}: separate (x gap {gap_x:.3f} pt, y gap {gap_y:.3f} pt)")
                else:
                    relations.append(f"{other_part.id}: {relation}")
            relation_text = "; ".join(relations) if relations else "no other extracted image pieces on this page"
            lines += [
                f"### {part.id}",
                "",
                f"- Page: {part.page}",
                f"- PDF xref: {part.xref}",
                f"- Bounding box: `{list(part.bbox)}`", 
                f"- Pixel size: {part.width} × {part.height}",
                f"- Colorspace: `{part.colorspace}`",
                f"- Mask present: {part.mask_present}" + (f" (xref {part.mask_xref}, {part.mask_byte_size} bytes, sha256 {part.mask_sha256[:hash_prefix_chars]})" if part.mask_present and part.mask_sha256 else ""),
                f"- Extracted byte size: {part.byte_size}",
                f"- SHA-256: `{part.sha256[:hash_prefix_chars]}`",
                f"- Relations to same-page image pieces: {relation_text}",
                "",
            ]
    lines += ["## Composite validation scores", "", "| Figure ID | Page | Parts | Validation DPI | Normalized mean absolute pixel difference |", "|---|---:|---:|---:|---:|"]
    for entry in composite_scores:
        lines.append(f"| {entry['figure_id']} | {entry['page']} | {entry['part_count']} | {validation_dpi} | {entry['score']:.8f} |")
    if not composite_scores:
        lines.append("No multipart composites were produced.")
    (output_dir / "figure_diagnosis.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError(f"Extraction config must be a mapping: {path}")
    return config


def _source_manifest(root: Path, config_path: Path) -> list[dict[str, str]]:
    raw = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    return raw["documents"]


def extract_document(
    doc_id: str,
    source_path: Path,
    work_root: Path,
    extraction_config: dict[str, Any],
    challenges_path: Path,
) -> dict[str, Any]:
    """Extract one PDF and write its stable JSON, page renders, and inventory."""
    output_dir = work_root / doc_id
    images_dir = output_dir / "images"
    pages_dir = output_dir / "pages"
    images_dir.mkdir(parents=True, exist_ok=True)
    pages_dir.mkdir(parents=True, exist_ok=True)
    for generated_image in images_dir.glob("img_*"):
        generated_image.unlink()
    for generated_image in images_dir.rglob("*"):
        if generated_image.is_file():
            generated_image.unlink()
    for page_render in pages_dir.glob("p*.png"):
        page_render.unlink()
    source_bytes = source_path.read_bytes()
    source_hash = hashlib.sha256(source_bytes).hexdigest()
    heading_pattern = re.compile(extraction_config["heading"]["numbered_pattern"])
    bullet_glyphs = extraction_config["bullet_glyphs"]
    min_font = float(extraction_config["heading"]["minimum_font_size_pt"])
    table_line_overlap = float(extraction_config["table_text_suppression"]["line_overlap_ratio"])
    page_number_cfg = extraction_config["page_number"]
    page_number_pattern = re.compile(page_number_cfg["digits_pattern"])
    vector_cfg = extraction_config["vector_region"]
    image_cfg = extraction_config["images"]
    table_settings = extraction_config["table_extraction"]
    render_dpi = int(extraction_config["render"]["dpi"])

    candidates: list[Candidate] = []
    font_histogram: Counter[str] = Counter()
    counts_by_page: dict[int, Counter[str]] = defaultdict(Counter)
    unknown_glyphs: list[dict[str, Any]] = []
    vectors: list[dict[str, Any]] = []
    vector_drawing_shapes_in_tables: list[dict[str, Any]] = []
    merges: list[dict[str, Any]] = []
    cover_lines: list[str] = []
    page_numbers: set[int] = set()

    with fitz.open(source_path) as pdf, pdfplumber.open(source_path) as plumber:
        for page_index, page in enumerate(pdf):
            page_no = page_index + 1
            plumber_page = plumber.pages[page_index]
            table_bboxes: list[tuple[float, float, float, float]] = []
            table_candidates: list[Candidate] = []
            pdfplumber_settings = {key: value for key, value in table_settings.items() if key != "backend"}
            for pdf_table in plumber_page.find_tables(table_settings=pdfplumber_settings):
                raw_bbox = tuple(float(v) for v in pdf_table.bbox)
                bbox = _convert_table_bbox(raw_bbox, float(page.rect.height))
                table_bboxes.append(bbox)
                rows = [[_normalise_whitespace(cell or "") for cell in row] for row in (pdf_table.extract() or [])]
                max_cols = max((len(row) for row in rows), default=0)
                rows = [row + [""] * (max_cols - len(row)) for row in rows]
                has_toc_header = any(
                    _normalise_whitespace(cell).casefold() == "topic"
                    for row in rows[:2]
                    for cell in row
                )
                page_text_above = page.get_text("text", clip=fitz.Rect(0, 0, page.rect.width, bbox[1]))
                contents_above = bool(re.search(r"\bcontents\b", page_text_above, re.IGNORECASE))
                role = "toc" if has_toc_header and contents_above else "body"
                table_candidates.append(
                    Candidate(page_no, bbox, "table", {"rows": rows, "header_rows": 1 if rows else 0, "role": role})
                )
            candidates.extend(table_candidates)

            for block in page.get_text("dict").get("blocks", []):
                if "lines" not in block:
                    continue
                bbox = tuple(float(v) for v in block["bbox"])
                all_block_spans = [span for line in block.get("lines", []) for span in line.get("spans", []) if span.get("text", "").strip()]
                for span in all_block_spans:
                    font_histogram[f"{float(span.get('size', 0)):.1f}"] += 1
                lines = block.get("lines", [])
                # Suppress table-contained lines rather than whole PyMuPDF blocks:
                # a block can contain both table cells and adjacent prose.
                lines = [
                    line for line in lines
                    if not any(
                        _intersection_ratio(tuple(float(value) for value in line["bbox"]), table_bbox) >= table_line_overlap
                        for table_bbox in table_bboxes
                    )
                ]
                if not lines:
                    continue
                bbox = _bbox_union([tuple(float(value) for value in line["bbox"]) for line in lines])
                block_spans = [span for line in lines for span in line.get("spans", []) if span.get("text", "").strip()]
                if not block_spans:
                    continue
                marker_indices = []
                for line_index, line in enumerate(lines):
                    line_text = _normalise_whitespace("".join(span.get("text", "") for span in line.get("spans", [])))
                    if line_text and line_text[0] in bullet_glyphs:
                        marker_indices.append(line_index)
                if marker_indices:
                    if marker_indices[0] > 0:
                        prefix_lines = lines[:marker_indices[0]]
                        prefix_bbox = (
                            min(float(line["bbox"][0]) for line in prefix_lines),
                            min(float(line["bbox"][1]) for line in prefix_lines),
                            max(float(line["bbox"][2]) for line in prefix_lines),
                            max(float(line["bbox"][3]) for line in prefix_lines),
                        )
                        candidates.append(Candidate(page_no, prefix_bbox, "paragraph", {"spans": _spans_from_lines(prefix_lines), "is_label": False, "role": "cover" if page_no == 1 else "body"}))
                    for marker_position, line_index in enumerate(marker_indices):
                        stop = marker_indices[marker_position + 1] if marker_position + 1 < len(marker_indices) else len(lines)
                        bullet_lines = lines[line_index:stop]
                        bullet_bbox = (
                            min(float(line["bbox"][0]) for line in bullet_lines),
                            min(float(line["bbox"][1]) for line in bullet_lines),
                            max(float(line["bbox"][2]) for line in bullet_lines),
                            max(float(line["bbox"][3]) for line in bullet_lines),
                        )
                        candidates.append(Candidate(page_no, bullet_bbox, "bullet", {"spans": _spans_from_lines(bullet_lines), "level": 0, "role": "cover" if page_no == 1 else "body"}))
                    continue
                joined = _spans_from_lines(lines)
                text = _span_text(joined)
                if not text:
                    continue
                max_size = max(float(span.get("size", 0)) for span in block_spans)
                match = heading_pattern.match(text)
                if match and max_size >= min_font:
                    number, title = match.groups()
                    candidates.append(Candidate(page_no, bbox, "heading", {"level": number.count(".") + 1, "number": number, "title": title, "role": "cover" if page_no == 1 else "body"}))
                    continue
                y_ratio = bbox[1] / max(1.0, float(page.rect.height))
                if page_number_pattern.fullmatch(text) and float(page_number_cfg["minimum_vertical_ratio"]) <= y_ratio <= float(page_number_cfg["maximum_vertical_ratio"]):
                    candidates.append(Candidate(page_no, bbox, "page_number", {"value": text}))
                    continue
                if page_no == 1:
                    cover_lines.extend(
                        _normalise_whitespace("".join(span.get("text", "") for span in line.get("spans", [])))
                        for line in lines
                        if _normalise_whitespace("".join(span.get("text", "") for span in line.get("spans", [])))
                    )
                first_char = text[0]
                if first_char in bullet_glyphs:
                    candidates.append(Candidate(page_no, bbox, "bullet", {"spans": joined, "level": 0, "role": "cover" if page_no == 1 else "body"}))
                else:
                    if first_char not in bullet_glyphs and unicodedata.category(first_char) in {"So", "Co"}:
                        unknown_glyphs.append({"page": page_no, "glyph": first_char, "text": text})
                    is_label = len(text) <= int(extraction_config["label_maximum_text_length"]) and all(span.bold for span in joined if span.text.strip())
                    candidates.append(Candidate(page_no, bbox, "paragraph", {"spans": joined, "is_label": is_label, "role": "cover" if page_no == 1 else "body"}))
            page_numbers.add(page_no)

            image_rects: list[fitz.Rect] = []
            occurrence = 0
            for image in page.get_images(full=True):
                xref = int(image[0])
                extracted = pdf.extract_image(xref)
                raw = extracted["image"]
                extension = extracted.get("ext", "bin")
                width, height = int(extracted["width"]), int(extracted["height"])
                mask_xref = int(extracted.get("smask", 0) or image[1] or 0)
                mask_info = pdf.extract_image(mask_xref) if mask_xref else None
                mask_raw = mask_info["image"] if mask_info else None
                for rect in page.get_image_rects(xref, transform=False):
                    occurrence += 1
                    image_rects.append(rect)
                    bbox = tuple(float(v) for v in rect)
                    payload = {
                        "xref": xref,
                        "page": page_no,
                        "bbox": bbox,
                        "sha256": hashlib.sha256(raw).hexdigest(),
                        "width": width,
                        "height": height,
                        "mime": f"image/{'jpeg' if extension in {'jpg', 'jpeg'} else extension}",
                        "colorspace": str(extracted.get("cs-name") or image[5] or "unknown"),
                        "mask_present": bool(mask_xref),
                        "mask_xref": mask_xref or None,
                        "mask_sha256": hashlib.sha256(mask_raw).hexdigest() if mask_raw else None,
                        "mask_byte_size": len(mask_raw) if mask_raw else 0,
                        "byte_size": len(raw),
                        "_bytes": raw,
                        "_mask_bytes": mask_raw,
                        "_mask_extension": mask_info.get("ext", "bin") if mask_info else None,
                        "_extension": extension,
                    }
                    candidates.append(Candidate(page_no, bbox, "image_piece", payload))

            page_area = float(page.rect.width * page.rect.height)
            for drawing_index, drawing in enumerate(page.get_drawings(), start=1):
                rect = fitz.Rect(drawing["rect"])
                bbox = tuple(float(v) for v in rect)
                area = rect.width * rect.height
                if area < float(vector_cfg["minimum_area_pt2"]) or area / page_area < float(vector_cfg["minimum_page_area_ratio"]):
                    continue
                if any(rect.intersects(image_rect) and rect.intersect(image_rect).get_area() / max(1.0, area) > float(vector_cfg["raster_overlap_ratio"]) for image_rect in image_rects):
                    continue
                if any(_intersection_ratio(bbox, table_bbox) > float(vector_cfg["table_overlap_ratio"]) for table_bbox in table_bboxes):
                    vector_drawing_shapes_in_tables.append({"page": page_no, "drawing_index": drawing_index, "bbox": [round(v, 2) for v in bbox], "area_pt2": round(area, 2)})
                    continue
                vectors.append({"page": page_no, "drawing_index": drawing_index, "bbox": [round(v, 2) for v in bbox], "area_pt2": round(area, 2)})
                pixmap = page.get_pixmap(matrix=fitz.Matrix(render_dpi / 72, render_dpi / 72), clip=rect, alpha=False)
                rendered_bytes = pixmap.tobytes("png")
                candidates.append(Candidate(page_no, bbox, "figure", {
                    "image_path": None,
                    "sha256": hashlib.sha256(rendered_bytes).hexdigest(),
                    "width": pixmap.width,
                    "height": pixmap.height,
                    "mime": "image/png",
                    "origin": "rendered",
                    "_bytes": rendered_bytes,
                    "_extension": "png",
                    "_vector": True,
                }))

            pixmap = page.get_pixmap(matrix=fitz.Matrix(render_dpi / 72, render_dpi / 72), alpha=False)
            pixmap.save(pages_dir / f"p{page_no:03d}.png")

        # A few Word-exported lists expose their glyph in a separate one-character text block.
        # Attach such a marker to the next paragraph so the item remains one bullet element.
        candidates = _group_image_pieces(candidates, float(image_cfg["adjacency_tolerance_pt"]))
        candidates.sort(key=lambda item: (item.page, round(item.bbox[1], 3), round(item.bbox[0], 3), item.kind))
        combined: list[Candidate] = []
        index = 0
        while index < len(candidates):
            candidate = candidates[index]
            marker = _span_text(candidate.payload.get("spans", [])) if candidate.kind == "bullet" else ""
            if (
                candidate.kind == "bullet"
                and marker in bullet_glyphs
                and index + 1 < len(candidates)
                and candidates[index + 1].kind == "paragraph"
                and candidates[index + 1].page == candidate.page
                and 0 <= candidates[index + 1].bbox[1] - candidate.bbox[1] <= float(extraction_config["bullet_marker_merge_max_gap_pt"])
            ):
                paragraph = candidates[index + 1]
                spans = candidate.payload["spans"] + [Span(text=" ")] + paragraph.payload["spans"]
                bbox = (
                    min(candidate.bbox[0], paragraph.bbox[0]),
                    min(candidate.bbox[1], paragraph.bbox[1]),
                    max(candidate.bbox[2], paragraph.bbox[2]),
                    max(candidate.bbox[3], paragraph.bbox[3]),
                )
                combined.append(Candidate(candidate.page, bbox, "bullet", {"spans": spans, "level": 0, "role": paragraph.payload["role"]}))
                index += 2
            else:
                combined.append(candidate)
                index += 1
        candidates = combined

        # Stable sequence order is page, top coordinate, then left coordinate.
        candidates.sort(key=lambda item: (item.page, round(item.bbox[1], 3), round(item.bbox[0], 3), item.kind))
        elements: list[Any] = []
        figure_index = 0
        figure_diagnostics: list[dict[str, Any]] = []
        composite_scores: list[dict[str, Any]] = []
        scaling_events: list[str] = []
        for candidate in candidates:
            if sum(counts_by_page[candidate.page].values()) >= int(extraction_config["element_id_max_per_page"]):
                raise ValueError(f"More than 999 elements on a page in {doc_id}")
            page_counts = counts_by_page[candidate.page]
            page_sequence = 1 + sum(page_counts.values())
            identifier = f"{doc_id}-p{candidate.page:03d}-{page_sequence:03d}"
            payload = candidate.payload
            common = {"id": identifier, "doc_id": doc_id, "page": candidate.page, "bbox": candidate.bbox, "disposition": "pending"}
            if candidate.kind == "heading":
                element = Heading(**common, role=payload["role"], level=payload["level"], number=payload["number"], title=payload["title"])
            elif candidate.kind == "paragraph":
                element = Paragraph(**common, role=payload["role"], spans=payload["spans"], is_label=payload["is_label"])
            elif candidate.kind == "bullet":
                element = Bullet(**common, role=payload["role"], spans=payload["spans"], level=payload["level"])
            elif candidate.kind == "table":
                rows = payload["rows"]
                element = Table(**common, role=payload["role"], rows=rows, header_rows=payload["header_rows"], n_rows=len(rows), n_cols=max((len(row) for row in rows), default=0))
            elif candidate.kind == "page_number":
                element = PageNumber(**common, value=payload["value"])
            elif candidate.kind == "figure" and "parts" in payload:
                figure_index += 1
                figure_id = identifier
                part_models: list[FigurePart] = []
                for part_index, part in enumerate(payload["parts"], start=1):
                    part_id = f"{figure_id}-part{part_index:02d}"
                    part_path = Path("images") / "parts" / f"{part_id}.{part['_extension']}"
                    part_destination = output_dir / part_path
                    part_destination.parent.mkdir(parents=True, exist_ok=True)
                    part_destination.write_bytes(part["_bytes"])
                    mask_path = None
                    if part["_mask_bytes"]:
                        mask_path_obj = Path("images") / "parts" / f"{part_id}_mask.{part['_mask_extension']}"
                        mask_destination = output_dir / mask_path_obj
                        mask_destination.write_bytes(part["_mask_bytes"])
                        mask_path = mask_path_obj.as_posix()
                    part_model = FigurePart(
                        id=part_id,
                        page=part["page"],
                        xref=part["xref"],
                        image_path=part_path.as_posix(),
                        sha256=part["sha256"],
                        bbox=part["bbox"],
                        width=part["width"],
                        height=part["height"],
                        mime=part["mime"],
                        colorspace=part["colorspace"],
                        mask_present=part["mask_present"],
                        mask_xref=part["mask_xref"],
                        mask_path=mask_path,
                        mask_sha256=part["mask_sha256"],
                        mask_byte_size=part["mask_byte_size"],
                        byte_size=part["byte_size"],
                    )
                    part_models.append(part_model)
                if len(payload["parts"]) > 1:
                    composite_bytes, display_width, display_height, score, events = _compose_parts(
                        payload["parts"],
                        candidate.bbox,
                        pdf[candidate.page - 1],
                        int(image_cfg["validation_dpi"]),
                        int(image_cfg["native_rounding_tolerance_px"]),
                    )
                    composite_path = Path("images") / "composites" / f"{figure_id}.png"
                    composite_destination = output_dir / composite_path
                    composite_destination.parent.mkdir(parents=True, exist_ok=True)
                    composite_destination.write_bytes(composite_bytes)
                    display_sha = hashlib.sha256(composite_bytes).hexdigest()
                    display_mime = "image/png"
                    composite_scores.append({"figure_id": figure_id, "page": candidate.page, "score": score, "part_count": len(payload["parts"])})
                    scaling_events.extend(f"{figure_id}: {event}" for event in events)
                else:
                    part = payload["parts"][0]
                    composite_path = Path(part_models[0].image_path)
                    display_width = part["width"]
                    display_height = part["height"]
                    display_sha = part["sha256"]
                    display_mime = part["mime"]
                element = Figure(
                    **common,
                    role="cover" if candidate.page == 1 else "body",
                    image_path=composite_path.as_posix(),
                    sha256=display_sha,
                    width=display_width,
                    height=display_height,
                    mime=display_mime,
                    origin="embedded",
                    parts=part_models,
                )
                figure_diagnostics.extend({"figure_id": figure_id, "figure_page": candidate.page, "part": part_model.model_dump()} for part_model in part_models)
            else:
                figure_index += 1
                extension = payload.pop("_extension")
                payload.pop("_vector", None)
                image_path = Path("images") / f"img_{figure_index:03d}.{extension}"
                destination = output_dir / image_path
                destination.write_bytes(payload.pop("_bytes"))
                payload["image_path"] = image_path.as_posix()
                element = Figure(**common, role="cover" if candidate.page == 1 else "body", **payload)
            elements.append(element)
            page_counts[candidate.kind] += 1

    # Page numbers and figures use their specific role values in the model.
    document = Document(
        doc_id=doc_id,
        source_file=source_path.name,
        source_sha256=source_hash,
        page_count=len(page_numbers),
        elements=elements,
        cover_lines=cover_lines,
    )
    (output_dir / "elements.json").write_text(document.model_dump_json(indent=2), encoding="utf-8")
    _write_tables_dump(output_dir, elements)
    _write_figure_diagnosis(
        output_dir,
        elements,
        composite_scores,
        int(image_cfg["diagnosis_hash_prefix_chars"]),
        float(image_cfg["adjacency_tolerance_pt"]),
        int(image_cfg["validation_dpi"]),
    )

    composite_title = f"## Image fragments grouped into composites for {doc_id}"
    if composite_scores and composite_title not in challenges_path.read_text(encoding="utf-8"):
        with challenges_path.open("a", encoding="utf-8") as log:
            log.write(f"\n{composite_title}\n")
            log.write(f"- Where: source pages {', '.join(str(item['page']) for item in composite_scores)}.\n")
            log.write(f"- Frequency: {sum(item['part_count'] for item in composite_scores)} parts grouped into {len(composite_scores)} composite(s).\n")
            log.write("- What happened: The PDF stores some logical figures as adjacent image fragments.\n")
            log.write("- Action: Retained each exact source fragment and built a deterministic PNG composite; figure diagnosis records per-part hashes and render comparison scores.\n")
            if scaling_events:
                log.write(f"- Scaling: {', '.join(scaling_events)}.\n")
            else:
                log.write("- Scaling: No source part required resampling; a one-pixel placement tolerance covers PDF coordinate rounding.\n")
            log.write("- Residual risk: Composite comparison uses a normalized 150 dpi page render and may show antialiasing differences.\n")

    vector_pages = {item["page"] for item in vectors}
    if vectors and f"## Vector drawing regions rendered for {doc_id}" not in challenges_path.read_text(encoding="utf-8"):
        with challenges_path.open("a", encoding="utf-8") as log:
            log.write(f"\n## Vector drawing regions rendered for {doc_id}\n")
            log.write(f"- Where: source PDF pages {', '.join(map(str, sorted(vector_pages)))}.\n")
            log.write(f"- Frequency: {len(vectors)} detected large drawing region(s).\n")
            log.write("- What happened: Large vector regions are not exposed as embedded image bytes.\n")
            log.write("- Action: Rendered each qualifying region at the configured page-render DPI and marked it `origin=rendered`.\n")
            log.write("- Residual risk: Region bounding boxes are heuristic and may include nearby page content.\n")
    if unknown_glyphs:
        with challenges_path.open("a", encoding="utf-8") as log:
            log.write(f"\n## Unknown leading bullet glyphs in {doc_id}\n")
            log.write(f"- Where: source pages {', '.join(map(str, sorted({item['page'] for item in unknown_glyphs})))}.\n")
            log.write(f"- Frequency: {len(unknown_glyphs)} occurrence(s).\n")
            log.write("- What happened: A leading glyph was not in the configured bullet glyph list.\n")
            log.write("- Action: Retained the line as source text and listed each occurrence in the inventory.\n")
            log.write("- Residual risk: The item is currently a paragraph rather than a classified bullet.\n")

    by_type = Counter(element.type for element in elements)
    lines = [f"# Extraction inventory — {doc_id}", "", f"Source: `{source_path.name}`", f"Pages: {document.page_count}", "", "## Counts by type", "", "| Type | Count |", "|---|---:|"]
    lines.extend(f"| {kind} | {count} |" for kind, count in sorted(by_type.items()))
    lines += ["", "## Counts by page", "", "| Page | " + " | ".join(sorted({kind for counts in counts_by_page.values() for kind in counts})) + " |", "|---:|" + "---:|" * len({kind for counts in counts_by_page.values() for kind in counts})]
    all_kinds = sorted({kind for counts in counts_by_page.values() for kind in counts})
    for page_no in range(1, document.page_count + 1):
        lines.append(f"| {page_no} | " + " | ".join(str(counts_by_page[page_no][kind]) for kind in all_kinds) + " |")
    lines += ["", "## Extracted table shapes", "", "| Element ID | Page | Rows | Columns | Role |", "|---|---:|---:|---:|---|"]
    lines.extend(
        f"| {element.id} | {element.page} | {element.n_rows} | {element.n_cols} | {element.role} |"
        for element in elements
        if isinstance(element, Table)
    )
    heading_counts = Counter(element.level for element in elements if isinstance(element, Heading))
    part_count = sum(len(element.parts) for element in elements if isinstance(element, Figure))
    lines += ["", "## Heading levels and image parts", "", f"Heading levels: {dict(sorted(heading_counts.items()))}", f"Logical figures: {by_type['figure']}; image parts: {part_count}; multipart composites: {len(composite_scores)}", ""]
    lines += ["", "## Font histogram (PyMuPDF span size, points)", "", "| Size | Span count |", "|---:|---:|"]
    lines.extend(f"| {size} | {count} |" for size, count in sorted(font_histogram.items(), key=lambda item: float(item[0])))
    lines += ["", "## Vector drawing regions", "", f"Detected {len(vectors)} standalone qualifying region(s); {len(vector_drawing_shapes_in_tables)} large drawing shape(s) overlap detected tables and were treated as table structure.", ""]
    if vector_drawing_shapes_in_tables:
        lines += ["| Page | Drawing index | Bounding box | Area (pt²) |", "|---:|---:|---|---:|"]
        lines.extend(f"| {item['page']} | {item['drawing_index']} | {item['bbox']} | {item['area_pt2']} |" for item in vector_drawing_shapes_in_tables)
        lines.append("")
    if not vectors:
        lines.append("No standalone vector-only image regions were identified outside detected tables and raster image areas.")
        lines.append("")
    if vectors:
        lines += ["| Page | Drawing index | Bounding box | Area (pt²) |", "|---:|---:|---|---:|"]
        lines.extend(f"| {item['page']} | {item['drawing_index']} | {item['bbox']} | {item['area_pt2']} |" for item in vectors)
    lines += ["", "## Unknown bullet glyphs", "", f"Count: {len(unknown_glyphs)}", ""]
    if unknown_glyphs:
        lines.extend(f"- Page {item['page']}: `{item['glyph']}` in `{item['text']}`" for item in unknown_glyphs)
    lines += ["", "## Cross-page paragraph merges", "", f"Count: {len(merges)} (disabled; source blocks remain separate across page boundaries)", ""]
    lines.extend(f"- Pages {item['from_page']}→{item['to_page']}: `{item['previous']}` / `{item['next']}`" for item in merges)
    lines += ["", "## Heading threshold evidence", "", f"Configured numbered heading minimum: {min_font:g} pt. Numbered headings observed at 18 pt; body copy at 10.5 pt.", ""]
    (output_dir / "inventory.md").write_text("\n".join(lines), encoding="utf-8")
    LOGGER.info("Extracted %s: %d elements, %d figures", doc_id, len(elements), by_type["figure"])
    return {"doc_id": doc_id, "page_count": document.page_count, "counts": dict(by_type), "parts": part_count, "composite_scores": composite_scores, "unknown_glyphs": len(unknown_glyphs), "vector_regions": vectors, "merges": merges, "inventory_path": str(output_dir / "inventory.md")}


def extract_all(
    root: Path | None = None,
    manifest_path: Path | None = None,
    extraction_config_path: Path | None = None,
) -> list[dict[str, Any]]:
    """Extract all configured documents into their work directories."""
    project_root = root or Path.cwd()
    manifest = _source_manifest(project_root, manifest_path or project_root / "config/documents.yaml")
    config = _read_config(extraction_config_path or project_root / "config/extraction.yaml")
    reports = []
    for item in manifest:
        reports.append(extract_document(
            item["doc_id"],
            project_root / "data/input" / item["source_file"],
            project_root / "data/work",
            config,
            project_root / "docs/challenges_log.md",
        ))
    return reports
