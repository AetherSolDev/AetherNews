# Created: 2026-08-12
# Last Edited: 2026-08-12 17:40 CT (America/Chicago)
# Path: Makefile
# Purpose: Build/install/verify targets for AetherNews.

PYTHON ?= python3
PIP ?= pip3

.PHONY: install install-user uninstall test lint clean

install:
	$(PIP) install .

install-user:
	$(PIP) install --user .

uninstall:
	$(PIP) uninstall -y aethernews

test:
	$(PYTHON) -m pytest tests/ -v

lint:
	uvx ruff check aethernews tests

clean:
	rm -rf build dist *.egg-info __pycache__ aethernews/__pycache__
	find . -name '__pycache__' -type d -exec rm -rf {} +
