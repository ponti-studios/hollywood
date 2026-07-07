# hollywood

Local-first entertainment data platform for research corpus building. A Hono REST API
ingests entertainment RSS feeds, browser-only directories like WGA, and structured
metadata sources (TMDB, Wikidata, IMDb) into a unified SQLite database, with raw-payload
archiving and JSONL exports.

## Run

```bash
just api-setup
just api-dev
```

The API starts at `http://localhost:4000`. OpenAPI docs are at `/openapi`.

## Endpoints

- `GET /sources` — list built-in ingest sources
- `POST /ingest` — LLM extraction from raw submission text (single doc or batch)
- `POST /ingest/source` — ingest a single source (`variety`, `deadline`, `hollywood_reporter`, `the_wrap`, `tmdb`, `wikidata`, `wga`, `imdb`)
- `POST /ingest/group` — ingest all sources in a named group (`news`, `entities`, `directories`, `all`)
- `POST /normalize` — re-derive normalized tables from already-archived raw records
- `GET /export` — export normalized tables as JSONL
- `GET /doctor` — health checks (data dir, DB, API keys, per-source config)
- `GET /candidates`, `/projects`, `/submissions`, `/search`, `/tags`, `/users` — entity graph CRUD/search

## Environment

```bash
HOLLYWOOD_DATA_DIR=data
HOLLYWOOD_DB_PATH=~/.hominem/hollywood.db
HOLLYWOOD_USER_AGENT=...
HOLLYWOOD_REQUEST_TIMEOUT_SECONDS=30
TMDB_API_KEY=...
OPENROUTER_API_KEY=...
```

The default storage layout is:

- `data/raw/` for archived payloads
- `~/.hominem/hollywood.db` for the unified SQLite database
- `data/parquet/` for JSONL exports (despite the directory name — parquet export is not yet implemented)

## Development

```bash
just api-setup
just api-dev        # dev server with hot reload
just api-typecheck
just api-build
just api-start       # run the compiled build
```
