# Nexus

Your terminal AI workbench.

## The Story

Nexus is the intersection of human intent and machine intelligence. While others build web interfaces and API wrappers, nexus lives where developers work — in the command line. It's not about hosting models; it's about using AI as a power tool in your daily workflow.

**Nexus** puts the full power of modern AI at your fingertips — chat, vision, audio, task extraction, and web scraping — all from the terminal where you already live.

## Features

- **AI Chat**: Interactive conversations with GPT models
- **Audio Processing**: Transcribe audio files with Whisper
- **Vision**: Analyze images with GPT-4 Vision
- **Task Extraction**: Extract tasks from natural language
- **Web Scraping**: Crawl websites and extract structured data
- **User Story Generation**: Create user stories from ideas

## Installation

### Prerequisites

- Python 3.11+
- [uv](https://docs.astral.sh/uv/) (recommended package manager)

### Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/charlesponti/nexus.git
   cd nexus
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

5. Verify installation:
   ```bash
   uv run nexus --version
   ```

## Usage

### Available Commands

```bash
# Get help
uv run nexus --help

# Chat with AI
uv run nexus chat message "Hello, how are you?"

# Transcribe audio
uv run nexus audio transcribe recording.m4a

# Analyze images
uv run nexus vision describe photo.jpg

# Extract tasks from text
uv run nexus tasks extract "I need to buy groceries tomorrow and call mom on Friday"

# Scrape websites
uv run nexus crawler scrape --url https://example.com

# Generate user stories
uv run nexus user-story generate "A login system with email and password"
```

## Development

```bash
# Install dev dependencies
uv sync --all-extras

# Run tests
uv run pytest

# Lint code
uv run ruff check .

# Format code
uv run ruff format .

# Type check
uv run pyright
```

## Project Structure

```
src/
├── main.py           # CLI entry point
├── nexus.py          # Package version info
├── commands/         # CLI command modules
│   ├── chat.py      # AI chat
│   ├── audio.py     # Audio transcription
│   ├── vision.py    # Image analysis
│   ├── tasks.py     # Task extraction
│   ├── crawler.py   # Web scraping
│   └── ...
├── lib/              # Core libraries
│   ├── clients/     # API clients (OpenAI, etc.)
│   ├── scrapers/    # Web scraping utilities
│   └── ...
└── models/           # Pydantic models
```

## License

MIT
