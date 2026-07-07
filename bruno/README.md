# Bruno collection

`hollywood-api/` is a [Bruno](https://www.usebruno.com/) API collection generated
directly from the live OpenAPI spec at `GET /openapi`. It's stored in the
[OpenCollection](https://github.com/usebruno/opencollection) format (see
`hollywood-api/opencollection.yml`) — Bruno's newer, tool-agnostic YAML
collection spec, not the older `.bru` plaintext format.

## Safe by default

All write/mutating endpoints (`POST /ingest`, `/ingest/source`, `/ingest/group`,
`/normalize`, and every CRUD write on `/candidates`, `/projects`, `/users`,
`/submissions`) are tagged `mutating` in the OpenAPI spec (see `tags: ["mutating"]`
on their `createRoute()` definitions in `api/src/routes/`). The importer groups
them into a separate `mutating/` folder automatically.

- `just bruno-run` — runs only the **safe, read-only** requests. No side effects.
- `just bruno-run-all` — runs everything, **including real writes**: a real
  OpenRouter LLM call, real RSS/TMDB/WGA/IMDb fetches, and real writes to
  whatever database `HOLLYWOOD_DB_PATH` points at. Don't run this against data
  you care about.

Two additional guardrails baked into the schemas themselves (so they survive
regeneration, not just this collection):
- `POST /ingest`'s example body has `dry_run: true` — even if someone runs
  `mutating/post -ingest.yml` directly, it reports what *would* be extracted
  without materializing a candidate.
- `POST /ingest/source` and `/ingest/group`'s example bodies have `limit: 1` —
  a naive run fetches one item from one feed, not an entire live source.

## Use it

- **Bruno desktop app**: File → Open Collection → select `bruno/hollywood-api/`.
- **CLI (safe subset)**: `just bruno-run`
- **CLI (everything, including writes)**: `just bruno-run-all`
- Run a single request: `cd bruno/hollywood-api && npx @usebruno/cli run "get -sources.yml" --env "Local development"`

## Regenerate

The collection is generated, not hand-maintained. After changing routes/schemas
in `api/src/routes/`, start the API (`just api-dev`) and run:

```bash
just bruno-import
```

This overwrites `bruno/hollywood-api/` with a fresh import from the running
server's `/openapi` spec. The `environments/Local development.yml` file's
`baseUrl` gets reset to `http://0.0.0.0:4000` by the importer every time —
change it back to `http://localhost:4000` after regenerating.

If you add a new mutating endpoint, tag its `createRoute()` call with
`tags: ["mutating"]` and give risky fields (unbounded fetches, real external
calls) a small/safe `.openapi({ example })` value — the importer copies those
examples verbatim into the generated request, and this collection is meant to
be runnable by anyone without reading the source first.
