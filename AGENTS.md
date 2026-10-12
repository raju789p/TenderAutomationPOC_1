# AGENTS.md — TenderAutomationPOC_1

## Mission
Proof of concept: convert two source PDFs (in `data/input/`) into our own target layout
(`config/target_format.yaml`) with NO data loss, and MEASURE how accurate the conversion is.
Output: converted Word documents, an accuracy report, and a challenges log.
Context: this is the seed of a larger system that must convert documents into
organisation-specific templates. Treat it as engineering work whose results will be reviewed
by an architect and presented to a team. Honest measurement matters more than a good-looking number.

## Working agreement
- You are the implementer. The architect (a separate reviewer) sees ONLY what the human relays
  to them: your stage reports, test output and generated files. Never assume they saw your chat.
- Work on ONE stage at a time, as named in `BUILD_PLAN.md`. When the stage's acceptance checks
  pass: write the stage report, then STOP. Do not start the next stage.
- If the spec is ambiguous, choose the simplest option that respects the Hard Rules, and
  record it under "Decisions & assumptions" in the stage report. Do not stall.
- Never edit `data/input/*`, `docs/answer_key.json` or any test to make a check pass.
  If a check fails because the key or test seems wrong, report it. Do not "fix" it silently.

## Hard rules (never break)
1. VERBATIM: text and table-cell content come from extraction and are copied as-is.
   An LLM must never generate, paraphrase, summarise, correct or "clean" source content.
   Only whitespace normalisation is allowed (collapse runs of spaces; join wrapped lines).
2. NO SILENT DROPS: every extracted element has a stable ID and ends with a disposition:
   `placed`, `regenerated` (e.g. contents table, printed page numbers) or `unplaced`.
   `unplaced` must be 0; anything that cannot be placed goes to the "Unplaced content" appendix.
3. Images are embedded as the exact extracted bytes. If the PDF stores one picture as several fragments, embed a lossless composite built only from the exact fragment bytes; store every fragment's hash and verify the composite can be rebuilt from them. Log this in `challenges_log.md`. Fall back to a page render only for vector graphics, marked `origin=rendered`.
4. LLM use is limited to (a) classifying headings the rules cannot classify, and
   (b) describing/transcribing images. Temperature 0. Output is JSON validated by pydantic.
   AI-produced text is always labelled "AI-generated" wherever it appears in outputs.
5. LLM access sits behind one provider interface with `gemini`, `groq`, `mock`.
   Provider and model names come from environment variables only. Never hard-code a model name.
   API keys come from `.env` / environment, are never logged, never committed.
6. Tests run offline using the `mock` provider. No network calls in tests.
7. Deterministic: same inputs give the same outputs (LLM calls are cached on disk by hash).
   Stable ordering everywhere.
8. Every problem hit (parsing quirk, library limit, mismatch, API error) is appended to
   `docs/challenges_log.md`: what happened, where, how often, what was done, residual risk.

## Environment and commands (cross-platform; use pathlib, never hard-coded separators)
```
python -m venv .venv
# activate: Windows  .venv\Scripts\activate    macOS/Linux  source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
python -m poc.cli --help
```
Allowed dependencies: pymupdf, pdfplumber, python-docx, pydantic (v2), pyyaml, pillow, pytest,
python-dotenv, google-genai, groq. Any other dependency needs a justification in the stage report.
After M0, freeze exact versions into `requirements.lock`.

## Code standards
Python 3.11+, type hints, pydantic v2 models, small single-purpose modules, `logging` (no print
in library code), docstrings on public functions, no global mutable state, config in YAML
(no magic numbers in code: thresholds live in `config/`).

## Stage report (write to `docs/STAGE_REPORT_<stage>.md`, then stop)
1. What was built (files/modules).
2. How to run it (exact commands).
3. Test results (paste real output).
4. Metrics or inventory produced in this stage (paste real numbers).
5. Decisions & assumptions.
6. Deviations from the spec (and why).
7. Challenges logged (titles only).
8. Open issues and risks. 
