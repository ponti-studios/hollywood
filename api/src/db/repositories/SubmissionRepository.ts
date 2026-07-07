import { randomUUID } from "node:crypto";
import { getDrizzle } from "../index.js";
import { submissions } from "../schema.js";
import { eq } from "drizzle-orm";
import type { BetterSQLite3Database } from "drizzle-orm/better-sqlite3";
import * as schema from "../schema.js";

type Db = BetterSQLite3Database<typeof schema>;

export interface SubmissionFields {
  id?: string;
  documentId: string;
  extractionId: string;
  submittedByPersonId?: string | null;
  submittedByCompanyId?: string | null;
  submittedToPersonId?: string | null;
  submittedToCompanyId?: string | null;
  opportunityTitleId?: string | null;
  purpose?: string | null;
  receivedAt?: string | null;
  sourceId: string;
  trustState?: string;
}

export class SubmissionRepository {
  constructor(private db: Db = getDrizzle()) {}

  /** Insert a submission. */
  insert(fields: SubmissionFields): string {
    const id = fields.id ?? randomUUID();
    const now = new Date().toISOString();
    this.db
      .insert(submissions)
      .values({
        id,
        documentId: fields.documentId,
        extractionId: fields.extractionId,
        submittedByPersonId: fields.submittedByPersonId ?? null,
        submittedByCompanyId: fields.submittedByCompanyId ?? null,
        submittedToPersonId: fields.submittedToPersonId ?? null,
        submittedToCompanyId: fields.submittedToCompanyId ?? null,
        opportunityTitleId: fields.opportunityTitleId ?? null,
        purpose: fields.purpose ?? null,
        receivedAt: fields.receivedAt ?? null,
        sourceId: fields.sourceId,
        trustState: fields.trustState ?? "machine_extracted",
        createdAt: now,
      })
      .run();
    return id;
  }

  /** Find a submission by ID. */
  findById(id: string) {
    return this.db.select().from(submissions).where(eq(submissions.id, id)).get() ?? null;
  }

  /** List all submissions ordered by creation date descending. */
  findAll() {
    return this.db
      .select()
      .from(submissions)
      .orderBy(submissions.createdAt)
      .all();
  }

  /** Delete a submission by ID. Returns number of rows deleted. */
  delete(id: string): number {
    const result = this.db.delete(submissions).where(eq(submissions.id, id)).run();
    return result.changes;
  }

  /** Get a submission with its extraction result JSON, using a raw join query. */
  findWithExtraction(id: string) {
    return this.db
      .select({
        id: submissions.id,
        documentId: submissions.documentId,
        extractionId: submissions.extractionId,
        createdAt: submissions.createdAt,
        resultJson: schema.extractionResults.resultJson,
      })
      .from(submissions)
      .leftJoin(schema.extractionResults, eq(schema.extractionResults.id, submissions.extractionId))
      .where(eq(submissions.id, id))
      .get() ?? null;
  }

  /** List all submissions with their extraction result JSON. */
  findAllWithExtractions() {
    return this.db
      .select({
        id: submissions.id,
        documentId: submissions.documentId,
        extractionId: submissions.extractionId,
        createdAt: submissions.createdAt,
        resultJson: schema.extractionResults.resultJson,
      })
      .from(submissions)
      .leftJoin(schema.extractionResults, eq(schema.extractionResults.id, submissions.extractionId))
      .orderBy(submissions.createdAt)
      .all();
  }
}
