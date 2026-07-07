# Hollywood API: Next Steps Plan

## Status

| Component | State |
|-----------|-------|
| GraphQL → Hono REST/OpenAPI migration | ✅ Done |
| Entity graph schema (Goose 00001) | ✅ Done |
| Kuma data migration → unified schema | ✅ Done |
| Extraction pipeline (LLM → entities) | ✅ Done |
| API ingest endpoint (POST /ingest) | ✅ Done |
| CLI deprecation / Python package deleted | ✅ Done |
| Ingest sources (RSS, TMDB, Wikidata, WGA, IMDb) ported to TS, via API | ✅ Done |
| EML email parsing (POST /ingest multipart upload) | ✅ Done |
| Parquet export (jsonl only for now) | ❌ Not yet |
| Async job queue | ❌ Not yet |

---

## 1. Delete the CLI, move commands to API

**Why:** The CLI exists solely as a development scaffold. Every operation should be
triggerable through the API. Maintaining both is unnecessary overhead.

### 1.1 New API endpoints to add

| Method | Path | Replaces CLI command |
|--------|------|---------------------|
| `GET` | `/sources` | `hollywood sources list` |
| `POST` | `/ingest/source` | `hollywood ingest source <id>` |
| `POST` | `/ingest/group` | `hollywood ingest group <name>` |
| `POST` | `/normalize` | `hollywood normalize` |
| `GET` | `/export` | `hollywood export --all` |
| `GET` | `/doctor` | `hollywood doctor` |

### 1.2 Source ingest adapters

Each adapter (variety, hollywood_reporter, tmdb, imdb, wga) becomes a Python
subprocess the API invokes:

```
POST /ingest/source
{
  "source_id": "tmdb",
  "limit": 100,
  "since": "2024-01-01",
  "full_text": true
}
→ 202 { "run_id": "...", "status": "queued" }
```

For now, run synchronously and return the run summary. Async queue comes later.

### 1.3 Files to delete after API endpoints are live

```
src/hollywood/cli.py
```
And remove `typer` from `pyproject.toml` dependencies.

**Effort:** ~3-4 route files + delete `cli.py`

---

## 2. Port the EML parser from Go to Python

**Why:** Actual submissions arrive as `.eml` files with PDF attachments. The raw
7MB EML can't be fed to the LLM. Kuma's Go parser (`internal/extract/extract.go`)
handles this — we need the same logic in Python.

### 2.1 What the Go parser does

1. Parses MIME message structure (multipart/mixed, multipart/alternative)
2. Skips file attachments (base64 PDFs)
3. Decodes `quoted-printable` and `base64` transfer encodings
4. Prefers `text/plain` parts, falls back to HTML with tag stripping
5. Strips quoting prefixes (`>`), forwarding headers, and signature lines
6. Normalizes whitespace and returns clean body text

### 2.2 Python module

```
src/hollywood/eml.py
```

Classes/functions:

```python
def parse_eml(path: str | Path) -> str:
    """Parse .eml file, return clean body text suitable for LLM extraction."""

def _parse_email_message(msg: email.message.Message) -> str:
    """Recursive MIME walker. Prefers text/plain, strips HTML as fallback."""

def _decode_part(part: email.message.Message) -> str:
    """Handle quoted-printable, base64, and raw text parts."""

def _strip_html(text: str) -> str:
    """Remove HTML tags, convert <br> to newlines, collapse whitespace."""

def _clean_email_body(text: str) -> str:
    """Strip forwarding headers, quote prefixes, signature blocks, normalize whitespace."""
```

**Dependencies:** `email` (stdlib). No new packages.

### 2.3 Integration

- `ingest_doc.py` calls `parse_eml()` before `_call_openrouter()` when input is `.eml`
- `POST /ingest` accepts `content_type: multipart/form-data` for raw `.eml` uploads
- `POST /ingest` also accepts `application/json` with `{"text": "..."}` for plain text

**Effort:** ~200 lines of Python, 1 file

---

## 3. Clean up test data pollution

**Why:** Manual testing during development left duplicate tags with inconsistent
normalized forms in `tags` table (e.g., "Emmy winner" + "emmy winner", "show runner"
+ "showrunner").

### 3.1 Normalize tags

Deduplicate the `tags` table and remap `entity_taggings` to use canonical tag IDs.

```sql
-- Find duplicates by normalized_tag (case-insensitive, underscore-separated)
-- Choose the first tag_id as canonical
-- UPDATE entity_taggings SET tag_id = canonical_id WHERE tag_id = duplicate_id
-- DELETE FROM tags WHERE id = duplicate_id
```

Script: `scripts/normalize_tags.py`

**Effort:** 1 script, run once.

---

## 4. Repopulate the database from EML fixtures

**Why:** The `sample_emails/` directory contains 2 EML files and 20 extracted `.txt`
files. After the EML parser is done, we should ingest these to populate the database
with real entertainment data before the production launch.

### 4.1 Process

```bash
# Via API:
for file in .data/sample_emails/*.eml; do
  curl -X POST localhost:4000/ingest -F "file=@$file"
done

# Or via Python script:
uv run python -m hollywood.ingest_batch .data/sample_emails/
```

This would create ~9-18 candidates with full credit/tag/org graphs in the DB.

**Effort:** Run once after EML parser is done.

---

## 5. Future: Async job queue

**Why:** Extraction and ingest operations take 30-120 seconds. Blocking HTTP
requests are fine for now, but production should be async.

### 5.1 Approach

- Use SQLite as a job queue (no external dependency needed)
- `runs` table already tracks status with `RunStatus` enum (running, succeeded, failed)
- API returns `202 Accepted` with `run_id`, client polls `GET /runs/{id}` for status
- Worker processes run as separate Node.js child processes or Python subprocesses

### 5.2 API changes

```
POST /ingest          → 202 { run_id, status: "queued" }
GET  /runs/{id}       → 200 { run_id, status: "succeeded", summary: {...} }
```

**Effort:** 1 route file, modify ingest routes to return 202 instead of blocking.

---

## Priority order

1. 🥇 **Delete CLI** — reduces surface area, forces all operations through API
2. 🥈 **EML parser** — unblocks actual email ingestion (the real data source)
3. 🥉 **Tag cleanup** — one-time fix, trivial
4. **Repopulate from EML fixtures** — validate the full pipeline with real data
5. **Async job queue** — production readiness (can defer)

---

## Files that will change

| File | Action |
|------|--------|
| `src/hollywood/cli.py` | Delete |
| `src/hollywood/ingest_doc.py` | Extend with EML support |
| `src/hollywood/eml.py` | Create (EML parser) |
| `src/hollywood/storage.py` | No changes needed |
| `api/src/routes/ingest.ts` | Accept file uploads, return 202 |
| `api/src/routes/sources.ts` | Create (list/run ingest sources) |
| `api/src/routes/doctor.ts` | Create (health checks) |
| `api/src/routes/export.ts` | Create (table exports) |
| `api/src/routes/runs.ts` | Create (job status polling) |
| `api/src/db/helpers.ts` | No changes needed |
| `pyproject.toml` | Remove typer dependency |
| `scripts/normalize_tags.py` | Create (one-time cleanup) |
