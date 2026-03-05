# Nexus - Python CLI Toolkit
# ==========================

.PHONY: help install test lint format typecheck clean

# Installation
install:
	uv sync

# Testing
test:
	uv run pytest -v

# Linting
lint:
	uv run ruff check src/

# Formatting
format:
	uv run ruff format src/

# Type checking
typecheck:
	uv run pyright src/

# Clean up
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true

# Quick commands
.PHONY: run version help-commands

run:
	uv run nexus

version:
	uv run nexus --version

help-commands:
	uv run nexus --help

# Help
help:
	@echo "Nexus - Your terminal AI workbench"
	@echo ""
	@echo "Available commands:"
	@echo "  make install       - Install dependencies (uv sync)"
	@echo "  make test         - Run tests"
	@echo "  make lint         - Run linter (ruff)"
	@echo "  make format       - Format code (ruff)"
	@echo "  make typecheck    - Type check (pyright)"
	@echo "  make clean        - Remove cache files"
	@echo "  make run          - Run CLI"
	@echo "  make version      - Show version"
	@echo "  make help-commands - Show CLI help"
