"""Acceptance checks for the M0 scaffold."""

from pathlib import Path

import fitz
import yaml
from pydantic import BaseModel, ConfigDict

from poc.models import Document, Paragraph, Span


ROOT = Path(__file__).resolve().parents[1]


class TargetSection(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    accepts: list[str]


class TargetAppendix(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    title: str
    generated: bool


class TargetFormat(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: str
    title_template: str
    sections: list[TargetSection]
    appendices: list[TargetAppendix]
    generated_label: str


def test_input_pdfs_open_with_expected_page_counts() -> None:
    expected = {
        "WaterFall_PM_Documentation 1.pdf": 14,
        "Kanban_PM_Final 2.pdf": 7,
    }
    for filename, page_count in expected.items():
        with fitz.open(ROOT / "data" / "input" / filename) as pdf:
            assert pdf.page_count == page_count


def test_target_format_loads_and_validates() -> None:
    raw = yaml.safe_load((ROOT / "config" / "target_format.yaml").read_text())
    target = TargetFormat.model_validate(raw)
    assert len(target.sections) == 6


def test_document_models_round_trip_to_json() -> None:
    paragraph = Paragraph(
        id="waterfall-p001-001",
        doc_id="waterfall",
        page=1,
        bbox=(0, 0, 10, 10),
        role="cover",
        spans=[Span(text="Sample", bold=True)],
    )
    document = Document(
        doc_id="waterfall",
        source_file="sample.pdf",
        source_sha256="0" * 64,
        page_count=1,
        elements=[paragraph],
        cover_lines=["Sample"],
    )
    assert Document.model_validate_json(document.model_dump_json()) == document
