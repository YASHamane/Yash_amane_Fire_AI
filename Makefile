PY ?= python

.PHONY: all setup test bench parse-eval change report clean

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

clean:
	cd ProjectA && $(MAKE) clean
