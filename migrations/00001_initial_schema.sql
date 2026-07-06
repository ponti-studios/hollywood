-- +goose Up
-- +goose StatementBegin

-- =============================================================================
-- Pipeline runtime
-- =============================================================================

CREATE TABLE runs (
    id              TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,
    run_kind        TEXT NOT NULL,              -- ingest, extraction
    status          TEXT NOT NULL,              -- running, succeeded, failed
    options_json    TEXT,
    summary_json    TEXT,
    error_text      TEXT,
    started_at      TEXT NOT NULL,
    completed_at    TEXT
);

CREATE TABLE raw_records (
    id              TEXT PRIMARY KEY,
    run_id          TEXT REFERENCES runs(id),
    source_id       TEXT NOT NULL,
    source_kind     TEXT NOT NULL,              -- rss, api, dataset, browser, upload
    payload_type    TEXT NOT NULL,              -- feed_xml, article_html, api_json, application/pdf
    content_path    TEXT NOT NULL,
    content_hash    TEXT NOT NULL,
    content_type    TEXT,
    source_url      TEXT,
    canonical_url   TEXT,
    fetched_at      TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE extraction_results (
    id              TEXT PRIMARY KEY,
    document_id     TEXT NOT NULL REFERENCES raw_records(id),
    job_id          TEXT REFERENCES runs(id),
    schema_version  TEXT NOT NULL,
    prompt_version  TEXT NOT NULL,
    model_name      TEXT NOT NULL,
    status          TEXT NOT NULL,              -- succeeded, failed, partial
    raw_json        TEXT NOT NULL DEFAULT '',
    result_json     TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

-- =============================================================================
-- Entity graph
-- =============================================================================

CREATE TABLE entities (
    id              TEXT PRIMARY KEY,
    source_id       TEXT NOT NULL,
    external_id     TEXT,
    entity_type     TEXT NOT NULL,              -- person, company, title, organization, award
    name            TEXT NOT NULL,
    canonical_name  TEXT NOT NULL,
    bio             TEXT,
    position        TEXT,
    title_type      TEXT,                       -- movie, tv, novel, podcast
    format          TEXT,                       -- feature, series, limited
    company_type    TEXT,                       -- network, studio, agency, production_company
    status          TEXT NOT NULL DEFAULT 'active',
    license_class   TEXT NOT NULL,
    metadata_json   TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);

CREATE TABLE entity_aliases (
    id              TEXT PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    source_id       TEXT NOT NULL,
    alias           TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

CREATE TABLE entity_contacts (
    id              TEXT PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    source_id       TEXT NOT NULL,
    contact_type    TEXT NOT NULL,              -- email, phone, website
    contact_value   TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    created_at      TEXT NOT NULL
);

CREATE TABLE entity_links (
    id              TEXT PRIMARY KEY,
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    source_id       TEXT NOT NULL,
    url             TEXT NOT NULL,
    link_type       TEXT NOT NULL,              -- IMDB, Twitter, Instagram, LinkedIn, Wikipedia
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    created_at      TEXT NOT NULL
);

-- =============================================================================
-- Credits and relationships
-- =============================================================================

CREATE TABLE credits (
    id              TEXT PRIMARY KEY,
    person_id       TEXT NOT NULL REFERENCES entities(id),
    title_id        TEXT NOT NULL REFERENCES entities(id),
    company_id      TEXT REFERENCES entities(id),
    source_id       TEXT NOT NULL,
    role            TEXT NOT NULL,
    credit_type     TEXT NOT NULL,              -- cast, crew
    billing         INTEGER,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT,
    created_at      TEXT NOT NULL
);

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

-- =============================================================================
-- Submissions and deals
-- =============================================================================

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

-- =============================================================================
-- Articles and content
-- =============================================================================

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
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    source_id       TEXT NOT NULL,
    relation        TEXT NOT NULL,              -- author, subject, mentioned
    metadata_json   TEXT NOT NULL DEFAULT '{}'
);

-- =============================================================================
-- Provenance and trust
-- =============================================================================

CREATE TABLE source_facts (
    id              TEXT PRIMARY KEY,
    source_table    TEXT NOT NULL,
    source_row_id   TEXT NOT NULL,
    document_id     TEXT REFERENCES raw_records(id),
    extraction_id   TEXT REFERENCES extraction_results(id),
    json_path       TEXT,
    source_text     TEXT,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    confidence      TEXT NOT NULL DEFAULT 'machine_extracted',
    created_at      TEXT NOT NULL
);

-- =============================================================================
-- Tagging and dedup
-- =============================================================================

CREATE TABLE tags (
    id              TEXT PRIMARY KEY,
    tag             TEXT NOT NULL,
    normalized_tag  TEXT NOT NULL UNIQUE,
    created_at      TEXT NOT NULL
);

CREATE TABLE entity_taggings (
    id              TEXT PRIMARY KEY,
    tag_id          TEXT NOT NULL REFERENCES tags(id),
    entity_id       TEXT NOT NULL REFERENCES entities(id),
    source_id       TEXT NOT NULL,
    trust_state     TEXT NOT NULL DEFAULT 'machine_extracted',
    source_fact_id  TEXT REFERENCES source_facts(id),
    created_at      TEXT NOT NULL
);

CREATE TABLE merge_candidates (
    id              TEXT PRIMARY KEY,
    entity_a_id     TEXT NOT NULL REFERENCES entities(id),
    entity_b_id     TEXT NOT NULL REFERENCES entities(id),
    reason          TEXT NOT NULL,
    status          TEXT NOT NULL DEFAULT 'needs_review',
    created_at      TEXT NOT NULL
);

CREATE TABLE entity_merges (
    id              TEXT PRIMARY KEY,
    surviving_id    TEXT NOT NULL REFERENCES entities(id),
    merged_id       TEXT NOT NULL REFERENCES entities(id),
    reason          TEXT NOT NULL,
    created_at      TEXT NOT NULL
);

-- =============================================================================
-- Search
-- =============================================================================

CREATE VIRTUAL TABLE search_index USING fts5(
    entity_type,
    entity_id,
    name,
    body
);

-- =============================================================================
-- Indexes
-- =============================================================================

CREATE INDEX idx_runs_source ON runs(source_id, run_kind);
CREATE INDEX idx_runs_status ON runs(status);
CREATE INDEX idx_raw_records_run ON raw_records(run_id);
CREATE INDEX idx_raw_records_source ON raw_records(source_id);
CREATE INDEX idx_extraction_results_document ON extraction_results(document_id);
CREATE INDEX idx_entities_type ON entities(entity_type);
CREATE INDEX idx_entities_canonical ON entities(canonical_name);
CREATE INDEX idx_entities_external ON entities(external_id);
CREATE INDEX idx_entity_aliases_entity ON entity_aliases(entity_id);
CREATE INDEX idx_entity_contacts_entity ON entity_contacts(entity_id);
CREATE INDEX idx_entity_links_entity ON entity_links(entity_id);
CREATE INDEX idx_credits_person ON credits(person_id);
CREATE INDEX idx_credits_title ON credits(title_id);
CREATE INDEX idx_credits_company ON credits(company_id);
CREATE INDEX idx_title_companies_title ON title_companies(title_id);
CREATE INDEX idx_title_companies_company ON title_companies(company_id);
CREATE INDEX idx_representation_client ON representation(client_id);
CREATE INDEX idx_representation_rep ON representation(rep_id);
CREATE INDEX idx_collaborations_a ON collaborations(person_a_id);
CREATE INDEX idx_collaborations_b ON collaborations(person_b_id);
CREATE INDEX idx_submissions_document ON submissions(document_id);
CREATE INDEX idx_deals_person ON deals(person_id);
CREATE INDEX idx_deals_title ON deals(title_id);
CREATE INDEX idx_articles_source ON articles(source_id);
CREATE INDEX idx_articles_url ON articles(canonical_url);
CREATE INDEX idx_article_content_article ON article_content(article_id);
CREATE INDEX idx_article_entities_article ON article_entities(article_id);
CREATE INDEX idx_article_entities_entity ON article_entities(entity_id);
CREATE INDEX idx_source_facts_target ON source_facts(source_table, source_row_id);
CREATE INDEX idx_source_facts_trust ON source_facts(trust_state);
CREATE INDEX idx_entity_taggings_entity ON entity_taggings(entity_id);
CREATE INDEX idx_merge_candidates_status ON merge_candidates(status);

-- +goose StatementEnd

-- +goose Down
-- +goose StatementBegin
DROP TABLE IF EXISTS entity_merges;
DROP TABLE IF EXISTS merge_candidates;
DROP TABLE IF EXISTS entity_taggings;
DROP TABLE IF EXISTS tags;
DROP TABLE IF EXISTS source_facts;
DROP TABLE IF EXISTS article_entities;
DROP TABLE IF EXISTS article_content;
DROP TABLE IF EXISTS articles;
DROP TABLE IF EXISTS deals;
DROP TABLE IF EXISTS submissions;
DROP TABLE IF EXISTS collaborations;
DROP TABLE IF EXISTS representation;
DROP TABLE IF EXISTS title_companies;
DROP TABLE IF EXISTS credits;
DROP TABLE IF EXISTS entity_links;
DROP TABLE IF EXISTS entity_contacts;
DROP TABLE IF EXISTS entity_aliases;
DROP TABLE IF EXISTS entities;
DROP TABLE IF EXISTS extraction_results;
DROP TABLE IF EXISTS raw_records;
DROP TABLE IF EXISTS runs;
DROP TABLE IF EXISTS search_index;
-- +goose StatementEnd
