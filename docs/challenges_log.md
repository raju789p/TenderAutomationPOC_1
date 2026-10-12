# Challenges log

## C1 Gemini planner request rejected with HTTP 400
- Where: First planner request for each source document.
- Frequency: Reported on both documents; no real request was made during this fix pass.
- Symptom: Gemini returned HTTP 400 when the planner submitted the generated Pydantic JSON schema.
- Root cause: Offline schema inspection found constructs outside the requested Gemini-safe subset: `$defs`/`$ref`, `anyOf` for nullable strings, `enum` values generated from `Literal`, `additionalProperties`, nested model references, and generated `title` metadata. The available report did not include Gemini's response body, so the precise rejected keyword cannot be established.
- Action: Added an inline flat response schema using plain strings for target section and block type. Gemini receives only this schema. The existing Pydantic `Plan` remains strict and validates the returned JSON locally. Prompt instructions now state allowed values, and the outline/previews are shorter. Added a one-chunk `plan-check` command and credential-safe provider error messages that retain the sanitized API message and HTTP status.
- Residual risk: No real Gemini request was made under the offline constraint, so acceptance and model output quality remain unverified. The human should first run the one-chunk plan check, then the two full conversions.
- Evidence: `docs/c1_gemini_schema_diagnostic.json` records the exact old/new response schemas, unsupported-keyword scan, and before/after prompt sizes (4,423 to 2,971 characters; rough estimate 1,106 to 743 tokens).

## C1 LangChain dependency versions differ from requested pins
- Where: C1 implementation environment.
- Frequency: Observed once during dependency inspection.
- Symptom: Requested package pins are langchain-core 1.6.9, langchain-google-genai 4.4.1, and langgraph 1.2.14; the existing virtual environment reports 0.3.76, 2.0.10, and 0.6.6.
- Root cause: The virtual environment does not contain the versions described in the request. Required LangChain and LangGraph imports succeeded, and no installation was attempted.
- Action: Added the requested exact pins to requirements.txt and implemented using available imports without upgrading packages.
- Residual risk: Compatibility with the requested newer versions has not been runtime-tested in this environment.

## C1 verifier initially flagged the generated unclassified-section label
- Where: C1 mock conversion of the Waterfall source PDF.
- Frequency: Observed once in the first smoke run.
- Symptom: The verifier reported generated heading text `Unclassified Source Content` as a possible excess word.
- Root cause: The backward-compatible verifier generated-text allowlist did not yet account for the optional C1 unclassified section heading.
- Action: Added that exact generated heading to the allowance only when the source classification contains an unclassified heading; repeated mock conversion reported 0 defects.
- Residual risk: Any future renderer-generated section labels must be represented in the verifier allowlist and covered by a regression test.

## C1 ID-based assembly equality check corrected during offline tests
- Where: `src/poc/convert/assemble.py` plan-to-IR resolution.
- Frequency: Found by the new fake-model conversion test.
- Symptom: Valid plans were rejected by the final ID-set assertion.
- Root cause: The ID counter was compared against a mapping's values instead of its keys.
- Action: Compare the plan IDs against the source ID keys; all seven C1 offline tests pass.
- Residual risk: Current tests exercise deterministic mock and fake-model plans; model-specific behavior remains unmeasured until the human's cached Gemini run.

## Input PDF filenames differ from the plan
- Where: M0 configuration, `data/input/`.
- Frequency: 2 source files.
- What happened: The actual filenames contain spaces (`WaterFall_PM_Documentation 1.pdf`, `Kanban_PM_Final 2.pdf`); the build plan lists underscores.
- Action: Configured the actual filenames without renaming or editing either input PDF.
- Residual risk: None for this stage; downstream configuration uses these exact filenames.

## Dependency installation initially lacked network access
- Where: M0 environment setup.
- Frequency: 1 initial install attempt.
- What happened: pip could not resolve the package index in the restricted environment.
- Action: Retried the same install with approved network access; dependencies installed successfully.
- Residual risk: Dependency installation requires package index access on a fresh environment.

## Editable install initially lacked network access
- Where: M0 editable package installation.
- Frequency: 1 initial attempt.
- What happened: pip's isolated build environment could not fetch the setuptools build dependency while installing the package editable.
- Action: Retried the editable installation with approved network access; `pip install -e .` and installation through `requirements.txt` succeeded.
- Residual risk: A fresh editable install needs access to the package index for the build backend unless setuptools is already available to pip.

## Word-exported list markers use a private-use glyph
- Where: Waterfall page 6 and Kanban page 4.
- Frequency: 14 list items (6 and 8 respectively), all marked with U+F0B7.
- What happened: PyMuPDF returns the Word bullet glyph as a private-use character, sometimes on its own line.
- Action: Added the glyph to `config/extraction.yaml` and grouped each marker with its corresponding text as a bullet element.
- Residual risk: Other unconfigured leading symbols are retained as text and reported in the inventory.

## pdfplumber fragments cells in ruled Waterfall tables
- Where: Waterfall pages 2, 7, 11, 12, 13, and 14.
- Frequency: 6 tables affected under the original default settings.
- What happened: Default pdfplumber settings and PyMuPDF `find_tables()` exposed merged visual cells as adjacent columns and wrapped cell text as additional rows.
- Action: Compared line strategies and snap/join tolerances. pdfplumber line detection with 8 pt snap and join tolerances yielded 11×2, 7×3, 6×3, 9×2, 6×2, and 6×2 tables, with every cell copied to `tables_dump.md`; table text remains excluded from paragraphs.
- Residual risk: Human review of `tables_dump.md` is still needed; the architect's shape expectation is unverified and was not loaded from or compared with the M2 answer key.

## Large PDF drawing shapes overlap ruled tables
- Where: Waterfall table pages and Kanban table pages.
- Frequency: 40 large drawing shapes in Waterfall and 26 in Kanban.
- What happened: PDF vector drawing detection identifies table fill and border shapes as large regions.
- Action: Reported their page and bounding boxes in the inventory, but did not treat them as standalone figure images because they overlap detected tables. No standalone vector-only regions remained after this filter.
- Residual risk: The table-overlap threshold is heuristic; a vector figure that overlaps a table boundary could be filtered as table structure.

## Image fragments grouped into composites
- Where: Waterfall page 1 and Kanban page 7.
- Frequency: 13 exact image pieces grouped into 2 composites (five Waterfall pieces and two Kanban pieces); 6 other image pieces remain single-part figures.
- What happened: The PDF stores the Waterfall cover photo and a Kanban diagram in adjacent image streams.
- Action: Stored each source image stream separately, retained per-part SHA-256 metadata, assembled lossless PNG composites without resampling, and validated them against 150 dpi page-region renders.
- Residual risk: Normalized pixel differences include PDF renderer antialiasing; scores are reported in each document's `figure_diagnosis.md`.

## Image fragments grouped into composites for waterfall
- Where: source pages 1.
- Frequency: 5 parts grouped into 1 composite(s).
- What happened: The PDF stores some logical figures as adjacent image fragments.
- Action: Retained each exact source fragment and built a deterministic PNG composite; figure diagnosis records per-part hashes and render comparison scores.
- Scaling: No source part required resampling; a one-pixel placement tolerance covers PDF coordinate rounding.
- Residual risk: Composite comparison uses a normalized 150 dpi page render and may show antialiasing differences.

## Image fragments grouped into composites for kanban
- Where: source pages 7.
- Frequency: 2 parts grouped into 1 composite(s).
- What happened: The PDF stores some logical figures as adjacent image fragments.
- Action: Retained each exact source fragment and built a deterministic PNG composite; figure diagnosis records per-part hashes and render comparison scores.
- Scaling: No source part required resampling; a one-pixel placement tolerance covers PDF coordinate rounding.
- Residual risk: Composite comparison uses a normalized 150 dpi page render and may show antialiasing differences.

## Table-overlap suppression dropped text adjacent to a table
- Where: Waterfall page 13, immediately after the Advantages table.
- Frequency: 1 paragraph.
- What happened: PyMuPDF combined the table-cell lines and the following bold sentence in one text block. The block-level 0.5 table-overlap test suppressed the entire block. The sentence's line begins 0.296 pt below the detected table bbox; the 8 pt pdfplumber snap/join tolerances did not include it in the table.
- Action: Changed the configured suppression rule to evaluate each line bbox independently using `table_text_suppression.line_overlap_ratio: 0.5`. Only lines substantially inside a table are suppressed; adjacent text lines are classified normally. Added a per-page word conservation test for both PDFs. The audit reports no missing or extra words on any page.
- Residual risk: The configured line overlap ratio remains a geometric heuristic for lines that straddle a table boundary.

## Cover line inventory included the printed page number
- Where: Page 1 of both source PDFs.
- Frequency: 2 cover inventories.
- What happened: Cover-line collection ran before footer page-number classification and included the printed `1` alongside the cover text.
- Action: Moved cover-line collection after the configured page-number check. The exact four cover strings in the draft key now match for both documents.
- Residual risk: Cover-line capture remains based on extracted text lines; source lines without text extraction cannot appear in this field.

## Draft answer key combines unrelated Waterfall spot-check text
- Where: `docs/answer_key.json`, Waterfall `spot_strings[3]`.
- Frequency: 1 key item.
- What happened: The key asks for the contiguous normalized phrase `Maintenance These advantages are most meaningful when the project's underlying assumptions remain stable`, but the source has `Maintenance` in other elements and the page 13 sentence separately.
- Action: Kept the key and comparison test unchanged. Confirmed the page 13 sentence is extracted; recorded the mismatch in `docs/extraction_audit.md`.
- Residual risk: M2 key comparison remains red on this one unverified draft-key item pending human correction or sign-off.
- Close-out: The current `docs/answer_key.json` represents “Maintenance” and the page 13 sentence as separate spot strings. Both now pass the strict key comparison; the earlier mismatch is retained here as the issue history.

## Draft key omits expected heading titles
- Where: M2 key comparison, both documents.
- Frequency: 2 documents.
- What happened: The draft key provides h1/h2 counts but no expected title lists, despite the M2 request to compare heading titles.
- Action: Asserted heading counts and non-empty extracted titles; listed all extracted titles and documented the absent expected values in `docs/extraction_audit.md`.
- Residual risk: Heading title accuracy cannot be compared to a key until expected title lists are supplied.

## Gemini enrichment could not reach the provider from the sandbox
- Where: M3 real enrichment, 8 logical figures across Waterfall and Kanban.
- Frequency: 8 failed figure requests; 0 valid cache results.
- What happened: The sandbox Gemini run returned only the provider-safe generic error `Provider request failed`; every figure was marked failed and no cache entry was written. No key or environment value was logged.
- Action: Stopped without retrying, as required. The human must run `.venv/bin/python -m poc.cli enrich --all --provider gemini` in their own terminal; resume the second-run cache check and M3 reports after valid cache files exist.
- Residual risk: Since the sandbox suppresses provider exception details, this run cannot independently distinguish network isolation from another request-level failure. The authorized successful human `llm-check` is the connectivity evidence available so far.
- Close-out: The human completed enrichment in their terminal for all 8 figures. A subsequent run completed with 0 provider calls and 8 cache hits (5 Waterfall, 3 Kanban); all figures remained complete. No key or environment values were displayed or logged.


## LibreOffice visual review skipped
- Where: M4 DOCX visual comparison.
- Frequency: 2 documents.
- What happened: `soffice` was not installed/on PATH.
- Action: Skipped PDF conversion and PNG page renders as directed.
- Residual risk: Human must compare DOCX files directly with the source PDFs.

## AI caption included an unsupported place name
- Where: M3 cached AI caption for a Waterfall image.
- Frequency: 1 caption; the saved output names “Skógafoss,” which is not established by the source image.
- What happened: The image description made a specific place-name claim beyond verifiable visible content.
- Action: Preserved the saved output and documented the issue. Planned prompt rule: “describe only what is visible; no place, person or brand names.” No new LLM request was made during M6.
- Residual risk: Existing saved captions can contain unsupported identification; a human must review them, and the revised prompt must be used before future enrichment.

## Strict image keyword score missed a hyphenated token
- Where: M3/M5 indicative token recall for the Kanban flow diagram.
- Frequency: 1 of 36 selected keywords under strict matching (`BOTTLE-NECK` versus `BOTTLENECK`).
- What happened: Strict case-insensitive substring matching treated a hyphen as meaningful punctuation, although the normalized comparison found the keyword.
- Action: Kept the strict score and added a second normalized score that removes hyphens and whitespace; report both and label them indicative keyword-presence measures.
- Residual risk: Keyword presence does not measure complete transcription accuracy or verify all image text.

## M6 demo reuses saved results only
- Where: End-to-end M6 command.
- Frequency: Every demo run.
- What happened: The M6 execution constraint prohibits network, real LLM calls, and reading `.env`; the existing extraction and enrichment artifacts are available locally.
- Action: The run command snapshots current extracted elements, reruns extraction, and restores only matching saved figure descriptions and heading classifications; missing matches are marked failed. It then renders, verifies, and generates the report without loading provider settings.
- Residual risk: New or changed figures without a matching saved result remain explicitly unenriched until a separately authorized enrichment run.

## Private-use bullet marker leaked into rendered text
- Where: M4 DOCX rendering of extracted bullets.
- Frequency: Affected bullet text included the PDF's private-use marker U+F0B7.
- What happened: The source marker was retained in IR text and was also emitted into Word, duplicating the marker supplied by the Word bullet style.
- Action: Filtered U+E000–U+F8FF characters only while rendering span text and added a DOCX text invariant.
- Residual risk: The source IR intentionally retains the extracted glyph; other private-use characters in newly encountered content are likewise omitted at render time and reported by verification if they remain elsewhere.

## DOCX pagination separated related content
- Where: M4 tables and figure captions.
- Frequency: Layout rules applied to source tables, table lead-ins, following paragraphs, and figures.
- What happened: Tables could split rows across pages, headers could disappear on continuation pages, and figure labels or descriptions could separate from their images.
- Action: Added repeating table headers, non-splitting rows, keep-with-next relationships for table lead-ins and figure blocks, and spacing after tables; tests inspect the WordprocessingML attributes.
- Residual risk: Page layout varies between Word-compatible renderers; a human must review the final DOCX visually.

## M7 baseline — m7_a_same_style: text
- Where: M7 synthetic document `m7_a_same_style`.
- Frequency: 1 baseline document.
- Symptom: Missing 8 words and excess 0 words..
- Root cause: `src/poc/extract.py` builds text elements from PyMuPDF text blocks and line spans; `config/extraction.yaml` supplies the heading and bullet heuristics. Image-only text has no OCR path..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic extractor or configuration change; OCR is out of scope.

## M7 baseline — m7_a_same_style: images
- Where: M7 synthetic document `m7_a_same_style`.
- Frequency: 1 baseline document.
- Symptom: Image count 2/2; exact hash matches 0/2..
- Root cause: `src/poc/extract.py` hashes extracted image streams; PDF image re-encoding and full-page rasterization can change byte identity relative to generator source bytes..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic provenance/hash handling or configuration change, measured only.

## M7 baseline — m7_a_same_style: ledger
- Where: M7 synthetic document `m7_a_same_style`.
- Frequency: 1 baseline document.
- Symptom: Unplaced=0; pending=12..
- Root cause: `src/poc/render_docx.py` places content only under a preceding heading with a canonical target section; unmatched headings leave elements without a destination..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic renderer or classification coverage; measured without fixes.

## M7 baseline — m7_b_new_style: text
- Where: M7 synthetic document `m7_b_new_style`.
- Frequency: 1 baseline document.
- Symptom: Missing 9 words and excess 0 words..
- Root cause: `src/poc/extract.py` builds text elements from PyMuPDF text blocks and line spans; `config/extraction.yaml` supplies the heading and bullet heuristics. Image-only text has no OCR path..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic extractor or configuration change; OCR is out of scope.

## M7 baseline — m7_b_new_style: images
- Where: M7 synthetic document `m7_b_new_style`.
- Frequency: 1 baseline document.
- Symptom: Image count 2/2; exact hash matches 0/2..
- Root cause: `src/poc/extract.py` hashes extracted image streams; PDF image re-encoding and full-page rasterization can change byte identity relative to generator source bytes..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic provenance/hash handling or configuration change, measured only.

## M7 baseline — m7_b_new_style: ledger
- Where: M7 synthetic document `m7_b_new_style`.
- Frequency: 1 baseline document.
- Symptom: Unplaced=0; pending=10..
- Root cause: `src/poc/render_docx.py` places content only under a preceding heading with a canonical target section; unmatched headings leave elements without a destination..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic renderer or classification coverage; measured without fixes.

## M7 baseline — m7_b_new_style: header_footer_leakage
- Where: M7 synthetic document `m7_b_new_style`.
- Frequency: 1 baseline document.
- Symptom: Header/footer leaks=[{'page': 2, 'field': 'header', 'text': 'M7 B New Style / Internal Playbook'}, {'page': 2, 'field': 'footer', 'text': 'Operations Excellence Series'}, {'page': 3, 'field': 'header', 'text': 'M7 B New Style / Internal Playbook'}, {'page': 3, 'field': 'footer', 'text': 'Operations Excellence Series'}, {'page': 4, 'field': 'header', 'text': 'M7 B New Style / Internal Playbook'}, {'page': 4, 'field': 'footer', 'text': 'Operations Excellence Series'}, {'page': 5, 'field': 'header', 'text': 'M7 B New Style / Internal Playbook'}, {'page': 5, 'field': 'footer', 'text': 'Operations Excellence Series'}, {'page': 6, 'field': 'header', 'text': 'M7 B New Style / Internal Playbook'}, {'page': 6, 'field': 'footer', 'text': 'Operations Excellence Series'}]; page-number leaks=[]..
- Root cause: `config/extraction.yaml` classifies only isolated digit spans near the page bottom; `src/poc/extract.py` otherwise processes repeated furniture as ordinary page text..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic header/footer detection or configuration change.

## M7 baseline — m7_c_borderless_tables: text
- Where: M7 synthetic document `m7_c_borderless_tables`.
- Frequency: 1 baseline document.
- Symptom: Missing 4 words and excess 0 words..
- Root cause: `src/poc/extract.py` builds text elements from PyMuPDF text blocks and line spans; `config/extraction.yaml` supplies the heading and bullet heuristics. Image-only text has no OCR path..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic extractor or configuration change; OCR is out of scope.

## M7 baseline — m7_c_borderless_tables: tables
- Where: M7 synthetic document `m7_c_borderless_tables`.
- Frequency: 1 baseline document.
- Symptom: Cell-exact matches 0/2; extracted 0 tables..
- Root cause: `src/poc/extract.py` calls pdfplumber `find_tables`; `config/extraction.yaml` selects the lines strategy and fixed snap/join tolerances, which cannot detect whitespace-aligned tables reliably or join split-page fragments..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic table detection/joining or configuration change, measured only.

## M7 baseline — m7_c_borderless_tables: images
- Where: M7 synthetic document `m7_c_borderless_tables`.
- Frequency: 1 baseline document.
- Symptom: Image count 1/1; exact hash matches 0/1..
- Root cause: `src/poc/extract.py` hashes extracted image streams; PDF image re-encoding and full-page rasterization can change byte identity relative to generator source bytes..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic provenance/hash handling or configuration change, measured only.

## M7 baseline — m7_c_borderless_tables: ledger
- Where: M7 synthetic document `m7_c_borderless_tables`.
- Frequency: 1 baseline document.
- Symptom: Unplaced=0; pending=29..
- Root cause: `src/poc/render_docx.py` places content only under a preceding heading with a canonical target section; unmatched headings leave elements without a destination..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic renderer or classification coverage; measured without fixes.

## M7 baseline — m7_d_two_column: text
- Where: M7 synthetic document `m7_d_two_column`.
- Frequency: 1 baseline document.
- Symptom: Missing 8 words and excess 0 words..
- Root cause: `src/poc/extract.py` builds text elements from PyMuPDF text blocks and line spans; `config/extraction.yaml` supplies the heading and bullet heuristics. Image-only text has no OCR path..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic extractor or configuration change; OCR is out of scope.

## M7 baseline — m7_d_two_column: images
- Where: M7 synthetic document `m7_d_two_column`.
- Frequency: 1 baseline document.
- Symptom: Image count 3/3; exact hash matches 0/3..
- Root cause: `src/poc/extract.py` hashes extracted image streams; PDF image re-encoding and full-page rasterization can change byte identity relative to generator source bytes..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic provenance/hash handling or configuration change, measured only.

## M7 baseline — m7_d_two_column: ledger
- Where: M7 synthetic document `m7_d_two_column`.
- Frequency: 1 baseline document.
- Symptom: Unplaced=0; pending=24..
- Root cause: `src/poc/render_docx.py` places content only under a preceding heading with a canonical target section; unmatched headings leave elements without a destination..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic renderer or classification coverage; measured without fixes.

## M7 baseline — m7_e_scanned: text
- Where: M7 synthetic document `m7_e_scanned`.
- Frequency: 1 baseline document.
- Symptom: Missing 130 words and excess 0 words..
- Root cause: `src/poc/extract.py` builds text elements from PyMuPDF text blocks and line spans; `config/extraction.yaml` supplies the heading and bullet heuristics. Image-only text has no OCR path..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic extractor or configuration change; OCR is out of scope.

## M7 baseline — m7_e_scanned: headings
- Where: M7 synthetic document `m7_e_scanned`.
- Frequency: 1 baseline document.
- Symptom: Matched 0/4; missing=[(1, 'risk resolution'), (1, 'prototype review'), (1, 'iteration contract'), (1, 'exit evidence')]; extra=[]..
- Root cause: `src/poc/extract.py` reads page text through PyMuPDF; these pages contain only raster images, so no heading text reaches the numbered-heading detector. OCR is out of scope.
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: OCR is out of scope; no baseline fix applied.

## M7 baseline — m7_e_scanned: section_mapping
- Where: M7 synthetic document `m7_e_scanned`.
- Frequency: 1 baseline document.
- Symptom: Correct 0/4 expected top-level classifications..
- Root cause: `src/poc/enrich.py` applies keyword rules from `config/classification.yaml`; the baseline runner deliberately skips LLM fallback, so unknown wording stays unclassified..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: classification configuration or generic rule coverage; no LLM used.

## M7 baseline — m7_e_scanned: ledger
- Where: M7 synthetic document `m7_e_scanned`.
- Frequency: 1 baseline document.
- Symptom: Unplaced=0; pending=5..
- Root cause: `src/poc/render_docx.py` places content only under a preceding heading with a canonical target section; unmatched headings leave elements without a destination..
- Action: Recorded as a baseline failure; no extractor, renderer, or configuration fix was applied in M7.
- Residual risk: generic renderer or classification coverage; measured without fixes.

## M7 verifier baseline — m7_a_same_style: heading_missing_or_wrong_level
- Where: M7 synthetic document `m7_a_same_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 4 verifier defect record(s).
- Symptom: The unchanged verifier emitted `heading_missing_or_wrong_level`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_a_same_style: image_set_or_count_mismatch
- Where: M7 synthetic document `m7_a_same_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `image_set_or_count_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_a_same_style: mapping_mismatch
- Where: M7 synthetic document `m7_a_same_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 2 verifier defect record(s).
- Symptom: The unchanged verifier emitted `mapping_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_a_same_style: pending_disposition
- Where: M7 synthetic document `m7_a_same_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `pending_disposition`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_a_same_style: placement_ledger_mismatch
- Where: M7 synthetic document `m7_a_same_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `placement_ledger_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_a_same_style: table_count_mismatch
- Where: M7 synthetic document `m7_a_same_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `table_count_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_a_same_style: table_shape_mismatch
- Where: M7 synthetic document `m7_a_same_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 2 verifier defect record(s).
- Symptom: The unchanged verifier emitted `table_shape_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_a_same_style: text_excess
- Where: M7 synthetic document `m7_a_same_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 32 verifier defect record(s).
- Symptom: The unchanged verifier emitted `text_excess`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_a_same_style: text_missing
- Where: M7 synthetic document `m7_a_same_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 43 verifier defect record(s).
- Symptom: The unchanged verifier emitted `text_missing`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_b_new_style: heading_missing_or_wrong_level
- Where: M7 synthetic document `m7_b_new_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 3 verifier defect record(s).
- Symptom: The unchanged verifier emitted `heading_missing_or_wrong_level`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_b_new_style: image_set_or_count_mismatch
- Where: M7 synthetic document `m7_b_new_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `image_set_or_count_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_b_new_style: mapping_mismatch
- Where: M7 synthetic document `m7_b_new_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 2 verifier defect record(s).
- Symptom: The unchanged verifier emitted `mapping_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_b_new_style: pending_disposition
- Where: M7 synthetic document `m7_b_new_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `pending_disposition`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_b_new_style: placement_ledger_mismatch
- Where: M7 synthetic document `m7_b_new_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `placement_ledger_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_b_new_style: source_order_violation
- Where: M7 synthetic document `m7_b_new_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `source_order_violation`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_b_new_style: text_excess
- Where: M7 synthetic document `m7_b_new_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 24 verifier defect record(s).
- Symptom: The unchanged verifier emitted `text_excess`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_b_new_style: text_missing
- Where: M7 synthetic document `m7_b_new_style`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 16 verifier defect record(s).
- Symptom: The unchanged verifier emitted `text_missing`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_c_borderless_tables: heading_missing_or_wrong_level
- Where: M7 synthetic document `m7_c_borderless_tables`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 4 verifier defect record(s).
- Symptom: The unchanged verifier emitted `heading_missing_or_wrong_level`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_c_borderless_tables: mapping_mismatch
- Where: M7 synthetic document `m7_c_borderless_tables`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 2 verifier defect record(s).
- Symptom: The unchanged verifier emitted `mapping_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_c_borderless_tables: pending_disposition
- Where: M7 synthetic document `m7_c_borderless_tables`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `pending_disposition`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_c_borderless_tables: placement_ledger_mismatch
- Where: M7 synthetic document `m7_c_borderless_tables`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `placement_ledger_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_c_borderless_tables: text_excess
- Where: M7 synthetic document `m7_c_borderless_tables`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 32 verifier defect record(s).
- Symptom: The unchanged verifier emitted `text_excess`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_c_borderless_tables: text_missing
- Where: M7 synthetic document `m7_c_borderless_tables`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 124 verifier defect record(s).
- Symptom: The unchanged verifier emitted `text_missing`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_d_two_column: heading_missing_or_wrong_level
- Where: M7 synthetic document `m7_d_two_column`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 7 verifier defect record(s).
- Symptom: The unchanged verifier emitted `heading_missing_or_wrong_level`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_d_two_column: image_placement_mismatch
- Where: M7 synthetic document `m7_d_two_column`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `image_placement_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_d_two_column: image_relationship_mismatch
- Where: M7 synthetic document `m7_d_two_column`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `image_relationship_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_d_two_column: image_set_or_count_mismatch
- Where: M7 synthetic document `m7_d_two_column`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `image_set_or_count_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_d_two_column: mapping_mismatch
- Where: M7 synthetic document `m7_d_two_column`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 4 verifier defect record(s).
- Symptom: The unchanged verifier emitted `mapping_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_d_two_column: pending_disposition
- Where: M7 synthetic document `m7_d_two_column`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `pending_disposition`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_d_two_column: placement_ledger_mismatch
- Where: M7 synthetic document `m7_d_two_column`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `placement_ledger_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_d_two_column: table_count_mismatch
- Where: M7 synthetic document `m7_d_two_column`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `table_count_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_d_two_column: table_shape_mismatch
- Where: M7 synthetic document `m7_d_two_column`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 2 verifier defect record(s).
- Symptom: The unchanged verifier emitted `table_shape_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_d_two_column: text_excess
- Where: M7 synthetic document `m7_d_two_column`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 56 verifier defect record(s).
- Symptom: The unchanged verifier emitted `text_excess`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_d_two_column: text_missing
- Where: M7 synthetic document `m7_d_two_column`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 119 verifier defect record(s).
- Symptom: The unchanged verifier emitted `text_missing`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_e_scanned: image_placement_mismatch
- Where: M7 synthetic document `m7_e_scanned`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `image_placement_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_e_scanned: image_relationship_mismatch
- Where: M7 synthetic document `m7_e_scanned`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `image_relationship_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_e_scanned: image_set_or_count_mismatch
- Where: M7 synthetic document `m7_e_scanned`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `image_set_or_count_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_e_scanned: mapping_mismatch
- Where: M7 synthetic document `m7_e_scanned`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 4 verifier defect record(s).
- Symptom: The unchanged verifier emitted `mapping_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_e_scanned: pending_disposition
- Where: M7 synthetic document `m7_e_scanned`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `pending_disposition`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_e_scanned: placement_ledger_mismatch
- Where: M7 synthetic document `m7_e_scanned`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `placement_ledger_mismatch`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## M7 verifier baseline — m7_e_scanned: text_excess
- Where: M7 synthetic document `m7_e_scanned`; existing verifier output in `data/m7/output/m7_metrics.json`.
- Frequency: 1 verifier defect record(s).
- Symptom: The unchanged verifier emitted `text_excess`.
- Root cause: See the per-code likely cause in `docs/M7_GENERALISATION_REPORT.md`.
- Action: Recorded as baseline measurement; no pipeline fix was applied.
- Residual risk: This defect remains and shows the baseline's measured generalisation limit.

## Image fragments grouped into composites for c1_waterfall_pm_documentation_1_329b8ad5
- Where: source pages 1.
- Frequency: 5 parts grouped into 1 composite(s).
- What happened: The PDF stores some logical figures as adjacent image fragments.
- Action: Retained each exact source fragment and built a deterministic PNG composite; figure diagnosis records per-part hashes and render comparison scores.
- Scaling: No source part required resampling; a one-pixel placement tolerance covers PDF coordinate rounding.
- Residual risk: Composite comparison uses a normalized 150 dpi page render and may show antialiasing differences.

## Image fragments grouped into composites for c1_kanban_pm_final_2_5340493d
- Where: source pages 7.
- Frequency: 2 parts grouped into 1 composite(s).
- What happened: The PDF stores some logical figures as adjacent image fragments.
- Action: Retained each exact source fragment and built a deterministic PNG composite; figure diagnosis records per-part hashes and render comparison scores.
- Scaling: No source part required resampling; a one-pixel placement tolerance covers PDF coordinate rounding.
- Residual risk: Composite comparison uses a normalized 150 dpi page render and may show antialiasing differences.
