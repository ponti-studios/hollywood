import { mkdirSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { getDb } from "../db/index.js";
import type { DbRow } from "../db/index.js";
import { makeStableId } from "./models.js";
import type {
  ArchivedPayload,
  ArticleContentRow,
  ArticleEntityRow,
  ArticleRow,
  CreditRow,
  EntityAliasRow,
  EntityRow,
  NormalizedBundle,
  RunStatus,
} from "./models.js";
import type { Candidate } from "./extraction.js";

function now(): string {
  return new Date().toISOString();
}

// ── Run tracking ─────────────────────────────────────────────────────────────

export function startRun(sourceId: string, optionsJson: string): string {
  const runId = makeStableId(sourceId, optionsJson, now());
  getDb()
    .prepare(
      `INSERT INTO runs (id, source_id, run_kind, status, started_at, options_json)
       VALUES (?, ?, 'ingest', ?, ?, ?)`,
    )
    .run(runId, sourceId, "running" satisfies RunStatus, now(), optionsJson);
  return runId;
}

export function finishRun(
  runId: string,
  status: RunStatus,
  summary: Record<string, unknown>,
  errorText?: string,
): void {
  getDb()
    .prepare(
      `UPDATE runs SET status = ?, completed_at = ?, summary_json = ?, error_text = ? WHERE id = ?`,
    )
    .run(status, now(), JSON.stringify(summary), errorText ?? null, runId);
}

export function startRunRaw(runKind: string, metadata: Record<string, unknown>): string {
  const runId = makeStableId(runKind, JSON.stringify(metadata), now());
  getDb()
    .prepare(
      `INSERT INTO runs (id, source_id, run_kind, status, started_at, options_json)
       VALUES (?, 'hollywood', ?, ?, ?, ?)`,
    )
    .run(runId, runKind, "running" satisfies RunStatus, now(), JSON.stringify(metadata));
  return runId;
}

export function insertExtractionRawRecord(
  runId: string,
  sourceId: string,
  contentPath: string,
  contentHash: string,
): string {
  const rawId = makeStableId("extraction_raw", runId, sourceId, contentHash);
  getDb()
    .prepare(
      `INSERT OR IGNORE INTO raw_records
       (id, run_id, source_id, source_kind, payload_type, content_path,
        content_hash, content_type, fetched_at)
       VALUES (?, ?, ?, 'upload', 'text/plain', ?, ?, 'text/plain', ?)`,
    )
    .run(rawId, runId, sourceId, contentPath, contentHash, now());
  return rawId;
}

export function saveExtractionResult(
  runId: string,
  sourceId: string,
  candidate: Candidate,
  modelName: string,
  promptVersion: string,
  rawJson: string,
  rawRecordId?: string,
): void {
  const docId = rawRecordId ?? runId;
  const resultId = makeStableId("extraction", docId, sourceId, candidate.name);
  getDb()
    .prepare(
      `INSERT OR REPLACE INTO extraction_results
       (id, document_id, job_id, schema_version, prompt_version, model_name,
        status, raw_json, result_json, created_at)
       VALUES (?, ?, ?, ?, ?, ?, 'succeeded', ?, ?, ?)`,
    )
    .run(
      resultId,
      docId,
      runId,
      "v1_submission_packet",
      promptVersion,
      modelName,
      rawJson,
      JSON.stringify(candidate),
      now(),
    );
}

export function materializeCandidate(
  candidate: Candidate,
  sourceId = "llm_extraction",
): string {
  const ts = now();
  const db = getDb();
  const entityId = makeStableId("entity", sourceId, candidate.name);

  db.prepare(
    `INSERT OR IGNORE INTO entities
     (id, source_id, entity_type, name, canonical_name, bio, position,
      status, license_class, created_at, updated_at)
     VALUES (?, ?, 'person', ?, ?, ?, ?, 'active', 'public', ?, ?)`,
  ).run(entityId, sourceId, candidate.name, candidate.name.toLowerCase(), candidate.bio, candidate.position ?? "", ts, ts);

  const aliasId = makeStableId("alias", entityId, candidate.name);
  db.prepare(
    `INSERT OR IGNORE INTO entity_aliases (id, entity_id, source_id, alias, created_at)
     VALUES (?, ?, ?, ?, ?)`,
  ).run(aliasId, entityId, sourceId, candidate.name, ts);

  if (candidate.email) {
    const emailId = makeStableId("contact", entityId, candidate.email);
    db.prepare(
      `INSERT OR IGNORE INTO entity_contacts (id, entity_id, source_id, contact_type, contact_value, created_at)
       VALUES (?, ?, ?, 'email', ?, ?)`,
    ).run(emailId, entityId, sourceId, candidate.email, ts);
  }

  if (candidate.phone_number) {
    const phoneId = makeStableId("contact", entityId, candidate.phone_number);
    db.prepare(
      `INSERT OR IGNORE INTO entity_contacts (id, entity_id, source_id, contact_type, contact_value, created_at)
       VALUES (?, ?, ?, 'phone', ?, ?)`,
    ).run(phoneId, entityId, sourceId, candidate.phone_number, ts);
  }

  for (const c of candidate.credits) {
    const titleId = makeStableId("entity", sourceId, c.production);
    db.prepare(
      `INSERT OR IGNORE INTO entities
       (id, source_id, entity_type, name, canonical_name, title_type, status, license_class, created_at, updated_at)
       VALUES (?, ?, 'title', ?, ?, 'tv', 'active', 'public', ?, ?)`,
    ).run(titleId, sourceId, c.production, c.production.toLowerCase(), ts, ts);

    const creditId = makeStableId("credit", entityId, titleId, c.role);
    db.prepare(
      `INSERT OR IGNORE INTO credits (id, person_id, title_id, source_id, role, credit_type, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?)`,
    ).run(creditId, entityId, titleId, sourceId, c.role, c.type || "crew", ts);
  }

  for (const org of candidate.organizations) {
    const orgId = makeStableId("entity", sourceId, org.name);
    db.prepare(
      `INSERT OR IGNORE INTO entities
       (id, source_id, entity_type, name, canonical_name, company_type, status, license_class, created_at, updated_at)
       VALUES (?, ?, 'company', ?, ?, ?, 'active', 'public', ?, ?)`,
    ).run(orgId, sourceId, org.name, org.name.toLowerCase(), org.type || "organization", ts, ts);
  }

  for (const tagText of candidate.tags) {
    const norm = tagText.toLowerCase().replace(/ /g, "_");
    const tagId = makeStableId("tag", tagText);
    db.prepare(
      `INSERT OR IGNORE INTO tags (id, tag, normalized_tag, created_at) VALUES (?, ?, ?, ?)`,
    ).run(tagId, tagText, norm, ts);
    const existingTag = db.prepare("SELECT id FROM tags WHERE normalized_tag = ?").get(norm) as { id: string } | undefined;
    const actualTagId = existingTag?.id ?? tagId;
    const taggingId = makeStableId("tagging", entityId, tagText);
    db.prepare(
      `INSERT OR IGNORE INTO entity_taggings (id, tag_id, entity_id, source_id, created_at)
       VALUES (?, ?, ?, ?, ?)`,
    ).run(taggingId, actualTagId, entityId, sourceId, ts);
  }

  for (const link of candidate.links) {
    const linkId = makeStableId("link", entityId, link.url);
    db.prepare(
      `INSERT OR IGNORE INTO entity_links (id, entity_id, source_id, url, link_type, created_at)
       VALUES (?, ?, ?, ?, ?, ?)`,
    ).run(linkId, entityId, sourceId, link.url, link.type, ts);
  }

  for (const rep of candidate.representatives) {
    const repEntityId = makeStableId("entity", sourceId, rep.name);
    db.prepare(
      `INSERT OR IGNORE INTO entities
       (id, source_id, entity_type, name, canonical_name, company_type, status, license_class, created_at, updated_at)
       VALUES (?, ?, 'person', ?, ?, 'agent', 'active', 'public', ?, ?)`,
    ).run(repEntityId, sourceId, rep.name, rep.name.toLowerCase(), ts, ts);

    const repRelId = makeStableId("rep", entityId, repEntityId);
    db.prepare(
      `INSERT OR IGNORE INTO representation
       (id, client_id, rep_id, rep_type, title, email, phone, source_id, trust_state, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'machine_extracted', ?)`,
    ).run(repRelId, entityId, repEntityId, rep.title, rep.title, rep.email ?? "", rep.phone_number ?? "", sourceId, ts);
  }

  return entityId;
}

// ── Raw records ──────────────────────────────────────────────────────────────

export function insertRawRecords(runId: string, archivedPayloads: ArchivedPayload[]): void {
  const db = getDb();
  const stmt = db.prepare(
    `INSERT OR REPLACE INTO raw_records
     (id, run_id, source_id, source_kind, payload_type, content_path, content_hash,
      content_type, source_url, canonical_url, fetched_at, metadata_json)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  );
  for (const p of archivedPayloads) {
    stmt.run(
      p.rawRecordId,
      runId,
      p.sourceId,
      p.sourceKind,
      p.payloadType,
      p.contentPath,
      p.contentHash,
      p.contentType,
      p.sourceUrl ?? null,
      p.canonicalUrl ?? null,
      p.fetchedAt.toISOString(),
      p.metadataJson,
    );
  }
}

export function loadRawRecords(opts: { sourceId?: string; runId?: string } = {}): DbRow[] {
  const conditions: string[] = [];
  const params: unknown[] = [];
  if (opts.sourceId) {
    conditions.push("source_id = ?");
    params.push(opts.sourceId);
  }
  if (opts.runId) {
    conditions.push("run_id = ?");
    params.push(opts.runId);
  }
  let query = "SELECT * FROM raw_records";
  if (conditions.length) query += " WHERE " + conditions.join(" AND ");
  query += " ORDER BY fetched_at ASC";
  return getDb().prepare(query).all(...params) as DbRow[];
}

// ── Normalized bundle ────────────────────────────────────────────────────────

export function applyBundle(bundle: NormalizedBundle): void {
  upsertArticles(bundle.articles);
  upsertArticleContent(bundle.articleContent);
  upsertEntities(bundle.entities);
  upsertEntityAliases(bundle.entityAliases);
  upsertArticleEntities(bundle.articleEntities);
  upsertCredits(bundle.credits);
}

function dedupeById<T extends object>(rows: T[], idKey: keyof T): T[] {
  const seen = new Map<unknown, T>();
  for (const row of rows) seen.set(row[idKey], row);
  return [...seen.values()];
}

function upsertArticles(rows: ArticleRow[]): void {
  const deduped = dedupeById(rows, "articleId");
  if (!deduped.length) return;
  const stmt = getDb().prepare(
    `INSERT OR REPLACE INTO articles
     (id, source_id, canonical_url, url, title, author, published_at, summary, feed_guid, license_class, run_id, metadata_json)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  );
  for (const r of deduped) {
    stmt.run(
      r.articleId,
      r.sourceId,
      r.canonicalUrl,
      r.url,
      r.title,
      r.author ?? null,
      r.publishedAt?.toISOString() ?? null,
      r.summary ?? null,
      r.feedGuid ?? null,
      r.licenseClass,
      r.runId,
      r.metadataJson,
    );
  }
}

function upsertArticleContent(rows: ArticleContentRow[]): void {
  const deduped = dedupeById(rows, "contentId");
  if (!deduped.length) return;
  const stmt = getDb().prepare(
    `INSERT OR REPLACE INTO article_content
     (id, article_id, source_id, content_kind, text, raw_record_id, content_hash, license_class, metadata_json)
     VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`,
  );
  for (const r of deduped) {
    stmt.run(r.contentId, r.articleId, r.sourceId, r.contentKind, r.text, r.rawRecordId, r.contentHash, r.licenseClass, r.metadataJson);
  }
}

function upsertEntities(rows: EntityRow[]): void {
  const deduped = dedupeById(rows, "entityId");
  if (!deduped.length) return;
  const ts = now();
  const stmt = getDb().prepare(
    `INSERT OR REPLACE INTO entities
     (id, source_id, external_id, entity_type, name, canonical_name, status, license_class, metadata_json, created_at, updated_at)
     VALUES (?, ?, ?, ?, ?, ?, 'active', ?, ?, ?, ?)`,
  );
  for (const r of deduped) {
    stmt.run(r.entityId, r.sourceId, r.externalId ?? null, r.entityType, r.name, r.canonicalName, r.licenseClass, r.metadataJson, ts, ts);
  }
}

function upsertEntityAliases(rows: EntityAliasRow[]): void {
  const deduped = dedupeById(rows, "entityAliasId");
  if (!deduped.length) return;
  const ts = now();
  const stmt = getDb().prepare(
    `INSERT OR REPLACE INTO entity_aliases (id, entity_id, source_id, alias, created_at) VALUES (?, ?, ?, ?, ?)`,
  );
  for (const r of deduped) stmt.run(r.entityAliasId, r.entityId, r.sourceId, r.alias, ts);
}

function upsertArticleEntities(rows: ArticleEntityRow[]): void {
  const deduped = dedupeById(rows, "articleEntityId");
  if (!deduped.length) return;
  const stmt = getDb().prepare(
    `INSERT OR REPLACE INTO article_entities (id, article_id, entity_id, source_id, relation, metadata_json) VALUES (?, ?, ?, ?, ?, ?)`,
  );
  for (const r of deduped) stmt.run(r.articleEntityId, r.articleId, r.entityId, r.sourceId, r.relation, r.metadataJson);
}

function upsertCredits(rows: CreditRow[]): void {
  const deduped = dedupeById(rows, "creditId");
  if (!deduped.length) return;
  const ts = now();
  const stmt = getDb().prepare(
    `INSERT OR REPLACE INTO credits
     (id, person_id, title_id, source_id, role, credit_type, billing, trust_state, metadata_json, created_at)
     VALUES (?, ?, ?, ?, ?, 'cast', ?, 'machine_extracted', ?, ?)`,
  );
  for (const r of deduped) {
    stmt.run(r.creditId, r.personEntityId, r.titleEntityId, r.sourceId, r.role, r.billing ?? null, r.metadataJson, ts);
  }
}

// ── Counts / exports ─────────────────────────────────────────────────────────

export function tableCount(table: string): number {
  const row = getDb().prepare(`SELECT COUNT(*) as count FROM ${table}`).get() as { count: number };
  return row.count;
}

const EXPORTABLE_TABLES = [
  "runs",
  "raw_records",
  "articles",
  "article_content",
  "article_entities",
  "entities",
  "entity_aliases",
  "credits",
] as const;

export function exportTable(table: string, outputDir: string, format: "jsonl" | "parquet"): string {
  if (!EXPORTABLE_TABLES.includes(table as (typeof EXPORTABLE_TABLES)[number])) {
    throw new Error(`Unknown table: ${table}`);
  }
  if (format === "parquet") {
    throw new Error("parquet export is not yet supported in the TypeScript port; use format=jsonl");
  }
  mkdirSync(outputDir, { recursive: true });
  const path = resolve(outputDir, `${table}.jsonl`);
  const rows = getDb().prepare(`SELECT * FROM ${table}`).all() as DbRow[];
  const lines = rows.map((row) => JSON.stringify(row)).join("\n");
  writeFileSync(path, lines ? lines + "\n" : "");
  return path;
}

export function exportAll(outputDir: string, format: "jsonl" | "parquet"): string[] {
  return EXPORTABLE_TABLES.map((table) => exportTable(table, outputDir, format));
}
