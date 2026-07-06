# Hollywood Data CLI Expansion

## Summary

Turn `hollywood` from a single WGA crawler into a local-first data collection CLI for building a research-grade Hollywood corpus. The product becomes a built-in source registry plus a multi-stage ingestion pipeline that can pull RSS feeds, dataset dumps, APIs, and browser-only crawlers, archive raw payloads and full text, and materialize normalized DuckDB and Parquet outputs for model training.

Confirmed source surfaces to plan around:
- WGA directory browser crawl: [directories.wga.org](https://directories.wga.org/)
- Entertainment RSS feeds: [Variety RSS](https://variety.com/feed/), [Deadline RSS](https://deadline.com/feed/), [The Hollywood Reporter RSS](https://www.hollywoodreporter.com/feed/), [TheWrap RSS](https://www.thewrap.com/feed/)
- Structured datasets and metadata: [IMDb non-commercial datasets](https://developer.imdb.com/non-commercial-datasets/), [TMDb developer docs](https://developer.themoviedb.org/docs/getting-started), [Wikidata database downloads](https://www.wikidata.org/wiki/Wikidata:Database_download)

## Key Changes

- Replace the one-shot crawler CLI with subcommands built on `argparse` subparsers:
  - `hollywood sources list`
  - `hollywood ingest --source <id> [--limit N] [--since ISO8601] [--full-text]`
  - `hollywood ingest-group --group news|entities|all`
  - `hollywood normalize [--source <id>]`
  - `hollywood export --table <name>|--all --format parquet|jsonl`
  - `hollywood doctor` for env, browser, API-key, and storage checks
- Promote source handling to a built-in registry shipped in the repo. Each source definition includes:
  - `source_id`, `source_kind` (`rss`, `api`, `dataset`, `browser`)
  - default endpoints or seed URLs
  - rate limits and fetch mode
  - native identifier extraction rules
  - license/use classification
  - whether feed content, linked page HTML, extracted article text, or attachments should be archived
- Keep the current WGA collector, but convert it into a `browser` source adapter under the shared pipeline instead of leaving it as a special-case CLI.

## Data Model And Pipeline

- Adopt a two-layer storage model:
  - Raw archive under `data/raw/<source_id>/<YYYY>/<MM>/<DD>/...` with original feed XML, API JSON, downloaded datasets, fetched HTML, extracted text, and manifest files
  - Local analytics store in `data/hollywood.duckdb`, with Parquet exports under `data/parquet/`
- Add normalized core tables for training prep:
  - `source_runs`: one row per CLI run with timing, status, counts, and config
  - `raw_records`: one row per fetched payload with content hash, path, URL, fetched time, source id, and parse status
  - `articles`: canonical article metadata from feeds or APIs
  - `article_bodies`: full-text body variants, with provenance such as `feed_description`, `feed_content`, `page_extract`, or `browser_snapshot`
  - `entities`: people, titles, companies, organizations, and awards
  - `entity_aliases`: alternate names and source-native IDs
  - `article_entities`: join table between articles and extracted entities
  - `credits`: writer, director, cast, producer, and related title-person-company relationships
- Use URL canonicalization plus source-native IDs plus payload SHA-256 hashes for dedupe. Canonical article URLs are the primary identity for news items; source-native IDs are primary for datasets and directory rows.
- Treat full-text archiving as enabled by default in this research/non-commercial build. Store both raw HTML and extracted clean text when the source has a linked article page, and keep feed-provided text as a separate body variant instead of overwriting it.
- Tag every source and every stored payload with a license/use field so downstream training jobs can filter later even though this build targets research/non-commercial use.

## Source Coverage For V1

- `rss` adapters:
  - Variety, Deadline, The Hollywood Reporter, TheWrap
  - Parse title, link, author, publish time, categories, description, optional `content:encoded`, media thumbnails, and feed-native GUIDs
  - Optionally fetch linked article pages and extract main text
- `browser` adapters:
  - Existing WGA writer directory crawl, reworked to emit normalized people and credits in addition to raw snapshots
- `dataset` and `api` adapters:
  - IMDb non-commercial datasets importer for titles, people, ratings, episodes, and principals
  - TMDb importer for title, person, credits, and external IDs via API key
  - Wikidata importer for selected Hollywood-relevant entity properties and cross-source identifiers
- Keep the registry open for later additions such as awards calendars, festival lineups, box office sources, trades newsletters, and podcast RSS, but do not include them in the first implementation pass.

## Public Interfaces And Defaults

- New default output location is a project-local data workspace:
  - DuckDB: `data/hollywood.duckdb`
  - Raw payloads: `data/raw/`
  - Exports: `data/parquet/`
- Add global flags:
  - `--data-dir`
  - `--db-path`
  - `--log-level`
  - `--no-full-text`
  - `--since`
  - `--limit`
- Add per-source credential lookup through environment variables only in v1:
  - `TMDB_API_KEY`
  - future sources follow the same `SOURCE_API_KEY` pattern
- Add source grouping in the built-in registry:
  - `news`
  - `entities`
  - `directories`
  - `all`
- Keep Rich progress output, but change it to multi-stage progress showing fetch, parse, normalize, and export counts.

## Dependencies And Implementation Approach

- Keep Python and the current packaging flow.
- Add dependencies for:
  - `duckdb`
  - `pyarrow`
  - `feedparser`
  - `httpx`
  - `selectolax` or `trafilatura` for article extraction
  - `python-dateutil`
- Keep `playwright` for browser-only sources like WGA.
- Organize code into clear modules:
  - CLI entry and subcommands
  - source registry
  - adapter interface and source implementations
  - raw archive writer
  - normalization and dedupe layer
  - DuckDB and Parquet storage layer
  - article extraction and entity parsing helpers

## Test Plan

- Unit tests:
  - source registry loading and source selection
  - RSS item parsing across the four confirmed feed shapes
  - URL canonicalization and article dedupe
  - license/use tagging
  - raw record manifest generation
  - normalized row builders for articles, entities, and credits
- Fixture-based integration tests:
  - saved RSS XML from Variety, Deadline, THR, and TheWrap
  - saved article HTML fixtures for clean-text extraction
  - saved WGA profile snapshots for entity and credit parsing
  - small IMDb and Wikidata fixture slices for dataset import behavior
- Live smoke tests, kept separate from unit tests:
  - one RSS ingest run that writes raw payloads and normalized rows
  - one WGA crawl with `--limit 1`
  - optional TMDb smoke gated on `TMDB_API_KEY`
- Acceptance checks:
  - `hollywood sources list` shows all built-ins
  - `hollywood ingest-group --group news --limit 5` archives feed payloads and normalizes article rows
  - `hollywood normalize` is idempotent across repeated runs
  - `hollywood export --all --format parquet` writes readable Parquet outputs
  - rerunning the same source does not duplicate canonical records

## Assumptions And Defaults

- This build is optimized for research and non-commercial model training, not commercial-safe distribution.
- Full-text archiving is on by default, but every payload and normalized row still carries a license/use tag.
- The CLI remains local-first and does not require a server or cloud database.
- Built-in source definitions are the primary extension mechanism in v1; user-defined external source configs are out of scope for the first pass.
- The first implementation should prioritize correctness, provenance, and repeatability over aggressive entity resolution or deep NLP. Initial entity extraction can rely on source metadata and lightweight parsing; richer enrichment can follow once the corpus pipeline is stable.
