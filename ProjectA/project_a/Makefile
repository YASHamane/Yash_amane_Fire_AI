# Project A Makefile: One command reproduces every reported number -> `make all`
PY ?= python

.PHONY: all setup test bench parse-eval change report clean ui

all: setup test bench parse-eval change report

setup:
	$(PY) -m pip install -r requirements.txt

# Test suite: regenerate cases (deterministic), then run pytest.
test:
	$(PY) tests/cases/generate_cases.py
	$(PY) -m pytest tests -q

# Accuracy, determinism, latency, cost, and traceability benchmarks.
bench:
	$(PY) bench/run_accuracy.py
	$(PY) bench/run_determinism.py
	$(PY) bench/run_latency.py
	$(PY) bench/run_cost.py
	$(PY) bench/run_traceability.py

# Task 3: plain-language extraction and clarification evaluation.
parse-eval:
	$(PY) bench/run_parser_eval.py

# Task 5: FY 2025-26 change experiment.
change:
	$(PY) bench/run_change_experiment.py

# Build RESULTS_A.md from results/*.json (no hand-typed numbers).
report:
	$(PY) bench/make_report.py

# Interactive Web UI Dashboard
ui:
	$(PY) -m ui.server

clean:
	python -c "import shutil, glob, os; [os.remove(f) for f in glob.glob('results/*.json')]; [shutil.rmtree(p, ignore_errors=True) for p in ['.pytest_cache', '__pycache__']]"
