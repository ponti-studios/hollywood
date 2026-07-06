# hollywood

Local-first Hollywood data CLI for research corpus building. It can ingest entertainment RSS
feeds, browser-only directories like WGA, and structured metadata sources into a raw archive,
DuckDB database, and Parquet exports.

## Run

```bash
uv run hollywood --help
uv run hollywood sources list
uv run python -m playwright install chromium
uv run hollywood ingest group news --limit 2
uv run hollywood ingest source wga --limit 1 --prefixes a
uv run hollywood normalize
uv run hollywood export --all
```

## Commands

- `hollywood sources list`
- `hollywood ingest source <source-id>`
- `hollywood ingest group <group-name>`
- `hollywood normalize`
- `hollywood export`
- `hollywood doctor`

## Environment

```bash
HOLLYWOOD_DATA_DIR=data
HOLLYWOOD_DB_PATH=data/hollywood.duckdb
TMDB_API_KEY=...
```

The default storage layout is:

- `data/raw/` for archived payloads
- `data/hollywood.duckdb` for normalized tables
- `data/parquet/` for exported datasets

## Development

```bash
just setup
just test
just lint
just typecheck
just smoke
just integration
```
