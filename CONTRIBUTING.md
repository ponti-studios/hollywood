# Contributing to Snakesss

Thank you for your interest in contributing! This document outlines the development process and guidelines.

## Development Environment

### Prerequisites

- Python 3.11+
- uv (https://github.com/astral-sh/uv)

### Setup

1. Fork and clone the repository
2. Install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`
3. Install dependencies: `uv sync`
4. Copy `.env.example` to `.env` and fill in your API keys
5. Install pre-commit hooks: `uv run pre-commit install`

### Code Quality

We use several tools to maintain code quality:

- **Black**: Code formatting
- **Ruff**: Linting and additional formatting
- **MyPy**: Type checking
- **Pre-commit**: Automated checks on commit

Run all checks:

```bash
uv run pre-commit run --all-files
```

Or individually:

```bash
uv run black .
uv run ruff check . --fix
uv run ruff format .
uv run mypy .
```

### Testing

Run tests with:

```bash
uv run pytest
```

## Workflow

1. Create a feature branch: `git checkout -b feature/your-feature`
2. Make changes, ensuring tests pass and code quality checks
3. Commit with clear messages
4. Push and create a pull request

## Project Structure

- `src/`: Main source code
  - `cli/`: CLI commands and server
  - `lib/`: Shared utilities
- `tests/`: Unit and integration tests
- `sandbox/`: Experimental code
- `prompts/`: LLM prompt templates

## Guidelines

- Follow PEP 8 style
- Use type hints
- Write tests for new features
- Update documentation as needed
- Keep commits focused and descriptive
