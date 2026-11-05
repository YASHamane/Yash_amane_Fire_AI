PY ?= python

.PHONY: all setup test bench parse-eval change report clean ui ui-a ui-b

all:
	cd ProjectA && $(MAKE) all

setup:
	cd ProjectA && $(MAKE) setup

test:
	cd ProjectA && $(MAKE) test

bench:
	cd ProjectA && $(MAKE) bench

parse-eval:
	cd ProjectA && $(MAKE) parse-eval

change:
	cd ProjectA && $(MAKE) change

report:
	cd ProjectA && $(MAKE) report

ui:
	$(PY) run_ui.py

ui-a:
	$(PY) run_ui.py --project a

ui-b:
	$(PY) run_ui.py --project b

clean:
	cd ProjectA && $(MAKE) clean
