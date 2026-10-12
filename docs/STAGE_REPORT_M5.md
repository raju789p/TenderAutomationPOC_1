# Stage Report — M5: Verifier and Metrics

## 1. What was built

- Added `src/poc/verify.py` with independent DOCX re-extraction via python-docx and ZIP media inspection.
- Wired `python -m poc.cli verify --all` to produce `data/output/metrics.json` and `data/output/verification.md`.
- Added offline clean-output and deliberate-corruption tests covering table row deletion, image swap, paragraph word change, paragraph deletion, heading title change, target section order change, and private-use character insertion.
- Verification uses cached AI enrichment from `elements.json`; it makes no network or LLM calls.

## 2. How to run it

```sh
.venv/bin/python -m poc.cli verify --all
.venv/bin/python -m pytest -q
```

## 3. Test results

```text
46 passed, 5 warnings in 25.15s
```

The five warnings are PyMuPDF/SWIG deprecation warnings. The corruption tests pass by asserting the verifier reports each targeted defect category and its location or exact word-level impact. Tests and verification run offline.

## 4. Metrics and inventory

All values below were read from `data/output/metrics.json`, produced by `verify --all`. Text recall is multiset word recall over source text excluding regenerated elements. Table matching excludes the regenerated contents table. Image keyword recall is **indicative; measures keyword presence only**.

| Document | Elements (placed / regenerated / unplaced / pending) | Text recall; missing / excess | Source tables matching | Headings matching | Contents topics | Media / display images | Composites rebuilt / matching | Mapping accuracy | Strict keyword recall | Normalised keyword recall | Section / relative order | Private-use chars | Defects |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---:|---:|
| waterfall | 74 (58 / 16 / 0 / 0) | 100.00%; 0 / 0 | 5/5 | 21/21 | 10/10 | 5/5 | 1/1 | 10/10 (100.00%) | 22/22 (100.00%) | 22/22 (100.00%) | PASS / PASS | 0 | 0 |
| kanban | 72 (63 / 9 / 0 / 0) | 100.00%; 0 / 0 | 3/3 | 18/18 | 10/10 | 3/3 | 1/1 | 10/10 (100.00%) | 13/14 (92.86%) | 14/14 (100.00%) | PASS / PASS | 0 | 0 |

| Overall | — | 100.00%; 0 / 0 | 8/8 | 39/39 | 20/20 | 8/8 | 2/2 | 20/20 (100.00%) | 35/36 (97.22%) | 36/36 (100.00%) | 2/2 / 2/2 | 0 | 0 |

**NOT MEASURED:** Waterfall cover-photo keyword recall has no denominator because the answer key selects no image tokens for that figure. The per-figure report records the reason. All other requested metrics were computed from the current source elements, classification records, cached enrichment, and DOCX outputs.

### Generated artifacts

- `data/output/metrics.json` contains per-document and overall metrics by category, detailed comparisons, and defect records.
- `data/output/verification.md` lists all misses, excess words with output locations, table/heading/contents/image/order findings, section mapping comparisons, and per-figure indicative keyword results.

## 5. Decisions and assumptions

- Source heading level 1 maps to Word Heading 2 and source heading level 2 maps to Word Heading 3, one level beneath the generated target-section Heading 1. The verifier checks the source title verbatim and this relative hierarchy.
- Generated-word allowances are constructed from the target configuration, renderer labels, source-map labels, and the saved AI captions/transcriptions; arbitrary unexplained output words remain possible-fabrication excess.
- Image token groups pair to figures in stable extraction order within each document, matching the M3 review. Strict matching is case-insensitive substring matching. Normalised matching lowercases both sides and removes hyphens and whitespace.
- The regenerated contents table is not compared as a source table; the remaining source tables are compared shape-wise and cell-by-cell after whitespace normalisation.

## 6. Deviations from the spec

- None. The verifier performs local DOCX, source IR, cached enrichment, config, and answer-key checks only.

## 7. Challenges logged

- No new M5 challenges. The earlier LibreOffice visual-review limitation remains in `docs/challenges_log.md`.

## 8. Open issues and risks

- Image-token recall measures selected keyword presence, not complete transcription accuracy. Strict matching misses `BOTTLENECK` where the transcription has `BOTTLE-NECK`; normalised matching records the match.
- Automated checks do not replace human visual review of the Word layout against source PDFs.
- M6 has not been started.
