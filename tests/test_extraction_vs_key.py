"""Compare M1 extraction output with the immutable M2 draft key."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
import yaml

from poc.extract import extract_document
from poc.models import Bullet, Document, Figure, Heading, PageNumber, Paragraph, Table


ROOT = Path(__file__).resolve().parents[1]
KEY = json.loads((ROOT / "docs" / "answer_key.json").read_text(encoding="utf-8"))
SOURCES = {"waterfall": "WaterFall_PM_Documentation 1.pdf", "kanban": "Kanban_PM_Final 2.pdf"}


def _normalise(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _element_text(element: object) -> str:
    if isinstance(element, (Paragraph, Bullet)):
        return "".join(span.text for span in element.spans)
    if isinstance(element, Heading):
        return f"{element.number or ''} {element.title}"
    if isinstance(element, Table):
        return " ".join(cell for row in element.rows for cell in row)
    if isinstance(element, PageNumber):
        return element.value
    return ""


@pytest.fixture(scope="module")
def extracted(tmp_path_factory: pytest.TempPathFactory) -> dict[str, Document]:
    config = yaml.safe_load((ROOT / "config" / "extraction.yaml").read_text(encoding="utf-8"))
    root = tmp_path_factory.mktemp("key-comparison")
    work = root / "work"
    challenges = root / "challenges_log.md"
    challenges.write_text("# Challenges log\n", encoding="utf-8")
    documents = {}
    for doc_id, filename in SOURCES.items():
        extract_document(doc_id, ROOT / "data" / "input" / filename, work, config, challenges)
        documents[doc_id] = Document.model_validate_json((work / doc_id / "elements.json").read_text(encoding="utf-8"))
    return documents


@pytest.mark.parametrize("doc_id", list(SOURCES))
def test_extraction_counts_and_spot_strings_match_key(doc_id: str, extracted: dict[str, Document]) -> None:
    key = KEY[doc_id]
    document = extracted[doc_id]
    elements = document.elements
    headings = [element for element in elements if isinstance(element, Heading)]
    heading_counts = {level: sum(element.level == level for element in headings) for level in (1, 2)}
    assert document.page_count == key["pages"]
    assert sum(isinstance(element, PageNumber) for element in elements) == key["page_numbers"]
    assert heading_counts == {1: key["h1"], 2: key["h2"]}
    assert all(heading.title.strip() for heading in headings)
    assert sum(isinstance(element, Bullet) for element in elements) == key["bullets"]
    tables = [element for element in elements if isinstance(element, Table)]
    assert len(tables) == key["tables"]
    shapes = [[name, table.n_rows, table.n_cols] for name, table in zip((shape[0] for shape in key["table_shapes"]), tables)]
    assert shapes == key["table_shapes"]
    assert sum(isinstance(element, Figure) for element in elements) == key["figures"]
    assert document.cover_lines == key["cover_lines"]
    corpus = _normalise(" ".join(_element_text(element) for element in elements))
    for spot_string in key["spot_strings"]:
        assert _normalise(spot_string) in corpus


@pytest.mark.parametrize("doc_id", list(SOURCES))
def test_every_table_cell_matches_golden_fixture(doc_id: str, extracted: dict[str, Document]) -> None:
    fixture_path = ROOT / "tests" / "fixtures" / f"golden_tables_{doc_id}.json"
    fixture_text = fixture_path.read_text(encoding="utf-8")
    comment, json_text = fixture_text.split("\n", 1)
    assert comment == "// verified cell by cell against the PDF by the architect"
    golden = json.loads(json_text)
    actual = [element for element in extracted[doc_id].elements if isinstance(element, Table)]
    assert len(actual) == len(golden)
    for actual_table, golden_table in zip(actual, golden):
        assert actual_table.id == golden_table["id"]
        assert actual_table.page == golden_table["page"]
        assert actual_table.rows == golden_table["rows"]


@pytest.mark.parametrize("doc_id", list(SOURCES))
def test_headings_match_golden_fixture_and_keep_number_separate(doc_id: str, extracted: dict[str, Document]) -> None:
    fixture_path = ROOT / "tests" / "fixtures" / f"golden_headings_{doc_id}.json"
    fixture_text = fixture_path.read_text(encoding="utf-8")
    comment, json_text = fixture_text.split("\n", 1)
    assert comment == "// verified against the PDF by the architect"
    golden = json.loads(json_text)
    actual = [
        {"level": element.level, "number": element.number, "title": element.title}
        for element in extracted[doc_id].elements
        if isinstance(element, Heading)
    ]
    assert actual == golden
    for heading in actual:
        if heading["level"] == 2:
            assert heading["number"] and heading["title"]
            assert "." in heading["number"]
            assert not heading["title"].startswith(heading["number"])
