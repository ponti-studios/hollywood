# Hollywood API: Next Steps

> This doc previously described a Python CLI (`src/hollywood/cli.py`, `pyproject.toml`)
> that predates the TypeScript/Drizzle migration (see `68e81b6 migrate to drizzle`,
> `8eb1ea4 migrate to typescript`). That CLI no longer exists — the API is TypeScript-only
> now. The plan below reflects the current state.

## Status

| Component | State |
|-----------|-------|
| Hono REST/OpenAPI API | ✅ Done |
| Domain schema v2 (`people`/`titles`/`companies` + joins) | ✅ Done — see `domain-schema-v2.md` |
| Ingestion pipeline architecture (bronze/silver/gold) | ✅ Documented — see `ingestion-pipeline-architecture.md` |
| Drizzle schema + migrations for v2 | ✅ Done |
| Ingest adapters (RSS, TMDB, Wikidata, WGA, IMDb) | ✅ Done |
| LLM extraction → candidate materialization | ✅ Done, verified end-to-end |
| Repository/service layer migrated to v2 schema | ✅ Done |
| Entity resolution (`entity_match_decisions` clustering job) | ❌ Not started — tables removed |
| Staged-facts materialization job | ❌ Not started — tables removed |
| Parquet export (JSONL only for now) | ❌ Not yet |
| Async job queue | ❌ Not yet |

MVP scope right now is **direct-write to gold**: ingest writes straight into
`people`/`titles`/`companies` with no deduplication. The silver-layer landing
zone this was meant to feed — `entities`, `entity_match_decisions`,
`staged_facts`, and `source_facts` — was **removed entirely** (not just left
empty) on 2026-07-13, since nothing read or wrote them under the direct-write
model (see `ingestion-pipeline-architecture.md`'s status note and commit
`eb0797c`). Resurrecting entity resolution means restoring those tables from
git history first (they're gone from `schema.ts`, not just unused), then
building the clustering job described in `ingestion-pipeline-architecture.md`.

The ID scheme (`makeStableId(sourceId, name)` in `EntityRepository.ts`)
embeds `sourceId` in every generated id, so it **cannot** merge the same
real-world person/title/company ingested from two different sources — this
is a structural gap, not a tuning issue. A live audit (2026-07-13) found zero
cross-source `canonical_name` collisions today, but only because `tmdb`/
`imdb`/`wikidata` — the only sources likely to describe the same real
people/titles — have each only run once so far (8 total ingest runs, all
same day). That's not evidence dedup is a non-problem; it's thin data. See
priority order below.

---

## 1. Entity resolution (when direct-write dedup becomes a problem)

Once the same person/title/company starts getting ingested from multiple
sources with slightly different names, direct-write will start producing
duplicates. At that point, restore `entities`/`entity_match_decisions`/
`staged_facts`/`source_facts` from git history (removed in `eb0797c`) and
build the clustering job described in `ingestion-pipeline-architecture.md`:
blocking, `entity_match_decisions`, connected-components clustering,
`canonical_id` promotion.

## 2. Staged-facts materialization

Same story for relationship facts (credits, deals, reps) extracted before
their referenced entities exist — currently a non-issue because ingest
resolves entity references synchronously against gold tables. Becomes
relevant once ingestion is async or multi-pass.

## 3. Parquet export

`GET /export` only supports `jsonl` today. `exportTable()` in
`ExportService.ts` throws on `format=parquet`.

## 4. Async job queue

Extraction and ingest operations are synchronous and can take 30-120 seconds.
`runs` already tracks status — the plan is `202 Accepted` + `GET /runs/{id}`
polling, with a worker processing runs out of band. Not urgent while ingest
volume is low.

---

## Priority order

1. **Entity resolution is now warranted, not just a future risk.** Re-running
   `tmdb`/`imdb`/`wikidata` at real volume (2026-07-13) produced **86**
   cross-source `canonical_name` collisions in `people` (e.g. "tom hanks"
   as three separate rows from `tmdb`/`imdb`/`wikidata`) and 2 in `titles`;
   `companies` still has none. This confirms the `makeStableId(sourceId,
   name)` id scheme (see status note above) cannot merge these — every
   overlapping ingest run makes it worse. Next step: restore
   `entities`/`entity_match_decisions` (removed in `eb0797c`) and build the
   blocking + clustering job described in `ingestion-pipeline-architecture.md`.
2. Parquet export, if downstream consumers need it.
3. Async job queue, once ingest latency becomes a UX problem.

Separately, while generating the volume above: `POST /ingest/source` for
`imdb` without a `limit` throws `Invalid string length` —
`ingest/adapters/imdb.ts` reads the full downloaded TSV via `readFileSync`
during normalization regardless of the `limit` passed to the earlier
download step, and the real IMDb datasets are large enough to exceed V8's
max string length. Works fine with an explicit `limit`; the unbounded path
is a real bug worth fixing before running IMDb ingestion at production
volume.
