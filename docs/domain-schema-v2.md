# Hollywood Domain Schema v2 — First Principles

> **Status (2026-07-13): the "Pipeline Tables" section below (`entities`,
> `entity_match_decisions`, `staged_facts`, `source_facts`) describes a
> resolution design that was never implemented. Those tables were removed
> from `schema.ts` and the live database on 2026-07-13 — see
> [`ingestion-pipeline-architecture.md`](./ingestion-pipeline-architecture.md)
> for the current MVP state (direct-write to gold, no resolution) and the
> design to resurrect from if/when it's needed. Sections 1–7 below (the
> `people`/`titles`/`companies`/join tables) are current.

The pipeline tables (`runs`, `raw_records`, `extraction_results`,
`source_facts`, `entities`, `entity_match_decisions`, `staged_facts`) are
intentionally omitted from the domain model below. They live in a separate
namespace — implementation detail of how data enters the system and gets
resolved into canonical records, not the domain model itself. See
**Pipeline Tables** near the end for how `entities` (one row per source
observation) resolves into `people`/`titles`/`companies` (one row per
real-world thing) via a `canonical_id` crosswalk, and how relationship facts
(credits, deals, etc.) stage in `staged_facts` until their referenced
entities resolve. Full job/orchestration design lives in
[`ingestion-pipeline-architecture.md`](./ingestion-pipeline-architecture.md).

---

## 1. Core Entity Tables

Rows here are golden records — populated by the entity resolution pipeline
(see **Pipeline Tables** below), not written directly by ingest.

### people

```sql
CREATE TABLE people (
    id              TEXT PRIMARY KEY,          -- stable SHA-256 hash
    source_id       TEXT NOT NULL,              -- variety, tmdb, wga, hollywood-api
    external_id     TEXT,                       -- TMDB person_id, IMDb nconst, Wikidata Q_id
    name            TEXT NOT NULL,
    canonical_name  TEXT NOT NULL,              -- casefolded for dedup
    bio             TEXT,
    birth_year      INTEGER,
    death_year      INTEGER,
    primary_profession TEXT,                    -- writer, producer, director, agent, etc.
    wga_status      TEXT,                       -- active, inactive, non_member
    sag_status      TEXT,                       -- active, inactive, non_member
    status          TEXT NOT NULL DEFAULT 'active',
    license_class   TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
```

Why separate from titles/companies:
- Professional credentials (WGA/SAG status) are person-specific
- Birth/death years don't apply to titles or companies
- No entity_type discriminator needed — every row is a person
- FK from credits.person_id can only point to people

### titles

```sql
CREATE TABLE titles (
    id              TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,
    external_id     TEXT,                       -- TMDB title_id, IMDb ttconst
    title           TEXT NOT NULL,
    canonical_name  TEXT NOT NULL,
    format          TEXT NOT NULL,              -- series, limited, feature, pilot, documentary, miniseries
    genre           TEXT,                       -- drama, comedy, thriller, etc.
    network         TEXT,                       -- CBS, Netflix, FX, Apple TV+
    season_count    INTEGER,
    episode_count   INTEGER,
    logline         TEXT,
    synopsis        TEXT,
    status          TEXT NOT NULL DEFAULT 'development',
                                                -- development, greenlit, production, aired, cancelled
    premiere_date   TEXT,
    announced_date  TEXT,
    license_class   TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
```

Title status values:
- `development` — being pitched, writers attached
- `greenlit` — formally ordered
- `production` — actively filming
- `aired` — released (one season or complete)
- `cancelled` — stopped before/during/after

Why separate from people/companies:
- Format, genre, network, season/episode counts are title-specific
- Logline/synopsis have no parallel in people or companies
- Title lifecycle (development → greenlit → production → aired → cancelled)
  is fundamentally different from a person's career status

### companies

```sql
CREATE TABLE companies (
    id              TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,
    external_id     TEXT,
    name            TEXT NOT NULL,
    canonical_name  TEXT NOT NULL,
    company_type    TEXT NOT NULL,              -- studio, network, streamer, prod_co,
                                                -- agency, mgmt_co, PR_firm, law_firm,
                                                -- financier, distributor
    parent_company_id TEXT REFERENCES companies(id),
    status          TEXT NOT NULL DEFAULT 'active',
    license_class   TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
```

Company type values:
- `studio` — Warner Bros, Disney, Sony, Universal, Paramount
- `network` — CBS, NBC, ABC, Fox, CW
- `streamer` — Netflix, Apple TV+, Amazon, Hulu, Max, Peacock
- `prod_co` — production company (Bad Robot, heckstall, etc.)
- `agency` — CAA, WME, Gersh, A3, UTA
- `mgmt_co` — management firm (Entertainment 360, etc.)
- `PR_firm` — public relations
- `law_firm` — entertainment law
- `financier` — financing entities
- `distributor` — distribution companies

---

## 2. Join Tables

### credits — person to title

```sql
CREATE TABLE credits (
    id              TEXT PRIMARY KEY,
    person_id       TEXT NOT NULL REFERENCES people(id),
    title_id        TEXT NOT NULL REFERENCES titles(id),
    company_id      TEXT REFERENCES companies(id),
    role            TEXT NOT NULL,              -- writer, executive producer, director, showrunner,
                                                -- co-executive producer, producer, consulting producer,
                                                -- staff writer, story editor, actor
    credit_category TEXT,                       -- staff_writer, freelance, room_writer, overall
    season          INTEGER,                    -- which season
    episodes        INTEGER,                    -- how many episodes
    year_start      INTEGER,                    -- start year
    year_end        INTEGER,                    -- end year (nullable, multi-year)
    network         TEXT,                       -- CBS, Netflix, FX (if different from title network)
    billing         INTEGER,                    -- credit order
    room_position   TEXT,                       -- showrunner, co-exec, producer, staff_writer
    contract_type   TEXT,                       -- WGA, non-WGA, overall, step, development
    active          INTEGER NOT NULL DEFAULT 1, -- boolean: is this credit still current
    source_id       TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT,
    created_at      TEXT NOT NULL
);
```

What this has that the current schema doesn't:
- `credit_category` — distinguishes staff writer from freelance from room writer
- `season` + `episodes` — which season, how many episodes
- `year_start` + `year_end` — when the credit spans (e.g., 2020–2023)
- `network` — the specific network/platform for this credit (Apple TV+ for the title,
  but this credit might be specifically for CBS)
- `room_position` — specific writers' room position
- `contract_type` — WGA vs non-WGA, overall deal attachment, step deal
- `active` — is this credit current (person still on the show)

### representation — person to person (agent, manager, lawyer)

```sql
CREATE TABLE representation (
    id              TEXT PRIMARY KEY,
    client_id       TEXT NOT NULL REFERENCES people(id),
    rep_id          TEXT NOT NULL REFERENCES people(id),
    rep_company_id  TEXT REFERENCES companies(id),
    rep_type        TEXT NOT NULL,              -- agent, manager, lawyer, publicist,
                                                -- assistant, business_manager
    department      TEXT,                       -- tv literary, talent, below-the-line,
                                                -- motion picture literary, digital
    title           TEXT,                       -- partner, senior agent, associate
    email           TEXT,
    phone           TEXT,
    primary_rep     INTEGER NOT NULL DEFAULT 0, -- boolean
    co_rep          INTEGER NOT NULL DEFAULT 0, -- boolean (co-rep with another agency)
    date_start      TEXT,
    date_end        TEXT,                       -- null = current
    active          INTEGER NOT NULL DEFAULT 1, -- boolean
    source_id       TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT,
    created_at      TEXT NOT NULL
);
```

What this has that the current schema doesn't:
- `department` — specific division within the agency
- `primary_rep` — only one primary rep per type; the rest are secondary
- `co_rep` — shared representation (e.g., co-rep with another agency for packaging)
- `date_start` — when this representation relationship began
- `date_end` — when it ended (null = current)
- `active` — quick filter for current representation

### deals — person/company to company/title (with terms)

```sql
CREATE TABLE deals (
    id                TEXT PRIMARY KEY,
    deal_type         TEXT NOT NULL,            -- overall, first_look, development, step,
                                                -- shopping, option, pay_or_play, producer,
                                                -- adaptation, consulting, holding
    person_id         TEXT REFERENCES people(id),
    company_id        TEXT REFERENCES companies(id),
    title_id          TEXT REFERENCES titles(id),
    counterparty_id   TEXT REFERENCES companies(id),  -- studio/network on the other side
    status            TEXT NOT NULL DEFAULT 'negotiating',
                                                -- negotiating, signed, completed,
                                                -- lapsed, cancelled
    compensation_min  INTEGER,                  -- annual guarantee floor (USD)
    compensation_max  INTEGER,                  -- annual ceiling (USD)
    backend_points    REAL,                     -- profit participation percentage
    option_periods    INTEGER,                  -- number of option periods
    exclusivity       TEXT,                     -- full, tv_only, streaming_only, none
    territory         TEXT,                     -- worldwide, US, North America
    date_signed       TEXT,
    date_start        TEXT,
    date_end          TEXT,
    credit_obligations TEXT,                    -- EP, consulting producer, etc.
    notes             TEXT,
    source_id         TEXT NOT NULL,
    trust_state       TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id    TEXT,
    created_at        TEXT NOT NULL
);
```

Deal type values:
- `overall` — exclusive multi-year deal with a studio/network
- `first_look` — right of first refusal on new projects
- `development` — develop specific project(s)
- `step` — step-by-step deal (bible → script → pilot)
- `shopping` — temporary rights to shop a project
- `option` — option agreement (with option periods)
- `pay_or_play` — guaranteed payment whether project happens
- `producer` — producing deal
- `adaptation` — rights to adapt source material
- `consulting` — consulting arrangement
- `holding` — holding deal (exclusive, no guaranteed production)

What this has that the current schema doesn't:
- `counterparty_id` — explicitly models both sides of the deal
- `compensation_min` + `compensation_max` — money ranges
- `backend_points` — profit participation
- `option_periods` — number of option renewals
- `exclusivity` — scope of exclusivity
- `territory` — geographic scope
- `date_signed`, `date_start`, `date_end` — full date tracking
- `credit_obligations` — what credits the deal requires
- `notes` — free-text for deal terms that don't fit columns

### awards — person or title to award

```sql
CREATE TABLE awards (
    id              TEXT PRIMARY KEY,
    award_name      TEXT NOT NULL,              -- Emmy, WGA Award, Golden Globe, Oscar, PGA, DGA, SAG
    category        TEXT NOT NULL,              -- Outstanding Drama Series,
                                                -- Best Writing for a Drama Series,
                                                -- Best Television Series – Drama
    year            INTEGER NOT NULL,
    person_id       TEXT REFERENCES people(id),
    title_id        TEXT REFERENCES titles(id),
    outcome         TEXT NOT NULL,              -- won, nominated
    source_id       TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT,
    created_at      TEXT NOT NULL
);
```

New table — no equivalent in current schema.

---

## 3. Name and Identity Tables

### aliases — all entity types (people, titles, companies)

```sql
CREATE TABLE aliases (
    id              TEXT PRIMARY KEY,
    entity_type     TEXT NOT NULL,              -- person, title, company
    entity_id       TEXT NOT NULL,              -- FK to people/titles/companies depending on entity_type
    source_id       TEXT NOT NULL,
    alias           TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
```

This replaces `entity_aliases`. The `entity_type` + `entity_id` pattern is one
of the few places where a polymorphic FK is acceptable — aliases are purely
for search/discovery and don't carry domain logic.

Alternatively: three separate tables (`person_aliases`, `title_aliases`,
`company_aliases`) for full referential integrity. The single table with
`entity_type` is a pragmatic compromise for search.

### contacts — contact info for people and companies

```sql
CREATE TABLE contacts (
    id              TEXT PRIMARY KEY,
    entity_type     TEXT NOT NULL,              -- person, company
    entity_id       TEXT NOT NULL,
    source_id       TEXT NOT NULL,
    contact_type    TEXT NOT NULL,              -- email, phone, website
    contact_value   TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    created_at      TEXT NOT NULL
);
```

This replaces `entity_contacts`. Same polymorphic pattern — contacts apply to
people (personal email, phone) and companies (general office line, HR email).

### links — external URLs for all entity types

```sql
CREATE TABLE links (
    id              TEXT PRIMARY KEY,
    entity_type     TEXT NOT NULL,              -- person, title, company
    entity_id       TEXT NOT NULL,
    source_id       TEXT NOT NULL,
    url             TEXT NOT NULL,
    link_type       TEXT NOT NULL,              -- IMDB, Twitter, Instagram, LinkedIn,
                                                -- Wikipedia, Website, Facebook, TikTok
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    created_at      TEXT NOT NULL
);
```

This replaces `entity_links`. Same pattern.

---

## 4. Submissions (first-class domain entity)

The current schema makes `submissions` a child of the data pipeline
(`document_id` and `extraction_id` are NOT NULL). A submission is a real-world
action — someone sends material to someone else for a role or opportunity.
It should be independent of how data entered the system.

```sql
CREATE TABLE submissions (
    id                    TEXT PRIMARY KEY,
    submitted_by_person   TEXT REFERENCES people(id),
    submitted_by_company  TEXT REFERENCES companies(id),
    submitted_to_person   TEXT REFERENCES people(id),
    submitted_to_company  TEXT REFERENCES companies(id),
    opportunity_title_id  TEXT REFERENCES titles(id),
    role                  TEXT,                  -- "writer", "showrunner", "actor", "director"
    material_type         TEXT,                  -- script, bible, packet, tape, treatment, sizzle
    purpose               TEXT,                  -- "open_writing_assignment", "general_consideration",
                                                  -- "staffing", "pilot_season", "replacement"
    received_at           TEXT,
    outcome               TEXT,                  -- pending, passed, interested, meeting_requested,
                                                  -- developing, hired
    outcome_date          TEXT,
    notes                 TEXT,
    -- Optional links to pipeline (for tracking provenance of discovered submissions)
    document_id           TEXT REFERENCES raw_records(id),
    extraction_id         TEXT REFERENCES extraction_results(id),
    source_id             TEXT NOT NULL,
    trust_state           TEXT NOT NULL DEFAULT 'machine_extracted',
    created_at            TEXT NOT NULL
);
```

Key changes from current:
- `document_id` and `extraction_id` are optional (nullable) — a submission can
  exist without being discovered through extraction
- Added `role` — specific role they were submitted for
- Added `material_type` — what was submitted
- Added `outcome` — what happened
- Added `outcome_date` — when
- Added `note`s — free-text
- Removed the implicit `projectId = "default"` hack from the route

---

## 5. Articles (minor adjustments)

Articles stay mostly the same, with two changes:
- `run_id` becomes optional (an article can exist independently of an ingest run)
- `article_entities` FKs point to `people.id` / `titles.id` / `companies.id`
  instead of `entities.id`

```sql
CREATE TABLE articles (
    id              TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,
    canonical_url   TEXT,
    url             TEXT NOT NULL,
    title           TEXT,
    author          TEXT,
    published_at    TEXT,
    summary         TEXT,
    feed_guid       TEXT,
    license_class   TEXT NOT NULL,
    run_id          TEXT REFERENCES runs(id),   -- now nullable
    metadata_json   TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE article_content (
    id              TEXT PRIMARY KEY,
    article_id      TEXT NOT NULL REFERENCES articles(id),
    source_id       TEXT NOT NULL,
    content_kind    TEXT NOT NULL,              -- feed_description, feed_content, page_extract
    text            TEXT NOT NULL,
    raw_record_id   TEXT REFERENCES raw_records(id),
    content_hash    TEXT NOT NULL,
    license_class   TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE article_entities (
    id              TEXT PRIMARY KEY,
    article_id      TEXT NOT NULL REFERENCES articles(id),
    entity_type     TEXT NOT NULL,              -- person, title, company
    entity_id       TEXT NOT NULL,              -- FK to people/titles/companies
    source_id       TEXT NOT NULL,
    relation        TEXT NOT NULL,              -- author, subject, mentioned
    metadata_json   TEXT NOT NULL DEFAULT '{}'
);
```

---

## 6. Collaboration Network

### collaborations — person to person

```sql
CREATE TABLE collaborations (
    id              TEXT PRIMARY KEY,
    person_a_id     TEXT NOT NULL REFERENCES people(id),
    person_b_id     TEXT NOT NULL REFERENCES people(id),
    title_id        TEXT REFERENCES titles(id),
    relationship    TEXT NOT NULL,              -- worked_together, room_mates,
                                                -- mentor_mentee, writer_director
    year_start      INTEGER,
    year_end        INTEGER,
    project_count   INTEGER,                    -- how many projects they've done together
    source_id       TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT,
    created_at      TEXT NOT NULL
);
```

### company_relations — company to title or company (extends current `title_companies`)

```sql
CREATE TABLE company_relations (
    id              TEXT PRIMARY KEY,
    company_a_id    TEXT NOT NULL REFERENCES companies(id),
    entity_type     TEXT NOT NULL,              -- title, company
    entity_id       TEXT NOT NULL,              -- FK to titles or companies
    relationship    TEXT NOT NULL,              -- production, distribution, network, streaming,
                                                -- parent, subsidiary, division, agency_client
    source_id       TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT,
    created_at      TEXT NOT NULL
);
```

This replaces `title_companies` and extends it to include company-to-company
relationships (parent/subsidiary, agency/client firm).

---

## 7. Tagging

Tags stay flat for now. The only change is the FK in `entity_taggings`.

```sql
CREATE TABLE tags (
    id              TEXT PRIMARY KEY,
    tag             TEXT NOT NULL,
    normalized_tag  TEXT NOT NULL UNIQUE,
    created_at      TEXT NOT NULL
);

CREATE TABLE entity_taggings (
    id              TEXT PRIMARY KEY,
    tag_id          TEXT NOT NULL REFERENCES tags(id),
    entity_type     TEXT NOT NULL,              -- person, title, company
    entity_id       TEXT NOT NULL,
    source_id       TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT REFERENCES source_facts(id),
    created_at      TEXT NOT NULL
);
```

---

## Pipeline Tables

A separate namespace from the domain model — data provenance, ingestion
tracking, and entity resolution. `runs`, `raw_records`, `extraction_results`,
and `source_facts` stay exactly as they are in the current schema. `entities`
is changed (adds `canonical_id`), and `entity_match_decisions` +
`staged_facts` are new, described below. See
[`ingestion-pipeline-architecture.md`](./ingestion-pipeline-architecture.md)
for the full bronze/silver/gold pipeline and the jobs that move data between
these tables.

### entities — one row per source observation (staging, not domain)

```sql
CREATE TABLE entities (
    id              TEXT PRIMARY KEY,          -- stable SHA-256 hash
    source_id       TEXT NOT NULL,
    external_id     TEXT,
    entity_type     TEXT NOT NULL,              -- person, title, company
    name            TEXT NOT NULL,
    canonical_name  TEXT NOT NULL,              -- casefolded, used for blocking
    bio             TEXT,
    position        TEXT,
    title_type      TEXT,
    format          TEXT,
    company_type    TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    license_class   TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    canonical_id    TEXT,                       -- FK to people/titles/companies(id)
                                                -- by entity_type; null = unresolved
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
```

This is today's `entities` table plus one column: `canonical_id`. Every row
ingest produces lands here first — one row per source observation, never
deduped in place. `canonical_id` is the crosswalk: null until resolution
runs, then it points directly at the golden record in
`people`/`titles`/`companies` (chosen by `entity_type`). Two `entities` rows
from different sources describing the same real person both end up with the
same `canonical_id` — that's what makes them "the same person" downstream.

### entity_match_decisions — append-only match log (replaces merge_candidates and entity_merges)

```sql
CREATE TABLE entity_match_decisions (
    id              TEXT PRIMARY KEY,
    entity_a_id     TEXT NOT NULL REFERENCES entities(id),
    entity_b_id     TEXT NOT NULL REFERENCES entities(id),
    entity_type     TEXT NOT NULL,              -- must match entity_type on both sides
    decision        TEXT NOT NULL,              -- match, no_match, needs_review
    confidence      REAL,                       -- match score, if machine-scored
    reason          TEXT NOT NULL,              -- blocking key / rule that surfaced this pair
    decided_by      TEXT NOT NULL,              -- 'system:<job>' or reviewer id
    decided_at      TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
```

Never updated — every decision, including a reviewer overturning a prior
one, is a new row. This is the audit trail: "what did we conclude about this
pair, when, by whom." It replaces both `merge_candidates` and the old
pairwise `entity_merges` design (a pairwise repoint-on-confirm approach is
prone to transitive over-merging — see
[`ingestion-pipeline-architecture.md`](./ingestion-pipeline-architecture.md)
for why). `entities.canonical_id` is *derived* from this log by a clustering
job, not written directly by decision review.

### staged_facts — relationship facts pending entity resolution (new)

```sql
CREATE TABLE staged_facts (
    id                   TEXT PRIMARY KEY,
    fact_type            TEXT NOT NULL,        -- credit, representation, deal,
                                                -- award, collaboration, submission
    entity_refs_json     TEXT NOT NULL,        -- {"person_id": "<entities.id>", ...}
    payload_json         TEXT NOT NULL,        -- fact-type-specific fields
    status               TEXT NOT NULL DEFAULT 'pending',
                                                -- pending, materialized, unresolvable
    materialized_table    TEXT,                 -- e.g. 'credits', set once promoted
    materialized_row_id   TEXT,                 -- id of the row created in the gold table
    source_id            TEXT NOT NULL,
    document_id           TEXT REFERENCES raw_records(id),
    extraction_id         TEXT REFERENCES extraction_results(id),
    trust_state           TEXT NOT NULL DEFAULT 'machine_extracted',
    created_at            TEXT NOT NULL,
    updated_at            TEXT NOT NULL
);
```

A credit extracted from a document names people and titles by their
`entities.id`, not by a golden id — those may not have resolved yet, or may
resolve in a later batch. `staged_facts` holds the fact until every entity it
references has a `canonical_id`, at which point a materialization job
promotes it into the matching gold join table. The gold tables'
`source_fact_id` column (see Join Tables above) points at `staged_facts.id`
once materialized — `source_facts` remains for provenance outside this
fact-type family (tags, article entities).

Full resolution and materialization mechanics — the clustering job, the
materialization job, idempotency and incremental-processing rules — are in
[`ingestion-pipeline-architecture.md`](./ingestion-pipeline-architecture.md).

---

## Summary of table count

| Layer | Tables |
|---|---|
| Core entities | `people`, `titles`, `companies` (3) |
| Join tables | `credits`, `representation`, `deals`, `awards` (4) |
| Identity | `aliases`, `contacts`, `links` (3) |
| Submissions | `submissions` (1) |
| Articles | `articles`, `article_content`, `article_entities` (3) |
| Network | `collaborations`, `company_relations` (2) |
| Tags | `tags`, `entity_taggings` (2) |
| Pipeline | `runs`, `raw_records`, `extraction_results`, `source_facts`, `entities`, `entity_match_decisions`, `staged_facts` (7) |
| **Total** | **25** (vs 21 today — adds `people`, `titles`, `companies`, `awards`, `aliases`, `contacts`, `links`, `company_relations`, `staged_facts`; removes `entity_aliases`, `entity_contacts`, `entity_links`, `title_companies`, `merge_candidates` (folded into `entity_match_decisions`); `entities` stays as a staging table with `canonical_id` added; `deals` and `submissions` restructured) |
