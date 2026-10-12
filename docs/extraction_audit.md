# M2 Extraction Audit

Compared the immutable draft key in `docs/answer_key.json` with the current extraction outputs in `data/work/<doc>/elements.json`. Counts and shapes are directly comparable. The draft contains heading counts but no expected heading-title lists, so extracted titles are listed for review and title presence is asserted; a title-by-title key comparison cannot be made. `section_types` and `image_tokens` are explicitly deferred to M3/M5 and were not tested.

## Waterfall

| Key item | Key value | Extracted value | Result |
|---|---|---|---|
| pages | 14 | 14 | PASS |
| page_numbers | 14 | 14 | PASS |
| h1 | 10 | 10 | PASS |
| h2 | 11 | 11 | PASS |
| heading titles | No titles listed in key | L1: Abstract; Scope; Introduction; Learning Objectives; Waterfall Lifecycle; Detailed Phase-by-Phase Explanation; When to Use Waterfall; Best Practices; Advantages of Waterfall; Limitations & Challenges. L2: 3.1 Background; 3.2 Purpose; 3.3 Scope; 3.4 Intended Audience; 6.1 Requirements; 6.2 Design; 6.3 Development; 6.4 Testing; 6.5 Deployment; 6.6 Maintenance; 7.1 Decision Framework. All 21 titles are non-empty. | Difference: title expectations are absent from draft key; no title-value comparison possible. |
| bullets | 6 | 6 | PASS |
| tables | 6 | 6 | PASS |
| table_shapes | contents 11×2; lifecycle 7×3; decision 6×3; best_practices 9×2; advantages 6×2; limitations 6×2 | Same ordered shapes: 11×2; 7×3; 6×3; 9×2; 6×2; 6×2 | PASS |
| figures | 5 | 5 | PASS |
| cover_lines | Four strings as listed in key | `MindX360 LMS PLATFORM`; `PROJECT MANAGEMENT METHODOLOGY`; `WATERFALL`; `Professional Methodology & Learning Document` | PASS |
| spot_strings[0] | `Waterfall is a structured, sequential approach to project delivery` | Exact normalized substring found in extracted element text. | PASS |
| spot_strings[1] | `False sense of certainty` | Exact normalized substring found in extracted element text. | PASS |
| spot_strings[2] | `Treat documentation as an operational asset` | Exact normalized substring found in extracted element text. | PASS |
| spot_strings[3] | `Maintenance` | Found in extracted element text. | PASS |
| spot_strings[4] | `These advantages are most meaningful when the project's underlying assumptions remain stable` | Exact normalized substring found in the page 13 paragraph. | PASS |
| section_types | Full 10-section mapping in draft key | Not produced in M2; deferred to M3. | DEFERRED by instruction |
| image_tokens | Five image-token lists in draft key | Not produced in M2; deferred to M3/M5. | DEFERRED by instruction |

## Kanban

| Key item | Key value | Extracted value | Result |
|---|---|---|---|
| pages | 7 | 7 | PASS |
| page_numbers | 7 | 7 | PASS |
| h1 | 10 | 10 | PASS |
| h2 | 8 | 8 | PASS |
| heading titles | No titles listed in key | L1: Abstract; Scope; Introduction; Learning Objectives; Kanban Methodology; Detailed Kanban Process Explanation; When to Use Kanban; Best Practices; Advantages of Kanban; Limitations & Challenges. L2: 3.1 Background; 3.2 Purpose; 3.3 Intended Audience; 6.1 Visualizing Work; 6.2 Defining the Workflow; 6.3 Managing Work in Progress; 6.4 Managing Flow; 6.5 Continuous Improvement. All 18 titles are non-empty. | Difference: title expectations are absent from draft key; no title-value comparison possible. |
| bullets | 8 | 8 | PASS |
| tables | 4 | 4 | PASS |
| table_shapes | contents 11×2; board_structure 5×2; suitability 8×2; key_challenges 6×2 | Same ordered shapes: 11×2; 5×2; 8×2; 6×2 | PASS |
| figures | 3 | 3 | PASS |
| cover_lines | Four strings as listed in key | `MindX360 LMS PLATFORM`; `PROJECT MANAGEMENT METHODOLOGY`; `KANBAN`; `Professional Methodology & Learning Document` | PASS |
| spot_strings | `Waiting for Customer`; `Review or approval constraints`; `Work-in-Progress (WIP) limits` | All three exact normalized substrings found in extracted element text. | PASS |
| section_types | Full 10-section mapping in draft key | Not produced in M2; deferred to M3. | DEFERRED by instruction |
| image_tokens | Three image-token lists in draft key | Not produced in M2; deferred to M3/M5. | DEFERRED by instruction |

## Golden table cells

All extracted cells in all six Waterfall and four Kanban tables match their corresponding `tests/fixtures/golden_tables_<doc>.json` fixture exactly. The fixtures contain the requested architect verification comment. Table dimensions include the header row.

## Conservation negative test

The deliberate-corruption test removes one paragraph from an in-memory Waterfall document, then audits the modified elements against the source PDF. The audit reports exactly the removed paragraph's word multiset as missing and reports no extra words. The production extraction continues to pass the ordinary per-page conservation check.
