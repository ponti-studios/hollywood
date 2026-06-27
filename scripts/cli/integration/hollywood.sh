#!/usr/bin/env bash
set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../.." && pwd -P)"
output_dir="$(mktemp -d)"
trap 'rm -rf "$output_dir"' EXIT

cd "$repo_root"

uv run python -m playwright install chromium

output_jsonl="$output_dir/wga_writers.jsonl"
uv run hollywood --prefixes a --max-profiles 1 --output "$output_jsonl"

python3 - "$output_jsonl" <<'PY'
import json
import sys

path = sys.argv[1]
with open(path, "r", encoding="utf-8") as handle:
    rows = [json.loads(line) for line in handle if line.strip()]

assert rows, "expected at least one writer row"
assert len({row["profile_url"] for row in rows}) == len(rows), rows

for row in rows:
    assert set(row) == {"writer_id", "profile_url", "raw_text_snapshot"}, row
    assert row["writer_id"], row
    assert row["profile_url"].startswith("https://directories.wga.org/member/"), row
    assert row["raw_text_snapshot"].strip(), row
PY
