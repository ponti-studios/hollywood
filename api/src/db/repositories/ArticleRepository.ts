import { getDrizzle } from "../index.js";
import { articles, articleContent, articleEntities } from "../schema.js";
import { eq } from "drizzle-orm";
import type { BetterSQLite3Database } from "drizzle-orm/better-sqlite3";
import * as schema from "../schema.js";
import { makeStableId } from "./EntityRepository.js";

type Db = BetterSQLite3Database<typeof schema>;

export interface ArticleFields {
  articleId: string;
  sourceId: string;
  canonicalUrl?: string | null;
  url: string;
  title?: string | null;
  author?: string | null;
  publishedAt?: string | null;
  summary?: string | null;
  feedGuid?: string | null;
  licenseClass: string;
  runId: string;
  metadataJson?: string;
}

export interface ArticleContentFields {
  contentId: string;
  articleId: string;
  sourceId: string;
  contentKind: string;
  text: string;
  rawRecordId?: string | null;
  contentHash: string;
  licenseClass: string;
  metadataJson?: string;
}

export interface ArticleEntityFields {
  articleEntityId: string;
  articleId: string;
  entityId: string;
  sourceId: string;
  relation: string;
  metadataJson?: string;
}

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
        licenseClass: fields.licenseClass,
        runId: fields.runId,
        metadataJson: fields.metadataJson ?? "{}",
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
          licenseClass: fields.licenseClass,
          runId: fields.runId,
          metadataJson: fields.metadataJson ?? "{}",
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
        licenseClass: fields.licenseClass,
        metadataJson: fields.metadataJson ?? "{}",
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
          licenseClass: fields.licenseClass,
          metadataJson: fields.metadataJson ?? "{}",
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
        metadataJson: fields.metadataJson ?? "{}",
      })
      .onConflictDoNothing()
      .run();
  }

  /** Look up which gold table an id belongs to. Defaults to "person" if not found. */
  private resolveEntityType(entityId: string): string {
    if (this.db.select({ id: schema.people.id }).from(schema.people).where(eq(schema.people.id, entityId)).get()) return "person";
    if (this.db.select({ id: schema.titles.id }).from(schema.titles).where(eq(schema.titles.id, entityId)).get()) return "title";
    if (this.db.select({ id: schema.companies.id }).from(schema.companies).where(eq(schema.companies.id, entityId)).get()) return "company";
    return "person";
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
}
