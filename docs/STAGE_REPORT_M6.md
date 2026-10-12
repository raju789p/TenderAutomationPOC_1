# Stage Report — M6: Report and One-Command Demo

## 1. What was built

- Added `python -m poc.cli run --all --provider <name>` to extract the configured documents, reuse matching saved image enrichment, restore saved heading classifications (or apply configured rules), render DOCX files, verify them, and generate the accuracy report and project summary.
- The M6 run path does not load provider settings, read `.env`, or instantiate a provider. It made zero provider calls. Figure enrichment is restored only when the stable figure ID and display-image SHA-256 match; missing results are marked failed rather than invented.
- Added `python -m poc.cli report`, which generates `docs/accuracy_report.md` and `docs/SUMMARY.md` from `data/output/metrics.json`.
- Completed `docs/challenges_log.md`, including the unsupported “Skógafoss” caption and the M4 rendering and pagination issues.
- Added `tests/test_m6_report.py` to assert that the report's results table is derived from the current metrics JSON.
- LibreOffice was not installed/on PATH. The existing optional conversion path skipped PDF and PNG review output and recorded the limitation in the challenges log.

## 2. How to run it

```sh
.venv/bin/python -m poc.cli run --all --provider mock
.venv/bin/python -m poc.cli report
.venv/bin/python -m pytest -q
```

The provider name is required for CLI compatibility but is not used by `run`; saved enrichment only is used. No network or LLM requests are made.

## 3. Test results

Full offline suite:

```text
47 passed, 5 warnings in 24.70s
```

The warnings are dependency deprecations from PyMuPDF bindings. The seven verifier corruption tests remain included and pass; the new report-to-metrics test also passes.

Two end-to-end demo runs completed. The second run reused all 8 figure results, had zero provider calls, and produced identical SHA-256 hashes for both DOCX files, both elements and classification files, both placement ledgers, `metrics.json`, `verification.md`, `accuracy_report.md`, and `SUMMARY.md`.

First-run command output:

```text
INFO: Extracting configured documents; enrichment is cache-only (provider=mock, calls=0)
INFO: Extracted waterfall: 74 elements, 5 figures
INFO: Extracted kanban: 72 elements, 3 figures
INFO: Saved enrichment reused: 8 figures; missing=0; classifications missing=0
INFO: LibreOffice not installed; skipped PDF and PNG review renders
INFO: waterfall: placed=58 regenerated=16 unplaced=0 defects=0
INFO: kanban: placed=63 regenerated=9 unplaced=0 defects=0
Run complete: waterfall, kanban; 121 placed, 25 regenerated, 0 unplaced, 0 defects
```

## 4. Metrics and inventory produced

| Metric | Waterfall | Kanban | Overall |
|---|---:|---:|---:|
| Text word recall | 100.00% | 100.00% | 100.00% |
| Tables matching | 5/5 | 3/3 | 8/8 |
| Headings matching | 21/21 | 18/18 | 39/39 |
| Display images | 5/5 | 3/3 | 8/8 |
| Composite rebuilds matching | 1/1 | 1/1 | 2/2 |
| Mapping accuracy | 10/10 (100.00%) | 10/10 (100.00%) | 20/20 (100.00%) |
| Image keywords strict, indicative | 22/22 | 13/14 | 35/36 (97.22%) |
| Image keywords normalised, indicative | 22/22 | 14/14 | 36/36 (100.00%) |
| Placed / regenerated / unplaced | 58 / 16 / 0 | 63 / 9 / 0 | 121 / 25 / 0 |
| Defects | 0 | 0 | 0 |

These values are taken from `data/output/metrics.json`; `docs/accuracy_report.md` is generated from that file. Image keyword scores measure selected keyword presence only. The Waterfall cover figure has no selected expected keywords and is not measured for this score.

## 5. Decisions and assumptions

- The M6 execution constraints prohibit reading `.env`, network access, and LLM calls. The demo therefore treats the current saved `elements.json` AI fields and `classification.json` as the local enrichment cache. It checks display-image hashes before reusing figure descriptions.
- When no saved classification matches, M6 applies configured heading rules locally. Unmatched headings are marked failed; no LLM fallback is attempted. Missing or changed figures are marked failed and reported by the run summary's reuse counts.
- The requested provider argument is accepted but does not select a provider in this cache-only workflow. This lets the documented one-command interface be exercised offline without reading any key or provider settings.
- Accuracy metrics remain scoped to the two configured PDFs and the current target template.

## 6. Deviations from the spec

- The M6 run does not make real-provider requests, even if `--provider gemini` or `--provider groq` is supplied, because this task explicitly prohibits network and LLM calls. It uses saved enrichment only.
- The report's “seven corruption tests” describes the existing independent offline tests: table row deletion, image swap, paragraph word change, paragraph deletion, heading change, section reordering, and private-use character insertion.
- Optional PDF output was skipped because LibreOffice was unavailable.

## 7. Challenges logged

- Input PDF filenames differ from the plan.
- Ruled table fragmentation and table-overlap text suppression.
- Split image streams and composite validation.
- Gemini sandbox connectivity failure and successful human-side close-out.
- Unsupported AI place-name caption and strict versus normalised keyword scoring.
- Private-use bullet marker rendering and DOCX pagination relationships.
- LibreOffice visual review skipped.

The complete M0–M6 history and residual risks are in `docs/challenges_log.md`.

## 8. Open issues and risks

- Human visual comparison of the DOCX files against both PDFs is still required; LibreOffice was unavailable for rendered review.
- The saved AI caption that names Skógafoss is unsupported by the source image. Future prompt work should say: “describe only what is visible; no place, person or brand names.” The saved output was not edited.
- Image keyword recall does not prove full transcription accuracy, and text embedded in images cannot be fully checked automatically.
- The contents list is static and contains no page numbers.
- M6 is complete. No later stage was started.
