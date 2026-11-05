.PHONY: all setup download profile inject detect measure report test clean

PYTHON = ./.venv/Scripts/python
PIP = ./.venv/Scripts/pip

all:
	$(PYTHON) run_all.py

setup:
	python -m venv .venv
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt

download:
	$(PYTHON) project_b/src/download.py

profile:
	$(PYTHON) project_b/src/profile.py

inject:
	$(PYTHON) project_b/src/injector.py

measure:
	$(PYTHON) project_b/src/metrics.py

report:
	$(PYTHON) project_b/src/report.py

test:
	$(PYTHON) -m pytest project_b/tests -v

clean:
	rm -rf project_b/data/cache/*
	rm -rf project_b/results/*.csv project_b/results/*.json
