"""Per-page source-word conservation checks for both M1 PDFs."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from pathlib import Path

import pymupdf
import pytest
import yaml

from poc.extract import extract_document
from poc.models import Bullet, Document, Heading, PageNumber, Paragraph, Table


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "waterfall": "WaterFall_PM_Documentation 1.pdf",
    "kanban": "Kanban_PM_Final 2.pdf",
}
WORD = re.compile(r"[^\W_]+(?:['’][^\W_]+)*", re.UNICODE)
LIGATURES = str.maketrans({"ﬀ": "ff", "ﬁ": "fi", "ﬂ": "fl", "ﬃ": "ffi", "ﬄ": "ffl", "ﬅ": "st", "ﬆ": "st"})


def _words(value: str) -> list[str]:
    value = unicodedata.normalize("NFKC", value.translate(LIGATURES))
    value = "".join(char for char in value if unicodedata.category(char) != "Co")
    return [word.casefold() for word in WORD.findall(value)]


def _element_words(element: object) -> list[str]:
    if isinstance(element, (Paragraph, Bullet)):
        return _words("".join(span.text for span in element.spans))
    if isinstance(element, Heading):
        return _words(f"{element.number or ''} {element.title}")
    if isinstance(element, Table):
        return [word for row in element.rows for cell in row for word in _words(cell)]
    if isinstance(element, PageNumber):
        return _words(element.value)
    return []


def _audit_document(pdf_path: Path, document: Document) -> list[dict[str, object]]:
    by_page: dict[int, list[str]] = {page: [] for page in range(1, document.page_count + 1)}
    for element in document.elements:
        by_page.setdefault(element.page, []).extend(_element_words(element))
    results = []
    with pymupdf.open(pdf_path) as pdf:
        for page_no, page in enumerate(pdf, 1):
            pdf_words = [word for item in page.get_text("words") for word in _words(item[4])]
            element_words = by_page.get(page_no, [])
            pdf_counts, element_counts = Counter(pdf_words), Counter(element_words)
            missing = pdf_counts - element_counts
            extra = element_counts - pdf_counts
            results.append({
                "page": page_no,
                "pdf_total": len(pdf_words),
                "element_total": len(element_words),
                "missing": sorted(missing.elements()),
                "extra": sorted(extra.elements()),
            })
    return results


def _audit(pdf_path: Path, elements_path: Path) -> list[dict[str, object]]:
    document = Document.model_validate_json(elements_path.read_text(encoding="utf-8"))
    return _audit_document(pdf_path, document)


@pytest.fixture(scope="module")
def audited_documents(tmp_path_factory: pytest.TempPathFactory) -> dict[str, list[dict[str, object]]]:
    config = yaml.safe_load((ROOT / "config" / "extraction.yaml").read_text(encoding="utf-8"))
    work_root = tmp_path_factory.mktemp("conservation") / "work"
    challenges = work_root.parent / "challenges_log.md"
    challenges.write_text("# Challenges log\n", encoding="utf-8")
    audited = {}
    for doc_id, filename in SOURCES.items():
        extract_document(doc_id, ROOT / "data" / "input" / filename, work_root, config, challenges)
        audited[doc_id] = _audit(ROOT / "data" / "input" / filename, work_root / doc_id / "elements.json")
    return audited


def test_every_pdf_word_is_represented_and_report_page_totals(audited_documents: dict[str, list[dict[str, object]]]) -> None:
    failures = []
    for doc_id, pages in audited_documents.items():
        print(f"\n### {doc_id}")
        print("page | PDF words | element words | missing | extra")
        for result in pages:
            missing = result["missing"]
            extra = result["extra"]
            print(f"{result['page']} | {result['pdf_total']} | {result['element_total']} | {missing} | {extra}")
            if missing:
                failures.append(f"{doc_id} page {result['page']}: missing {missing}")
    assert not failures, "Source words missing from extracted elements:\n" + "\n".join(failures)


def test_conservation_reports_exact_text_removed_from_memory(tmp_path: Path) -> None:
    config = yaml.safe_load((ROOT / "config" / "extraction.yaml").read_text(encoding="utf-8"))
    work_root = tmp_path / "work"
    challenges = tmp_path / "challenges_log.md"
    challenges.write_text("# Challenges log\n", encoding="utf-8")
    pdf_path = ROOT / "data" / "input" / SOURCES["waterfall"]
    extract_document("waterfall", pdf_path, work_root, config, challenges)
    document = Document.model_validate_json((work_root / "waterfall" / "elements.json").read_text(encoding="utf-8"))
    target = next(element for element in document.elements if isinstance(element, Paragraph) and _element_words(element))
    target_page = target.page
    removed_words = _element_words(target)
    document.elements.remove(target)
    result = next(page for page in _audit_document(pdf_path, document) if page["page"] == target_page)
    assert result["missing"] == sorted(removed_words)
    assert result["extra"] == []
