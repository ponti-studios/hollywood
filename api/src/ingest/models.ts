import { createHash } from 'node:crypto';

import type { EntityFields } from '../db/repositories/EntityRepository.js';
import type { RunStatus } from '../db/repositories/RunRepository.js';
import type {
  articles,
  articleContent,
  articleEntities,
  credits,
  aliases,
  rawRecords,
} from '../db/schema.js';

// ── Helpers ──────────────────────────────────────────────────────────────────

const TRACKING_QUERY_KEYS = new Set([
  'fbclid',
  'gclid',
  'mc_cid',
  'mc_eid',
  'ref',
  'source',
  'utm_campaign',
  'utm_content',
  'utm_medium',
  'utm_source',
  'utm_term',
]);

export function makeStableId(...parts: string[]): string {
  const joined = parts
    .filter(Boolean)
    .map((p) => p.trim())
    .join('::');
  return createHash('sha256').update(joined, 'utf-8').digest('hex').slice(0, 24);
}

export function canonicalizeUrl(url: string): string {
  const split = new URL(url.trim());
  const query = [...split.searchParams.entries()].filter(
    ([key]) => !TRACKING_QUERY_KEYS.has(key.toLowerCase()),
  );
  const path = split.pathname.replace(/\/+$/, '') || '/';
  const qs = query.map(([k, v]) => `${k}=${v}`).join('&');
  return `${split.protocol.toLowerCase()}//${split.host.toLowerCase()}${path}${qs ? '&' + qs : ''}`;
}

export function normalizeWhitespace(text: string): string {
  return text.split(/\s+/).filter(Boolean).join(' ');
}

// ── Enums ────────────────────────────────────────────────────────────────────

type SourceKind = 'rss' | 'api' | 'dataset' | 'browser';
type LicenseClass =
  | 'research_non_commercial'
  | 'web_copyright'
  | 'api_terms'
  | 'public_knowledge';
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

/**
 * Pre-`raw_records` archival result. Mirrors the `raw_records` table
 * (via `$inferInsert`) except for `logicalId` (a dedup key that's never
 * persisted) and `fetchedAt`/`contentType` (required here; the row is only
 * ever constructed with both already resolved).
 */
export type ArchivedPayload = Omit<
  typeof rawRecords.$inferInsert,
  'id' | 'runId' | 'contentType' | 'fetchedAt' | 'metadataJson'
> & {
  rawRecordId: string;
  logicalId: string;
  contentType: string;
  fetchedAt: Date;
  metadataJson: string;
};

// ── Normalized rows ──────────────────────────────────────────────────────────
// These mirror the `articles`/`article_content`/`article_entities`/`credits`
// gold tables via `$inferInsert`, tightened to the subset of fields adapters
// actually populate (narrower optionality than the DB allows) and renamed
// where the pipeline hasn't resolved a DB primary key yet (e.g. `*EntityId`
// suffixes on `CreditRow` — these are adapter-generated stable ids, not
// guaranteed-persisted `people`/`titles` rows, until `IngestService` writes
// them).

export type ArticleRow = Omit<
  typeof articles.$inferInsert,
  'id' | 'canonicalUrl' | 'title' | 'runId' | 'metadataJson' | 'publishedAt'
> & {
  articleId: string;
  canonicalUrl: string;
  title: string;
  runId: string;
  metadataJson: string;
  publishedAt?: Date;
};

export type ArticleContentRow = Omit<
  typeof articleContent.$inferInsert,
  'id' | 'rawRecordId' | 'metadataJson'
> & {
  contentId: string;
  rawRecordId: string;
  metadataJson: string;
};

export type EntityRow = Pick<
  EntityFields,
  'sourceId' | 'externalId' | 'entityType' | 'name' | 'canonicalName' | 'titleType'
> & {
  entityId: string;
  metadataJson: string;
};

export type EntityAliasRow = Pick<
  typeof aliases.$inferInsert,
  'entityId' | 'sourceId' | 'alias'
> & {
  entityAliasId: string;
};

export type ArticleEntityRow = Omit<
  typeof articleEntities.$inferInsert,
  'id' | 'entityType' | 'metadataJson'
> & {
  articleEntityId: string;
  metadataJson: string;
};

export type CreditRow = Pick<
  typeof credits.$inferInsert,
  'role' | 'sourceId' | 'creditCategory'
> & {
  creditId: string;
  personEntityId?: string;
  titleEntityId?: string;
  billing?: number;
  metadataJson: string;
};

export interface NormalizedBundle {
  articles: ArticleRow[];
  articleContent: ArticleContentRow[];
  entities: EntityRow[];
  entityAliases: EntityAliasRow[];
  articleEntities: ArticleEntityRow[];
  credits: CreditRow[];
}

export function emptyBundle(): NormalizedBundle {
  return {
    articles: [],
    articleContent: [],
    entities: [],
    entityAliases: [],
    articleEntities: [],
    credits: [],
  };
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
  entitiesMatched: number;
  entitiesCreated: number;
}

export interface DoctorCheck {
  name: string;
  ok: boolean;
  detail: string;
}
