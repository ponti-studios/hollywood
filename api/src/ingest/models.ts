import { createHash } from "node:crypto";

// ── Helpers ──────────────────────────────────────────────────────────────────

const TRACKING_QUERY_KEYS = new Set([
  "fbclid",
  "gclid",
  "mc_cid",
  "mc_eid",
  "ref",
  "source",
  "utm_campaign",
  "utm_content",
  "utm_medium",
  "utm_source",
  "utm_term",
]);

export function makeStableId(...parts: string[]): string {
  const joined = parts.filter(Boolean).map((p) => p.trim()).join("::");
  return createHash("sha256").update(joined, "utf-8").digest("hex").slice(0, 24);
}

export function canonicalizeUrl(url: string): string {
  const split = new URL(url.trim());
  const query = [...split.searchParams.entries()].filter(
    ([key]) => !TRACKING_QUERY_KEYS.has(key.toLowerCase()),
  );
  const path = split.pathname.replace(/\/+$/, "") || "/";
  const qs = query.map(([k, v]) => `${k}=${v}`).join("&");
  return `${split.protocol.toLowerCase()}//${split.host.toLowerCase()}${path}${qs ? "&" + qs : ""}`;
}

export function normalizeWhitespace(text: string): string {
  return text.split(/\s+/).filter(Boolean).join(" ");
}

// ── Enums ────────────────────────────────────────────────────────────────────

export type SourceKind = "rss" | "api" | "dataset" | "browser";
export type LicenseClass =
  | "research_non_commercial"
  | "web_copyright"
  | "api_terms"
  | "public_knowledge";
export type EntityKind = "person" | "title" | "company" | "organization" | "award";
export type RunStatus = "running" | "succeeded" | "failed";

// ── Source definition ────────────────────────────────────────────────────────

export interface SourceDefinition {
  sourceId: string;
  name: string;
  kind: SourceKind;
  description: string;
  groups: readonly string[];
  defaultUrls: readonly string[];
  licenseClass: LicenseClass;
  archiveModes: readonly string[];
  fetchStrategy: string;
  rateLimitPerMinute?: number;
  apiKeyEnv?: string;
  defaultFullText: boolean;
  metadata: Record<string, unknown>;
}

export interface IngestOptions {
  limit?: number;
  since?: Date;
  fullText: boolean;
  prefixes?: string[];
}

export interface RawPayload {
  payloadType: string;
  logicalId: string;
  body: Buffer;
  contentType: string;
  sourceUrl?: string;
  canonicalUrl?: string;
  fetchedAt: Date;
  metadata: Record<string, unknown>;
  extension?: string;
}

export interface ArchivedPayload {
  rawRecordId: string;
  sourceId: string;
  sourceKind: string;
  payloadType: string;
  logicalId: string;
  contentPath: string;
  contentHash: string;
  contentType: string;
  sourceUrl?: string;
  canonicalUrl?: string;
  fetchedAt: Date;
  metadataJson: string;
}

// ── Normalized rows ──────────────────────────────────────────────────────────

export interface ArticleRow {
  articleId: string;
  sourceId: string;
  canonicalUrl: string;
  url: string;
  title: string;
  author?: string;
  publishedAt?: Date;
  summary?: string;
  feedGuid?: string;
  licenseClass: string;
  runId: string;
  metadataJson: string;
}

export interface ArticleContentRow {
  contentId: string;
  articleId: string;
  sourceId: string;
  contentKind: string;
  text: string;
  rawRecordId: string;
  contentHash: string;
  licenseClass: string;
  metadataJson: string;
}

export interface EntityRow {
  entityId: string;
  sourceId: string;
  externalId?: string;
  entityType: string;
  name: string;
  canonicalName: string;
  licenseClass: string;
  metadataJson: string;
}

export interface EntityAliasRow {
  entityAliasId: string;
  entityId: string;
  sourceId: string;
  alias: string;
}

export interface ArticleEntityRow {
  articleEntityId: string;
  articleId: string;
  entityId: string;
  sourceId: string;
  relation: string;
  metadataJson: string;
}

export interface CreditRow {
  creditId: string;
  sourceId: string;
  personEntityId?: string;
  titleEntityId?: string;
  role: string;
  billing?: number;
  metadataJson: string;
}

export interface NormalizedBundle {
  articles: ArticleRow[];
  articleContent: ArticleContentRow[];
  entities: EntityRow[];
  entityAliases: EntityAliasRow[];
  articleEntities: ArticleEntityRow[];
  credits: CreditRow[];
}

export function emptyBundle(): NormalizedBundle {
  return { articles: [], articleContent: [], entities: [], entityAliases: [], articleEntities: [], credits: [] };
}

export function extendBundle(target: NormalizedBundle, other: NormalizedBundle): void {
  target.articles.push(...other.articles);
  target.articleContent.push(...other.articleContent);
  target.entities.push(...other.entities);
  target.entityAliases.push(...other.entityAliases);
  target.articleEntities.push(...other.articleEntities);
  target.credits.push(...other.credits);
}

export function bundleCounts(bundle: NormalizedBundle): Record<string, number> {
  return {
    articles: bundle.articles.length,
    article_content: bundle.articleContent.length,
    entities: bundle.entities.length,
    entity_aliases: bundle.entityAliases.length,
    article_entities: bundle.articleEntities.length,
    credits: bundle.credits.length,
  };
}

export interface RunSummary {
  runId: string;
  sourceId: string;
  status: RunStatus;
  rawRecords: number;
  normalized: Record<string, number>;
}

export interface DoctorCheck {
  name: string;
  ok: boolean;
  detail: string;
}
