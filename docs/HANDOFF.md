# Session handoff — entertainment-graph unification (setlist + hollywood)

Written 2026-09-28, updated same day after the budget/box-office gap (see
below) was resolved. This is a snapshot for picking up in a fresh chat —
read this first, then the referenced files/docs for detail.

## The big picture

Merging two repos into one "master entertainment industry" platform, built
inside **`ponti-studios/hollywood`** (TypeScript/Hono, mature entity-graph
platform) rather than a new repo — **`charlesponti/setlist`** (Python/
Flask/CrewAI music chat-assistant prototype) was the *source* of product
ideas (Director/sub-agent chat pattern) but is not itself being modified.
The strategy was phased: P0 (schema/adapter extension for music) → P1
(port the chat assistant) → P2 (deferred — UI, not started, no location
chosen) → cost tracking/model swap → MCP server (in progress, see below).

**Local clone**: `~/Developer/hollywood` (moved here from a scratchpad
mid-session — this is the permanent location).

**Standing constraint — do not violate this**: `~/.hominem/hollywood.db`
is the user's real local DB, on an old pre-unification "kuma" schema
(`people`/`companies`/`titles`/`company_relations`), with real prior data.
**Never touch, migrate, or write to it.** All ingest/live-testing uses a
disposable scratch DB at `/tmp/hollywood-test.db` (already exists, already
has real Spotify-ingested data + a couple of manual-test rows — safe to
keep using or to delete and re-migrate). Cost/response logs from the
assistant land in `/tmp/hollywood-data/assistant-runs.jsonl` (also scratch,
not real).

**Decision-authority constraint** (applied throughout, per the hominem
repo's `AGENTS.md` "Decision authority" principle, extended here to
hollywood's own architecture): the user is the product manager/architect.
Do not invent, infer, or silently choose product behavior, schema shape,
or architecture — ask first via `AskUserQuestion` when a real fork exists.
This has already happened twice successfully (implementation location →
inside hollywood; LLM SDK choice → openai + @openai/agents; MCP
architecture → standalone server in hollywood repo) and is **currently
blocked** on a third (see "Immediate next step" below).

## Where things actually stand, concretely

### Shipped and merged (main branch)
- **P0** (PR #4, merged): schema/adapter extension for music. `EntityKind`
  gained `artist`/`venue`; `docs/unified-schema.md` documents the music
  convention (artist/label/album/tour/venue via the existing free-text
  `entity_type`/`title_type`/`company_type` columns, no new tables).
- **P1** (PR #5, merged): ported setlist's Director→4-sub-agent
  (Touring/Financial/Marketing/Calendar) chat pattern to TypeScript.
  Originally hand-rolled OpenRouter fetch + regex-based routing; **this was
  later fully rewritten** (see below) — the hand-rolled version is gone.

### Open, unmerged: PR #6 (`feat/assistant-cost-tracking`)
**Not merged — the user has not asked to merge it.** Bound and monitored
in this session (`ccd_pr` `auto_fix`+`address_comments` on). Contains, in
order:
1. **SDK rewrite**: replaced the hand-rolled OpenRouter client + regex
   Director-routing with `openai` (pointed at OpenRouter's base URL) +
   `@openai/agents` (`Agent`, `run()`, native `handoffs`, `tool()`). Files:
   `api/src/assistant/{model,agents,tools,service}.ts`. Deleted:
   `director.ts`, `grounding.ts`, `llm.ts` (all pre-SDK).
2. **Model + cost tracking**: model is `openai/gpt-5.6-luna` (user's
   explicit choice) via `model.ts`'s `ASSISTANT_MODEL` — independent of
   `ingest/llm.ts`'s `DEFAULT_MODEL` (`gpt-4o-mini`, extraction only, not
   touched). Every `chat()` call logs to `assistant/costLog.ts`, which
   **appends JSONL** (`assistant-runs.jsonl`) — deliberately not a JSON
   array (a Codex review comment caught the original array version as
   quadratic, request-blocking I/O; fixed before merge-readiness).
3. **Spotify adapter fixes**: `/browse/new-releases` returns 403 under
   Spotify's Nov-2024 policy change for standard-quota apps — switched to
   `GET /search?q=tag:new&type=album` (same shape, verified live).
4. **Grounding fix**: `search_entity_graph` (in `tools.ts`) now surfaces
   flat `metadataJson` fields (e.g. `genre: synth-pop`) via a
   `formatMetadata()` helper — previously it only ever returned
   `name (type)`, so genre/bio/etc. questions got wrong "I don't know"
   answers even when the data was right there in the DB.
5. **MCP server** (latest commit, `e0e3fbf`): `POST /mcp` in
   `api/src/index.ts`, built in `api/src/mcp/server.ts`, using
   `@modelcontextprotocol/sdk`'s `McpServer` + `@hono/mcp`'s
   `StreamableHTTPTransport`. Three tools: `search_entities` (wraps
   `searchEntityGraph`), `list_sources` (lists `BUILTIN_SOURCES`), `chat`
   (wraps `AssistantService.chat` — full Director/sub-agent routing).
   Read-safe only, no write/ingest-triggering tools. This is the
   foundation for "use hollywood from a chat agent, eventually WhatsApp" —
   **the WhatsApp integration itself is explicitly out of scope**, per the
   user's own words: "we don't have to focus on building the WhatsApp
   integration right now."

   Verified: `npx tsc --noEmit` clean, `npx vitest run` → 129/129 passing
   (3 new MCP tests using the SDK's real `InMemoryTransport`+`Client`, not
   just calling handler functions directly), and live end-to-end over real
   HTTP (`initialize` → `tools/list` → `tools/call`) against the scratch
   DB with **real OpenRouter + Spotify credentials** (both are in
   `~/Developer/hollywood/.env`, confirmed present this session —
   `TMDB_API_KEY` was **not** set at the time, since fixed, see below).
   Live `chat` calls through MCP correctly grounded a real question ("What
   genre is Nova Bright?" → "synth-pop", via the Marketing sub-agent
   calling `search_entity_graph`) and honestly declined for a fabricated
   artist name (no hallucination) — both calls landed in the cost log with
   real OpenRouter cost/token numbers (~$0.00025–0.00029 each).
6. **Movie budget/revenue capture** (commit `1f16f96`, same PR #6): resolves
   the "Immediate next step" blocker below. `TmdbAdapter.normalizeTitle()`
   (`api/src/ingest/adapters/tmdb.ts`) now reads `document["budget"]` /
   `document["revenue"]` from TMDb's `/movie/{id}` detail response into the
   title entity's `metadataJson` as `budget`/`revenue` (USD) plus a
   `budgetCurrency: "USD"` key added only when either is present. TMDb's
   `0` means "unknown," not zero dollars — treated as absent and omitted,
   never persisted as `0`. Movie-only: TV has no budget/revenue field in
   TMDb's API at all, and the code doesn't attempt it for `mediaType ===
   "tv"`. New test file `api/src/ingest/adapters/tmdb.test.ts` (6 cases:
   both present, both zero, one zero, tv exclusion, payload skip, doctor
   check). New `docs/unified-schema.md` "Film vertical extension" section,
   mirroring the existing "Music vertical extension" one.

   Verified: `npx tsc --noEmit` clean, `npx vitest run` → 135/135 passing,
   and live end-to-end — started the API with `HOLLYWOOD_DB_PATH=/tmp/
   hollywood-test.db`, `POST /ingest/source {"source_id":"tmdb","limit":3}`
   against the real TMDb API (key now present, see below), then queried
   the scratch DB directly. Confirmed real movies landed with only
   `budget` present (revenue unknown/omitted), only `revenue` present
   (budget unknown/omitted), and a TV title ("Lanterns") with neither key
   at all — matching the intended semantics exactly.

   **TV budget/revenue was investigated and is not currently pursued.**
   The user asked whether Wikidata could fill the TV gap (TMDb doesn't
   have TV budget/revenue at all, not even as a droppable `0`). Checked
   live: Wikidata's `P2130` ("capital cost") property, which is what
   movie/TV budgets use — "Lanterns" and even "Game of Thrones" have no
   such claim, and a SPARQL count found only **16 TV series in all of
   Wikidata** have this property, in inconsistent currencies (USD, KRW,
   UAH, DEM, ...). Conclusion: not worth an adapter path. Accepted gap,
   not resolved — if revisited later, the realistic options are Wikipedia
   infobox scraping or trade-press parsing (both unstructured/lower-
   confidence), not a clean structured-data source.
7. **Actor/producer salary investigation (accepted gap, nothing shipped)**:
   checked live rather than assumed. TMDb's cast/crew credit objects have
   no money-shaped field at all (confirmed via a real `GET /movie/1726`
   call — keys are `character`/`job`/`department`/`order`/etc., nothing
   compensation-related). Wikidata's `P3618` ("base salary") property has
   only **2 actors in all of Wikidata** — not usable. Conclusion:
   individual salaries/deal terms are not structured data anywhere
   accessible to this project; they're reported piecemeal by trade press
   as prose, when disclosed at all. No code changed for this.
8. **Movie financiers/investors → production-company capture** (same
   session, unmerged): the user's follow-up ask, "finding movie
   investors," was also checked live rather than assumed. Wikidata's
   `P1951` ("investor") has only 2 film claims, both miscategorized (one
   points at "Yukon" the territory). `P8324` ("funder") has 382 film
   claims but they're almost all Finnish public-broadcaster/city arts
   grants (`Yle`, `Tampere`, `Salzburg`), not commercial investors. TMDb
   has no "investor" concept either — but its `production_companies`
   field (present on both `/movie/{id}` and `/tv/{id}`, already fetched,
   confirmed live for both Iron Man and House of the Dragon) is the
   closest real, structured proxy for "who financed this," and was being
   silently dropped, same as budget/revenue had been.

   This surfaced a bigger gap: the DB already had a `title_companies`
   join table (`api/src/db/schema.ts`) for exactly this kind of
   relationship, but **it had zero ingest-pipeline support** — no
   `TitleCompanyRow` type, no field on `NormalizedBundle`, no repository,
   nothing in `IngestService` persisted to it. Asked the user (per the
   decision-authority constraint) whether to wire up the real relational
   path or take a metadataJson shortcut like budget/revenue — user chose
   the full wiring. Shipped:
   - `TitleCompanyRow` + `titleCompanies: TitleCompanyRow[]` added to
     `NormalizedBundle` (`api/src/ingest/models.ts`; also updated
     `emptyBundle`/`extendBundle`/`bundleCounts`).
   - New `TitleCompanyRepository` (`api/src/db/repositories/
     TitleCompanyRepository.ts`), mirroring `CreditRepository`'s
     idempotent `upsert()` pattern (stable ID from title+company+
     relationship, `onConflictDoNothing`).
   - `IngestService.upsertTitleCompanies()` wired into `applyBundle()`
     (`api/src/db/services/IngestService.ts`) — the reusable persistence
     path any future adapter (labels, distributors, networks) can now
     write to.
   - `TmdbAdapter.normalizeTitle()` now reads `document["production_companies"]`
     for both movie and tv, creates a `company` entity per company
     (`metadataJson.company_type = "production_company"`) and a
     `title_companies` row with `relationship = "production"`.
   - New tests in `tmdb.test.ts` (2 more cases: movie and tv production
     companies). New rows in `docs/unified-schema.md`'s "Film vertical
     extension" section documenting the company/`title_companies`
     convention.

   Verified: `npx tsc --noEmit` clean, `npx vitest run` → 137/137 passing,
   and live end-to-end against `/tmp/hollywood-test.db` — a real ingest
   run produced 25 `title_companies` rows; spot-checked the join query
   directly (e.g. "Digger" → Warner Bros. Pictures + Legendary Pictures +
   TC Productions, all `relationship = 'production'`). Note: re-running
   ingest against the same TMDb trending list on the same day hit a
   pre-existing (unrelated to this change) `UNIQUE constraint failed:
   raw_records.id` because `RawRecordRepository.insertBatch()` has no
   `onConflictDoNothing` — worked around by deleting stale `raw_records`
   rows for `source_id='tmdb'` in the scratch DB before re-running (safe,
   scratch-only; entities/credits/title_companies are all upsert-safe and
   unaffected). Not fixed — flagged as a real latent bug for whoever next
   touches raw-record ingestion idempotency.

## Session verification discipline (keep following this)

Every change in this whole effort followed: implement → `npx tsc --noEmit`
→ `npx vitest run` (full suite, always green before commit) → live-verify
against a real running API (`npx tsx src/index.ts` or `npx tsx watch
src/index.ts`, scratch DB, real credentials where relevant) → commit
(Conventional Commits style, `Co-Authored-By: Claude Sonnet 5
<noreply@anthropic.com>` trailer) → push → for review-comment events,
reply on each addressed inline GitHub thread and resolve it via GraphQL.
Don't skip steps to save time — this repo's reviewers (Codex + Copilot
bots) have caught 3 real bugs this session (entity-ID persistence mismatch
affecting *every* bundle-based adapter, an OPENAI_API_KEY silent-fallback
footgun, prompt injection via unescaped entity names in the system
prompt) that would have shipped otherwise.

## Resolved this session: box-office/budget, salaries, investors

The original ask — **"we need to test the hollywood side (movies,
producers, actors, box office numbers, budgets)"** — plus two live
follow-ups ("test the available financial data for movies, salaries etc."
and "finding movie investors") are all now resolved, in the sense of
"investigated live and either shipped or confirmed as a genuine gap":

- **Budget/revenue** (movie-level): shipped, commit `1f16f96`. See item 6
  above.
- **TV budget/revenue**: accepted gap — TMDb doesn't have it, Wikidata
  coverage is negligible (16 series total). See item 6 above.
- **Actor/producer salaries**: accepted gap — no structured source
  anywhere (TMDb: no field; Wikidata: 2 actors total). See item 7 above.
  Nothing to build here; don't revisit without a new data source idea.
- **Movie investors/financiers**: the literal "investor" concept is also
  an accepted gap (Wikidata near-empty/off-topic), but this led to a real
  shipped feature — **production-company capture**, including building
  out the previously-unused `title_companies` persistence path from
  scratch. See item 8 above for what shipped and how it was verified.

Scratch DB now has real film data (movies + a TV show, with production
companies) alongside the Spotify/music entities from before.

**No open question is currently blocking.** If picking this up fresh, the
natural next thing (not yet asked for) would be extending
`title_companies` usage to other adapters — confirmed by grep that
`spotify.ts` doesn't write to it either, despite `docs/unified-schema.md`'s
music-vertical section already describing a `relationship = 'label'` row
as the intended shape for label-distributes-release. `TitleCompanyRepository`
now exists and is reusable for that. But don't start it without the user
asking; there's no evidence it's wanted yet.

## Files worth re-reading in the new chat

- `docs/assistant.md` — architecture of the chat assistant + MCP server.
- `docs/unified-schema.md` — "Music vertical extension" (P0) and "Film
  vertical extension" (budget/revenue + production companies, both
  shipped this session) — read this first for the existing conventions.
- `api/src/ingest/adapters/tmdb.ts` — budget/revenue and production-company
  capture both shipped here; `normalizeTitle()` is the pattern to follow
  for any further film-vertical field.
- `api/src/ingest/models.ts` — `TitleCompanyRow` (new) alongside
  `CreditRow`/`EntityRow`; `NormalizedBundle` now has a `titleCompanies`
  field.
- `api/src/db/repositories/TitleCompanyRepository.ts` (new) — reusable
  persistence for any title↔company relationship, not just `production`.
- `api/src/db/services/IngestService.ts` — `upsertTitleCompanies()`
  wired into `applyBundle()`.
- `api/src/ingest/registry.ts` — `BUILTIN_SOURCES`, `apiKeyEnv` per source.
- `api/src/mcp/server.ts` + `docs/assistant.md`'s "MCP server" section —
  what's already built and tested for the chat-agent integration.
- `~/Developer/hollywood/.env` — `TMDB_API_KEY` is now set (confirmed).

## Open threads not otherwise captured above

- PR #6 is open, clean as of this session (checks not re-verified after
  the latest pushes — re-check `MERGEABLE`/`CLEAN` in a fresh chat before
  assuming), monitored — merge only if/when the user says to. Now
  contains 8 commits including budget/revenue and production-company
  capture.
- **Fixed (was a latent bug)**: `RawRecordRepository.insertBatch()` used a
  plain insert, so re-ingesting unchanged content (raw-record IDs are
  content-hash based, e.g. TMDb's trending list on the same day) threw
  `UNIQUE constraint failed: raw_records.id`. It now upserts and re-points
  the existing row's `runId`/`fetchedAt` at the new run — deliberately not
  `onConflictDoNothing`, because `runIngestSource` normalizes via
  `loadRawRecords({ runId })` and skipped rows would keep the old runId,
  making the new run silently normalize nothing. Covered by 2 new tests in
  `RawRecordRepository.test.ts`; live-verified by running TMDb ingest twice
  back to back against a fresh scratch DB (same normalized counts both times).
- Scratch-DB note: `/tmp/hollywood-test.db` got wiped between sessions;
  recreate by applying `api/drizzle/0000_yummy_captain_america.sql` (split
  on `--> statement-breakpoint`) — the server does not auto-migrate.
- P2 (a chat UI) was scoped but never started; the "where should it live
  in the hominem monorepo" question was dismissed earlier in an even
  prior session — worth checking if the user wants to revisit it, or has
  moved on.
- No rigorous A/B test exists comparing `gpt-4o-mini` vs `gpt-5.6-luna` for
  tool-calling reliability — two manual runs only, noted as unproven in
  `docs/assistant.md`'s "Known gaps" section, worth re-testing if
  reliability regresses.
- The Director agent itself still has no `search_entity_graph` tool (only
  the 4 sub-agents do) — never actually fixed, only incidentally masked by
  the model switch. Flagged, not resolved.
- `title_companies` is now wired up but only `tmdb.ts` writes to it
  (`relationship = 'production'`). `spotify.ts` still doesn't, despite
  `docs/unified-schema.md`'s music convention already describing a
  `relationship = 'label'` row as the intended shape — not started,
  no evidence the user wants it yet.
