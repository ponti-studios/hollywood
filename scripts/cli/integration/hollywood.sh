#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
output_dir="$(mktemp -d)"
trap 'rm -rf "$output_dir"' EXIT

cd "$repo_root"

uv run python -m playwright install chromium

data_dir="$output_dir/data"
uv run hollywood sources list > /dev/null
uv run hollywood ingest group news --limit 1 --data-dir "$data_dir"
uv run hollywood ingest source wga --limit 1 --prefixes a --data-dir "$data_dir"
uv run hollywood normalize --data-dir "$data_dir"
uv run hollywood export --all --data-dir "$data_dir"

uv run python - "$data_dir" <<'PY'
from pathlib import Path
import duckdb
import sys

data_dir = Path(sys.argv[1])
db_path = data_dir / "hollywood.duckdb"
assert db_path.exists(), db_path

conn = duckdb.connect(str(db_path))
article_count = conn.execute("select count(*) from articles").fetchone()[0]
raw_count = conn.execute("select count(*) from raw_records").fetchone()[0]
entity_count = conn.execute("select count(*) from entities").fetchone()[0]
assert article_count >= 1, article_count
assert raw_count >= 1, raw_count
assert entity_count >= 1, entity_count

parquet_dir = data_dir / "parquet"
assert (parquet_dir / "articles.parquet").exists(), parquet_dir
assert (parquet_dir / "entities.parquet").exists(), parquet_dir
PY
