import { sqliteTable, text, integer } from "drizzle-orm/sqlite-core";

// ── Pipeline runtime ─────────────────────────────────────────────────────────

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

// ── Entity graph ─────────────────────────────────────────────────────────────

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
  createdAt: text("created_at").notNull(),
  updatedAt: text("updated_at").notNull(),
});

export const entityAliases = sqliteTable("entity_aliases", {
  id: text("id").primaryKey(),
  entityId: text("entity_id").notNull().references(() => entities.id),
  sourceId: text("source_id").notNull(),
  alias: text("alias").notNull(),
  createdAt: text("created_at").notNull(),
});

export const entityContacts = sqliteTable("entity_contacts", {
  id: text("id").primaryKey(),
  entityId: text("entity_id").notNull().references(() => entities.id),
  sourceId: text("source_id").notNull(),
  contactType: text("contact_type").notNull(),
  contactValue: text("contact_value").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  createdAt: text("created_at").notNull(),
});

export const entityLinks = sqliteTable("entity_links", {
  id: text("id").primaryKey(),
  entityId: text("entity_id").notNull().references(() => entities.id),
  sourceId: text("source_id").notNull(),
  url: text("url").notNull(),
  linkType: text("link_type").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  createdAt: text("created_at").notNull(),
});

// ── Credits and relationships ────────────────────────────────────────────────

export const credits = sqliteTable("credits", {
  id: text("id").primaryKey(),
  personId: text("person_id").notNull().references(() => entities.id),
  titleId: text("title_id").notNull().references(() => entities.id),
  companyId: text("company_id").references(() => entities.id),
  sourceId: text("source_id").notNull(),
  role: text("role").notNull(),
  creditType: text("credit_type").notNull(),
  billing: integer("billing"),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id"),
  createdAt: text("created_at").notNull(),
});

export const titleCompanies = sqliteTable("title_companies", {
  id: text("id").primaryKey(),
  titleId: text("title_id").notNull().references(() => entities.id),
  companyId: text("company_id").notNull().references(() => entities.id),
  sourceId: text("source_id").notNull(),
  relationship: text("relationship").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id"),
  createdAt: text("created_at").notNull(),
});

export const representation = sqliteTable("representation", {
  id: text("id").primaryKey(),
  clientId: text("client_id").notNull().references(() => entities.id),
  repId: text("rep_id").notNull().references(() => entities.id),
  repCompanyId: text("rep_company_id").references(() => entities.id),
  repType: text("rep_type").notNull(),
  title: text("title"),
  email: text("email"),
  phone: text("phone"),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id"),
  createdAt: text("created_at").notNull(),
});

export const collaborations = sqliteTable("collaborations", {
  id: text("id").primaryKey(),
  personAId: text("person_a_id").notNull().references(() => entities.id),
  personBId: text("person_b_id").notNull().references(() => entities.id),
  titleId: text("title_id").references(() => entities.id),
  relationship: text("relationship").notNull(),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id"),
  createdAt: text("created_at").notNull(),
});

// ── Submissions and deals ────────────────────────────────────────────────────

export const submissions = sqliteTable("submissions", {
  id: text("id").primaryKey(),
  documentId: text("document_id").notNull().references(() => rawRecords.id),
  extractionId: text("extraction_id").notNull().references(() => extractionResults.id),
  submittedByPersonId: text("submitted_by_person_id").references(() => entities.id),
  submittedByCompanyId: text("submitted_by_company_id").references(() => entities.id),
  submittedToPersonId: text("submitted_to_person_id").references(() => entities.id),
  submittedToCompanyId: text("submitted_to_company_id").references(() => entities.id),
  opportunityTitleId: text("opportunity_title_id").references(() => entities.id),
  purpose: text("purpose"),
  receivedAt: text("received_at"),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  createdAt: text("created_at").notNull(),
});

export const deals = sqliteTable("deals", {
  id: text("id").primaryKey(),
  personId: text("person_id").references(() => entities.id),
  companyId: text("company_id").references(() => entities.id),
  titleId: text("title_id").references(() => entities.id),
  dealType: text("deal_type").notNull(),
  status: text("status").notNull().default("machine_extracted"),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id"),
  createdAt: text("created_at").notNull(),
});

// ── Articles and content ─────────────────────────────────────────────────────

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
  runId: text("run_id").notNull().references(() => runs.id),
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
  entityId: text("entity_id").notNull().references(() => entities.id),
  sourceId: text("source_id").notNull(),
  relation: text("relation").notNull(),
  metadataJson: text("metadata_json").notNull().default("{}"),
});

// ── Provenance and trust ─────────────────────────────────────────────────────

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

// ── Tagging and dedup ────────────────────────────────────────────────────────

export const tags = sqliteTable("tags", {
  id: text("id").primaryKey(),
  tag: text("tag").notNull(),
  normalizedTag: text("normalized_tag").notNull().unique(),
  createdAt: text("created_at").notNull(),
});

export const entityTaggings = sqliteTable("entity_taggings", {
  id: text("id").primaryKey(),
  tagId: text("tag_id").notNull().references(() => tags.id),
  entityId: text("entity_id").notNull().references(() => entities.id),
  sourceId: text("source_id").notNull(),
  trustState: text("trust_state").notNull().default("machine_extracted"),
  sourceFactId: text("source_fact_id").references(() => sourceFacts.id),
  createdAt: text("created_at").notNull(),
});

export const mergeCandidates = sqliteTable("merge_candidates", {
  id: text("id").primaryKey(),
  entityAId: text("entity_a_id").notNull().references(() => entities.id),
  entityBId: text("entity_b_id").notNull().references(() => entities.id),
  reason: text("reason").notNull(),
  status: text("status").notNull().default("needs_review"),
  createdAt: text("created_at").notNull(),
});

export const entityMerges = sqliteTable("entity_merges", {
  id: text("id").primaryKey(),
  survivingId: text("surviving_id").notNull().references(() => entities.id),
  mergedId: text("merged_id").notNull().references(() => entities.id),
  reason: text("reason").notNull(),
  createdAt: text("created_at").notNull(),
});
