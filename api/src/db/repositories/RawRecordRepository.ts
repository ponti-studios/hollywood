import { eq, and } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';

import { getDrizzle } from '../index.js';
import { rawRecords } from '../schema.js';
import * as schema from '../schema.js';

type Db = BetterSQLite3Database<typeof schema>;

export type RawRecordInsert = typeof rawRecords.$inferInsert;
export type RawRecordRow = typeof rawRecords.$inferSelect;

export class RawRecordRepository {
  constructor(private db: Db = getDrizzle()) {}

  /** Insert a batch of raw records. */
  insertBatch(records: RawRecordInsert[]): void {
    if (!records.length) return;
    const stmt = this.db.insert(rawRecords).values(
      records.map((r) => ({
        id: r.id,
        runId: r.runId,
        sourceId: r.sourceId,
        sourceKind: r.sourceKind,
        payloadType: r.payloadType,
        contentPath: r.contentPath,
        contentHash: r.contentHash,
        contentType: r.contentType ?? null,
        sourceUrl: r.sourceUrl ?? null,
        canonicalUrl: r.canonicalUrl ?? null,
        fetchedAt: r.fetchedAt,
        metadataJson: r.metadataJson,
      })),
    );
    stmt.run();
  }

  /** Insert a single raw record (upsert). */
  insertOne(record: RawRecordInsert): void {
    this.db
      .insert(rawRecords)
      .values({
        id: record.id,
        runId: record.runId,
        sourceId: record.sourceId,
        sourceKind: record.sourceKind,
        payloadType: record.payloadType,
        contentPath: record.contentPath,
        contentHash: record.contentHash,
        contentType: record.contentType ?? null,
        sourceUrl: record.sourceUrl ?? null,
        canonicalUrl: record.canonicalUrl ?? null,
        fetchedAt: record.fetchedAt,
        metadataJson: record.metadataJson,
      })
      .run();
  }

  /** Find a raw record by ID. */
  findById(id: string) {
    return this.db.select().from(rawRecords).where(eq(rawRecords.id, id)).get() ?? null;
  }

  /** Find raw records by run ID. */
  findByRunId(runId: string) {
    return this.db
      .select()
      .from(rawRecords)
      .where(eq(rawRecords.runId, runId))
      .orderBy(rawRecords.fetchedAt)
      .all();
  }

  /** Find raw records by source ID. */
  findBySourceId(sourceId: string) {
    return this.db
      .select()
      .from(rawRecords)
      .where(eq(rawRecords.sourceId, sourceId))
      .orderBy(rawRecords.fetchedAt)
      .all();
  }

  /** Find raw records filtered by source and/or run. */
  find(opts: { sourceId?: string; runId?: string } = {}) {
    const conditions: ReturnType<typeof eq>[] = [];
    if (opts.sourceId) conditions.push(eq(rawRecords.sourceId, opts.sourceId));
    if (opts.runId) conditions.push(eq(rawRecords.runId, opts.runId));
    let query = this.db.select().from(rawRecords);
    if (conditions.length) query = query.where(and(...conditions)) as typeof query;
    return query.orderBy(rawRecords.fetchedAt).all();
  }
}
