# Stage Report — M0 Scaffold

## 1. What was built

- Added `src/poc/` and the Pydantic v2 data models in `src/poc/models.py`.
- Added the argparse CLI stubs in `src/poc/cli.py` for `extract`, `enrich`, `render`, `verify`, `report`, and `run`.
- Added `config/documents.yaml`, `config/target_format.yaml`, `.env.example`, `.gitignore`, `requirements.txt`, `requirements.lock`, `pytest.ini`, and `pyproject.toml` for editable installation from `src/`.
- Added M0 acceptance checks in `tests/test_m0_scaffold.py`.
- Added `data/work/.gitkeep` and `data/output/.gitkeep`; generated contents in both directories remain ignored.
- Added `docs/challenges_log.md` entries for the filename mismatch and package index access issues.

## 2. How to run it

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -q
python -m poc.cli --help
```

## 3. Test results

Command: `python -m pytest -q` (with `.venv` active)

```text
...                                                                      [100%]
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
3 passed, 5 warnings in 0.17s
```

Command: `python -m poc.cli --help` (with `.venv` active)

```text
usage: poc [-h] {extract,enrich,render,verify,report,run} ...

Tender document conversion pipeline

positional arguments:
  {extract,enrich,render,verify,report,run}
    extract             Extract documents
    enrich              Enrich documents
    render              Render documents
    verify              Verify documents
    report              Report documents
    run                 Run documents

options:
  -h, --help            show this help message and exit
```

## 4. Metrics or inventory produced

- Input PDFs opened: 2.
- Page counts: waterfall 14; kanban 7 (21 total).
- Target format: 6 sections and 3 appendices loaded and validated.
- Model JSON round-trip: 1 document model with 1 paragraph element passed.
- Test suite: 3 passed.
- Editable package installation: succeeded through `pip install -r requirements.txt` (`-e .`).
- Workspace directories `data/work/` and `data/output/`: both exist with `.gitkeep` files.

## 5. Decisions & assumptions

- The actual input files are `WaterFall_PM_Documentation 1.pdf` and `Kanban_PM_Final 2.pdf`, with spaces. The plan specifies underscore names; configuration points to the actual files, and neither input was renamed or modified.
- Declared the package in `pyproject.toml` with `src/` package discovery; CLI and test imports rely on the editable installation instead of a root symlink.
- Test coverage was added for the M0 acceptance checks; no test or input file was altered to bypass a failure.

## 6. Deviations from the spec

- `config/documents.yaml` uses the filenames present on disk rather than the underscore names listed in the plan.
- Added `pyproject.toml` and `pytest.ini` so editable installation exposes `src/poc/` to both CLI and tests.

## 7. Challenges logged

- Input PDF filenames differ from the plan.
- Dependency installation initially lacked network access.
- Editable install initially lacked network access.

## 8. Open issues and risks

- The installed runtime is Python 3.12.3, above the specified Python 3.11+ minimum.
- PyMuPDF emitted five Swig deprecation warnings during tests; all M0 checks passed.
- The other CLI stages are stubs as expected at M0.
