"""Permanent M1 extraction invariants over the provided source PDFs."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pytest
import yaml

from poc.extract import _build_composite_bytes, extract_document
from poc.models import Document, Figure, Heading, Paragraph, Table


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "waterfall": "WaterFall_PM_Documentation 1.pdf",
    "kanban": "Kanban_PM_Final 2.pdf",
}


@pytest.fixture(scope="module")
def extraction_runs(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, Path]:
    """Extract both PDFs twice into isolated work roots for repeatability checks."""
    config = yaml.safe_load((ROOT / "config" / "extraction.yaml").read_text(encoding="utf-8"))
    work_roots = []
    for run_name in ("run_a", "run_b"):
        run_root = tmp_path_factory.mktemp(run_name)
        challenge_log = run_root / "challenges_log.md"
        challenge_log.write_text("# Challenges log\n", encoding="utf-8")
        work_root = run_root / "work"
        for doc_id, filename in SOURCES.items():
            extract_document(
                doc_id=doc_id,
                source_path=ROOT / "data" / "input" / filename,
                work_root=work_root,
                extraction_config=config,
                challenges_path=challenge_log,
            )
        work_roots.append(work_root)
    return work_roots[0], work_roots[1]


def _load_document(work_root: Path, doc_id: str) -> Document:
    return Document.model_validate_json((work_root / doc_id / "elements.json").read_text(encoding="utf-8"))


def test_elements_json_is_deterministic_across_two_runs(extraction_runs: tuple[Path, Path]) -> None:
    first, second = extraction_runs
    for doc_id in SOURCES:
        first_files = {
            path.relative_to(first / doc_id): path.read_bytes()
            for path in (first / doc_id).rglob("*")
            if path.is_file()
        }
        second_files = {
            path.relative_to(second / doc_id): path.read_bytes()
            for path in (second / doc_id).rglob("*")
            if path.is_file()
        }
        assert first_files == second_files


def test_all_part_hashes_match_and_composites_rebuild(extraction_runs: tuple[Path, Path]) -> None:
    first, _ = extraction_runs
    for doc_id in SOURCES:
        doc_root = first / doc_id
        document = _load_document(first, doc_id)
        for figure in (element for element in document.elements if isinstance(element, Figure)):
            display_path = doc_root / figure.image_path
            assert hashlib.sha256(display_path.read_bytes()).hexdigest() == figure.sha256
            assert figure.parts
            for part in figure.parts:
                part_bytes = (doc_root / part.image_path).read_bytes()
                assert hashlib.sha256(part_bytes).hexdigest() == part.sha256
                mask_bytes = (doc_root / part.mask_path).read_bytes() if part.mask_path else None
                if mask_bytes is not None:
                    assert hashlib.sha256(mask_bytes).hexdigest() == part.mask_sha256
            if len(figure.parts) > 1:
                raw_parts = []
                for part in figure.parts:
                    raw_parts.append({
                        "xref": part.xref,
                        "bbox": part.bbox,
                        "width": part.width,
                        "height": part.height,
                        "_bytes": (doc_root / part.image_path).read_bytes(),
                        "_mask_bytes": (doc_root / part.mask_path).read_bytes() if part.mask_path else None,
                    })
                rebuilt, _, _, _ = _build_composite_bytes(raw_parts, figure.bbox, rounding_tolerance_px=1)
                assert hashlib.sha256(rebuilt).hexdigest() == figure.sha256
            else:
                assert figure.sha256 == figure.parts[0].sha256


def test_table_text_is_not_duplicated_in_paragraphs(extraction_runs: tuple[Path, Path]) -> None:
    first, _ = extraction_runs
    for doc_id in SOURCES:
        document = _load_document(first, doc_id)
        table_cells = {
            " ".join(cell.split())
            for table in document.elements
            if isinstance(table, Table)
            for row in table.rows
            for cell in row
            if cell.strip()
        }
        paragraph_text = {
            " ".join("".join(span.text for span in paragraph.spans).split())
            for paragraph in document.elements
            if isinstance(paragraph, Paragraph)
        }
        assert not table_cells.intersection(paragraph_text)
        for table in (element for element in document.elements if isinstance(element, Table)):
            tx0, ty0, tx1, ty1 = table.bbox
            for paragraph in (element for element in document.elements if isinstance(element, Paragraph)):
                if paragraph.page != table.page:
                    continue
                px0, py0, px1, py1 = paragraph.bbox
                paragraph_center = ((px0 + px1) / 2, (py0 + py1) / 2)
                assert not (tx0 <= paragraph_center[0] <= tx1 and ty0 <= paragraph_center[1] <= ty1)


def test_table_shapes_from_configured_line_strategy(extraction_runs: tuple[Path, Path]) -> None:
    first, _ = extraction_runs
    expected = {
        "waterfall": [(11, 2), (7, 3), (6, 3), (9, 2), (6, 2), (6, 2)],
        "kanban": [(11, 2), (5, 2), (8, 2), (6, 2)],
    }
    for doc_id, expected_shapes in expected.items():
        document = _load_document(first, doc_id)
        actual = [(element.n_rows, element.n_cols) for element in document.elements if isinstance(element, Table)]
        assert actual == expected_shapes


def test_numbered_heading_levels(extraction_runs: tuple[Path, Path]) -> None:
    first, _ = extraction_runs
    expected = {"waterfall": {1: 10, 2: 11}, "kanban": {1: 10, 2: 8}}
    for doc_id, level_counts in expected.items():
        document = _load_document(first, doc_id)
        actual = {}
        for element in document.elements:
            if isinstance(element, Heading):
                actual[element.level] = actual.get(element.level, 0) + 1
        assert actual == level_counts


def test_expected_image_grouping_and_parts_stay_on_figure_page(extraction_runs: tuple[Path, Path]) -> None:
    first, _ = extraction_runs
    expectations = {"waterfall": (5, 9), "kanban": (3, 4)}
    for doc_id, (expected_figures, expected_parts) in expectations.items():
        document = _load_document(first, doc_id)
        figures = [element for element in document.elements if isinstance(element, Figure)]
        assert len(figures) == expected_figures
        assert sum(len(figure.parts) for figure in figures) == expected_parts
        for figure in figures:
            assert figure.parts
            assert all(part.page == figure.page for part in figure.parts)
            assert all(re.fullmatch(rf"{re.escape(figure.id)}-part\d{{2}}", part.id) for part in figure.parts)
