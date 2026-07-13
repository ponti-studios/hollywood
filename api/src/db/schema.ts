import { sqliteTable, text, integer, real, type AnySQLiteColumn } from "drizzle-orm/sqlite-core";

// ── Pipeline: bronze (raw ingestion) ─────────────────────────────────────────

export const runs = sqliteTable("runs", {
  id: text("id").primaryKey(),
  sourceId: text("source_id").notNull(),
  runKind: text("run_kind").notNull(),
  status: text("status").notNull(),
  optionsJson: text("options_json"),
  summaryJson: text("summary_json"),
  errorText: text("error_text"),
  startedAt: text("started_at").notNull(),
  completedAt: text("completed_at"),
});

export const rawRecords = sqliteTable("raw_records", {
  id: text("id").primaryKey(),
  runId: text("run_id").references(() => runs.id),
  sourceId: text("source_id").notNull(),
  sourceKind: text("source_kind").notNull(),
  payloadType: text("payload_type").notNull(),
  contentPath: text("content_path").notNull(),
  contentHash: text("content_hash").notNull(),
  contentType: text("content_type"),
  sourceUrl: text("source_url"),
  canonicalUrl: text("canonical_url"),
  fetchedAt: text("fetched_at").notNull(),
  metadataJson: text("metadata_json").notNull().default("{}"),
});

export const extractionResults = sqliteTable("extraction_results", {
  id: text("id").primaryKey(),
  documentId: text("document_id").notNull().references(() => rawRecords.id),
  jobId: text("job_id").references(() => runs.id),
  schemaVersion: text("schema_version").notNull(),
  promptVersion: text("prompt_version").notNull(),
  modelName: text("model_name").notNull(),
  status: text("status").notNull(),
  rawJson: text("raw_json").notNull().default(""),
  resultJson: text("result_json").notNull(),
  createdAt: text("created_at").notNull(),
});

export const sourceFacts = sqliteTable("source_facts", {
  id: text("id").primaryKey(),
  sourceTable: text("source_table").notNull(),
  sourceRowId: text("source_row_id").notNull(),
  documentId: text("document_id").references(() => rawRecords.id),
  extractionId: text("extraction_id").references(() => extractionResults.id),
  jsonPath: text("json_path"),
  sourceText: text("source_text"),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  confidence: text("confidence").notNull().default("machine_extracted"),
  createdAt: text("created_at").notNull(),
});

// ── Pipeline: silver (entity resolution) ─────────────────────────────────────

export const entities = sqliteTable("entities", {
  id: text("id").primaryKey(),
  sourceId: text("source_id").notNull(),
  externalId: text("external_id"),
  entityType: text("entity_type").notNull(),
  name: text("name").notNull(),
  canonicalName: text("canonical_name").notNull(),
  bio: text("bio"),
  position: text("position"),
  titleType: text("title_type"),
  format: text("format"),
  companyType: text("company_type"),
  status: text("status").notNull().default("active"),
  licenseClass: text("license_class").notNull(),
  metadataJson: text("metadata_json").notNull().default("{}"),
  canonicalId: text("canonical_id"),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
});

export const entityMatchDecisions = sqliteTable("entity_match_decisions", {
  id: text("id").primaryKey(),
  entityAId: text("entity_a_id").notNull().references(() => entities.id),
  entityBId: text("entity_b_id").notNull().references(() => entities.id),
  entityType: text("entity_type").notNull(),
  decision: text("decision").notNull(),
  confidence: real("confidence"),
  reason: text("reason").notNull(),
  decidedBy: text("decided_by").notNull(),
  decidedAt: text("decided_at").notNull(),
  createdAt: text("created_at").notNull(),
});

// ── Pipeline: silver (staged relationship facts) ─────────────────────────────

export const stagedFacts = sqliteTable("staged_facts", {
  id: text("id").primaryKey(),
  factType: text("fact_type").notNull(),
  entityRefsJson: text("entity_refs_json").notNull(),
  payloadJson: text("payload_json").notNull(),
  status: text("status").notNull().default("pending"),
  materializedTable: text("materialized_table"),
  materializedRowId: text("materialized_row_id"),
  sourceId: text("source_id").notNull(),
  documentId: text("document_id").references(() => rawRecords.id),
  extractionId: text("extraction_id").references(() => extractionResults.id),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
});

// ── Gold: core entities ───────────────────────────────────────────────────────

export const people = sqliteTable("people", {
  id: text("id").primaryKey(),
  sourceId: text("source_id").notNull(),
  externalId: text("external_id"),
  name: text("name").notNull(),
  canonicalName: text("canonical_name").notNull(),
  bio: text("bio"),
  birthYear: integer("birth_year"),
  deathYear: integer("death_year"),
  primaryProfession: text("primary_profession"),
  wgaStatus: text("wga_status"),
  sagStatus: text("sag_status"),
  status: text("status").notNull().default("active"),
  licenseClass: text("license_class").notNull(),
  metadataJson: text("metadata_json").notNull().default("{}"),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
});

export const titles = sqliteTable("titles", {
  id: text("id").primaryKey(),
  sourceId: text("source_id").notNull(),
  externalId: text("external_id"),
  title: text("title").notNull(),
  canonicalName: text("canonical_name").notNull(),
  format: text("format").notNull(),
  genre: text("genre"),
  network: text("network"),
  seasonCount: integer("season_count"),
  episodeCount: integer("episode_count"),
  logline: text("logline"),
  synopsis: text("synopsis"),
  status: text("status").notNull().default("development"),
  premiereDate: text("premiere_date"),
  announcedDate: text("announced_date"),
  licenseClass: text("license_class").notNull(),
  metadataJson: text("metadata_json").notNull().default("{}"),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
});

export const companies = sqliteTable("companies", {
  id: text("id").primaryKey(),
  sourceId: text("source_id").notNull(),
  externalId: text("external_id"),
  name: text("name").notNull(),
  canonicalName: text("canonical_name").notNull(),
  companyType: text("company_type").notNull(),
  parentCompanyId: text("parent_company_id").references((): AnySQLiteColumn => companies.id),
  status: text("status").notNull().default("active"),
  licenseClass: text("license_class").notNull(),
  metadataJson: text("metadata_json").notNull().default("{}"),
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
});

// ── Gold: join tables ─────────────────────────────────────────────────────────

export const credits = sqliteTable("credits", {
  id: text("id").primaryKey(),
  personId: text("person_id").notNull().references(() => people.id),
  titleId: text("title_id").notNull().references(() => titles.id),
  companyId: text("company_id").references(() => companies.id),
  role: text("role").notNull(),
  creditCategory: text("credit_category"),
  season: integer("season"),
  episodes: integer("episodes"),
  yearStart: integer("year_start"),
  yearEnd: integer("year_end"),
  network: text("network"),
  billing: integer("billing"),
  roomPosition: text("room_position"),
  contractType: text("contract_type"),
  active: integer("active").notNull().default(1),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id"),
  createdAt: text("created_at").notNull(),
});

export const representation = sqliteTable("representation", {
  id: text("id").primaryKey(),
  clientId: text("client_id").notNull().references(() => people.id),
  repId: text("rep_id").notNull().references(() => people.id),
  repCompanyId: text("rep_company_id").references(() => companies.id),
  repType: text("rep_type").notNull(),
  department: text("department"),
  title: text("title"),
  email: text("email"),
  phone: text("phone"),
  primaryRep: integer("primary_rep").notNull().default(0),
  coRep: integer("co_rep").notNull().default(0),
  dateStart: text("date_start"),
  dateEnd: text("date_end"),
  active: integer("active").notNull().default(1),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id"),
  createdAt: text("created_at").notNull(),
});

export const deals = sqliteTable("deals", {
  id: text("id").primaryKey(),
  dealType: text("deal_type").notNull(),
  personId: text("person_id").references(() => people.id),
  companyId: text("company_id").references(() => companies.id),
  titleId: text("title_id").references(() => titles.id),
  counterpartyId: text("counterparty_id").references(() => companies.id),
  status: text("status").notNull().default("negotiating"),
  compensationMin: integer("compensation_min"),
  compensationMax: integer("compensation_max"),
  backendPoints: real("backend_points"),
  optionPeriods: integer("option_periods"),
  exclusivity: text("exclusivity"),
  territory: text("territory"),
  dateSigned: text("date_signed"),
  dateStart: text("date_start"),
  dateEnd: text("date_end"),
  creditObligations: text("credit_obligations"),
  notes: text("notes"),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id"),
  createdAt: text("created_at").notNull(),
});

export const awards = sqliteTable("awards", {
  id: text("id").primaryKey(),
  awardName: text("award_name").notNull(),
  category: text("category").notNull(),
  year: integer("year").notNull(),
  personId: text("person_id").references(() => people.id),
  titleId: text("title_id").references(() => titles.id),
  outcome: text("outcome").notNull(),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id"),
  createdAt: text("created_at").notNull(),
});

// ── Gold: identity (polymorphic — entity_type + entity_id, no FK) ────────────

export const aliases = sqliteTable("aliases", {
  id: text("id").primaryKey(),
  entityType: text("entity_type").notNull(),
  entityId: text("entity_id").notNull(),
  sourceId: text("source_id").notNull(),
  alias: text("alias").notNull(),
  createdAt: text("created_at").notNull(),
});

export const contacts = sqliteTable("contacts", {
  id: text("id").primaryKey(),
  entityType: text("entity_type").notNull(),
  entityId: text("entity_id").notNull(),
  sourceId: text("source_id").notNull(),
  contactType: text("contact_type").notNull(),
  contactValue: text("contact_value").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  createdAt: text("created_at").notNull(),
});

export const links = sqliteTable("links", {
  id: text("id").primaryKey(),
  entityType: text("entity_type").notNull(),
  entityId: text("entity_id").notNull(),
  sourceId: text("source_id").notNull(),
  url: text("url").notNull(),
  linkType: text("link_type").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  createdAt: text("created_at").notNull(),
});

// ── Gold: submissions ─────────────────────────────────────────────────────────

export const submissions = sqliteTable("submissions", {
  id: text("id").primaryKey(),
  submittedByPerson: text("submitted_by_person").references(() => people.id),
  submittedByCompany: text("submitted_by_company").references(() => companies.id),
  submittedToPerson: text("submitted_to_person").references(() => people.id),
  submittedToCompany: text("submitted_to_company").references(() => companies.id),
  opportunityTitleId: text("opportunity_title_id").references(() => titles.id),
  role: text("role"),
  materialType: text("material_type"),
  purpose: text("purpose"),
  receivedAt: text("received_at"),
  outcome: text("outcome"),
  outcomeDate: text("outcome_date"),
  notes: text("notes"),
  documentId: text("document_id").references(() => rawRecords.id),
  extractionId: text("extraction_id").references(() => extractionResults.id),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  createdAt: text("created_at").notNull(),
});

// ── Gold: articles and content ────────────────────────────────────────────────

export const articles = sqliteTable("articles", {
  id: text("id").primaryKey(),
  sourceId: text("source_id").notNull(),
  canonicalUrl: text("canonical_url"),
  url: text("url").notNull(),
  title: text("title"),
  author: text("author"),
  publishedAt: text("published_at"),
  summary: text("summary"),
  feedGuid: text("feed_guid"),
  licenseClass: text("license_class").notNull(),
  runId: text("run_id").references(() => runs.id),
  metadataJson: text("metadata_json").notNull().default("{}"),
});

export const articleContent = sqliteTable("article_content", {
  id: text("id").primaryKey(),
  articleId: text("article_id").notNull().references(() => articles.id),
  sourceId: text("source_id").notNull(),
  contentKind: text("content_kind").notNull(),
  text: text("text").notNull(),
  rawRecordId: text("raw_record_id").references(() => rawRecords.id),
  contentHash: text("content_hash").notNull(),
  licenseClass: text("license_class").notNull(),
  metadataJson: text("metadata_json").notNull().default("{}"),
});

export const articleEntities = sqliteTable("article_entities", {
  id: text("id").primaryKey(),
  articleId: text("article_id").notNull().references(() => articles.id),
  entityType: text("entity_type").notNull(),
  entityId: text("entity_id").notNull(),
  sourceId: text("source_id").notNull(),
  relation: text("relation").notNull(),
  metadataJson: text("metadata_json").notNull().default("{}"),
});

// ── Gold: collaboration network ──────────────────────────────────────────────

export const collaborations = sqliteTable("collaborations", {
  id: text("id").primaryKey(),
  personAId: text("person_a_id").notNull().references(() => people.id),
  personBId: text("person_b_id").notNull().references(() => people.id),
  titleId: text("title_id").references(() => titles.id),
  relationship: text("relationship").notNull(),
  yearStart: integer("year_start"),
  yearEnd: integer("year_end"),
  projectCount: integer("project_count"),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id"),
  createdAt: text("created_at").notNull(),
});

export const companyRelations = sqliteTable("company_relations", {
  id: text("id").primaryKey(),
  companyAId: text("company_a_id").notNull().references(() => companies.id),
  entityType: text("entity_type").notNull(),
  entityId: text("entity_id").notNull(),
  relationship: text("relationship").notNull(),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id"),
  createdAt: text("created_at").notNull(),
});

// ── Gold: tagging ─────────────────────────────────────────────────────────────

export const tags = sqliteTable("tags", {
  id: text("id").primaryKey(),
  tag: text("tag").notNull(),
  normalizedTag: text("normalized_tag").notNull().unique(),
  createdAt: text("created_at").notNull(),
});

export const entityTaggings = sqliteTable("entity_taggings", {
  id: text("id").primaryKey(),
  tagId: text("tag_id").notNull().references(() => tags.id),
  entityType: text("entity_type").notNull(),
  entityId: text("entity_id").notNull(),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id").references(() => sourceFacts.id),
  createdAt: text("created_at").notNull(),
});
