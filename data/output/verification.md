# Verification Report — M5

All checks ran offline against local IR, cached enrichment, and generated DOCX files.

## Summary

| Document | Text recall | Missing words | Excess words | Tables matching | Images media/source | Mapping accuracy | Strict image keywords | Normalised image keywords | Placed / regenerated / unplaced | Defects |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| waterfall | 100.0000% | 0 | 0 | 5/5 | 5/5 | 10/10 (100.0000%) | 22/22 (100.0000%) | 22/22 (100.0000%) | 58 / 16 / 0 | 0 |
| kanban | 100.0000% | 0 | 0 | 3/3 | 3/3 | 10/10 (100.0000%) | 13/14 (92.8571%) | 14/14 (100.0000%) | 63 / 9 / 0 | 0 |

### Overall

- Text word recall: 100.0000%; missing 0 source words; excess 0 possible-fabrication words.
- Tables matching: 8/8.
- Display images: 8/8; composites rebuilt and matching: 2/2.
- Mapping accuracy: 20/20 (100.0000%).
- Image transcription, indicative; measures keyword presence only: strict 35/36 (97.2222%); normalised 36/36 (100.0000%).
- Dispositions: 121 placed, 25 regenerated, 0 unplaced, 0 pending.
- Private-use characters: 0; defects: 0.

Image transcription token scores are indicative; they measure presence of selected keywords only.

## Waterfall details

### Ledger

Disposition counts: {'placed': 58, 'regenerated': 16, 'unplaced': 0, 'pending': 0}. Expected regenerated set matches: True.

### Text misses and possible excess

No missing or excess words.

### Table comparison

- `waterfall-p007-002`: expected [7, 3], output [7, 3]; shape PASS, cells PASS.
- `waterfall-p011-004`: expected [6, 3], output [6, 3]; shape PASS, cells PASS.
- `waterfall-p012-002`: expected [9, 2], output [9, 2]; shape PASS, cells PASS.
- `waterfall-p013-002`: expected [6, 2], output [6, 2]; shape PASS, cells PASS.
- `waterfall-p014-002`: expected [6, 2], output [6, 2]; shape PASS, cells PASS.

### Heading and contents checks

All 21 source headings match at their expected Word heading levels; all 10 TOC topics are headings.

### Image checks

- `waterfall-p001-005` rebuilt composite: PASS; rebuilt SHA-256 `3805ba5b973d9ab7edc82fdf87053bd1f6d57222c05ba377d53d309baf432420`.

### Section mapping and indicative image keywords

- `waterfall-p003-001` section 1: expected `abstract`, extracted `abstract` — PASS.
- `waterfall-p004-001` section 2: expected `scope`, extracted `scope` — PASS.
- `waterfall-p005-001` section 3: expected `introduction`, extracted `introduction` — PASS.
- `waterfall-p006-001` section 4: expected `learning_objectives`, extracted `learning_objectives` — PASS.
- `waterfall-p007-001` section 5: expected `core_concept`, extracted `core_concept` — PASS.
- `waterfall-p008-001` section 6: expected `process_detail`, extracted `process_detail` — PASS.
- `waterfall-p011-001` section 7: expected `when_to_use`, extracted `when_to_use` — PASS.
- `waterfall-p012-001` section 8: expected `best_practices`, extracted `best_practices` — PASS.
- `waterfall-p013-001` section 9: expected `advantages`, extracted `advantages` — PASS.
- `waterfall-p014-001` section 10: expected `limitations`, extracted `limitations` — PASS.
- `waterfall-p001-005`: NOT MEASURED — The answer key selects no image keywords for this figure.
- `waterfall-p008-002` / `sdlc_cycle`: strict 7/7; normalised 7/7 — indicative; measures keyword presence only. Missing strict: none; missing normalised: none.
- `waterfall-p008-007` / `ux_cycle`: strict 4/4; normalised 4/4 — indicative; measures keyword presence only. Missing strict: none; missing normalised: none.
- `waterfall-p009-005` / `testing_cycle`: strict 4/4; normalised 4/4 — indicative; measures keyword presence only. Missing strict: none; missing normalised: none.
- `waterfall-p010-001` / `phase_role_chart`: strict 7/7; normalised 7/7 — indicative; measures keyword presence only. Missing strict: none; missing normalised: none.

### Other defects

None.

## Kanban details

### Ledger

Disposition counts: {'placed': 63, 'regenerated': 9, 'unplaced': 0, 'pending': 0}. Expected regenerated set matches: True.

### Text misses and possible excess

No missing or excess words.

### Table comparison

- `kanban-p004-015`: expected [5, 2], output [5, 2]; shape PASS, cells PASS.
- `kanban-p006-004`: expected [8, 2], output [8, 2]; shape PASS, cells PASS.
- `kanban-p007-007`: expected [6, 2], output [6, 2]; shape PASS, cells PASS.

### Heading and contents checks

All 18 source headings match at their expected Word heading levels; all 10 TOC topics are headings.

### Image checks

- `kanban-p007-008` rebuilt composite: PASS; rebuilt SHA-256 `692d7cf00e68937adb5545fd9fc75fc5cb5c2da6c3d0cc83721ab9598e0017c8`.

### Section mapping and indicative image keywords

- `kanban-p003-001` section 1: expected `abstract`, extracted `abstract` — PASS.
- `kanban-p003-005` section 2: expected `scope`, extracted `scope` — PASS.
- `kanban-p003-007` section 3: expected `introduction`, extracted `introduction` — PASS.
- `kanban-p004-001` section 4: expected `learning_objectives`, extracted `learning_objectives` — PASS.
- `kanban-p004-011` section 5: expected `core_concept`, extracted `core_concept` — PASS.
- `kanban-p005-001` section 6: expected `process_detail`, extracted `process_detail` — PASS.
- `kanban-p006-001` section 7: expected `when_to_use`, extracted `when_to_use` — PASS.
- `kanban-p006-006` section 8: expected `best_practices`, extracted `best_practices` — PASS.
- `kanban-p006-009` section 9: expected `advantages`, extracted `advantages` — PASS.
- `kanban-p007-003` section 10: expected `limitations`, extracted `limitations` — PASS.
- `kanban-p004-016` / `board_diagram`: strict 6/6; normalised 6/6 — indicative; measures keyword presence only. Missing strict: none; missing normalised: none.
- `kanban-p005-008` / `wip_comparison`: strict 4/4; normalised 4/4 — indicative; measures keyword presence only. Missing strict: none; missing normalised: none.
- `kanban-p007-008` / `flow_diagram`: strict 3/4; normalised 4/4 — indicative; measures keyword presence only. Missing strict: BOTTLENECK; missing normalised: none.

### Other defects

None.
