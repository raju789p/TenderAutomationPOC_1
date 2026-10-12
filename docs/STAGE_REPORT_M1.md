# Stage Report — M1 Extraction (Fix Pass)

## Fix pass 2 — text conservation and table-adjacent prose

Waterfall page 13 previously had zero paragraphs because PyMuPDF placed the table cells and the bold sentence after the table in one text block. The extractor compared that full block bbox with the table bbox and discarded the block at the configured 0.5 overlap ratio. The sentence line begins at y=270.434 pt; the detected table bbox ends at y=270.137 pt, so it lies 0.296 pt below the table. The pdfplumber 8 pt snap/join settings did not expand the table bbox over it. The failure was caused by block-level suppression, not by those tolerances.

Changed the general rule to check each PyMuPDF text line against the configured `table_text_suppression.line_overlap_ratio` (0.5). Table-contained lines are omitted while non-overlapping lines in the same block continue through normal classification. This restores the sentence as a paragraph without a page-specific exception. Waterfall page 13 now has 1 paragraph.

Added `tests/test_text_conservation.py`. It compares per-page multisets of normalized words from `page.get_text("words")` with words in paragraphs, bullets, headings, table cells, and page numbers. It normalizes ligatures and case, ignores private-use glyphs, and reports both missing and extra words. Every page below has no missing or extra words.

| Document | Page | PDF words | Element words | Missing words | Extra words |
|---|---:|---:|---:|---|---|
| Waterfall | 1 | 12 | 12 | [] | [] |
| Waterfall | 2 | 38 | 38 | [] | [] |
| Waterfall | 3 | 100 | 100 | [] | [] |
| Waterfall | 4 | 75 | 75 | [] | [] |
| Waterfall | 5 | 153 | 153 | [] | [] |
| Waterfall | 6 | 73 | 73 | [] | [] |
| Waterfall | 7 | 131 | 131 | [] | [] |
| Waterfall | 8 | 146 | 146 | [] | [] |
| Waterfall | 9 | 249 | 249 | [] | [] |
| Waterfall | 10 | 1 | 1 | [] | [] |
| Waterfall | 11 | 130 | 130 | [] | [] |
| Waterfall | 12 | 132 | 132 | [] | [] |
| Waterfall | 13 | 93 | 93 | [] | [] |
| Waterfall | 14 | 99 | 99 | [] | [] |
| Kanban | 1 | 12 | 12 | [] | [] |
| Kanban | 2 | 37 | 37 | [] | [] |
| Kanban | 3 | 346 | 346 | [] | [] |
| Kanban | 4 | 286 | 286 | [] | [] |
| Kanban | 5 | 299 | 299 | [] | [] |
| Kanban | 6 | 355 | 355 | [] | [] |
| Kanban | 7 | 289 | 289 | [] | [] |

The production extraction was run twice. `elements.json` hashes matched between runs:

```text
waterfall 746cfc993c9c19ff2ba8bb5ab1ce547cbefaf079a82b364bf0922bdf43dc40a9
kanban    d4319197679708d19db5ceafc0e4bba416e5b8a1a709587c4290f884de45cdea
```

All tests pass: `10 passed` (`.venv/bin/python -m pytest -q`). The existing inventory and `elements.json` files were refreshed by the repeated extraction; heading, table, figure, and part counts remain unchanged from the M1 fix pass acceptance audit below.

## 1. What was built

- Updated numbered heading parsing in `src/poc/extract.py` and `config/extraction.yaml` so number segments determine heading level. Main headings are level 1; numbered subheadings such as `3.1 Background` are level 2, with number and title stored separately.
- Compared pdfplumber and PyMuPDF table detection. Configured pdfplumber line detection with 8 pt snap and join tolerances; all ten tables now have coherent rows and columns.
- Added per-document `tables_dump.md`, listing every extracted cell as JSON.
- Extended `Figure` with exact-source `parts` metadata. Adjacent/overlapping image pieces on a page are grouped into a logical figure; each source part and any mask bytes are stored and hashed separately.
- Built composite PNGs from exact decoded image bytes, retaining part bytes in `images/parts/`. Composite figures display the PNG; single-part figures point to their exact extracted bytes.
- Added `figure_diagnosis.md` per document with xref, page, bbox, pixel size, colorspace, mask, byte count, hash prefix, same-page relations, and composite comparison scores.
- Updated Hard Rule 3 in `AGENTS.md` to cover fragment composites and their rebuild hashes.
- Added permanent invariants in `tests/test_extract_invariants.py` for deterministic output, part hashes and composite rebuilds, table/paragraph separation, table shapes, heading levels, and same-page grouping.

## 2. How to run it

```sh
source .venv/bin/activate
python -m poc.cli extract --all
python -m pytest -q
```

Human-review artifacts are at `data/work/waterfall/tables_dump.md`, `data/work/kanban/tables_dump.md`, and each document's `figure_diagnosis.md`.

## 3. Test results from the initial M1 fix pass

These historical results were superseded by fix pass 2 above, which reran production extraction and the complete suite after adding the text-conservation test.

The actual extraction command was run twice. The `elements.json` hashes matched across runs:

```text
Run 1: waterfall 37e47b682c88094af39a241b7f6964c314c80e0c3bd26d1c27c4f4ae671de317
       kanban    d4319197679708d19db5ceafc0e4bba416e5b8a1a709587c4290f884de45cdea
Run 2: waterfall 37e47b682c88094af39a241b7f6964c314c80e0c3bd26d1c27c4f4ae671de317
       kanban    d4319197679708d19db5ceafc0e4bba416e5b8a1a709587c4290f884de45cdea
```

Acceptance audit after both runs:

```text
waterfall: pages=14; headings={1: 10, 2: 11}; tables=[(11, 2), (7, 3), (6, 3), (9, 2), (6, 2), (6, 2)]; figures=5; parts=9; all display/part/mask hashes verified
kanban: pages=7; headings={1: 10, 2: 8}; tables=[(11, 2), (5, 2), (8, 2), (6, 2)]; figures=3; parts=4; all display/part/mask hashes verified
deterministic actual extraction: yes
```

Regression and new permanent tests: `python -m pytest -q`

```text
.........                                                                [100%]
=============================== warnings summary ===============================
<frozen importlib._bootstrap>:488
<frozen importlib._bootstrap>:488
  <frozen importlib._bootstrap>:488: DeprecationWarning: builtin type SwigPyPacked has no __module__ attribute

<frozen importlib._bootstrap>:488
<frozen importlib._bootstrap>:488
  <frozen importlib._bootstrap>:488: DeprecationWarning: builtin type SwigPyObject has no __module__ attribute

<frozen importlib._bootstrap>:488
  <frozen importlib._bootstrap>:488: DeprecationWarning: builtin type swigvarlink has no __module__ attribute

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
9 passed, 5 warnings in 5.39s
```

## 4. Metrics and inventory

### Before and after counts

“Before” is the first M1 extractor output. Its image parts are counted as one part per extracted image because the previous model did not retain part records.

| Document | Measure | Before | After |
|---|---|---:|---:|
| Waterfall | Headings (level 1 / level 2) | 10 / 0 | 10 / 11 |
| Waterfall | Tables | 6 | 6 |
| Waterfall | Logical figures | 9 | 5 |
| Waterfall | Image parts | 9 | 9 |
| Kanban | Headings (level 1 / level 2) | 10 / 0 | 10 / 8 |
| Kanban | Tables | 4 | 4 |
| Kanban | Logical figures | 4 | 3 |
| Kanban | Image parts | 4 | 4 |
| Overall | Headings (level 1 / level 2) | 20 / 0 | 20 / 19 |
| Overall | Tables | 10 | 10 |
| Overall | Logical figures | 13 | 8 |
| Overall | Image parts | 13 | 13 |

### Table strategy evidence

The strategy sweep tested pdfplumber line tolerance pairs 0, 1, 2, 3, 5, 8, 10, and 15, plus text-based strategies. PyMuPDF `page.find_tables()` defaults were also checked. The selected pdfplumber `lines/lines` strategy with `snap_tolerance=8` and `join_tolerance=8` produced the human-review shapes across all ten tables. The provided expectations remain unverified; no M2 answer-key audit was run.

| PDF | Page | pdfplumber default | PyMuPDF default | Selected pdfplumber lines, snap/join 8 |
|---|---:|---:|---:|---:|
| Waterfall | 2 | 11×4 | 11×4 | 11×2 |
| Waterfall | 7 | 11×7 | 11×7 | 7×3 |
| Waterfall | 11 | 8×5 | 8×5 | 6×3 |
| Waterfall | 12 | 14×4 | 14×4 | 9×2 |
| Waterfall | 13 | 11×4 | 11×4 | 6×2 |
| Waterfall | 14 | 10×4 | 10×4 | 6×2 |
| Kanban | 2 | 11×2 | 11×2 | 11×2 |
| Kanban | 4 | 5×2 | 5×2 | 5×2 |
| Kanban | 6 | 8×2 | 8×2 | 8×2 |
| Kanban | 7 | 6×2 | 6×2 | 6×2 |

### Composite validation

The metric is normalized mean absolute RGB pixel difference in `[0, 1]` between the composite and a 150 dpi rendering of the same page region. Lower values indicate closer pixel agreement.

| Composite | Page | Parts | Difference score | Resampling |
|---|---:|---:|---:|---|
| `waterfall-p001-005` | 1 | 5 | 0.01187915 | None |
| `kanban-p007-008` | 7 | 2 | 0.02021262 | None |

### Inventories

The complete per-document inventories follow.

#### Waterfall inventory

```markdown
# Extraction inventory — waterfall

Source: `WaterFall_PM_Documentation 1.pdf`
Pages: 14

## Counts by type

| Type | Count |
|---|---:|
| bullet | 6 |
| figure | 5 |
| heading | 21 |
| page_number | 14 |
| paragraph | 21 |
| table | 6 |

## Counts by page

| Page | bullet | figure | heading | page_number | paragraph | table |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 1 | 0 | 1 | 4 | 0 |
| 2 | 0 | 0 | 0 | 1 | 1 | 1 |
| 3 | 0 | 0 | 1 | 1 | 2 | 0 |
| 4 | 0 | 0 | 1 | 1 | 1 | 0 |
| 5 | 0 | 0 | 5 | 1 | 4 | 0 |
| 6 | 6 | 0 | 1 | 1 | 1 | 0 |
| 7 | 0 | 0 | 1 | 1 | 1 | 1 |
| 8 | 0 | 2 | 3 | 1 | 2 | 0 |
| 9 | 0 | 1 | 4 | 1 | 4 | 0 |
| 10 | 0 | 1 | 0 | 1 | 0 | 0 |
| 11 | 0 | 0 | 2 | 1 | 1 | 1 |
| 12 | 0 | 0 | 1 | 1 | 0 | 1 |
| 13 | 0 | 0 | 1 | 1 | 0 | 1 |
| 14 | 0 | 0 | 1 | 1 | 0 | 1 |

## Extracted table shapes

| Element ID | Page | Rows | Columns | Role |
|---|---:|---:|---:|---|
| waterfall-p002-002 | 2 | 11 | 2 | toc |
| waterfall-p007-002 | 7 | 7 | 3 | body |
| waterfall-p011-004 | 11 | 6 | 3 | body |
| waterfall-p012-002 | 12 | 9 | 2 | body |
| waterfall-p013-002 | 13 | 6 | 2 | body |
| waterfall-p014-002 | 14 | 6 | 2 | body |

## Heading levels and image parts

Heading levels: {1: 10, 2: 11}
Logical figures: 5; image parts: 9; multipart composites: 1


## Font histogram (PyMuPDF span size, points)

| Size | Span count |
|---:|---:|
| 10.5 | 267 |
| 12.0 | 2 |
| 14.0 | 11 |
| 15.9 | 1 |
| 18.0 | 11 |
| 33.9 | 1 |

## Vector drawing regions

Detected 0 standalone qualifying region(s); 40 large drawing shape(s) overlap detected tables and were treated as table structure.

| Page | Drawing index | Bounding box | Area (pt²) |
|---:|---:|---|---:|
| 2 | 5 | [51.96, 75.72, 542.04, 90.96] | 7468.82 |
| 2 | 11 | [51.96, 91.44, 542.04, 106.32] | 7292.39 |
| 2 | 13 | [51.96, 106.32, 542.04, 121.68] | 7527.64 |
| 2 | 19 | [51.96, 121.68, 542.04, 136.92] | 7468.81 |
| 2 | 22 | [51.96, 136.92, 542.04, 152.28] | 7527.63 |
| 2 | 28 | [51.96, 152.28, 542.04, 167.52] | 7468.82 |
| 2 | 31 | [51.96, 167.52, 542.04, 182.88] | 7527.63 |
| 2 | 37 | [51.96, 182.88, 542.04, 198.24] | 7527.63 |
| 2 | 40 | [51.96, 198.24, 542.04, 213.48] | 7468.82 |
| 2 | 46 | [51.96, 213.48, 542.04, 228.84] | 7527.62 |
| 7 | 17 | [51.96, 114.24, 549.24, 139.92] | 12770.15 |
| 7 | 19 | [51.96, 139.92, 549.24, 165.96] | 12949.17 |
| 7 | 29 | [51.96, 165.96, 549.24, 192.12] | 13008.85 |
| 7 | 32 | [51.96, 192.12, 549.24, 218.28] | 13008.85 |
| 7 | 43 | [51.96, 218.28, 549.24, 257.16] | 19334.25 |
| 11 | 14 | [51.96, 230.4, 558.24, 256.56] | 13244.28 |
| 11 | 23 | [51.96, 269.88, 558.24, 296.04] | 13244.29 |
| 12 | 12 | [51.96, 114.24, 549.24, 139.92] | 12770.15 |
| 12 | 14 | [51.96, 139.92, 549.24, 178.8] | 19334.24 |
| 12 | 22 | [51.96, 178.8, 549.24, 204.96] | 13008.85 |
| 12 | 25 | [51.96, 204.96, 549.24, 231.12] | 13008.85 |
| 12 | 27 | [52.44, 231.6, 300.36, 270.0] | 9520.13 |
| 12 | 29 | [300.84, 231.6, 548.76, 270.0] | 9520.13 |
| 12 | 34 | [51.96, 231.12, 549.24, 270.0] | 19334.25 |
| 12 | 37 | [51.96, 270.0, 549.24, 296.16] | 13008.85 |
| 12 | 45 | [51.96, 296.16, 549.24, 322.32] | 13008.85 |
| 13 | 12 | [51.96, 114.24, 549.24, 139.92] | 12770.15 |
| 13 | 14 | [51.96, 139.92, 549.24, 165.96] | 12949.17 |
| 13 | 16 | [52.44, 166.44, 300.36, 204.96] | 9549.88 |
| 13 | 18 | [300.84, 166.44, 548.76, 204.96] | 9549.88 |
| 13 | 23 | [51.96, 165.96, 549.24, 204.96] | 19393.92 |
| 13 | 26 | [51.96, 204.96, 549.24, 231.12] | 13008.85 |
| 13 | 28 | [52.44, 231.6, 300.36, 270.0] | 9520.13 |
| 13 | 30 | [300.84, 231.6, 548.76, 270.0] | 9520.13 |
| 14 | 12 | [51.96, 114.24, 549.24, 139.92] | 12770.15 |
| 14 | 14 | [51.96, 139.92, 549.24, 178.8] | 19334.24 |
| 14 | 22 | [51.96, 178.8, 549.24, 204.96] | 13008.85 |
| 14 | 25 | [51.96, 204.96, 549.24, 231.12] | 13008.85 |
| 14 | 27 | [52.44, 231.6, 300.36, 270.0] | 9520.13 |
| 14 | 29 | [300.84, 231.6, 548.76, 270.0] | 9520.13 |

No standalone vector-only image regions were identified outside detected tables and raster image areas.


## Unknown bullet glyphs

Count: 0


## Cross-page paragraph merges

Count: 0 (disabled; source blocks remain separate across page boundaries)


## Heading threshold evidence

Configured numbered heading minimum: 14 pt. Numbered headings observed at 18 pt; body copy at 10.5 pt.
```

#### Kanban inventory

```markdown
# Extraction inventory — kanban

Source: `Kanban_PM_Final 2.pdf`
Pages: 7

## Counts by type

| Type | Count |
|---|---:|
| bullet | 8 |
| figure | 3 |
| heading | 18 |
| page_number | 7 |
| paragraph | 32 |
| table | 4 |

## Counts by page

| Page | bullet | figure | heading | page_number | paragraph | table |
|---:|---:|---:|---:|---:|---:|---:|
| 1 | 0 | 0 | 0 | 1 | 4 | 0 |
| 2 | 0 | 0 | 0 | 1 | 1 | 1 |
| 3 | 0 | 0 | 6 | 1 | 7 | 0 |
| 4 | 8 | 1 | 2 | 1 | 4 | 1 |
| 5 | 0 | 1 | 6 | 1 | 5 | 0 |
| 6 | 0 | 0 | 3 | 1 | 6 | 1 |
| 7 | 0 | 1 | 1 | 1 | 5 | 1 |

## Extracted table shapes

| Element ID | Page | Rows | Columns | Role |
|---|---:|---:|---:|---|
| kanban-p002-002 | 2 | 11 | 2 | toc |
| kanban-p004-015 | 4 | 5 | 2 | body |
| kanban-p006-004 | 6 | 8 | 2 | body |
| kanban-p007-007 | 7 | 6 | 2 | body |

## Heading levels and image parts

Heading levels: {1: 10, 2: 8}
Logical figures: 3; image parts: 4; multipart composites: 1


## Font histogram (PyMuPDF span size, points)

| Size | Span count |
|---:|---:|
| 9.0 | 32 |
| 9.5 | 6 |
| 10.5 | 144 |
| 11.0 | 1 |
| 18.0 | 20 |
| 24.0 | 1 |
| 29.9 | 1 |

## Vector drawing regions

Detected 0 standalone qualifying region(s); 26 large drawing shape(s) overlap detected tables and were treated as table structure.

| Page | Drawing index | Bounding box | Area (pt²) |
|---:|---:|---|---:|
| 2 | 4 | [51.96, 85.68, 549.24, 105.96] | 10084.84 |
| 2 | 9 | [51.96, 106.44, 549.24, 126.12] | 9786.47 |
| 2 | 11 | [51.96, 126.12, 549.24, 146.4] | 10084.83 |
| 2 | 16 | [51.96, 146.4, 549.24, 166.68] | 10084.85 |
| 2 | 19 | [51.96, 166.68, 549.24, 186.84] | 10025.16 |
| 2 | 24 | [51.96, 186.84, 549.24, 207.12] | 10084.84 |
| 2 | 27 | [51.96, 207.12, 549.24, 227.4] | 10084.85 |
| 2 | 32 | [51.96, 227.4, 549.24, 247.56] | 10025.16 |
| 2 | 35 | [51.96, 247.56, 549.24, 267.84] | 10084.84 |
| 2 | 40 | [51.96, 267.84, 549.24, 288.12] | 10084.84 |
| 4 | 4 | [51.96, 481.08, 549.24, 496.92] | 7876.9 |
| 4 | 9 | [51.96, 497.4, 549.24, 512.04] | 7280.16 |
| 4 | 11 | [51.96, 512.04, 549.24, 527.16] | 7518.9 |
| 4 | 16 | [51.96, 527.16, 549.24, 542.28] | 7518.84 |
| 6 | 4 | [51.96, 204.84, 549.24, 220.68] | 7876.91 |
| 6 | 9 | [51.96, 221.16, 549.24, 235.8] | 7280.17 |
| 6 | 11 | [51.96, 235.8, 549.24, 250.92] | 7518.88 |
| 6 | 16 | [51.96, 250.92, 549.24, 266.04] | 7518.88 |
| 6 | 19 | [51.96, 266.04, 549.24, 281.28] | 7578.54 |
| 6 | 24 | [51.96, 281.28, 549.24, 296.4] | 7518.89 |
| 6 | 27 | [51.96, 296.4, 549.24, 311.52] | 7518.86 |
| 7 | 4 | [51.96, 428.52, 549.24, 444.36] | 7876.91 |
| 7 | 9 | [51.96, 444.84, 549.24, 459.48] | 7280.19 |
| 7 | 11 | [51.96, 459.48, 549.24, 474.6] | 7518.86 |
| 7 | 16 | [51.96, 474.6, 549.24, 489.72] | 7518.9 |
| 7 | 19 | [51.96, 489.72, 549.24, 504.84] | 7518.86 |

No standalone vector-only image regions were identified outside detected tables and raster image areas.


## Unknown bullet glyphs

Count: 0


## Cross-page paragraph merges

Count: 0 (disabled; source blocks remain separate across page boundaries)


## Heading threshold evidence

Configured numbered heading minimum: 14 pt. Numbered headings observed at 18 pt; body copy at 10.5 pt.
```

## 5. Decisions & assumptions

- Heading recognition is configuration-driven by `numbered_pattern`; level is the number of numeric segments. The 14 pt threshold retains headings while excluding observed 10.5 pt body text. Span histograms remain in the inventories.
- Table extraction uses pdfplumber with the measured 8 pt line snap/join tolerances. Cell strings are copied with whitespace normalization only; `tables_dump.md` exposes every cell for human review.
- Image pieces are grouped by same-page bbox overlap or adjacency within the configured 1 pt tolerance. Parts are sorted by page position and xref before receiving stable part IDs.
- Composite dimensions and placement use source pixel dimensions and PDF bboxes. A one-pixel tolerance handles coordinate rounding; neither current composite required resizing.
- Composite validation resizes only the comparison copy to the 150 dpi render dimensions. The saved composite is not resampled.
- No answer key was opened or compared, and no M2 audit was started.

## 6. Deviations from the spec

- None for the requested M1 correction pass. The selected table output matches the provided unverified shapes; this is a strategy check, not answer-key validation.
- The actual source filenames still contain spaces, as recorded in M0; inputs were not renamed or modified.

## 7. Challenges logged

- Word-exported list markers use a private-use glyph.
- pdfplumber fragments cells in ruled Waterfall tables (resolved with configured snap/join tolerances; human review remains).
- Large PDF drawing shapes overlap ruled tables.
- Image fragments grouped into composites.

## 8. Open issues and risks

- Human review of both `tables_dump.md` files is still needed. Shapes were selected from line-detection evidence and the architect's unverified expectation; they have not been checked against an answer key.
- Nonzero composite pixel-difference scores include renderer antialiasing and are indicative. Exact fragment and mask hashes are preserved, and the permanent test rebuilds each composite from those bytes.
- Image grouping uses geometric adjacency; an unrelated image placed directly against another could be grouped. Diagnosis files retain each part's bbox and relations for review.
- No image transcription or M2 answer-key validation was performed.
