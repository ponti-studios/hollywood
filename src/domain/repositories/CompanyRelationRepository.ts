import { eq } from 'drizzle-orm';
import type { BetterSQLite3Database } from 'drizzle-orm/better-sqlite3';

import { getDrizzle } from '../../db.js';
import { companyRelations } from '../schema.js';
import * as schema from '../schema.js';
import { makeStableId } from './EntityRepository.js';

type Db = BetterSQLite3Database<typeof schema>;

export type CompanyRelationFields = Omit<typeof companyRelations.$inferInsert, 'id' | 'createdAt'>;

export class CompanyRelationRepository {
  constructor(private db: Db = getDrizzle()) {}

  /** Upsert a company relation. Idempotent — uses stable ID from company + entity + relationship. */
  upsert(fields: CompanyRelationFields): string {
    const id = makeStableId(
      'company_relation',
      fields.companyAId,
      fields.entityId,
      fields.relationship,
    );
    const now = new Date().toISOString();
    this.db
      .insert(companyRelations)
      .values({
        id,
        companyAId: fields.companyAId,
        entityType: fields.entityType,
        entityId: fields.entityId,
        relationship: fields.relationship,
        sourceId: fields.sourceId,
        trustState: fields.trustState ?? 'machine_extracted',
        sourceFactId: null,
        createdAt: now,
      })
      .onConflictDoNothing()
      .run();
    return id;
  }

  /** Find all relations for a company. */
  findByCompany(companyAId: string) {
    return this.db
      .select()
      .from(companyRelations)
      .where(eq(companyRelations.companyAId, companyAId))
      .all();
  }
}
