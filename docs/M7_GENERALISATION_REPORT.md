# M7 Generalisation Report

## Baseline results

| Document | Pages | Text recall | Headings | Tables shape/cells | Images count/hash | Mapping accuracy | Unplaced / pending | Verifier defects | Crashes | Header/footer leaks |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| m7_a_same_style | 6/6 | 95.3% | 7/7 | 2/2 shape; 2/2 cells | 2/2; 0/2 hashes | 4/4 | 0 / 12 | 87 | 0 | 0 |
| m7_b_new_style | 6/6 | 95.9% | 7/7 | 2/2 shape; 2/2 cells | 2/2; 0/2 hashes | 4/4 | 0 / 10 | 49 | 0 | 10 |
| m7_c_borderless_tables | 5/5 | 97.9% | 4/4 | 0/2 shape; 0/2 cells | 1/1; 0/1 hashes | 2/2 | 0 / 29 | 164 | 0 | 0 |
| m7_d_two_column | 6/6 | 95.7% | 7/7 | 2/2 shape; 2/2 cells | 3/3; 0/3 hashes | 4/4 | 0 / 24 | 194 | 0 | 0 |
| m7_e_scanned | 6/6 | no text extracted | 0/4 | 0/0 shape; 0/0 cells | 6/6; 6/6 hashes | 0/4 | 0 / 5 | 10 | 0 | 0 |

## What worked

- m7_a_same_style: text recall 95.3%, 7/7 headings, 2 extracted figures.
- m7_b_new_style: text recall 95.9%, 7/7 headings, 2 extracted figures.
- m7_c_borderless_tables: text recall 97.9%, 4/4 headings, 1 extracted figures.
- m7_d_two_column: text recall 95.7%, 7/7 headings, 3 extracted figures.
- m7_e_scanned: text recall no text extracted, 0/4 headings, 6 extracted figures.

The unchanged extraction, rendering, and verification functions completed where noted; no provider or network calls were made. Exact hashes and per-document details are in `data/m7/output/m7_metrics.json`.

## What broke and likely root causes

### m7_a_same_style — text

- Observed: Missing 8 words and excess 0 words.
- Likely root cause: `src/poc/extract.py` builds text elements from PyMuPDF text blocks and line spans; `config/extraction.yaml` supplies the heading and bullet heuristics. Image-only text has no OCR path.
- Scope: generic extractor or configuration change; OCR is out of scope

### m7_a_same_style — images

- Observed: Image count 2/2; exact hash matches 0/2.
- Likely root cause: `src/poc/extract.py` hashes extracted image streams; PDF image re-encoding and full-page rasterization can change byte identity relative to generator source bytes.
- Scope: generic provenance/hash handling or configuration change, measured only

### m7_a_same_style — ledger

- Observed: Unplaced=0; pending=12.
- Likely root cause: `src/poc/render_docx.py` places content only under a preceding heading with a canonical target section; unmatched headings leave elements without a destination.
- Scope: generic renderer or classification coverage; measured without fixes

### m7_b_new_style — text

- Observed: Missing 9 words and excess 0 words.
- Likely root cause: `src/poc/extract.py` builds text elements from PyMuPDF text blocks and line spans; `config/extraction.yaml` supplies the heading and bullet heuristics. Image-only text has no OCR path.
- Scope: generic extractor or configuration change; OCR is out of scope

### m7_b_new_style — images

- Observed: Image count 2/2; exact hash matches 0/2.
- Likely root cause: `src/poc/extract.py` hashes extracted image streams; PDF image re-encoding and full-page rasterization can change byte identity relative to generator source bytes.
- Scope: generic provenance/hash handling or configuration change, measured only

### m7_b_new_style — ledger

- Observed: Unplaced=0; pending=10.
- Likely root cause: `src/poc/render_docx.py` places content only under a preceding heading with a canonical target section; unmatched headings leave elements without a destination.
- Scope: generic renderer or classification coverage; measured without fixes

### m7_b_new_style — header_footer_leakage

- Observed: Header/footer leaks=[{'page': 2, 'field': 'header', 'text': 'M7 B New Style / Internal Playbook'}, {'page': 2, 'field': 'footer', 'text': 'Operations Excellence Series'}, {'page': 3, 'field': 'header', 'text': 'M7 B New Style / Internal Playbook'}, {'page': 3, 'field': 'footer', 'text': 'Operations Excellence Series'}, {'page': 4, 'field': 'header', 'text': 'M7 B New Style / Internal Playbook'}, {'page': 4, 'field': 'footer', 'text': 'Operations Excellence Series'}, {'page': 5, 'field': 'header', 'text': 'M7 B New Style / Internal Playbook'}, {'page': 5, 'field': 'footer', 'text': 'Operations Excellence Series'}, {'page': 6, 'field': 'header', 'text': 'M7 B New Style / Internal Playbook'}, {'page': 6, 'field': 'footer', 'text': 'Operations Excellence Series'}]; page-number leaks=[].
- Likely root cause: `config/extraction.yaml` classifies only isolated digit spans near the page bottom; `src/poc/extract.py` otherwise processes repeated furniture as ordinary page text.
- Scope: generic header/footer detection or configuration change

### m7_c_borderless_tables — text

- Observed: Missing 4 words and excess 0 words.
- Likely root cause: `src/poc/extract.py` builds text elements from PyMuPDF text blocks and line spans; `config/extraction.yaml` supplies the heading and bullet heuristics. Image-only text has no OCR path.
- Scope: generic extractor or configuration change; OCR is out of scope

### m7_c_borderless_tables — tables

- Observed: Cell-exact matches 0/2; extracted 0 tables.
- Likely root cause: `src/poc/extract.py` calls pdfplumber `find_tables`; `config/extraction.yaml` selects the lines strategy and fixed snap/join tolerances, which cannot detect whitespace-aligned tables reliably or join split-page fragments.
- Scope: generic table detection/joining or configuration change, measured only

### m7_c_borderless_tables — images

- Observed: Image count 1/1; exact hash matches 0/1.
- Likely root cause: `src/poc/extract.py` hashes extracted image streams; PDF image re-encoding and full-page rasterization can change byte identity relative to generator source bytes.
- Scope: generic provenance/hash handling or configuration change, measured only

### m7_c_borderless_tables — ledger

- Observed: Unplaced=0; pending=29.
- Likely root cause: `src/poc/render_docx.py` places content only under a preceding heading with a canonical target section; unmatched headings leave elements without a destination.
- Scope: generic renderer or classification coverage; measured without fixes

### m7_d_two_column — text

- Observed: Missing 8 words and excess 0 words.
- Likely root cause: `src/poc/extract.py` builds text elements from PyMuPDF text blocks and line spans; `config/extraction.yaml` supplies the heading and bullet heuristics. Image-only text has no OCR path.
- Scope: generic extractor or configuration change; OCR is out of scope

### m7_d_two_column — images

- Observed: Image count 3/3; exact hash matches 0/3.
- Likely root cause: `src/poc/extract.py` hashes extracted image streams; PDF image re-encoding and full-page rasterization can change byte identity relative to generator source bytes.
- Scope: generic provenance/hash handling or configuration change, measured only

### m7_d_two_column — ledger

- Observed: Unplaced=0; pending=24.
- Likely root cause: `src/poc/render_docx.py` places content only under a preceding heading with a canonical target section; unmatched headings leave elements without a destination.
- Scope: generic renderer or classification coverage; measured without fixes

### m7_e_scanned — text

- Observed: Missing 130 words and excess 0 words.
- Likely root cause: `src/poc/extract.py` builds text elements from PyMuPDF text blocks and line spans; `config/extraction.yaml` supplies the heading and bullet heuristics. Image-only text has no OCR path.
- Scope: generic extractor or configuration change; OCR is out of scope

### m7_e_scanned — headings

- Observed: Matched 0/4; missing=[(1, 'risk resolution'), (1, 'prototype review'), (1, 'iteration contract'), (1, 'exit evidence')]; extra=[].
- Likely root cause: `src/poc/extract.py` reads page text with PyMuPDF; these pages contain only raster images, so no heading text reaches the numbered-heading detector. OCR is out of scope.
- Scope: OCR is out of scope; no baseline fix applied

### m7_e_scanned — section_mapping

- Observed: Correct 0/4 expected top-level classifications.
- Likely root cause: `src/poc/enrich.py` applies keyword rules from `config/classification.yaml`; the baseline runner deliberately skips LLM fallback, so unknown wording stays unclassified.
- Scope: classification configuration or generic rule coverage; no LLM used

### m7_e_scanned — ledger

- Observed: Unplaced=0; pending=5.
- Likely root cause: `src/poc/render_docx.py` places content only under a preceding heading with a canonical target section; unmatched headings leave elements without a destination.
- Scope: generic renderer or classification coverage; measured without fixes

## Existing verifier findings by defect code

These counts come from the unchanged M5 verifier. They are listed separately from ground-truth scoring because the categories overlap.

### m7_a_same_style — verifier `heading_missing_or_wrong_level` (4)

- Likely root cause: `src/poc/extract.py` heading recognition uses numbered-heading and font-size heuristics in `config/extraction.yaml`; raster pages have no text layer.
- Scope: generic heading detection/configuration change; OCR is out of scope

### m7_a_same_style — verifier `image_set_or_count_mismatch` (1)

- Likely root cause: `src/poc/extract.py` extracts image streams while `src/poc/render_docx.py` embeds placed figures; source images may be omitted or normalized.
- Scope: generic image extraction/rendering or provenance change

### m7_a_same_style — verifier `mapping_mismatch` (2)

- Likely root cause: `src/poc/enrich.py` applies keyword rules in `config/classification.yaml`; M7 intentionally made no LLM fallback calls.
- Scope: classification configuration or generic rule coverage change

### m7_a_same_style — verifier `pending_disposition` (1)

- Likely root cause: `src/poc/render_docx.py` places content under recognized target sections; unresolved headings leave dependent source elements pending.
- Scope: generic renderer or classification coverage change

### m7_a_same_style — verifier `placement_ledger_mismatch` (1)

- Likely root cause: `src/poc/render_docx.py` does not create exactly one placement entry per extracted source element in this baseline.
- Scope: generic ledger/rendering change

### m7_a_same_style — verifier `table_count_mismatch` (1)

- Likely root cause: `src/poc/extract.py` uses pdfplumber line-based table detection configured in `config/extraction.yaml`; borderless and split-page grids exceed that strategy.
- Scope: generic table detection or configuration change

### m7_a_same_style — verifier `table_shape_mismatch` (2)

- Likely root cause: `src/poc/extract.py` table extraction relies on line geometry and configured snap/join tolerances in `config/extraction.yaml`.
- Scope: generic table detection or configuration change

### m7_a_same_style — verifier `text_excess` (32)

- Likely root cause: The verifier's generated-text allowlist does not cover some renderer-generated appendix metadata or fallback labels emitted by `src/poc/render_docx.py`.
- Scope: generic generated-text accounting or renderer change

### m7_a_same_style — verifier `text_missing` (43)

- Likely root cause: `src/poc/render_docx.py` places extracted text under recognized target headings; unresolved or misclassified headings leave source words out.
- Scope: generic renderer/classification change

### m7_b_new_style — verifier `heading_missing_or_wrong_level` (3)

- Likely root cause: `src/poc/extract.py` heading recognition uses numbered-heading and font-size heuristics in `config/extraction.yaml`; raster pages have no text layer.
- Scope: generic heading detection/configuration change; OCR is out of scope

### m7_b_new_style — verifier `image_set_or_count_mismatch` (1)

- Likely root cause: `src/poc/extract.py` extracts image streams while `src/poc/render_docx.py` embeds placed figures; source images may be omitted or normalized.
- Scope: generic image extraction/rendering or provenance change

### m7_b_new_style — verifier `mapping_mismatch` (2)

- Likely root cause: `src/poc/enrich.py` applies keyword rules in `config/classification.yaml`; M7 intentionally made no LLM fallback calls.
- Scope: classification configuration or generic rule coverage change

### m7_b_new_style — verifier `pending_disposition` (1)

- Likely root cause: `src/poc/render_docx.py` places content under recognized target sections; unresolved headings leave dependent source elements pending.
- Scope: generic renderer or classification coverage change

### m7_b_new_style — verifier `placement_ledger_mismatch` (1)

- Likely root cause: `src/poc/render_docx.py` does not create exactly one placement entry per extracted source element in this baseline.
- Scope: generic ledger/rendering change

### m7_b_new_style — verifier `source_order_violation` (1)

- Likely root cause: `src/poc/render_docx.py` groups source elements by target section, changing their original relative order in this case.
- Scope: generic renderer ordering change

### m7_b_new_style — verifier `text_excess` (24)

- Likely root cause: The verifier's generated-text allowlist does not cover some renderer-generated appendix metadata or fallback labels emitted by `src/poc/render_docx.py`.
- Scope: generic generated-text accounting or renderer change

### m7_b_new_style — verifier `text_missing` (16)

- Likely root cause: `src/poc/render_docx.py` places extracted text under recognized target headings; unresolved or misclassified headings leave source words out.
- Scope: generic renderer/classification change

### m7_c_borderless_tables — verifier `heading_missing_or_wrong_level` (4)

- Likely root cause: `src/poc/extract.py` heading recognition uses numbered-heading and font-size heuristics in `config/extraction.yaml`; raster pages have no text layer.
- Scope: generic heading detection/configuration change; OCR is out of scope

### m7_c_borderless_tables — verifier `mapping_mismatch` (2)

- Likely root cause: `src/poc/enrich.py` applies keyword rules in `config/classification.yaml`; M7 intentionally made no LLM fallback calls.
- Scope: classification configuration or generic rule coverage change

### m7_c_borderless_tables — verifier `pending_disposition` (1)

- Likely root cause: `src/poc/render_docx.py` places content under recognized target sections; unresolved headings leave dependent source elements pending.
- Scope: generic renderer or classification coverage change

### m7_c_borderless_tables — verifier `placement_ledger_mismatch` (1)

- Likely root cause: `src/poc/render_docx.py` does not create exactly one placement entry per extracted source element in this baseline.
- Scope: generic ledger/rendering change

### m7_c_borderless_tables — verifier `text_excess` (32)

- Likely root cause: The verifier's generated-text allowlist does not cover some renderer-generated appendix metadata or fallback labels emitted by `src/poc/render_docx.py`.
- Scope: generic generated-text accounting or renderer change

### m7_c_borderless_tables — verifier `text_missing` (124)

- Likely root cause: `src/poc/render_docx.py` places extracted text under recognized target headings; unresolved or misclassified headings leave source words out.
- Scope: generic renderer/classification change

### m7_d_two_column — verifier `heading_missing_or_wrong_level` (7)

- Likely root cause: `src/poc/extract.py` heading recognition uses numbered-heading and font-size heuristics in `config/extraction.yaml`; raster pages have no text layer.
- Scope: generic heading detection/configuration change; OCR is out of scope

### m7_d_two_column — verifier `image_placement_mismatch` (1)

- Likely root cause: `src/poc/render_docx.py` emits figures in target-section placement order, which can diverge from source order.
- Scope: generic figure ordering/placement change

### m7_d_two_column — verifier `image_relationship_mismatch` (1)

- Likely root cause: `src/poc/render_docx.py` creates inline image relationships from placed figure elements; the resulting package lacks the full source display-image set.
- Scope: generic image placement change

### m7_d_two_column — verifier `image_set_or_count_mismatch` (1)

- Likely root cause: `src/poc/extract.py` extracts image streams while `src/poc/render_docx.py` embeds placed figures; source images may be omitted or normalized.
- Scope: generic image extraction/rendering or provenance change

### m7_d_two_column — verifier `mapping_mismatch` (4)

- Likely root cause: `src/poc/enrich.py` applies keyword rules in `config/classification.yaml`; M7 intentionally made no LLM fallback calls.
- Scope: classification configuration or generic rule coverage change

### m7_d_two_column — verifier `pending_disposition` (1)

- Likely root cause: `src/poc/render_docx.py` places content under recognized target sections; unresolved headings leave dependent source elements pending.
- Scope: generic renderer or classification coverage change

### m7_d_two_column — verifier `placement_ledger_mismatch` (1)

- Likely root cause: `src/poc/render_docx.py` does not create exactly one placement entry per extracted source element in this baseline.
- Scope: generic ledger/rendering change

### m7_d_two_column — verifier `table_count_mismatch` (1)

- Likely root cause: `src/poc/extract.py` uses pdfplumber line-based table detection configured in `config/extraction.yaml`; borderless and split-page grids exceed that strategy.
- Scope: generic table detection or configuration change

### m7_d_two_column — verifier `table_shape_mismatch` (2)

- Likely root cause: `src/poc/extract.py` table extraction relies on line geometry and configured snap/join tolerances in `config/extraction.yaml`.
- Scope: generic table detection or configuration change

### m7_d_two_column — verifier `text_excess` (56)

- Likely root cause: The verifier's generated-text allowlist does not cover some renderer-generated appendix metadata or fallback labels emitted by `src/poc/render_docx.py`.
- Scope: generic generated-text accounting or renderer change

### m7_d_two_column — verifier `text_missing` (119)

- Likely root cause: `src/poc/render_docx.py` places extracted text under recognized target headings; unresolved or misclassified headings leave source words out.
- Scope: generic renderer/classification change

### m7_e_scanned — verifier `image_placement_mismatch` (1)

- Likely root cause: `src/poc/render_docx.py` emits figures in target-section placement order, which can diverge from source order.
- Scope: generic figure ordering/placement change

### m7_e_scanned — verifier `image_relationship_mismatch` (1)

- Likely root cause: `src/poc/render_docx.py` creates inline image relationships from placed figure elements; the resulting package lacks the full source display-image set.
- Scope: generic image placement change

### m7_e_scanned — verifier `image_set_or_count_mismatch` (1)

- Likely root cause: `src/poc/extract.py` extracts image streams while `src/poc/render_docx.py` embeds placed figures; source images may be omitted or normalized.
- Scope: generic image extraction/rendering or provenance change

### m7_e_scanned — verifier `mapping_mismatch` (4)

- Likely root cause: `src/poc/enrich.py` applies keyword rules in `config/classification.yaml`; M7 intentionally made no LLM fallback calls.
- Scope: classification configuration or generic rule coverage change

### m7_e_scanned — verifier `pending_disposition` (1)

- Likely root cause: `src/poc/render_docx.py` places content under recognized target sections; unresolved headings leave dependent source elements pending.
- Scope: generic renderer or classification coverage change

### m7_e_scanned — verifier `placement_ledger_mismatch` (1)

- Likely root cause: `src/poc/render_docx.py` does not create exactly one placement entry per extracted source element in this baseline.
- Scope: generic ledger/rendering change

### m7_e_scanned — verifier `text_excess` (1)

- Likely root cause: The verifier's generated-text allowlist does not cover some renderer-generated appendix metadata or fallback labels emitted by `src/poc/render_docx.py`.
- Scope: generic generated-text accounting or renderer change


## Image text

Printed words inside images are recorded in each truth file. OCR and LLM transcription were not run, so recognition of those words is NOT MEASURED.

## Header, footer, and page-number leakage

- m7_a_same_style: header/footer leaked into body=False; page-number leaked into body=False.
- m7_b_new_style: header/footer leaked into body=True; page-number leaked into body=False.
- m7_c_borderless_tables: header/footer leaked into body=False; page-number leaked into body=False.
- m7_d_two_column: header/footer leaked into body=False; page-number leaked into body=False.
- m7_e_scanned: header/footer leaked into body=False; page-number leaked into body=False.

## Limits of this evidence

These are synthetic documents made by the same team and model that built the pipeline. They are cleaner and less messy than real documents, so they are a floor on risk, not a guarantee. The set samples only 5 constructed layouts and does not represent the range of publishers, scans, encodings, or document quality found in production.
