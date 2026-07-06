# Hollywood Unified Schema

Single SQLite database (`data/hollywood.db`) replacing kuma's `kuma.db` and
hollywood's `hollywood.duckdb`. One entertainment industry graph.

## Design Decisions

### SQLite over DuckDB

Corpus scale (~100K articles, ~500K entities, ~1M credits) fits easily in SQLite.
WAL mode handles concurrent reads + writes. FTS5 for full-text search. Goose for
migrations — same tooling as warehouse and ai-lab.

### Unified entities over separate tables

Kuma had separate `people`, `companies`, `projects` tables with parallel alias,
contact, and link tables ×3. Hollywood has a single `entities` table with an
`entity_type` column. The unified approach is cleaner for cross-referencing and
avoids schema duplication.

### Normalized over denormalized

The schema normalizes aggressively — separate tables for aliases, contacts, links,
credits, relationships. This is because the graph is built incrementally from
multiple sources (RSS feeds, TMDB, WGA, extraction pipeline) and the same entity
will be independently discovered by different sources. Merge candidates and
canonical resolution require fine-grained provenance.

---

## Schema

### Pipeline runtime

```sql
-- Ingest and extraction run tracking
CREATE TABLE runs (
    id              TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,              -- variety, tmdb, wga, extraction
    run_kind        TEXT NOT NULL,              -- ingest, extraction
    status          TEXT NOT NULL,              -- running, succeeded, failed
    options_json    TEXT,
    summary_json    TEXT,
    error_text      TEXT,
    started_at      TEXT NOT NULL,
    completed_at    TEXT
);

-- Raw fetched or uploaded payloads
CREATE TABLE raw_records (
    id              TEXT PRIMARY KEY,
    run_id          TEXT REFERENCES runs(id),
    source_id       TEXT NOT NULL,
    source_kind     TEXT NOT NULL,              -- rss, api, dataset, browser, upload
    payload_type    TEXT NOT NULL,              -- feed_xml, article_html, api_json, application/pdf
    content_path    TEXT NOT NULL,              -- filesystem path to raw file
    content_hash    TEXT NOT NULL,
    content_type    TEXT,
    source_url      TEXT,
    canonical_url   TEXT,
    fetched_at      TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}'
);

-- Extraction results from LLM processing
CREATE TABLE extraction_results (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES raw_records(id),
    job_id          TEXT REFERENCES runs(id),
    schema_version  TEXT NOT NULL,              -- schema version of the output contract
    prompt_version  TEXT NOT NULL,              -- prompt template version
    model_name      TEXT NOT NULL,
    status          TEXT NOT NULL,              -- succeeded, failed, partial
    raw_json        TEXT NOT NULL DEFAULT '',   -- raw LLM response
    result_json     TEXT NOT NULL,              -- validated + normalized output
    created_at      TEXT NOT NULL
);
```

### Entity graph

```sql
-- Universal entity table (people, companies, projects, awards, etc.)
CREATE TABLE entities (
    id              TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,              -- variety, tmdb, wga, extraction
    external_id     TEXT,                       -- TMDB person_id, IMDb tt_id, Wikidata Q_id
    entity_type     TEXT NOT NULL,              -- person, company, title, organization, award
    name            TEXT NOT NULL,
    canonical_name  TEXT NOT NULL,              -- casefolded for dedup
    -- Person fields
    bio             TEXT,
    position        TEXT,
    -- Title fields
    title_type      TEXT,                       -- movie, tv, novel, podcast
    format          TEXT,                       -- feature, series, limited
    -- Company fields
    company_type    TEXT,                       -- network, studio, agency, production_company, etc.
    -- General
    status          TEXT NOT NULL DEFAULT 'active',
    license_class   TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

-- Alternate names
CREATE TABLE entity_aliases (
    id              TEXT PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    source_id       TEXT NOT NULL,
    alias           TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

-- Contact info (emails, phones)
CREATE TABLE entity_contacts (
    id              TEXT PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    source_id       TEXT NOT NULL,
    contact_type    TEXT NOT NULL,              -- email, phone, website
    contact_value   TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    created_at      TEXT NOT NULL
);

-- External URLs
CREATE TABLE entity_links (
    id              TEXT PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    source_id       TEXT NOT NULL,
    url             TEXT NOT NULL,
    link_type       TEXT NOT NULL,              -- IMDB, Twitter, Instagram, LinkedIn, Wikipedia
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    created_at      TEXT NOT NULL
);
```

### Credits and relationships

```sql
-- Person credited on a title
CREATE TABLE credits (
    id              TEXT PRIMARY KEY,
    person_id       TEXT NOT NULL REFERENCES entities(id),
    title_id        TEXT NOT NULL REFERENCES entities(id),
    company_id      TEXT REFERENCES entities(id),  -- if credited through a company
    source_id       TEXT NOT NULL,
    role            TEXT NOT NULL,              -- writer, director, cast, producer
    credit_type     TEXT NOT NULL,              -- cast, crew
    billing         INTEGER,                    -- cast order
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT,
    created_at      TEXT NOT NULL
);

-- Company ↔ project relationships
CREATE TABLE title_companies (
    id              TEXT PRIMARY KEY,
    title_id        TEXT NOT NULL REFERENCES entities(id),
    company_id      TEXT NOT NULL REFERENCES entities(id),
    source_id       TEXT NOT NULL,
    relationship    TEXT NOT NULL,              -- production, distribution, network, streaming
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT,
    created_at      TEXT NOT NULL
);

-- Representation: agent/manager → client
CREATE TABLE representation (
    id              TEXT PRIMARY KEY,
    client_id       TEXT NOT NULL REFERENCES entities(id),
    rep_id          TEXT NOT NULL REFERENCES entities(id),
    rep_company_id  TEXT REFERENCES entities(id),
    rep_type        TEXT NOT NULL,              -- agent, manager, publicist, assistant
    title           TEXT,
    email           TEXT,
    phone           TEXT,
    source_id       TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT,
    created_at      TEXT NOT NULL
);

-- Collaboration: two people worked together
CREATE TABLE collaborations (
    id              TEXT PRIMARY KEY,
    person_a_id     TEXT NOT NULL REFERENCES entities(id),
    person_b_id     TEXT NOT NULL REFERENCES entities(id),
    title_id        TEXT REFERENCES entities(id),
    relationship    TEXT NOT NULL,
    source_id       TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT,
    created_at      TEXT NOT NULL
);
```

### Submissions and deals

```sql
-- Submission: a document contains candidate submissions
CREATE TABLE submissions (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES raw_records(id),
    extraction_id   TEXT NOT NULL REFERENCES extraction_results(id),
    submitted_by_person_id   TEXT REFERENCES entities(id),
    submitted_by_company_id  TEXT REFERENCES entities(id),
    submitted_to_person_id   TEXT REFERENCES entities(id),
    submitted_to_company_id  TEXT REFERENCES entities(id),
    opportunity_title_id     TEXT REFERENCES entities(id),
    purpose         TEXT,
    received_at     TEXT,
    source_id       TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    created_at      TEXT NOT NULL
);

-- Deals: person/company attached to a project
CREATE TABLE deals (
    id              TEXT PRIMARY KEY,
    person_id       TEXT REFERENCES entities(id),
    company_id      TEXT REFERENCES entities(id),
    title_id        TEXT REFERENCES entities(id),
    deal_type       TEXT NOT NULL,              -- development, production, attachment
    status          TEXT NOT NULL DEFAULT 'machine_extracted',
    source_id       TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT,
    created_at      TEXT NOT NULL
);
```

### Articles and content

```sql
-- Articles from RSS feeds and web scraping
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
    run_id          TEXT NOT NULL REFERENCES runs(id),
    metadata_json   TEXT NOT NULL DEFAULT '{}'
);

-- Text segments from articles (feed summary, feed content, scraped page)
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

-- Article ↔ entity links
CREATE TABLE article_entities (
    id              TEXT PRIMARY KEY,
    article_id      TEXT NOT NULL REFERENCES articles(id),
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    source_id       TEXT NOT NULL,
    relation        TEXT NOT NULL,              -- author, subject, mentioned
    metadata_json   TEXT NOT NULL DEFAULT '{}'
);
```

### Provenance and trust

```sql
-- Every fact in the graph has a source
CREATE TABLE source_facts (
    id              TEXT PRIMARY KEY,
    source_table    TEXT NOT NULL,              -- credits, representation, title_companies, etc.
    source_row_id   TEXT NOT NULL,              -- the row id in the source table
    document_id     TEXT REFERENCES raw_records(id),
    extraction_id   TEXT REFERENCES extraction_results(id),
    json_path       TEXT,                       -- path within extraction result JSON
    source_text     TEXT,                       -- the exact text that produced this fact
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    confidence      TEXT NOT NULL DEFAULT 'machine_extracted',
    created_at      TEXT NOT NULL
);
```

### Tagging and dedup

```sql
-- Tags
CREATE TABLE tags (
    id              TEXT PRIMARY KEY,
    tag             TEXT NOT NULL,
    normalized_tag  TEXT NOT NULL UNIQUE,
    created_at      TEXT NOT NULL
);

-- Entity ↔ tag
CREATE TABLE entity_taggings (
    id              TEXT PRIMARY KEY,
    tag_id          TEXT NOT NULL REFERENCES tags(id),
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    source_id       TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT REFERENCES source_facts(id),
    created_at      TEXT NOT NULL
);

-- Potential duplicate entities for review
CREATE TABLE merge_candidates (
    id              TEXT PRIMARY KEY,
    entity_a_id     TEXT NOT NULL REFERENCES entities(id),
    entity_b_id     TEXT NOT NULL REFERENCES entities(id),
    reason          TEXT NOT NULL,              -- name_match, external_id_match, contact_match
    status          TEXT NOT NULL DEFAULT 'needs_review',
    created_at      TEXT NOT NULL
);

-- Resolved merges
CREATE TABLE entity_merges (
    id              TEXT PRIMARY KEY,
    surviving_id    TEXT NOT NULL REFERENCES entities(id),
    merged_id       TEXT NOT NULL REFERENCES entities(id),
    reason          TEXT NOT NULL,
    created_at      TEXT NOT NULL
);
```

### Search

```sql
-- Full-text search across entities and articles
CREATE VIRTUAL TABLE search_index USING fts5(
    entity_type,    -- person, company, title
    entity_id,      -- references entities(id)
    name,           -- indexed text
    body            -- bio, summary, article text
);
```

---

## What Changed vs The Two Separate DBs

| Before | After |
|--------|-------|
| kuma: `people`, `companies`, `projects` × 3 (tables + aliases + contacts + links) | One `entities` table with `entity_type` |
| kuma: `credits` (person↔project↔company) | Same shape, added `credit_type` (cast/crew) from Hollywood |
| kuma: `project_companies`, `company_people`, `attachments` | Folded into `title_companies` and `credits` |
| Hollywood: `article_bodies` | Renamed `article_content` with `content_kind` |
| Hollywood: `source_runs` | Merged into `runs` with `run_kind` (ingest/extraction) |
| Both: separate DB files | One `data/hollywood.db` |
| kuma: `submissions`, `deals`, `representation`, `collaborations`, `tags` | Preserved as-is |
| kuma: `search_index`, `merge_candidates`, `entity_merges`, `source_facts` | Preserved as-is |

---

## Migration Steps

1. **Create the unified migration** — single 00001_initial_schema.sql in hollywood with all tables above
2. **Port kuma's extraction pipeline** — writes to `extraction_results`, pulls entities into `entities` table
3. **Port Hollywood's ingest flows** — writes `articles`, `article_content` (was `article_bodies`)
4. **Data migration** — SQL scripts to copy existing data from kuma's `kuma.db` into hollywood's `hollywood.db`:
   - `people`/`companies`/`projects` → `entities` (with entity_type)
   - Parallel alias/contact/link tables → unified tables
   - `credits`, `submissions`, etc. → same tables (new `source_id` column)
   - `articles`, `article_content` → from duckdb import
5. **Remove kuma's database code** — everything in `internal/database/` is dead after migration
6. **New kuma purpose** — TBD, separate initiative

## Decisions (Confirmed)

1. **Database location:** `~/.hominem/hollywood.db` — alongside warehouse.db and lab.db
2. **Surface:** API-only (FastAPI), not CLI-first. Prefect for async processing
3. **Migration tool:** Goose (same as warehouse, ai-lab)
4. **Naming:** `article_content` / `content_kind` replaces `article_bodies` / `body_kind`
