# Make commands for building docs website for our python projects.

# if the .venv directory exists, use the python binary from there
# otherwise use the system python
SHELL := /bin/bash
PYTHON := $(if $(wildcard ./.venv/),./.venv/bin/python,python)

generate-docs:
	$(PYTHON) tools/generate_docs.py $(library)

serve-docs:
	cd libraries/$(library) && PYTHONPATH=src mkdocs serve

build-docs:
	cd libraries/$(library) && PYTHONPATH=src mkdocs build

clean-docs:
	rm -rf libraries/$(library)/site

build-docs-index:
	$(PYTHON) tools/build_docs_index.py

deploy-docs:
	vercel --prod
