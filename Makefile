GCP_PROJECT_ID ?= tft-data-463022
GCP_ARTIFACT_REPO ?= tft-data-python-registry
GCP_REGION ?=

REPO_URL = https://$(GCP_REGION)-python.pkg.dev/$(GCP_PROJECT_ID)/$(GCP_ARTIFACT_REPO)/

.PHONY: install test clean build publish

install:
	pip install -e ".[dev]"

test:
	pytest

clean:
	rm -rf dist build *.egg-info src/*.egg-info

build: clean
	python -m build

publish: build
	@if [ -z "$(GCP_REGION)" ]; then \
		echo "GCP_REGION is not set. Pass it as 'make publish GCP_REGION=us-central1' or export it."; \
		exit 1; \
	fi
	twine upload --repository-url $(REPO_URL) dist/*
