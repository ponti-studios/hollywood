import { getDrizzle } from "../index.js";
import { titleCompanies } from "../schema.js";
import type { BetterSQLite3Database } from "drizzle-orm/better-sqlite3";
import * as schema from "../schema.js";
import { makeStableId } from "./EntityRepository.js";

type Db = BetterSQLite3Database<typeof schema>;

export interface TitleCompanyFields {
  titleId: string;
  companyId: string;
  sourceId: string;
  relationship: string;
  trustState?: string;
}

export class TitleCompanyRepository {
  constructor(private db: Db = getDrizzle()) {}

  /** Upsert a title-company relationship. Idempotent — uses stable ID from title + company + relationship. */
  upsert(fields: TitleCompanyFields): string {
    const titleCompanyId = makeStableId("title_company", fields.titleId, fields.companyId, fields.relationship);
    const now = new Date().toISOString();
    this.db
      .insert(titleCompanies)
      .values({
        id: titleCompanyId,
        titleId: fields.titleId,
        companyId: fields.companyId,
        sourceId: fields.sourceId,
        relationship: fields.relationship,
        trustState: fields.trustState ?? "machine_extracted",
        sourceFactId: null,
        createdAt: now,
      })
      .onConflictDoNothing()
      .run();
    return titleCompanyId;
  }
}
