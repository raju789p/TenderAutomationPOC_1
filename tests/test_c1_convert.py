"""Offline C1 conversion tests using deterministic fake structured models."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pymupdf as fitz
import pytest
from docx import Document as WordDocument
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError

from poc.convert.assemble import chunk_elements, validate_chunk_plan
from poc.convert.graph import plan_chunk
from poc.convert.plan_schema import Plan
from poc.convert.runner import _restore_matching_figure_captions, convert_pdf


TYPE_MAP = {"figure": "image", "page_number": "paragraph"}


class FakeModel:
    """Return a valid plan containing only IDs found in the current prompt chunk."""

    def __init__(self):
        self.calls = 0

    def with_structured_output(self, schema):
        def invoke(values):
            self.calls += 1
            elements = _prompt_chunk(values)
            heading_id = next((item["id"] for item in elements if item["type"] == "heading" and item.get("level") == 1), None)
            blocks = [{"source_id": item["id"], "block_type": TYPE_MAP.get(item["type"], item["type"])} for item in elements]
            return schema.model_validate({"sections": [{"target_section": "A_overview", "source_heading_id": heading_id, "blocks": blocks}]})

        return RunnableLambda(invoke)


class InvalidThenValidModel:
    """Return plans missing a source id for three attempts, forcing rule fallback."""

    def __init__(self):
        self.calls = 0

    def with_structured_output(self, schema):
        def invoke(values):
            self.calls += 1
            elements = _prompt_chunk(values)
            heading_id = next((item["id"] for item in elements if item["type"] == "heading" and item.get("level") == 1), None)
            return schema.model_validate({"sections": [{"target_section": "A_overview", "source_heading_id": heading_id, "blocks": []}]})

        return RunnableLambda(invoke)


def _make_project(tmp_path: Path) -> tuple[Path, Path]:
    root = tmp_path / "project"
    (root / "config").mkdir(parents=True)
    (root / "docs").mkdir()
    (root / "data/work").mkdir(parents=True)
    for name in ("extraction.yaml", "classification.yaml", "target_format.yaml"):
        source = Path(__file__).parents[1] / "config" / name
        (root / "config" / name).write_bytes(source.read_bytes())
    instructions = Path(__file__).parents[1] / "docs/instructions.md"
    (root / "docs/instructions.md").write_bytes(instructions.read_bytes())
    (root / "docs/challenges_log.md").write_text("# Challenges log\n", encoding="utf-8")
    (root / "docs/answer_key.json").write_text("{}\n", encoding="utf-8")
    pdf_path = tmp_path / "sample_method.pdf"
    pdf = fitz.open()
    cover = pdf.new_page()
    cover.insert_text((72, 90), "SAMPLE METHOD", fontsize=20)
    body = pdf.new_page()
    body.insert_text((72, 80), "1. Overview", fontsize=18, fontname="hebo")
    body.insert_text((72, 125), "This source paragraph remains verbatim.", fontsize=11)
    pdf.save(pdf_path, garbage=4, deflate=True, no_new_id=True, reproducible=True)
    pdf.close()
    return root, pdf_path


def _prompt_chunk(prompt_value):
    text = prompt_value.to_string()
    return ast.literal_eval(text.rsplit("Current source chunk (JSON): ", 1)[1].strip())


def test_plan_schema_validation_and_rejects_new_text():
    Plan.model_validate({"sections": [{"target_section": "A_overview", "source_heading_id": "h1", "blocks": [{"source_id": "p1", "block_type": "paragraph"}]}]})
    with pytest.raises(ValidationError):
        Plan.model_validate({"sections": [{"target_section": "A_overview", "source_heading_id": "h1", "blocks": [{"source_id": "p1", "block_type": "paragraph", "text": "invented"}]}]})


@pytest.mark.parametrize("mode", ["missing", "duplicated", "invented"])
def test_assembler_rejects_bad_id_coverage(mode):
    elements = [
        {"id": "h1", "type": "heading", "level": 1},
        {"id": "p1", "type": "paragraph"},
    ]
    chunk = chunk_elements(elements)[0]
    blocks = [{"source_id": "h1", "block_type": "heading"}, {"source_id": "p1", "block_type": "paragraph"}]
    if mode == "missing":
        blocks = blocks[:1]
    elif mode == "duplicated":
        blocks.append(blocks[-1])
    else:
        blocks[-1] = {"source_id": "new-id", "block_type": "paragraph"}
    plan = Plan.model_validate({"sections": [{"target_section": "A_overview", "source_heading_id": "h1", "blocks": blocks}]})
    with pytest.raises(ValueError):
        validate_chunk_plan(plan, chunk)


def test_graph_retries_validation_then_falls_back():
    model = InvalidThenValidModel()
    elements = [{"id": "h1", "type": "heading", "level": 1, "title": "Overview"}, {"id": "p1", "type": "paragraph", "spans": []}]
    chunk = chunk_elements(elements)[0]
    target_config = {"sections": [{"id": "A_overview", "accepts": ["abstract", "scope", "introduction"]}]}
    result = plan_chunk(model, {
        "chunk": chunk, "outline": [], "instructions": "rules", "target_config": target_config,
        "classification_config": {"section_rules": [{"canonical_type": "introduction", "keywords": ["overview"]}]},
    })
    assert model.calls == 3
    assert result["attempts"] == 3
    assert result["fallback_used"] is True
    assert result["section"].target_section == "A_overview"


def test_saved_figure_caption_reused_only_for_matching_pdf_and_image(tmp_path):
    source_dir = tmp_path / "data/work/waterfall"
    source_dir.mkdir(parents=True)
    saved = {
        "source_sha256": "pdf-hash",
        "elements": [{"type": "figure", "sha256": "image-hash", "ai_status": "complete", "ai": {"caption": "Saved caption."}}],
    }
    (source_dir / "elements.json").write_text(json.dumps(saved), encoding="utf-8")
    payload = {"source_sha256": "pdf-hash", "elements": [{"type": "figure", "sha256": "image-hash"}]}
    assert _restore_matching_figure_captions(payload, tmp_path) == 1
    assert payload["elements"][0]["ai"]["caption"] == "Saved caption."
    mismatched = {"source_sha256": "different-pdf", "elements": [{"type": "figure", "sha256": "image-hash"}]}
    assert _restore_matching_figure_captions(mismatched, tmp_path) == 0


def test_fake_plan_conversion_preserves_source_text(tmp_path, monkeypatch):
    root, pdf_path = _make_project(tmp_path)
    monkeypatch.setattr("poc.convert.runner.ROOT", root)
    monkeypatch.setattr("poc.render_docx.ROOT", root)
    monkeypatch.setattr("poc.verify.ROOT", root)
    fake = FakeModel()
    result = convert_pdf(pdf_path, tmp_path / "out", "mock", root=root, model_override=fake)
    assert Path(result["output_docx"]).is_file()
    assert result["verification"]["text"]["missing_word_count"] == 0
    assert result["verification"]["ledger"]["counts"]["unplaced"] == 0
    word_text = "\n".join(paragraph.text for paragraph in WordDocument(result["output_docx"]).paragraphs)
    assert "This source paragraph remains verbatim." in word_text
    report = Path(result["report_path"]).read_text()
    assert "This source paragraph remains verbatim." not in report  # report contains verifier metrics, not source content
    assert result["verification"]["headings"]["matched_count"] == 1


def test_cli_end_to_end_with_mock_model_and_cache_hit(tmp_path, monkeypatch, capsys):
    from poc import cli

    root, pdf_path = _make_project(tmp_path)
    monkeypatch.setattr("poc.convert.runner.ROOT", root)
    monkeypatch.setattr("poc.render_docx.ROOT", root)
    monkeypatch.setattr("poc.verify.ROOT", root)
    def invoke_cli():
        sys.argv = ["poc", "convert", str(pdf_path), "--out", str(tmp_path / "cli-out"), "--provider", "mock"]
        cli.main()

    invoke_cli()
    invoke_cli()
    output = capsys.readouterr().out
    assert "Converted sample_method.pdf" in output
    assert "calls=0" in output.splitlines()[-1]
    assert "defects=0" in output.splitlines()[-1]
    assert (tmp_path / "cli-out/sample_method_converted.docx").is_file()
    call_log = json.loads((tmp_path / "cli-out/sample_method_llm_calls.json").read_text())
    assert all(entry["prompt_version"] == "c1-plan-v1" for entry in call_log)
    assert [entry["cache_hit"] for entry in call_log] == [False, False, True, True]

