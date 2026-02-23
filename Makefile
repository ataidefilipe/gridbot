.PHONY: run test lint check format
.DEFAULT_GOAL := run

run:
	python -m src.main

run-dry:
	python -m src.main --dry-run

test:
	pytest

lint:
	ruff check .

format:
	ruff format .

check: lint test
