.PHONY: install test lint run demo clean

install:
	pip install -e ".[dev]"

test:
	pytest --cov=energpt --cov-report=term-missing

lint:
	ruff check energpt tests

run:
	uvicorn energpt.main:app --reload --port 8000

demo:
	python -m energpt.cli demo

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
