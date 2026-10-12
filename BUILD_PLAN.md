# BUILD_PLAN.md — stage-by-stage instructions

Read `AGENTS.md` first and follow it. Do ONLY the stage the human names. Finish with the stage
report and STOP.

## Inputs
- `data/input/WaterFall_PM_Documentation_1.pdf` (14 pages), `data/input/Kanban_PM_Final_2.pdf` (7 pages).
- Both are Word-exported "MindX360 LMS Platform – Project Management Methodology" documents:
  cover page, contents table, numbered sections 1–10, tables, bullets, and embedded images
  (some images contain meaningful text, e.g. diagrams).

## Pipeline
PDF → extract → elements (JSON, "IR") → enrich (rules + LLM) → render (.docx) → verify → report.
Each stage writes to `data/work/<doc_id>/` or `data/output/`.

---
## Stage M0 — Scaffold
Build:
- Folder layout: `src/poc/`, `tests/`, `config/`, `docs/`, `data/{input,work,output}/`.
- `requirements.txt`, `.gitignore` (.env, .venv, data/work, data/output, __pycache__),
  `.env.example` with: `LLM_PROVIDER=mock`, `GEMINI_API_KEY=`, `GEMINI_MODEL=`, `GROQ_API_KEY=`,
  `GROQ_MODEL=`, `GROQ_VISION_MODEL=`, `LLM_RPM=10`, `LLM_MAX_RETRIES=5`.
- `config/documents.yaml`: doc_id `waterfall` → `WaterFall_PM_Documentation_1.pdf`;
  doc_id `kanban` → `Kanban_PM_Final_2.pdf`.
- `config/target_format.yaml` exactly as in Appendix A.
- `src/poc/models.py` (pydantic v2), the data model below.
- `src/poc/cli.py` (argparse): subcommands `extract`, `enrich`, `render`, `verify`, `report`, `run`
  (stubs that log "not implemented" except what the stage implements).
- `docs/challenges_log.md` (header only).
Data model (`models.py`):
- `Span(text, bold, italic)`.
- `Element` base: `id` (`<doc_id>-p<page:03d>-<seq:03d>`), `doc_id`, `page` (1-based), `bbox`,
  `type`, `role` (`cover|toc|body|page_number`), `disposition` (`placed|regenerated|unplaced|pending`).
- Types: `heading(level, number|None, title)`, `paragraph(spans, is_label)`,
  `bullet(spans, level)`, `table(rows: list[list[str]], header_rows, n_rows, n_cols)`,
  `figure(image_path, sha256, width, height, mime, origin, ai|None)`, `page_number(value)`.
- `ImageDescription(kind, caption, transcribed_text: list[str], uncertain: bool, provider, model, prompt_version)`.
- `Document(doc_id, source_file, source_sha256, page_count, elements, cover_lines)`.
Acceptance:
- `pytest` passes: both PDFs open with page_count 14 and 7; `target_format.yaml` loads and validates;
  models round-trip to JSON; `python -m poc.cli --help` works.
STOP after the stage report.

---
## Stage M1 — Extraction
Build `src/poc/extract.py` and `config/extraction.yaml` (thresholds live here):
1. Text with PyMuPDF (`get_text("dict")`): blocks → paragraphs; keep bold/italic per span
   (inline bold inside a sentence must survive).
2. Tables with pdfplumber; text lying inside a table bbox must NOT also appear as paragraphs.
   Detect the contents table (role `toc`: header cell "TOPIC", sits under a "Contents" title).
3. Images: for each embedded image, store the exact bytes from `extract_image`, sha256, size, bbox;
   write to `data/work/<doc_id>/images/`. Also detect large vector-drawing regions
   (`get_drawings`) that are not raster images and REPORT them. Do not ignore them.
4. Headings: numbering regex (`^\d+\.\s`, `^\d+\.\d+\s`) plus font size/bold. First print a font
   histogram into the inventory, then set thresholds in config from evidence.
5. Bullets: configurable bullet glyphs; log any unknown leading glyph.
6. Printed page numbers (page footers) get type `page_number`, role `page_number`.
7. Page 1 of each document: role `cover` (keep every line in `cover_lines`).
8. Reading order: page, then y, then x. Optional paragraph continuation across a page break only
   if BOTH: previous block lacks terminal punctuation AND next block starts lowercase; log every merge.
Outputs per doc: `elements.json`, `images/*`, `inventory.md`
(counts by type and by page, font histogram, vector regions, unknown glyphs, merges),
and `pages/p<NNN>.png` page renders at 100 dpi for human comparison.
Acceptance:
- `python -m poc.cli extract --all` runs end to end, twice, with identical `elements.json`.
- Every image hash in `elements.json` matches the file on disk.
- No text appears both in a table and as a paragraph.
- `inventory.md` printed in the stage report. Do NOT compare to the answer key yet (that is M2).
STOP.

---
## Stage M2 — Answer key and extraction audit
The architect's draft key is below. A human verifies it against the PDFs before you use it.
1. Create `docs/answer_key.json` from the draft (below) verbatim.
2. Write `tests/test_extraction_vs_key.py` comparing `elements.json` to the key:
   page count, heading counts by level and their titles, bullet counts, table count and
   per-table shape (rows including header, cols), figure count, page-number count, spot-check strings.
3. Run it. For each mismatch, produce `docs/extraction_audit.md`: key value, extracted value,
   and your diagnosis. Fix the EXTRACTOR for real bugs. Do not edit the key or loosen tests.
Draft key (visual read by the architect; unverified until the human signs off):
```json
{
  "waterfall": {
    "pages": 14, "page_numbers": 14, "h1": 10, "h2": 11, "bullets": 6, "tables": 6, "figures": 5,
    "table_shapes": [["contents",11,2],["lifecycle",7,3],["decision",6,3],["best_practices",9,2],["advantages",6,2],["limitations",6,2]],
    "cover_lines": ["MindX360 LMS PLATFORM","PROJECT MANAGEMENT METHODOLOGY","WATERFALL","Professional Methodology & Learning Document"],
    "section_types": {"1":"abstract","2":"scope","3":"introduction","4":"learning_objectives","5":"core_concept","6":"process_detail","7":"when_to_use","8":"best_practices","9":"advantages","10":"limitations"},
   "spot_strings": [
  "Waterfall is a structured, sequential approach to project delivery",
  "False sense of certainty",
  "Treat documentation as an operational asset",
  "Maintenance",
  "These advantages are most meaningful when the project's underlying assumptions remain stable"
],
    "image_tokens": {
      "cover_photo": [],
      "sdlc_cycle": ["SOFTWARE","DEVELOPMENT","PLANNING","DESIGN","TESTING","DEPLOYMENT","MAINTENANCE"],
      "ux_cycle": ["MULTIPLE ITERATIONS","Understand","Define","Evaluation"],
      "testing_cycle": ["SOFTWARE TESTING","Test Planning","Test Execution","Test Closure"],
      "phase_role_chart": ["Planning","Analysis","Design","Implementation","Test","Deploy","Maintenance"]
    }
  },
  "kanban": {
    "pages": 7, "page_numbers": 7, "h1": 10, "h2": 8, "bullets": 8, "tables": 4, "figures": 3,
    "table_shapes": [["contents",11,2],["board_structure",5,2],["suitability",8,2],["key_challenges",6,2]],
    "cover_lines": ["MindX360 LMS PLATFORM","PROJECT MANAGEMENT METHODOLOGY","KANBAN","Professional Methodology & Learning Document"],
    "section_types": {"1":"abstract","2":"scope","3":"introduction","4":"learning_objectives","5":"core_concept","6":"process_detail","7":"when_to_use","8":"best_practices","9":"advantages","10":"limitations"},
    "spot_strings": ["Waiting for Customer","Review or approval constraints","Work-in-Progress (WIP) limits"],
    "image_tokens": {
      "board_diagram": ["Kanban Board","Commitment Point","Delivery Point","Swimlanes","Cards","EXPEDITE"],
      "wip_comparison": ["Without WIP Limits","With WIP Limit","18%","67%"],
      "flow_diagram": ["MANAGE FLOW","BOTTLENECK","VISUALIZE","LIMIT WORK IN PROGRESS"]
    }
  }
}
```
Sub-sections inherit the section type of their parent (3.x introduction, 6.x process_detail, 7.1 when_to_use).
Acceptance: extraction matches the key, or every difference is explained in `extraction_audit.md`
with the extractor fixed where it was wrong. STOP.

---
## Stage M3 — LLM provider layer and enrichment
Build `src/poc/llm/` and `src/poc/enrich.py`:
1. Interface `LLMProvider.generate_json(prompt, schema, image: bytes|None, mime) -> dict`.
   Implementations: `GeminiProvider` (google-genai), `GroqProvider` (groq; images only if
   `GROQ_VISION_MODEL` is set), `MockProvider` (deterministic; reads `tests/fixtures/mock_llm.json`,
   falls back to a clearly marked placeholder). Select via `LLM_PROVIDER`.
2. Model names from env only; if unset for a real provider, fail with a clear message.
3. Reliability: rate limiter from `LLM_RPM`; exponential backoff with jitter on 429/5xx up to
   `LLM_MAX_RETRIES`; one repair retry on invalid JSON (include the validation error);
   after that mark the item `status=failed` (never crash the run).
4. Cache: `data/work/llm_cache/<sha256(provider+model+prompt_version+prompt+image_sha256)>.json`.
   Prompts live in `src/poc/prompts/*.txt`; a `PROMPT_VERSION` is part of the cache key.
5. Section classification, RULES FIRST: map heading titles to canonical types
   (abstract, scope, introduction, learning_objectives, core_concept, process_detail, when_to_use,
   best_practices, advantages, limitations) with keyword rules in `config/classification.yaml`.
   Only headings the rules cannot resolve go to the LLM. Record `method: rule|llm` per decision.
   Subsections inherit the parent type.
6. Image enrichment, once per image: prompt must demand (a) `kind` (photo|diagram|chart|screenshot|other),
   (b) one-sentence `caption`, (c) `transcribed_text`: all visible text copied exactly in reading order,
   no inference, `[?]` for unreadable parts, (d) `uncertain` flag.
7. Write results into `elements.json` (`figure.ai`) and `data/work/<doc_id>/classification.json`.
Acceptance:
- Offline tests with `mock` pass; cache hit on second run makes 0 provider calls (assert it).
- Every heading has a canonical type; every figure has `ai` or an explicit `failed` status.
- With a real provider and key: run `enrich --all --provider gemini` once; paste the first 2
  image descriptions and the rule/LLM split into the stage report. STOP.

---
## Stage M4 — Word renderer
Build `src/poc/render_docx.py` driven by `config/target_format.yaml` (python-docx):
1. Title block from `cover_lines` (verbatim) plus the cover figure if present.
2. Contents: Word TOC field with update-on-open (log the Word prompt behaviour as a challenge);
   acceptable fallback: a static list of section titles.
3. Sections A–F in config order. Within a section, source elements keep their original relative order.
   Original heading titles are kept verbatim as sub-headings (the number prefix is dropped and
   recorded in the source map). Lead-in label paragraphs (e.g. "Suitability Framework") stay with their table.
4. Tables: real Word tables, header row shaded, cell text verbatim, bold preserved.
5. Figures: embed the stored original bytes; add caption "Figure N" and, below it, the AI caption
   labelled "AI-generated description:". Max width 6 in.
6. Appendix 1 Figure index: per figure: id, source page, hash prefix, caption, transcribed text
   (all labelled AI-generated). Appendix 2 Source map: source section → target section.
   Appendix 3 Unplaced content (expected empty).
7. Set each element's disposition (`placed|regenerated|unplaced`) and write `placement.json`
   (element id → output section and order index).
Outputs: `data/output/<doc_id>_decision_brief.docx`.
Acceptance: both files open; every element has a non-pending disposition; Appendix 3 is empty;
the stage report lists counts by disposition. Include a short checklist for the human to compare
page renders to the output visually. STOP.

---
## Stage M5 — Verifier and metrics
Build `src/poc/verify.py`:
1. Ledger: all source elements have exactly one disposition; `unplaced == 0`.
2. Re-extract the produced .docx (python-docx + unzip media) and compare to the source:
   - Text recall: multiset of normalised source word tokens (excluding `regenerated` elements)
     present in output; text excess: output tokens not in source, excluding headings from config and
     AI-labelled text (flag the rest as possible fabrication).
   - Tables: shape equality and cell-by-cell exact match after whitespace normalisation.
   - Images: set of sha256 in docx media equals source set; counts equal.
   - Order: within each target section, source order is preserved (report violations).
   - Contents: every source TOC topic exists as a heading in the output.
3. Mapping accuracy: classification vs `answer_key.section_types`.
4. Image transcription: token recall per image vs `answer_key.image_tokens`
   (case-insensitive substring match), reported separately and marked "indicative".
5. Write `data/output/metrics.json` (per doc and overall; per-category) and a readable
   `data/output/verification.md` listing every miss with element ids.
Acceptance: unit tests for each check, including deliberate-corruption tests (delete a table row,
swap an image, alter a word) that the verifier MUST catch. STOP.

---
## Stage M6 — Report and one-command demo
1. `python -m poc.cli run --all --provider <name>` performs extract → enrich → render → verify → report.
2. Generate `docs/accuracy_report.md` from `metrics.json`: overall and per-doc table of
   text recall, table accuracy, image preservation, mapping accuracy, image transcription recall,
   unplaced count; plus method notes and an explicit "limits of this evidence" section
   (2 documents, our own template, text-in-image not auto-verifiable).
3. Complete `docs/challenges_log.md` and add a one-page summary: top challenges, what worked,
   what a human must still check.
4. Optional, only if LibreOffice is installed: PDF copy via `soffice --headless --convert-to pdf`;
   otherwise log it as skipped.
Acceptance: a fresh clone + `.env` + `run --all --provider mock` completes; real-provider run completes;
the report numbers are copied from `metrics.json`, never typed by hand. STOP.

---
## Appendix A — `config/target_format.yaml` (create exactly this)
```yaml
name: "MindX360 Decision Brief"
title_template: "{methodology} — Decision Brief"
sections:
  - id: A_overview
    title: "A. Overview"
    accepts: [abstract, scope, introduction]
  - id: B_core_concept
    title: "B. Core Concept"
    accepts: [core_concept]
  - id: C_process_detail
    title: "C. Process in Detail"
    accepts: [process_detail]
  - id: D_fit_check
    title: "D. Fit Check"
    accepts: [when_to_use]
  - id: E_strengths_risks
    title: "E. Strengths and Risks"
    accepts: [advantages, limitations, best_practices]   # this order
  - id: F_learning_checklist
    title: "F. Learning Checklist"
    accepts: [learning_objectives]
appendices:
  - {id: app1_figures, title: "Appendix 1 — Figure Index", generated: true}
  - {id: app2_source_map, title: "Appendix 2 — Source Map", generated: true}
  - {id: app3_unplaced, title: "Appendix 3 — Unplaced Content", generated: true}
generated_label: "AI-generated description:"
```