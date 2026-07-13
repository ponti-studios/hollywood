import { getDrizzle } from "../index.js";
import { people, titles, companies, aliases, contacts, links, representation as representationTable } from "../schema.js";
import { eq, like, and, or, count } from "drizzle-orm";
import type { BetterSQLite3Database } from "drizzle-orm/better-sqlite3";
import * as schema from "../schema.js";
import { createHash } from "node:crypto";

type Db = BetterSQLite3Database<typeof schema>;

// entityType -> gold table. "title"/"project" both land in `titles` (legacy alias).
type Kind = "person" | "title" | "company";

function kindFor(entityType: string): Kind {
  if (entityType === "person") return "person";
  if (entityType === "title" || entityType === "project") return "title";
  if (entityType === "company") return "company";
  throw new Error(`Unknown entityType: ${entityType}`);
}

export interface EntityFields {
  sourceId: string;
  externalId?: string | null;
  entityType: string;
  name: string;
  canonicalName: string;
  bio?: string | null;
  position?: string | null;
  titleType?: string | null;
  format?: string | null;
  companyType?: string | null;
  status?: string;
  licenseClass: string;
  metadataJson?: string;
}

export interface EntityUpdate {
  name?: string;
  canonicalName?: string;
  bio?: string | null;
  position?: string | null;
  titleType?: string | null;
  format?: string | null;
  companyType?: string | null;
  status?: string;
  licenseClass?: string;
  metadataJson?: string;
}

/** Unified read shape — same as the old flat `entities` row, reshaped from people/titles/companies. */
export interface EntityLikeRow {
  id: string;
  sourceId: string;
  externalId: string | null;
  entityType: Kind;
  name: string;
  canonicalName: string;
  bio: string | null;
  position: string | null;
  titleType: string | null;
  format: string | null;
  companyType: string | null;
  status: string | null;
  licenseClass: string;
  metadataJson: string | null;
  createdAt: string;
  updatedAt: string;
}

export interface EntityAliasRow {
  id: string;
  entityId: string;
  sourceId: string;
  alias: string;
  createdAt: string;
}

export interface EntityContactRow {
  id: string;
  entityId: string;
  sourceId: string;
  contactType: string;
  contactValue: string;
  trustState: string;
  createdAt: string;
}

export interface EntityLinkRow {
  id: string;
  entityId: string;
  sourceId: string;
  url: string;
  linkType: string;
  trustState: string;
  createdAt: string;
}

export function makeStableId(...parts: string[]): string {
  const joined = parts.filter(Boolean).map((p) => p.trim()).join("::");
  return createHash("sha256").update(joined, "utf-8").digest("hex").slice(0, 24);
}

// biome-ignore lint: rough reshaping helpers, not type-precious right now
function toPersonRow(row: any): EntityLikeRow {
  return {
    id: row.id,
    sourceId: row.sourceId,
    externalId: row.externalId ?? null,
    entityType: "person",
    name: row.name,
    canonicalName: row.canonicalName,
    bio: row.bio ?? null,
    position: row.primaryProfession ?? null,
    titleType: null,
    format: null,
    companyType: null,
    status: row.status,
    licenseClass: row.licenseClass,
    metadataJson: row.metadataJson,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

function toTitleRow(row: any): EntityLikeRow {
  return {
    id: row.id,
    sourceId: row.sourceId,
    externalId: row.externalId ?? null,
    entityType: "title",
    name: row.title,
    canonicalName: row.canonicalName,
    bio: row.synopsis ?? null,
    position: null,
    titleType: row.format ?? null,
    format: row.format ?? null,
    companyType: null,
    status: row.status,
    licenseClass: row.licenseClass,
    metadataJson: row.metadataJson,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

function toCompanyRow(row: any): EntityLikeRow {
  return {
    id: row.id,
    sourceId: row.sourceId,
    externalId: row.externalId ?? null,
    entityType: "company",
    name: row.name,
    canonicalName: row.canonicalName,
    bio: null,
    position: null,
    titleType: null,
    format: null,
    companyType: row.companyType,
    status: row.status,
    licenseClass: row.licenseClass,
    metadataJson: row.metadataJson,
    createdAt: row.createdAt,
    updatedAt: row.updatedAt,
  };
}

export class EntityRepository {
  constructor(private db: Db = getDrizzle()) {}

  // ── Lookup ────────────────────────────────────────────────────────────────

  findById(id: string): EntityLikeRow | null {
    const p = this.db.select().from(people).where(eq(people.id, id)).get();
    if (p) return toPersonRow(p);
    const t = this.db.select().from(titles).where(eq(titles.id, id)).get();
    if (t) return toTitleRow(t);
    const c = this.db.select().from(companies).where(eq(companies.id, id)).get();
    if (c) return toCompanyRow(c);
    return null;
  }

  findByType(entityType: string, limit = 50, offset = 0): EntityLikeRow[] {
    const kind = kindFor(entityType);
    if (kind === "person") {
      return this.db.select().from(people).orderBy(people.name).limit(limit).offset(offset).all().map(toPersonRow);
    }
    if (kind === "title") {
      return this.db.select().from(titles).orderBy(titles.title).limit(limit).offset(offset).all().map(toTitleRow);
    }
    return this.db.select().from(companies).orderBy(companies.name).limit(limit).offset(offset).all().map(toCompanyRow);
  }

  findByTypes(entityTypes: string[], limit = 50, offset = 0): EntityLikeRow[] {
    const kinds = new Set(entityTypes.map(kindFor));
    let rows: EntityLikeRow[] = [];
    if (kinds.has("person")) rows = rows.concat(this.db.select().from(people).all().map(toPersonRow));
    if (kinds.has("title")) rows = rows.concat(this.db.select().from(titles).all().map(toTitleRow));
    if (kinds.has("company")) rows = rows.concat(this.db.select().from(companies).all().map(toCompanyRow));
    rows.sort((a, b) => a.name.localeCompare(b.name));
    return rows.slice(offset, offset + limit);
  }

  findByName(name: string): EntityLikeRow[] {
    return [
      ...this.db.select().from(people).where(eq(people.name, name)).all().map(toPersonRow),
      ...this.db.select().from(titles).where(eq(titles.title, name)).all().map(toTitleRow),
      ...this.db.select().from(companies).where(eq(companies.name, name)).all().map(toCompanyRow),
    ];
  }

  searchByName(query: string, limit = 20, offset = 0): { rows: EntityLikeRow[]; total: number } {
    const pattern = `%${query}%`;
    const allRows = [
      ...this.db.select().from(people).where(like(people.name, pattern)).all().map(toPersonRow),
      ...this.db.select().from(titles).where(like(titles.title, pattern)).all().map(toTitleRow),
      ...this.db.select().from(companies).where(like(companies.name, pattern)).all().map(toCompanyRow),
    ];
    allRows.sort((a, b) => a.name.localeCompare(b.name));
    return { rows: allRows.slice(offset, offset + limit), total: allRows.length };
  }

  countByType(entityType: string): number {
    const kind = kindFor(entityType);
    if (kind === "person") {
      const [{ value }] = this.db.select({ value: count() }).from(people).all();
      return value;
    }
    if (kind === "title") {
      const [{ value }] = this.db.select({ value: count() }).from(titles).all();
      return value;
    }
    const [{ value }] = this.db.select({ value: count() }).from(companies).all();
    return value;
  }

  // ── Create / Upsert ───────────────────────────────────────────────────────

  /** Generate a stable entity ID from source + name. */
  makeEntityId(sourceId: string, name: string): string {
    return makeStableId("entity", sourceId, name);
  }

  /** Insert if not exists. Uses stable ID from sourceId + name. */
  upsert(fields: EntityFields): string {
    const id = this.makeEntityId(fields.sourceId, fields.name);
    this.insertWithId(id, fields);
    return id;
  }

  /** Insert or replace. Overwrites all fields. */
  upsertReplace(fields: EntityFields): string {
    const id = this.makeEntityId(fields.sourceId, fields.name);
    const kind = kindFor(fields.entityType);
    const now = new Date().toISOString();

    if (kind === "person") {
      this.db
        .insert(people)
        .values({
          id,
          sourceId: fields.sourceId,
          externalId: fields.externalId ?? null,
          name: fields.name,
          canonicalName: fields.canonicalName,
          bio: fields.bio ?? null,
          primaryProfession: fields.position ?? null,
          status: fields.status ?? "active",
          licenseClass: fields.licenseClass,
          metadataJson: fields.metadataJson ?? "{}",
          createdAt: now,
          updatedAt: now,
        })
        .onConflictDoUpdate({
          target: people.id,
          set: {
            sourceId: fields.sourceId,
            externalId: fields.externalId ?? null,
            name: fields.name,
            canonicalName: fields.canonicalName,
            bio: fields.bio ?? null,
            primaryProfession: fields.position ?? null,
            status: fields.status ?? "active",
            licenseClass: fields.licenseClass,
            metadataJson: fields.metadataJson ?? "{}",
            updatedAt: now,
          },
        })
        .run();
    } else if (kind === "title") {
      this.db
        .insert(titles)
        .values({
          id,
          sourceId: fields.sourceId,
          externalId: fields.externalId ?? null,
          title: fields.name,
          canonicalName: fields.canonicalName,
          format: fields.titleType ?? fields.format ?? "unknown",
          status: fields.status ?? "development",
          licenseClass: fields.licenseClass,
          metadataJson: fields.metadataJson ?? "{}",
          createdAt: now,
          updatedAt: now,
        })
        .onConflictDoUpdate({
          target: titles.id,
          set: {
            sourceId: fields.sourceId,
            externalId: fields.externalId ?? null,
            title: fields.name,
            canonicalName: fields.canonicalName,
            format: fields.titleType ?? fields.format ?? "unknown",
            status: fields.status ?? "development",
            licenseClass: fields.licenseClass,
            metadataJson: fields.metadataJson ?? "{}",
            updatedAt: now,
          },
        })
        .run();
    } else {
      this.db
        .insert(companies)
        .values({
          id,
          sourceId: fields.sourceId,
          externalId: fields.externalId ?? null,
          name: fields.name,
          canonicalName: fields.canonicalName,
          companyType: fields.companyType ?? "unknown",
          status: fields.status ?? "active",
          licenseClass: fields.licenseClass,
          metadataJson: fields.metadataJson ?? "{}",
          createdAt: now,
          updatedAt: now,
        })
        .onConflictDoUpdate({
          target: companies.id,
          set: {
            sourceId: fields.sourceId,
            externalId: fields.externalId ?? null,
            name: fields.name,
            canonicalName: fields.canonicalName,
            companyType: fields.companyType ?? "unknown",
            status: fields.status ?? "active",
            licenseClass: fields.licenseClass,
            metadataJson: fields.metadataJson ?? "{}",
            updatedAt: now,
          },
        })
        .run();
    }
    return id;
  }

  /** Insert with an explicit ID (for routes that generate IDs differently). Idempotent. */
  insertWithId(id: string, fields: EntityFields): void {
    const kind = kindFor(fields.entityType);
    const now = new Date().toISOString();

    if (kind === "person") {
      this.db
        .insert(people)
        .values({
          id,
          sourceId: fields.sourceId,
          externalId: fields.externalId ?? null,
          name: fields.name,
          canonicalName: fields.canonicalName,
          bio: fields.bio ?? null,
          primaryProfession: fields.position ?? null,
          status: fields.status ?? "active",
          licenseClass: fields.licenseClass,
          metadataJson: fields.metadataJson ?? "{}",
          createdAt: now,
          updatedAt: now,
        })
        .onConflictDoNothing()
        .run();
    } else if (kind === "title") {
      this.db
        .insert(titles)
        .values({
          id,
          sourceId: fields.sourceId,
          externalId: fields.externalId ?? null,
          title: fields.name,
          canonicalName: fields.canonicalName,
          format: fields.titleType ?? fields.format ?? "unknown",
          status: fields.status ?? "development",
          licenseClass: fields.licenseClass,
          metadataJson: fields.metadataJson ?? "{}",
          createdAt: now,
          updatedAt: now,
        })
        .onConflictDoNothing()
        .run();
    } else {
      this.db
        .insert(companies)
        .values({
          id,
          sourceId: fields.sourceId,
          externalId: fields.externalId ?? null,
          name: fields.name,
          canonicalName: fields.canonicalName,
          companyType: fields.companyType ?? "unknown",
          status: fields.status ?? "active",
          licenseClass: fields.licenseClass,
          metadataJson: fields.metadataJson ?? "{}",
          createdAt: now,
          updatedAt: now,
        })
        .onConflictDoNothing()
        .run();
    }
  }

  // ── Update ────────────────────────────────────────────────────────────────

  update(id: string, fields: EntityUpdate): void {
    const existing = this.findById(id);
    if (!existing) return;
    const now = new Date().toISOString();

    if (existing.entityType === "person") {
      const values: Record<string, unknown> = { updatedAt: now };
      if (fields.name !== undefined) values.name = fields.name;
      if (fields.canonicalName !== undefined) values.canonicalName = fields.canonicalName;
      if (fields.bio !== undefined) values.bio = fields.bio;
      if (fields.position !== undefined) values.primaryProfession = fields.position;
      if (fields.status !== undefined) values.status = fields.status;
      if (fields.licenseClass !== undefined) values.licenseClass = fields.licenseClass;
      if (fields.metadataJson !== undefined) values.metadataJson = fields.metadataJson;
      this.db.update(people).set(values).where(eq(people.id, id)).run();
    } else if (existing.entityType === "title") {
      const values: Record<string, unknown> = { updatedAt: now };
      if (fields.name !== undefined) values.title = fields.name;
      if (fields.canonicalName !== undefined) values.canonicalName = fields.canonicalName;
      if (fields.format !== undefined) values.format = fields.format;
      if (fields.titleType !== undefined) values.format = fields.titleType;
      if (fields.status !== undefined) values.status = fields.status;
      if (fields.licenseClass !== undefined) values.licenseClass = fields.licenseClass;
      if (fields.metadataJson !== undefined) values.metadataJson = fields.metadataJson;
      this.db.update(titles).set(values).where(eq(titles.id, id)).run();
    } else {
      const values: Record<string, unknown> = { updatedAt: now };
      if (fields.name !== undefined) values.name = fields.name;
      if (fields.canonicalName !== undefined) values.canonicalName = fields.canonicalName;
      if (fields.companyType !== undefined) values.companyType = fields.companyType;
      if (fields.status !== undefined) values.status = fields.status;
      if (fields.licenseClass !== undefined) values.licenseClass = fields.licenseClass;
      if (fields.metadataJson !== undefined) values.metadataJson = fields.metadataJson;
      this.db.update(companies).set(values).where(eq(companies.id, id)).run();
    }
  }

  // ── Delete ────────────────────────────────────────────────────────────────

  exists(id: string): boolean {
    return this.findById(id) !== null;
  }

  /** Delete an entity and its related child records. */
  delete(id: string): void {
    const existing = this.findById(id);
    if (!existing) return;

    // Delete child records first to avoid FK violations
    this.db.delete(aliases).where(eq(aliases.entityId, id)).run();
    this.db.delete(contacts).where(eq(contacts.entityId, id)).run();
    this.db.delete(links).where(eq(links.entityId, id)).run();
    this.db.delete(representationTable).where(eq(representationTable.clientId, id)).run();
    this.db.delete(representationTable).where(eq(representationTable.repId, id)).run();
    this.db.delete(schema.entityTaggings).where(eq(schema.entityTaggings.entityId, id)).run();
    this.db.delete(schema.credits).where(eq(schema.credits.personId, id)).run();
    this.db.delete(schema.credits).where(eq(schema.credits.titleId, id)).run();
    this.db.delete(schema.articleEntities).where(eq(schema.articleEntities.entityId, id)).run();
    this.db.delete(schema.collaborations).where(eq(schema.collaborations.personAId, id)).run();
    this.db.delete(schema.collaborations).where(eq(schema.collaborations.personBId, id)).run();

    if (existing.entityType === "person") {
      this.db.delete(people).where(eq(people.id, id)).run();
    } else if (existing.entityType === "title") {
      this.db.delete(titles).where(eq(titles.id, id)).run();
    } else {
      this.db.delete(companies).where(eq(companies.id, id)).run();
    }
  }

  // ── Aliases ───────────────────────────────────────────────────────────────

  addAlias(entityId: string, sourceId: string, alias: string): string {
    const entity = this.findById(entityId);
    const entityType = entity?.entityType ?? "person";
    const aliasId = makeStableId("alias", entityId, alias);
    const now = new Date().toISOString();
    this.db
      .insert(aliases)
      .values({ id: aliasId, entityType, entityId, sourceId, alias, createdAt: now })
      .onConflictDoNothing()
      .run();
    return aliasId;
  }

  findAliases(entityId: string): EntityAliasRow[] {
    return this.db.select().from(aliases).where(eq(aliases.entityId, entityId)).all();
  }

  // ── Contacts ──────────────────────────────────────────────────────────────

  addContact(entityId: string, sourceId: string, contactType: string, contactValue: string): string {
    const entity = this.findById(entityId);
    const entityType = entity?.entityType ?? "person";
    const contactId = makeStableId("contact", entityId, contactValue);
    const now = new Date().toISOString();
    this.db
      .insert(contacts)
      .values({
        id: contactId,
        entityType,
        entityId,
        sourceId,
        contactType,
        contactValue,
        trustState: "machine_extracted",
        createdAt: now,
      })
      .onConflictDoNothing()
      .run();
    return contactId;
  }

  findContacts(entityId: string, contactType?: string): EntityContactRow[] {
    const conditions = [eq(contacts.entityId, entityId)];
    if (contactType) conditions.push(eq(contacts.contactType, contactType));
    return this.db.select().from(contacts).where(and(...conditions)).all();
  }

  // ── Links ─────────────────────────────────────────────────────────────────

  addLink(entityId: string, sourceId: string, url: string, linkType: string): string {
    const entity = this.findById(entityId);
    const entityType = entity?.entityType ?? "person";
    const linkId = makeStableId("link", entityId, url);
    const now = new Date().toISOString();
    this.db
      .insert(links)
      .values({
        id: linkId,
        entityType,
        entityId,
        sourceId,
        url,
        linkType,
        trustState: "machine_extracted",
        createdAt: now,
      })
      .onConflictDoNothing()
      .run();
    return linkId;
  }

  findLinks(entityId: string): EntityLinkRow[] {
    return this.db.select().from(links).where(eq(links.entityId, entityId)).all();
  }

  // ── Representation ──────────────────────────────────────────────────────────

  upsertRepresentation(
    repRelId: string,
    clientId: string,
    repId: string,
    repType: string,
    title: string,
    email: string,
    phone: string,
    sourceId: string,
  ): void {
    const now = new Date().toISOString();
    this.db
      .insert(representationTable)
      .values({
        id: repRelId,
        clientId,
        repId,
        repType,
        title,
        email,
        phone,
        sourceId,
        trustState: "machine_extracted",
        sourceFactId: null,
        createdAt: now,
      })
      .onConflictDoNothing()
      .run();
  }

  findRepresentatives(clientId: string) {
    return this.db
      .select()
      .from(representationTable)
      .where(eq(representationTable.clientId, clientId))
      .all();
  }
}
