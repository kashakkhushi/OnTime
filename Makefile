PYTHON ?= python
ifeq ($(OS),Windows_NT)
VENV_PY = .venv/Scripts/python.exe
else
VENV_PY = .venv/bin/python
endif

.PHONY: setup data build test figures all
setup:
	$(PYTHON) -m venv .venv
	$(VENV_PY) -m pip install -r requirements.txt
	$(VENV_PY) -m pip install --no-build-isolation --no-deps -e .
data:
	$(VENV_PY) -m ontime.ingest
build:
	$(VENV_PY) -m ontime.build
	$(VENV_PY) -m ontime.pipeline
	$(VENV_PY) -m ontime.report
test:
	$(VENV_PY) -m pytest
figures:
	$(VENV_PY) -m ontime.figures
all:
	$(MAKE) setup
	$(MAKE) data
	$(MAKE) build
	$(MAKE) figures
	$(MAKE) test
