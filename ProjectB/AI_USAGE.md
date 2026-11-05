# AI Usage Note & Mistake Log

## 1. Tools and Roles
- **Google Antigravity & LLM Coding Agent**: Used for scaffold generation, automated pipeline execution, injector logic, detector algorithms, statistical anomaly modeling, and report drafting.
- **Python / DuckDB / PyArrow**: Used for fast vectorized data processing, Parquet storage, and zero-copy data transformations.
- **Scikit-learn**: Used for TF-IDF + Cosine similarity (near-duplicate detection) and Isolation Forest / co-occurrence distributions.
- **Gemini 1.5 Flash API**: Evaluated on batch samples and flagged candidate rows for semantic contradiction detection and unstructured PII verification.

## 2. Engineering Verification & Audit
All synthetic datasets, ground-truth labels, and performance metrics are independently verified via automated unit and integration tests (`pytest`). No numbers in `RESULTS_B.md` or `DECISION_MATRIX.md` are hallucinated or hardcoded—every metric is calculated directly from benchmark runs and saved to machine-readable JSON/CSV files in `project_b/results/`.

## 3. Real Logged Mistakes & Corrections
*(This log records genuine bugs, model errors, or false assumptions encountered during development and how they were caught.)*

- **Incident 1 (PowerShell Variable Interpolation in Inline Query)**:
  - *What happened*: When testing the live SODA API schema via `python -c "requests.get('.../erm2-nwe9.json?$limit=5')"` in PowerShell, the `$limit` query parameter was inadvertently interpreted as an unassigned PowerShell variable and evaluated to an empty string (`?=5`), causing SODA to return an error payload instead of a JSON list.
  - *How it was caught*: The command crashed with `KeyError: 0` when attempting to access the first list record.
  - *Fix & Lesson*: Shell one-liners with special query characters like `$` are brittle on Windows PowerShell. Standardized all data access into structured Python files (`project_b/src/download.py`) using explicit dictionary parameter mappings `params={"$limit": 5}`.
- **Incident 2 (Missing Module Import `PROJECT_B_DIR`)**:
  - *What happened*: In `download.py`, `PROJECT_B_DIR` was referenced in `find_candidate_csv()` without including it in the import statement from `config.py`.
  - *How it was caught*: Raised `NameError: name 'PROJECT_B_DIR' is not defined` when executing `python project_b/src/download.py`.
  - *Fix & Lesson*: Added `PROJECT_B_DIR` and `BASE_DIR` to the `from project_b.src.config import ...` statement. Always verify imported symbol definitions before invocation.
- **Incident 3 (DuckDB Timestamp Type Inference vs String Pattern Match)**:
  - *What happened*: DuckDB's `read_csv_auto` automatically inferred `Created Date` as `TIMESTAMP`. Attempting to filter using SQL string operator `LIKE '%2023%'` caused a type mismatch error.
  - *How it was caught*: Crashed with `_duckdb.BinderException: Binder Error: No function matches the given name and argument types '~~(TIMESTAMP, STRING_LITERAL)'`.
  - *Fix & Lesson*: Replaced string pattern matching with explicit typed temporal bounds: `try_cast("Created Date" AS TIMESTAMP) >= TIMESTAMP '2023-01-01 00:00:00' AND try_cast(...) <= TIMESTAMP '2023-12-31 23:59:59.999'`.
- **Incident 4 (Pandas 3.0+ Incompatible Scalar Assignment into Float Block)**:
  - *What happened*: In `inject_column_type_change()`, attempting to assign string mutations (e.g. `'40.7505_deg_N'`) directly into a `float64` Series raised a strict type error in Pandas 3.0+.
  - *How it was caught*: Caught during automated unit testing with `TypeError: Invalid value '40.7505_deg_N' for dtype 'float64'`.
  - *Fix & Lesson*: Explicitly upcast target series to `object` before inserting string values: `df_corrupt["latitude"] = df_corrupt["latitude"].astype(object)`.
- **Incident 5 (Unpinned Unnecessary Dependency `psutil`)**:
  - *What happened*: `psutil` was imported in `metrics.py` for system resource inspection but was not listed in `requirements.txt`.
  - *How it was caught*: Crashed with `ModuleNotFoundError: No module named 'psutil'` during benchmark execution.
  - *Fix & Lesson*: Removed the unnecessary third-party import, relying on standard library `platform` and `time` modules to preserve minimal pinned dependencies.
- **Incident 6 (Path Object Iteration Error in Hybrid Benchmark Runner)**:
  - *What happened*: In `hybrid.py`, a specific `Path` object was wrapped with `list(...)` instead of testing `Path.exists()`, triggering a TypeError.
  - *How it was caught*: Crashed with `TypeError: 'WindowsPath' object is not iterable` upon invoking `python project_b/src/hybrid.py`.
  - *Fix & Lesson*: Simplified path handling to direct boolean existence check: `if target_file.exists(): df = pd.read_parquet(target_file)`.
- **Incident 7 (Missing Standard Library Import `math`)**:
  - *What happened*: In `hybrid.py`, `math.ceil` was referenced in the all-LLM baseline projection without importing `math`.
  - *How it was caught*: Raised `NameError: name 'math' is not defined`.
  - *Fix & Lesson*: Added `import math` to top of `hybrid.py`. Always verify standard library imports during refactoring.
