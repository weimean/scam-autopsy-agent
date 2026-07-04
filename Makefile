# Scam Autopsy Makefile

.PHONY: grade load-data

load-data:
	@echo "Checking evaluation datasets..."
	@if [ ! -f eval/dataset_classifier.json ]; then \
		PATH="/Users/tsoiwaimun/.local/bin:$$PATH" uv run python3 eval/load_datasets.py; \
	fi

grade: load-data
	@echo "Running all evaluation suites..."
	PATH="/Users/tsoiwaimun/.local/bin:$$PATH" uv run python3 eval/run_eval.py
