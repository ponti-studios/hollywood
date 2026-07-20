import { eq } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';

import { getDrizzle } from '../index.js';
import { articles, articleContent, articleEntities, extractionResults } from '../schema.js';
import * as schema from '../schema.js';
import { makeStableId } from './EntityRepository.js';

type Db = BetterSQLite3Database<typeof schema>;

// Prefer the richest available content variant per article — lower index wins.
const CONTENT_KIND_PRIORITY = ['page_extract', 'feed_content', 'feed_description'];

export type ArticleFields = Omit<typeof articles.$inferInsert, 'id'> & { articleId: string };

export type ArticleContentFields = Omit<typeof articleContent.$inferInsert, 'id'> & {
  contentId: string;
};

export type ArticleEntityFields = Omit<typeof articleEntities.$inferInsert, 'id' | 'entityType'> & {
  articleEntityId: string;
};

export class ArticleRepository {
  constructor(private db: Db = getDrizzle()) {}

  /** Upsert (INSERT OR REPLACE) an article. */
  upsertArticle(fields: ArticleFields): void {
    this.db
      .insert(articles)
      .values({
        id: fields.articleId,
        sourceId: fields.sourceId,
        canonicalUrl: fields.canonicalUrl ?? null,
        url: fields.url,
        title: fields.title ?? null,
        author: fields.author ?? null,
        publishedAt: fields.publishedAt ?? null,
        summary: fields.summary ?? null,
        feedGuid: fields.feedGuid ?? null,
        runId: fields.runId,
        metadataJson: fields.metadataJson ?? '{}',
      })
      .onConflictDoUpdate({
        target: articles.id,
        set: {
          sourceId: fields.sourceId,
          canonicalUrl: fields.canonicalUrl ?? null,
          url: fields.url,
          title: fields.title ?? null,
          author: fields.author ?? null,
          publishedAt: fields.publishedAt ?? null,
          summary: fields.summary ?? null,
          feedGuid: fields.feedGuid ?? null,
          runId: fields.runId,
          metadataJson: fields.metadataJson ?? '{}',
        },
      })
      .run();
  }

  /** Batch upsert articles. */
  upsertArticles(rows: ArticleFields[]): void {
    for (const row of rows) this.upsertArticle(row);
  }

  /** Upsert article content. */
  upsertContent(fields: ArticleContentFields): void {
    this.db
      .insert(articleContent)
      .values({
        id: fields.contentId,
        articleId: fields.articleId,
        sourceId: fields.sourceId,
        contentKind: fields.contentKind,
        text: fields.text,
        rawRecordId: fields.rawRecordId ?? null,
        contentHash: fields.contentHash,
        metadataJson: fields.metadataJson ?? '{}',
      })
      .onConflictDoUpdate({
        target: articleContent.id,
        set: {
          articleId: fields.articleId,
          sourceId: fields.sourceId,
          contentKind: fields.contentKind,
          text: fields.text,
          rawRecordId: fields.rawRecordId ?? null,
          contentHash: fields.contentHash,
          metadataJson: fields.metadataJson ?? '{}',
        },
      })
      .run();
  }

  /** Batch upsert article content. */
  upsertContentBatch(rows: ArticleContentFields[]): void {
    for (const row of rows) this.upsertContent(row);
  }

  /** Link an entity to an article. */
  linkEntity(fields: ArticleEntityFields): void {
    const entityType = this.resolveEntityType(fields.entityId);
    this.db
      .insert(articleEntities)
      .values({
        id: fields.articleEntityId,
        articleId: fields.articleId,
        entityType,
        entityId: fields.entityId,
        sourceId: fields.sourceId,
        relation: fields.relation,
        metadataJson: fields.metadataJson ?? '{}',
      })
      .onConflictDoNothing()
      .run();
  }

  /** Look up which gold table an id belongs to. Returns "unknown" if not found. */
  private resolveEntityType(entityId: string): string {
    if (
      this.db
        .select({ id: schema.people.id })
        .from(schema.people)
        .where(eq(schema.people.id, entityId))
        .get()
    )
      return 'person';
    if (
      this.db
        .select({ id: schema.titles.id })
        .from(schema.titles)
        .where(eq(schema.titles.id, entityId))
        .get()
    )
      return 'title';
    if (
      this.db
        .select({ id: schema.companies.id })
        .from(schema.companies)
        .where(eq(schema.companies.id, entityId))
        .get()
    )
      return 'company';
    return 'unknown';
  }

  /** Find article by ID. */
  findArticleById(id: string) {
    return this.db.select().from(articles).where(eq(articles.id, id)).get() ?? null;
  }

  /** Find content for an article. */
  findContentByArticleId(articleId: string) {
    return this.db
      .select()
      .from(articleContent)
      .where(eq(articleContent.articleId, articleId))
      .all();
  }

  /** Find entities linked to an article. */
  findEntitiesByArticleId(articleId: string) {
    return this.db
      .select()
      .from(articleEntities)
      .where(eq(articleEntities.articleId, articleId))
      .all();
  }

  /** Find articles by source. */
  findBySource(sourceId: string) {
    return this.db
      .select()
      .from(articles)
      .where(eq(articles.sourceId, sourceId))
      .orderBy(articles.publishedAt)
      .all();
  }

  /**
   * Finds articles that haven't been LLM-extracted yet under the given
   * schema version, one row per article, picking the richest available
   * content variant (page_extract > feed_content > feed_description).
   *
   * Provenance is checked against `extraction_results.document_id`, which
   * has a hard FK to `raw_records.id` — so the check (and the returned
   * `rawRecordId`, for callers to save provenance against) uses the raw
   * record id of the selected content row, not the article id itself.
   * `feed_description`/`feed_content` for one article share the same
   * `rawRecordId`, which naturally keeps this one-check-per-article even
   * though multiple content rows can exist.
   */
  findUnextractedContent(
    schemaVersion: string,
    limit: number,
  ): Array<{ articleId: string; contentId: string; rawRecordId: string; text: string }> {
    const rows = this.db
      .select({
        articleId: articleContent.articleId,
        contentId: articleContent.id,
        contentKind: articleContent.contentKind,
        rawRecordId: articleContent.rawRecordId,
        text: articleContent.text,
      })
      .from(articleContent)
      .all();

    const bestByArticle = new Map<string, (typeof rows)[number]>();
    for (const row of rows) {
      if (!row.rawRecordId) continue;
      const existing = bestByArticle.get(row.articleId);
      const priority = CONTENT_KIND_PRIORITY.indexOf(row.contentKind);
      const existingPriority = existing
        ? CONTENT_KIND_PRIORITY.indexOf(existing.contentKind)
        : Infinity;
      const rank = priority === -1 ? CONTENT_KIND_PRIORITY.length : priority;
      const existingRank =
        existingPriority === -1 ? CONTENT_KIND_PRIORITY.length : existingPriority;
      if (!existing || rank < existingRank) bestByArticle.set(row.articleId, row);
    }

    const extractedDocumentIds = new Set(
      this.db
        .select({ documentId: extractionResults.documentId })
        .from(extractionResults)
        .where(eq(extractionResults.schemaVersion, schemaVersion))
        .all()
        .map((r) => r.documentId),
    );

    const result: Array<{
      articleId: string;
      contentId: string;
      rawRecordId: string;
      text: string;
    }> = [];
    for (const row of bestByArticle.values()) {
      if (extractedDocumentIds.has(row.rawRecordId!)) continue;
      result.push({
        articleId: row.articleId,
        contentId: row.contentId,
        rawRecordId: row.rawRecordId!,
        text: row.text,
      });
      if (result.length >= limit) break;
    }
    return result;
  }
}
