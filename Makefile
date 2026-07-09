# Scam Autopsy Makefile

.PHONY: grade load-data lint test

load-data:
	@echo "Checking evaluation datasets..."
	@if [ ! -f eval/dataset_classifier.json ]; then \
		uv run python3 eval/load_datasets.py; \
	fi

grade: load-data
	@echo "Running all evaluation suites..."
	uv run python3 eval/run_eval.py

lint:
	@echo "Running linters..."
	uvx ruff check .
	uvx ruff format --check .
	uvx codespell

test:
	@echo "Running unit tests..."
	uv run --group dev pytest tests/unit
