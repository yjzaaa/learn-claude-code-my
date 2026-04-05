.PHONY: help install lint format type check fix clean test

# Default target
help:
	@echo "Available targets:"
	@echo "  install     - Install development dependencies (ruff, mypy, pre-commit)"
	@echo "  lint        - Run ruff linter"
	@echo "  format      - Run ruff formatter (check only)"
	@echo "  format-fix  - Run ruff formatter (auto-fix)"
	@echo "  type        - Run mypy type checker"
	@echo "  check       - Run all checks (lint + format + type)"
	@echo "  fix         - Auto-fix all auto-fixable issues"
	@echo "  pre-commit  - Install and run pre-commit hooks"
	@echo "  test        - Run pytest"
	@echo "  clean       - Clean cache files"

# Install development dependencies
install:
	pip install ruff mypy pre-commit pydantic>=2.0
	pre-commit install

# Run linter
lint:
	ruff check backend/ --output-format=text

# Check formatting
format:
	ruff format backend/ --check

# Fix formatting
format-fix:
	ruff format backend/

# Run type checker
type:
	mypy backend/ --ignore-missing-imports

# Run all checks
check: lint format type check-bare-dicts
	@echo "✅ All checks passed!"

# Check for bare dict literals (should use Pydantic models)
check-bare-dicts:
	@python scripts/check_bare_dicts.py backend/

# Auto-fix all fixable issues
fix:
	ruff check backend/ --fix
	ruff format backend/
	@echo "✅ Auto-fix complete!"

# Setup and run pre-commit hooks
pre-commit:
	pre-commit install
	pre-commit run --all-files

# Run tests
test:
	pytest tests/ -v

# Clean cache files
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@echo "✅ Cache cleaned!"
