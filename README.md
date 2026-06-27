# hollywood

CLI for crawling the WGA directory and capturing writer profile snapshots as JSONL.

## Run

```bash
uv run hollywood --help
uv run python -m playwright install chromium
uv run hollywood --prefixes a --max-profiles 1 --output wga_writers.jsonl
```

## Development

```bash
just setup
just test
just smoke
just integration
```

The crawl is prefix-driven, dedupes profile URLs within a run, and appends JSONL rows with a stable writer id and raw profile text snapshot.
