import { randomUUID } from 'node:crypto';

import { eq } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';

import { getDrizzle } from '../index.js';
import { extractionResults } from '../schema.js';
import * as schema from '../schema.js';

type Db = BetterSQLite3Database<typeof schema>;

export type ExtractionFields = Omit<typeof extractionResults.$inferInsert, 'id' | 'createdAt'> & {
  id?: string;
};

export class ExtractionRepository {
  constructor(private db: Db = getDrizzle()) {}

  /** Save an extraction result. */
  save(fields: ExtractionFields): string {
    const id = fields.id ?? randomUUID();
    const now = new Date().toISOString();
    this.db
      .insert(extractionResults)
      .values({
        id,
        documentId: fields.documentId,
        jobId: fields.jobId ?? null,
        schemaVersion: fields.schemaVersion,
        promptVersion: fields.promptVersion,
        modelName: fields.modelName,
        status: fields.status,
        rawJson: fields.rawJson,
        resultJson: fields.resultJson,
        createdAt: now,
      })
      .onConflictDoUpdate({
        target: extractionResults.id,
        set: {
          documentId: fields.documentId,
          jobId: fields.jobId ?? null,
          schemaVersion: fields.schemaVersion,
          promptVersion: fields.promptVersion,
          modelName: fields.modelName,
          status: fields.status,
          rawJson: fields.rawJson,
          resultJson: fields.resultJson,
        },
      })
      .run();
    return id;
  }

  /** Find an extraction result by ID. */
  findById(id: string) {
    return (
      this.db.select().from(extractionResults).where(eq(extractionResults.id, id)).get() ?? null
    );
  }

  /** Find extraction results for a document. */
  findByDocumentId(documentId: string) {
    return this.db
      .select()
      .from(extractionResults)
      .where(eq(extractionResults.documentId, documentId))
      .orderBy(extractionResults.createdAt)
      .all();
  }

  /** Find extraction results for a job. */
  findByJobId(jobId: string) {
    return this.db
      .select()
      .from(extractionResults)
      .where(eq(extractionResults.jobId, jobId))
      .orderBy(extractionResults.createdAt)
      .all();
  }
}
