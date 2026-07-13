import { getDrizzle } from "../index.js";
import { credits } from "../schema.js";
import { eq } from "drizzle-orm";
import type { BetterSQLite3Database } from "drizzle-orm/better-sqlite3";
import * as schema from "../schema.js";
import { makeStableId } from "./EntityRepository.js";

type Db = BetterSQLite3Database<typeof schema>;

export interface CreditFields {
  personId: string;
  titleId: string;
  companyId?: string | null;
  sourceId: string;
  role: string;
  creditType?: string;
  billing?: number | null;
  trustState?: string;
}

export interface CreditWithTitle {
  id: string;
  personId: string;
  titleId: string;
  role: string;
  creditType: string | null;
  titleName?: string | null;
}

export class CreditRepository {
  constructor(private db: Db = getDrizzle()) {}

  /** Upsert a credit. Idempotent — uses stable ID from person + title + role. */
  upsert(fields: CreditFields): string {
    const creditId = makeStableId("credit", fields.personId, fields.titleId, fields.role);
    const now = new Date().toISOString();
    this.db
      .insert(credits)
      .values({
        id: creditId,
        personId: fields.personId,
        titleId: fields.titleId,
        companyId: fields.companyId ?? null,
        sourceId: fields.sourceId,
        role: fields.role,
        creditCategory: fields.creditType ?? "crew",
        billing: fields.billing ?? null,
        trustState: fields.trustState ?? "machine_extracted",
        sourceFactId: null,
        createdAt: now,
      })
      .onConflictDoNothing()
      .run();
    return creditId;
  }

  /** Find all credits for a person, joined with title name. */
  findByPerson(personId: string): CreditWithTitle[] {
    const rows = this.db
      .select({
        id: credits.id,
        personId: credits.personId,
        titleId: credits.titleId,
        role: credits.role,
        creditType: credits.creditCategory,
        titleName: schema.titles.title,
      })
      .from(credits)
      .leftJoin(schema.titles, eq(schema.titles.id, credits.titleId))
      .where(eq(credits.personId, personId))
      .orderBy(credits.createdAt)
      .all();
    return rows;
  }

  /** Find all credits for a title. */
  findByTitle(titleId: string) {
    return this.db
      .select({
        id: credits.id,
        personId: credits.personId,
        titleId: credits.titleId,
        role: credits.role,
        creditType: credits.creditCategory,
        personName: schema.people.name,
      })
      .from(credits)
      .leftJoin(schema.people, eq(schema.people.id, credits.personId))
      .where(eq(credits.titleId, titleId))
      .orderBy(credits.createdAt)
      .all();
  }
}
