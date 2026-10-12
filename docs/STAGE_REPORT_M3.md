# Stage Report — M3: AI Enrichment

## 1. What was built

- Added the provider interface and Gemini, Groq, and mock providers, runtime settings, retry/rate-limit handling, validated response models, and disk caching.
- Added rule-first section classification and image enrichment for the extracted display images. LLM classification is reserved for unresolved heading titles; level-2 headings inherit their parent type.
- Added the image review at [ai_outputs_review.md](ai_outputs_review.md), with the saved AI-generated figure descriptions/transcriptions, indicative token recall, and complete heading classification table.
- Updated `docs/challenges_log.md` with the real-run close-out. No environment or key values were printed or recorded.

## 2. How to run it

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m poc.cli llm-check
.venv/bin/python -m poc.cli enrich --all --provider gemini
```

The `llm-check` command is the authorized one-prompt connectivity check. Enrichment reads the provider and model settings from the runtime environment and uses the on-disk cache on repeat runs.

## 3. Test results

Offline M3 test suite, using the mock provider:

```text
24 passed, 5 warnings in 14.17s
```

The five warnings were dependency deprecation warnings; there were no test failures.

## 4. Metrics and inventory

- Real enrichment: all 8 logical figures completed (5 Waterfall and 3 Kanban), as reported by the human after running it in their terminal.
- Repeat enrichment verification:

```text
INFO: Enriched waterfall: 21 headings (21 rule, 0 LLM), 5/5 figures complete; 0 provider calls, 5 cache hits
INFO: Enriched kanban: 18 headings (18 rule, 0 LLM), 3/3 figures complete; 0 provider calls, 3 cache hits
```

- The second run made **0 provider calls** and used **8 cache hits**. All 8 figures remained complete.
- Classification: 20 level-1 headings resolved by configured rules; 19 level-2 headings inherited their parent’s type. There were 39 heading records total and no heading required an LLM call.
- Strict indicative image-token recall was 35/36 (97.2%); normalized recall was 36/36 (100.0%). Normalization lowercases both sides and removes hyphens and whitespace before substring matching. The cover photo has no expected tokens and is excluded. The metric measures only presence of selected keywords, not complete transcription accuracy. Per-image results and all text are in `docs/ai_outputs_review.md`.

## 5. Decisions and assumptions

- Rules classify every current level-1 heading, so no real classification requests were needed. Mock tests exercise the unknown-heading LLM path.
- Figure-to-key token groups are paired in stable extraction order within each document, as documented in the review. Recall uses case-insensitive substring matching and does not edit model transcriptions.
- AI captions and transcriptions remain labelled AI-generated in the review; they are descriptive enrichment and do not replace extracted source text.
- The successful first enrichment was run by the human in their terminal. This agent verified the repeat run against the resulting cache; the successful user-reported first run was not repeated here.

## 6. Deviations from the spec

- The first sandbox-side real enrichment attempt failed with the generic provider-safe error and produced no cache. Per the instruction not to keep retrying, the human completed the real enrichment in their terminal. The subsequent cache-only run was performed and verified here.
- GroqProvider was implemented but not run, as requested.

## 7. Challenges logged

- Gemini enrichment could not reach the provider from the sandbox; the human terminal run completed all figures, and the repeat run confirmed cache-only behavior.
- Other existing M0–M2 challenge entries remain in `docs/challenges_log.md`.

## 8. Open issues and risks

- Image transcription and token-recall figures are indicative and measure only selected keyword presence. Strict matching misses `BOTTLENECK` against the preserved `BOTTLE-NECK` transcription; normalized matching counts it.
- The initial sandbox provider failure exposed only a generic error, so its underlying cause could not be diagnosed from that attempt. The human-reported successful run and the verified cache-only repeat complete the requested M3 workflow.
- M4 has not been started.
