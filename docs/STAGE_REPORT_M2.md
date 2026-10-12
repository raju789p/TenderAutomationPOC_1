# Stage Report — M2 Answer Key and Extraction Audit

## 1. What was built

- Created [answer_key.json](answer_key.json) from the M2 draft in `BUILD_PLAN.md`. Its content was not adjusted to match extraction.
- Added `tests/test_extraction_vs_key.py` for page count, printed page-number count, heading counts by level, non-empty heading titles, bullets, table counts and ordered shapes (including headers), logical figure counts, exact cover lines, and whitespace-normalized spot strings. It does not test `section_types` or `image_tokens`.
- Added golden fixtures `tests/fixtures/golden_tables_waterfall.json` and `tests/fixtures/golden_tables_kanban.json`, with the requested verification comment, plus exact cell-by-cell fixture tests.
- Confirmed level-2 headings store the number (`3.1`) and title (`Background`) in separate fields. Added `tests/fixtures/golden_headings_waterfall.json` and `tests/fixtures/golden_headings_kanban.json` with level, number, and title for every heading, plus an exact regression test.
- Added a conservation negative test that removes one paragraph from an in-memory extraction and verifies the audit reports exactly its missing word multiset.
- Fixed a real M1 bug: printed page number `1` was included in `cover_lines`. Cover-line collection now follows page-number classification, and both documents match the four key cover lines.
- Wrote the per-item comparison and mismatch explanations in `docs/extraction_audit.md`.

## 2. How to run it

```sh
.venv/bin/python -m poc.cli extract --all
.venv/bin/python -m pytest -q
```

## 3. Test results

The complete test suite was run after adding the heading fixtures:

```text
.................                                                        [100%]
=============================== warnings summary ===============================
... PyMuPDF SWIG deprecation warnings ...
17 passed, 5 warnings in 11.87s
```

All tests pass. The current `docs/answer_key.json` has separate Waterfall spot strings for “Maintenance” and the page 13 sentence; both match extracted element text. The audit reflects those current key values. The full pytest run reports five PyMuPDF SWIG deprecation warnings.

## 4. Metrics and inventory

| Document | Pages | Page numbers | H1 | H2 | Bullets | Tables | Table shapes (rows × cols) | Figures | Cover lines |
|---|---:|---:|---:|---:|---:|---:|---|---:|---|
| Waterfall | 14 | 14 | 10 | 11 | 6 | 6 | 11×2, 7×3, 6×3, 9×2, 6×2, 6×2 | 5 | 4/4 match |
| Kanban | 7 | 7 | 10 | 8 | 8 | 4 | 11×2, 5×2, 8×2, 6×2 | 3 | 4/4 match |

Golden table fixture comparisons: 10 tables, all cells match exactly. Golden heading fixtures cover 21 Waterfall headings and 18 Kanban headings; every `(level, number, title)` tuple matches. The conservation negative test detected exactly the deliberately removed paragraph's word multiset, with no extra words.

Heading titles extracted are listed in the audit. The draft contains no expected title lists, so title-by-title comparison is not possible. `section_types` and `image_tokens` were not tested, as specified for later stages.

## 5. Decisions and assumptions

- Golden fixtures are generated from the current extraction and carry the exact requested comment. The architect verification state itself is not independently established by this implementation; the fixtures freeze the extracted cell values for future regression checks.

## 6. Deviations from the spec

- The draft provides no expected heading titles, despite the request to compare titles. Extracted titles are checked for non-empty values and reported, but cannot be compared title-by-title without changing the key.
- The draft plan does not provide expected heading-title lists, so the new golden fixtures provide regression coverage from current extraction but cannot provide independent title-key validation.

## 7. Challenges logged

- Cover line inventory included the printed page number.
- Draft key omits expected heading titles.

## 8. Open issues and risks

- Expected heading title lists are needed for title-by-title acceptance.
- M2 is stopped here; M3 was not started.
