# Stage Report — C1: LLM-Driven Conversion

## 1. What was built

- Added `src/poc/convert/plan_schema.py`, a strict Pydantic plan that can contain only target section ids, source heading ids, source element ids, and allowed block types. Additional prose/content fields are rejected.
- Added `src/poc/convert/planner.py` for the pinned `c1-plan-v1` LangChain prompt, path-free element previews, structured `Plan` output, an adapter to the existing provider/cache service, and a deterministic offline mock planner.
- Added `src/poc/convert/graph.py` with LangGraph plan → validate → up to two validation retries → rule-based fallback. Per-chunk attempts and fallback decisions are recorded.
- Added `src/poc/convert/assemble.py` for section chunking, exact ID/type/order validation, and resolving plans back to the untouched IR records by ID.
- Added `src/poc/convert/runner.py` and the `convert` CLI command. Conversion writes `<name>_converted.docx`, `<name>_plan.json`, `<name>_report.md`, and `<name>_llm_calls.json` under the requested output directory. Matching saved image captions are reused only when both source PDF hash and display-image hash match.
- Added `compare --all`; it writes `docs/MODE_COMPARISON.md` and `data/output/mode_comparison.json` from the same verifier for Mode A and rule-only Mode B.
- Added `docs/instructions.md` with placement rules and exact-source-content constraints.
- Added offline fake/mock coverage in `tests/test_c1_convert.py`.
- Updated `requirements.txt` with the requested exact LangChain/LangGraph pins. No packages were installed.
- Added backward-compatible optional plan/source-element inputs to `render_docx.render_document` and an optional answer-key override to the verifier. The original no-plan behavior was checked against pre-C1 hashes.

## 2. How to run it

Offline mock conversion:

```sh
.venv/bin/python -m poc.cli convert "data/input/WaterFall_PM_Documentation 1.pdf" --out data/output/c1 --provider mock
```

Real Gemini conversion in the human's terminal (the model and key are read by the application from the environment or `.env`; no key is included here):

```sh
unset LLM_PROVIDER GEMINI_API_KEY GEMINI_MODEL GROQ_API_KEY GROQ_MODEL GROQ_VISION_MODEL LLM_RPM LLM_MAX_RETRIES
export LLM_PROVIDER=gemini LLM_RPM=2
.venv/bin/python -m poc.cli convert "data/input/WaterFall_PM_Documentation 1.pdf" --out data/output/c1 --provider gemini
.venv/bin/python -m poc.cli convert "data/input/Kanban_PM_Final 2.pdf" --out data/output/c1 --provider gemini
.venv/bin/python -m poc.cli compare --all
```

The current extraction inventory has 10 level-1 headings per PDF plus one preamble chunk, so expect **11 uncached planner requests per document (22 total)** on the first two conversions. At `LLM_RPM=2`, each command rate-limits its own requests. `compare --all` should make **0 additional provider requests** because it reuses the shared plan cache.

Send back these files:

- `data/output/c1/waterfall_pm_documentation_1_converted.docx`
- `data/output/c1/waterfall_pm_documentation_1_plan.json`
- `data/output/c1/waterfall_pm_documentation_1_report.md`
- `data/output/c1/waterfall_pm_documentation_1_llm_calls.json`
- The corresponding four `kanban_pm_final_2_*` files
- `docs/MODE_COMPARISON.md` and `data/output/mode_comparison.json`

## 3. Test results

Full offline suite:

```text
56 passed, 5 warnings in 26.07s
```

The five warnings are existing PyMuPDF binding deprecations. The eight added C1 test cases cover plan schema restrictions, missing/duplicated/invented ids, validation retries and fallback, exact source-text rendering, matching cached captions, CLI conversion, and a second-run cache hit. No network or real LLM calls were made by the tests.

Mock CLI smoke run on the Waterfall PDF:

```text
INFO: Extracted c1_waterfall_pm_documentation_1_329b8ad5: 74 elements, 5 figures
Converted WaterFall_PM_Documentation 1.pdf: .../waterfall_pm_documentation_1_converted.docx; calls=11, retries=0, fallbacks=0, defects=1
```

After the verifier allowance for the generated unclassified-section label was added, a repeated mock run reported `calls=0, retries=0, fallbacks=0, defects=0` from cache. That run reused all 5 saved image captions. The mock output is a plumbing check, not evidence of Gemini plan quality.

Existing Mode B command:

```text
Run complete: waterfall, kanban; 121 placed, 25 regenerated, 0 unplaced, 0 defects
```

Pre-C1 and post-C1 SHA-256 values matched for both existing DOCX files, `data/output/metrics.json`, and both original `elements.json` files. This confirms the original Mode B outputs remain byte-identical.

## 4. Metrics and inventory

- Existing configured PDFs: 10 top-level heading chunks plus one preamble chunk per document; 11 planning requests each on an uncached first run.
- Local mock smoke: 74 extracted elements, 5 figures; 11 mock requests on first run and 0 on repeat; 0 fallbacks after validation; final mock verifier defects 0.
- Full suite: 56 passed; 5 dependency deprecation warnings.
- Mode A versus Mode B comparison files were not generated in this agent run because doing so with Gemini would require the prohibited real calls. The `compare --all` command generates both requested files after the human's terminal conversions.

## 5. Decisions and assumptions

- A planning chunk is the preamble before the first level-1 heading or one level-1 heading and its following elements up to the next level-1 heading. The planner assigns one destination per chunk; subordinate headings and their content therefore stay with their parent chunk.
- Page numbers are included as paragraph references in the plan and remain regenerated by the renderer. The contents table and title are also referenced in the plan and retain the renderer's existing regenerated disposition.
- `unclassified` is rendered in a dedicated generated section so source elements still receive a destination and disposition.
- “LLM misplaced” is reported as ids whose destinations differ from the existing keyword-rule baseline. This is explicitly diagnostic; a rule difference alone is not proof that the LLM chose the wrong semantic section.
- The C1 prompt version is embedded in the prompt and logs. The existing disk cache keys provider, model, prompt, and its prompt-version constant; therefore the distinct C1 prompt text keeps C1 results separate from M3 results.
- The mock planner puts chunks in `unclassified`; it is used only to validate offline plumbing and cache behavior.

## 6. Deviations from the spec

- The requested versions are declared in `requirements.txt`, but the installed environment reports `langchain-core 0.3.76`, `langchain-google-genai 2.0.10`, and `langgraph 0.6.6`. Required imports and the implemented graph/prompt flow succeeded with the installed versions. No installation or upgrade was attempted. Compatibility with the requested pins remains unverified here.
- Real Gemini conversion and the Mode A/Mode B comparison were not run. The request reserves real calls for the human's terminal; the exact commands and expected first-run request count are above.
- Token usage is logged as `null` when the existing provider response does not expose token counts.

## 7. Challenges logged

- C1 LangChain dependency versions differ from requested pins.
- C1 verifier initially flagged the generated unclassified-section label.
- C1 ID-based assembly equality check corrected during offline tests.

## 8. Open issues and risks

- Model-specific placement accuracy remains unmeasured until the human runs Gemini and returns the cached outputs.
- One uncached Gemini run is expected to take several minutes at two requests per minute; retry/backoff may add time.
- The current rule fallback uses existing keyword rules and may send unfamiliar headings to `unclassified`.
- Human review should compare each converted DOCX with its source PDF, especially heading placement, tables, figures, and the verifier's listed placement differences.
- Mode A comparison artifacts are generated by `python -m poc.cli compare --all` after the real conversions; they do not exist yet.

## 9. C1 Gemini HTTP 400 fix pass

- Offline diagnosis is recorded in [c1_gemini_schema_diagnostic.json](c1_gemini_schema_diagnostic.json). The previous Pydantic schema included `$defs`/`$ref`, `anyOf`, `enum`, `additionalProperties`, nested model definitions, and generated titles. The precise rejected keyword is unknown because the earlier failure report did not retain Gemini's response body.
- Gemini now receives a flat inline schema with plain strings for `target_section` and `block_type`. The response is still validated by the strict local Pydantic `Plan`; invalid target and block values remain rejected. The installed Gemini SDK accepted the schema configuration locally; no request was sent.
- Prompt size for the same Waterfall preamble chunk fell from 4,423 characters (about 1,106 tokens) to 2,971 characters (about 743 tokens), using the rough characters-divided-by-four estimate.
- HTTP provider errors now retain the API message and status after sanitizing credentials and URL query strings. The sanitized text is included in the C1 call log.
- Added `plan-check`, which makes one planner request, validates the plan against one source chunk, and does not render a document. No real Gemini call was made in this fix pass.
- Full offline suite after the fix: 61 passed, 5 existing dependency warnings. Mode B DOCX, metrics, and source IR hashes matched their pre-fix values.

To try one chunk first in the human's terminal:

```sh
.venv/bin/python -m poc.cli plan-check "data/input/WaterFall_PM_Documentation 1.pdf" --out data/output/c1_probe --provider gemini
```

After that succeeds, run the full conversions and comparison:

```sh
.venv/bin/python -m poc.cli convert "data/input/WaterFall_PM_Documentation 1.pdf" --out data/output/c1 --provider gemini
.venv/bin/python -m poc.cli convert "data/input/Kanban_PM_Final 2.pdf" --out data/output/c1 --provider gemini
.venv/bin/python -m poc.cli compare --all
```

The real Gemini acceptance and placement quality remain unverified until those commands are run with the human's configured credentials.
