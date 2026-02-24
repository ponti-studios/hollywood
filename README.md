# Snakesss

A modern Python toolkit for AI, automation, and backend services.

## Features

- CLI tools for calculations, web scraping, note-taking, and user story generation
- FastAPI server with routers for chat, tasks, media, and more
- Integration with LLMs (OpenAI, Ollama, etc.)
- Utilities for document processing, embeddings, and cost tracking

## Installation

### Prerequisites

- Python 3.11+
- uv (for dependency management)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/charlesponti/snakesss.git
   cd snakesss
   ```

2. Install uv if not already installed:
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

3. Install dependencies:
   ```bash
   uv sync
   ```

4. Copy environment variables:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

5. Install pre-commit hooks:
   ```bash
   uv run pre-commit install
   ```

## Usage

### CLI

```bash
uv run snakesss --help
```

### Server

```bash
uv run python -m src.cli.server.main
```

Or using the script:
```bash
uv run snakesss server
```

## Development

- Format code: `uv run black .`
- Lint: `uv run ruff check .`
- Type check: `uv run mypy .`
- Test: `uv run pytest`

## Project Structure

- `src/cli/`: Command-line interface modules
- `src/lib/`: Shared libraries and utilities
- `tests/`: Test suite
- `sandbox/`: Experimental scripts
- `prompts/`: Prompt templates

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines.
