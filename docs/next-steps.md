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
| Entity resolution (`entity_match_decisions` clustering job) | ❌ Not started |
| Staged-facts materialization job | ❌ Not started |
| Parquet export (JSONL only for now) | ❌ Not yet |
| Async job queue | ❌ Not yet |

MVP scope right now is **direct-write to gold**: ingest writes straight into
`people`/`titles`/`companies` with no deduplication. `entities`,
`entity_match_decisions`, and `staged_facts` exist in the schema but are empty
and unused — they're the landing zone for the resolution pipeline described in
`ingestion-pipeline-architecture.md`, which is deliberately deferred until the
direct-write path is proven out with real data.

---

## 1. Entity resolution (when direct-write dedup becomes a problem)

Once the same person/title/company starts getting ingested from multiple
sources with slightly different names, direct-write will start producing
duplicates. At that point, build the clustering job described in
`ingestion-pipeline-architecture.md`: blocking, `entity_match_decisions`,
connected-components clustering, `canonical_id` promotion.

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

1. Ingest real sources at volume and see whether direct-write duplication is
   actually a problem in practice before building resolution.
2. Parquet export, if downstream consumers need it.
3. Async job queue, once ingest latency becomes a UX problem.
