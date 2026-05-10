.PHONY: format lint test

format:
	uv run ruff format .

lint:
	uv run ruff check .

test:
	uv run pytest tests/ -v
