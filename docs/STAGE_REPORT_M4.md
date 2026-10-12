# Stage Report — M4: Word Renderer

## 1. What was built

- Added `src/poc/render_docx.py` and wired `python -m poc.cli render` to render both extracted documents using `config/target_format.yaml`.
- Created `data/output/waterfall_decision_brief.docx` and `data/output/kanban_decision_brief.docx`.
- Wrote `data/work/<doc_id>/placement.json` for each document. Source elements now have a final disposition. The contents title and table, plus source printed page numbers, are marked `regenerated`; all other source elements are `placed`.
- Kept source heading titles verbatim as sub-headings, omitted their number prefixes from the headings, and recorded each number/title/target mapping in Appendix 2 and the placement source map.
- Embedded figure display images from their stored bytes (composite PNGs for multi-part figures and original bytes for single-part figures). Added the requested figure labels and AI-generated descriptions. Appendix 1 is a six-column table with one row per figure; its AI-generated column labels cover the figure id, source page, display hash prefix, caption, transcription, and full source part SHA-256 hashes. The structure-loss note appears once above the table.
- Used a static contents list, the documented M4 fallback, and generated Word page-number fields in the footer.
- In the M4 layout fix pass, removed all U+E000–U+F8FF characters from rendered span text (including the source bullet glyph, with Word list styling providing the marker), added 8 pt before paragraphs immediately following source tables, repeated table header rows, prevented table row splitting, and kept lead-in labels and figure image/label paragraphs together.
- Updated M3 recall reporting in `docs/ai_outputs_review.md` and `docs/STAGE_REPORT_M3.md`: strict score **35/36 (97.2%)** and normalized score **36/36 (100.0%)**. Normalization lowercases and removes hyphens and whitespace before keyword substring matching. The note now states this metric measures only the presence of selected keywords. No answer-key or saved AI output was changed.

## 2. How to run it

```sh
.venv/bin/python -m poc.cli render
.venv/bin/python -m pytest -q
```

No network or real LLM calls are made by the renderer or tests.

## 3. Test results

```text
38 passed, 5 warnings in 18.22s
```

The warnings are PyMuPDF/SWIG deprecation warnings. Offline renderer tests confirmed both DOCX files open, all dispositions are final, `unplaced == 0`, source table cells match the golden fixtures and rendered non-contents table cells, image media SHA-256 values match the display images, no private-use glyphs occur in rendered DOCX text, table pagination and keep-together properties are present, and two renders are byte-deterministic.

## 4. Metrics and inventory

| Document | Source elements | Placed | Regenerated | Unplaced | Pending |
|---|---:|---:|---:|---:|---:|
| Waterfall | 74 | 58 | 16 | 0 | 0 |
| Kanban | 72 | 63 | 9 | 0 | 0 |

The regenerated items are the contents title and contents table plus printed page numbers (14 Waterfall and 7 Kanban page numbers). Appendix 3 is empty in both documents. The two full CLI renders produced identical SHA-256 values on both runs: Waterfall `2c53d13cbdb5d27e068e47cffc762701d5d87d52ce8c1ee8204ae276b3eb5662`; Kanban `c9d004d61a7cf436de391b407987c102f22a8332b2f95019e11ebe436a3ac29b`.

Outputs:

- `data/output/waterfall_decision_brief.docx`
- `data/output/kanban_decision_brief.docx`
- `data/work/waterfall/placement.json`
- `data/work/kanban/placement.json`

## 5. Decisions and assumptions

- Used the static list of target section titles as the M4-allowed contents fallback. It is generated navigation and does not copy the source contents table’s page references.
- Target sections are emitted in config order. Elements assigned to each target section are walked in source reading order, preserving their relative order, including lead-in paragraphs before their tables.
- Figures are numbered in document reading order, including a cover figure if present. Appendix 1’s hash prefix is the hash of the displayed image; source fragment hashes remain available in each figure’s `parts` metadata.
- If cached enrichment is absent, the renderer reports `[missing enrichment result]` in the figure index and does not invent a description or transcription.

## 6. Deviations from the spec

- LibreOffice (`soffice`) was not installed/on PATH, so PDF conversion and page PNG generation under `data/output/review/` were skipped. This is recorded in `docs/challenges_log.md`.
- Used a static contents list rather than a Word TOC field, which is explicitly allowed by M4.

## 7. Challenges logged

- LibreOffice visual review skipped because `soffice` was unavailable.
- Existing M0–M3 challenge entries remain in `docs/challenges_log.md`.

## 8. Open issues and risks

- A human should visually compare the generated Word documents with the source PDFs using the checklist below. Automated checks establish content/table/media consistency and determinism, but not page-level visual fidelity.
- The static contents list lists the target sections and does not contain dynamic page references.
- The M4 layout fix pass changed only rendered layout and Appendix 1 presentation. Extracted element text, dispositions, and content expectations remain unchanged.

### Human visual comparison checklist

- [ ] Compare each cover’s lines, figure, and overall title-block spacing with source page 1.
- [ ] Check all six target sections appear in the configured order and source headings retain their exact titles with number prefixes omitted.
- [ ] Compare paragraphs, bullets, lead-in labels, and tables with the source; inspect table widths, wrapping, and header shading.
- [ ] Check each figure’s displayed image, `Figure N` label, and labelled AI-generated description.
- [ ] Review Appendix 1 captions/transcriptions and the structure-loss note; check Appendix 2 numbering and target mappings.
- [ ] Confirm Appendix 3 is empty and inspect footer page numbering.

M5 has not been started.
