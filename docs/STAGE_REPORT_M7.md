# Stage Report — M7: Generalisation Baseline

## 1. What was built

- Added `scripts/make_m7_docs.py`, which generates five fixed-seed PyMuPDF PDFs and independent ground-truth JSON files. PDF saves use reproducible metadata and stable trailer IDs.
- Added `config/documents_m7.yaml` for the five isolated source documents.
- Added `scripts/run_m7.py`, which invokes the existing extractor, renderer, and verifier in `data/m7/runtime` and writes DOCX files only to `data/m7/output/`. Classification uses existing configured rules only; unknown headings are left unclassified. No LLM or network call is made.
- Added `scripts/m7_score.py`, which compares extraction and DOCX verification results against generator-owned truth, writes `data/m7/output/m7_metrics.json`, generates `docs/M7_GENERALISATION_REPORT.md`, and appends each measured failure to `docs/challenges_log.md`.
- Added `tests/test_m7_generator.py`, which generates the fixture set twice in separate temporary directories and compares the SHA-256 hashes of every PDF, truth JSON, and image asset.
- No changes were made to `src/`, `config/extraction.yaml`, `config/classification.yaml`, `docs/answer_key.json`, golden fixtures, or pre-existing tests. No fixes were applied to the measured pipeline.

## 2. How to run it

```sh
.venv/bin/python scripts/make_m7_docs.py
.venv/bin/python scripts/run_m7.py
.venv/bin/python scripts/m7_score.py
.venv/bin/python -m pytest -q
```

The scorer uses the existing verifier where applicable. M7 runs in an isolated runtime tree, so the M0–M6 input and output files are left untouched.

## 3. Test results

Full offline test suite:

```text
48 passed, 5 warnings in 26.04s
```

The five warnings are existing PyMuPDF binding deprecations. The generator determinism test passed: two independent fixture generations produced identical hashes for all generated PDFs, truth files, and image assets. The earlier failed determinism check identified variable PDF trailer IDs; enabling PyMuPDF reproducible output resolved that generator issue without changing the conversion pipeline.

Pipeline and scorer output:

```text
m7_a_same_style: complete
m7_b_new_style: complete
m7_c_borderless_tables: complete
m7_d_two_column: complete
m7_e_scanned: complete
Scored 5 documents; crashes=0; failure categories=18
```

## 4. Metrics and inventory produced

| Document | Pages | Text recall | Headings | Tables shape/cells | Images count/hash match | Mapping | Unplaced / pending | Existing verifier defects | Header/footer leaks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| m7_a_same_style | 6/6 | 95.3% | 7/7 | 2/2; 2/2 | 2/2; 0/2 | 4/4 | 0 / 12 | 87 | 0 |
| m7_b_new_style | 6/6 | 95.9% | 7/7 | 2/2; 2/2 | 2/2; 0/2 | 4/4 | 0 / 10 | 49 | 10 |
| m7_c_borderless_tables | 5/5 | 97.9% | 4/4 | 0/2; 0/2 | 1/1; 0/1 | 2/2 | 0 / 29 | 164 | 0 |
| m7_d_two_column | 6/6 | 95.7% | 7/7 | 2/2; 2/2 | 3/3; 0/3 | 4/4 | 0 / 24 | 194 | 0 |
| m7_e_scanned | 6/6 | no text extracted | 0/4 | 0/0; 0/0 | 6/6; 6/6 | 0/4 | 0 / 5 | 10 | 0 |

All five completed without a pipeline crash. The reported 18 failure categories are recorded with likely causes and scope recommendations in the generated generalisation report and challenges log. Text recall includes expected words printed inside figures; no OCR or AI transcription was run. The scanned fixture therefore records **no text extracted** with 0% truth-word recall. Image counts and extracted-image hashes are measured separately; normal PDF fixtures preserved image counts, while their extracted byte hashes did not match the original generated PNG bytes. The scanned page-image hashes matched 6/6.

The detailed metrics include missing and excess words, exact heading comparisons, expected and extracted table cells, image SHA-256 sets, section mapping comparisons, disposition counts, leakage checks, crashes, and the existing verifier's defect records.

## 5. Decisions and assumptions

- “Expected section type” is assigned from the generator's source headings: a type is recorded only where an existing type clearly fits; otherwise the truth value is `unclassified`.
- The M7 runtime copies the unchanged extraction and target-format configs into an isolated directory because the existing renderer and verifier use repository-root paths. A truth-derived runtime answer-key-shaped file lets the existing verifier run without editing the real answer key.
- Unknown headings are not sent to the mock provider. They remain unclassified in the baseline and may leave rendered source elements pending; this is measured, not repaired.
- The image hash comparison uses the source PNG bytes created by the generator against the exact bytes extracted from the PDF. A mismatch is reported even where the image count matches.
- Text printed within images is listed in truth and counted in the text-word comparison, but its OCR/transcription quality is marked not measured.

## 6. Deviations from the spec

- PyMuPDF was used instead of ReportLab, so no dependency installation was needed.
- The separate M7 runtime tree is under `data/m7/runtime`; DOCX outputs and metrics remain under the requested `data/m7/output/` directory.
- This is a baseline-only measurement. No extraction, classification, rendering, or verification behavior was changed.

## 7. Challenges logged

- M7 baseline failures were appended individually to `docs/challenges_log.md` with symptoms, likely root causes, the no-fix action, and residual scope.
- The determinism test initially found non-stable PDF hashes caused by generated trailer IDs; reproducible PDF save settings made generation stable.
- The scanned fixture has no text layer; OCR remains out of scope for this measurement.

## 8. Open issues and risks

- Synthetic documents were made by the same team and model that built the pipeline. They are easier and less messy than real documents: this set is a floor on risk, not a guarantee.
- Borderless and split-page tables were not extracted; repeated header/footer text entered the new-style document's body inventory; unsupported headings left pending elements.
- The scanned PDF produced image elements but no text or headings. OCR would be needed to address that limitation, and no such change was made.
- Exact extracted image bytes differ from the original PNG byte hashes for the non-scanned fixtures despite matching image counts; this baseline does not assert visual pixel equality.
- M7 is complete. No fix stage was started.
