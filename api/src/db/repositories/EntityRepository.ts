import { getDrizzle } from "../index.js";
import { entities, entityAliases, entityContacts, entityLinks, representation as representationTable } from "../schema.js";
import { eq, like, and, or, count } from "drizzle-orm";
import type { BetterSQLite3Database } from "drizzle-orm/better-sqlite3";
import * as schema from "../schema.js";
import { createHash } from "node:crypto";

type Db = BetterSQLite3Database<typeof schema>;

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

export class EntityRepository {
  constructor(private db: Db = getDrizzle()) {}

  // ── Lookup ────────────────────────────────────────────────────────────────

  findById(id: string) {
    return this.db.select().from(entities).where(eq(entities.id, id)).get() ?? null;
  }

  findByType(entityType: string, limit = 50, offset = 0) {
    return this.db
      .select()
      .from(entities)
      .where(eq(entities.entityType, entityType))
      .orderBy(entities.name)
      .limit(limit)
      .offset(offset)
      .all();
  }

  findByTypes(entityTypes: string[], limit = 50, offset = 0) {
    const conditions = entityTypes.map((t) => eq(entities.entityType, t));
    return this.db
      .select()
      .from(entities)
      .where(or(...conditions))
      .orderBy(entities.name)
      .limit(limit)
      .offset(offset)
      .all();
  }

  findByName(name: string) {
    return this.db.select().from(entities).where(eq(entities.name, name)).all();
  }

  searchByName(query: string, limit = 20, offset = 0) {
    const pattern = `%${query}%`;
    const rows = this.db
      .select()
      .from(entities)
      .where(like(entities.name, pattern))
      .orderBy(entities.name)
      .limit(limit)
      .offset(offset)
      .all();
    const [{ value: total }] = this.db
      .select({ value: count() })
      .from(entities)
      .where(like(entities.name, pattern))
      .all();
    return { rows, total };
  }

  countByType(entityType: string): number {
    const [{ value }] = this.db
      .select({ value: count() })
      .from(entities)
      .where(eq(entities.entityType, entityType))
      .all();
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
    const now = new Date().toISOString();
    this.db
      .insert(entities)
      .values({
        id,
        sourceId: fields.sourceId,
        externalId: fields.externalId ?? null,
        entityType: fields.entityType,
        name: fields.name,
        canonicalName: fields.canonicalName,
        bio: fields.bio ?? null,
        position: fields.position ?? null,
        titleType: fields.titleType ?? null,
        format: fields.format ?? null,
        companyType: fields.companyType ?? null,
        status: fields.status ?? "active",
        licenseClass: fields.licenseClass,
        metadataJson: fields.metadataJson ?? "{}",
        createdAt: now,
        updatedAt: now,
      })
      .onConflictDoNothing()
      .run();
    return id;
  }

  /** Insert or replace. Overwrites all fields. */
  upsertReplace(fields: EntityFields): string {
    const id = this.makeEntityId(fields.sourceId, fields.name);
    const now = new Date().toISOString();
    this.db
      .insert(entities)
      .values({
        id,
        sourceId: fields.sourceId,
        externalId: fields.externalId ?? null,
        entityType: fields.entityType,
        name: fields.name,
        canonicalName: fields.canonicalName,
        bio: fields.bio ?? null,
        position: fields.position ?? null,
        titleType: fields.titleType ?? null,
        format: fields.format ?? null,
        companyType: fields.companyType ?? null,
        status: fields.status ?? "active",
        licenseClass: fields.licenseClass,
        metadataJson: fields.metadataJson ?? "{}",
        createdAt: now,
        updatedAt: now,
      })
      .onConflictDoUpdate({
        target: entities.id,
        set: {
          sourceId: fields.sourceId,
          externalId: fields.externalId ?? null,
          entityType: fields.entityType,
          name: fields.name,
          canonicalName: fields.canonicalName,
          bio: fields.bio ?? null,
          position: fields.position ?? null,
          titleType: fields.titleType ?? null,
          format: fields.format ?? null,
          companyType: fields.companyType ?? null,
          status: fields.status ?? "active",
          licenseClass: fields.licenseClass,
          metadataJson: fields.metadataJson ?? "{}",
          updatedAt: now,
        },
      })
      .run();
    return id;
  }

  /** Insert with an explicit ID (for routes that generate IDs differently). Idempotent. */
  insertWithId(id: string, fields: EntityFields): void {
    const now = new Date().toISOString();
    this.db
      .insert(entities)
      .values({
        id,
        sourceId: fields.sourceId,
        externalId: fields.externalId ?? null,
        entityType: fields.entityType,
        name: fields.name,
        canonicalName: fields.canonicalName,
        bio: fields.bio ?? null,
        position: fields.position ?? null,
        titleType: fields.titleType ?? null,
        format: fields.format ?? null,
        companyType: fields.companyType ?? null,
        status: fields.status ?? "active",
        licenseClass: fields.licenseClass,
        metadataJson: fields.metadataJson ?? "{}",
        createdAt: now,
        updatedAt: now,
      })
      .onConflictDoNothing()
      .run();
  }

  // ── Update ────────────────────────────────────────────────────────────────

  update(id: string, fields: EntityUpdate): void {
    const now = new Date().toISOString();
    const values: Record<string, unknown> = { updatedAt: now };
    if (fields.name !== undefined) values.name = fields.name;
    if (fields.canonicalName !== undefined) values.canonicalName = fields.canonicalName;
    if (fields.bio !== undefined) values.bio = fields.bio;
    if (fields.position !== undefined) values.position = fields.position;
    if (fields.titleType !== undefined) values.titleType = fields.titleType;
    if (fields.format !== undefined) values.format = fields.format;
    if (fields.companyType !== undefined) values.companyType = fields.companyType;
    if (fields.status !== undefined) values.status = fields.status;
    if (fields.licenseClass !== undefined) values.licenseClass = fields.licenseClass;
    if (fields.metadataJson !== undefined) values.metadataJson = fields.metadataJson;

    this.db.update(entities).set(values).where(eq(entities.id, id)).run();
  }

  // ── Delete ────────────────────────────────────────────────────────────────

  exists(id: string): boolean {
    const row = this.db.select({ id: entities.id }).from(entities).where(eq(entities.id, id)).get();
    return row !== undefined;
  }

  /** Delete an entity and its related child records. */
  delete(id: string): void {
    // Delete child records first to avoid FK violations
    this.db.delete(entityAliases).where(eq(entityAliases.entityId, id)).run();
    this.db.delete(entityContacts).where(eq(entityContacts.entityId, id)).run();
    this.db.delete(entityLinks).where(eq(entityLinks.entityId, id)).run();
    this.db.delete(representationTable).where(eq(representationTable.clientId, id)).run();
    this.db.delete(representationTable).where(eq(representationTable.repId, id)).run();
    this.db.delete(schema.entityTaggings).where(eq(schema.entityTaggings.entityId, id)).run();
    this.db.delete(schema.credits).where(eq(schema.credits.personId, id)).run();
    this.db.delete(schema.credits).where(eq(schema.credits.titleId, id)).run();
    this.db.delete(schema.articleEntities).where(eq(schema.articleEntities.entityId, id)).run();
    this.db.delete(schema.collaborations).where(eq(schema.collaborations.personAId, id)).run();
    this.db.delete(schema.collaborations).where(eq(schema.collaborations.personBId, id)).run();
    this.db.delete(schema.mergeCandidates).where(eq(schema.mergeCandidates.entityAId, id)).run();
    this.db.delete(schema.mergeCandidates).where(eq(schema.mergeCandidates.entityBId, id)).run();
    this.db.delete(schema.entityMerges).where(eq(schema.entityMerges.survivingId, id)).run();
    this.db.delete(schema.entityMerges).where(eq(schema.entityMerges.mergedId, id)).run();
    // Finally delete the entity itself
    this.db.delete(entities).where(eq(entities.id, id)).run();
  }

  // ── Aliases ───────────────────────────────────────────────────────────────

  addAlias(entityId: string, sourceId: string, alias: string): string {
    const aliasId = makeStableId("alias", entityId, alias);
    const now = new Date().toISOString();
    this.db
      .insert(entityAliases)
      .values({ id: aliasId, entityId, sourceId, alias, createdAt: now })
      .onConflictDoNothing()
      .run();
    return aliasId;
  }

  findAliases(entityId: string): EntityAliasRow[] {
    const rows = this.db
      .select()
      .from(entityAliases)
      .where(eq(entityAliases.entityId, entityId))
      .all();
    return rows;
  }

  // ── Contacts ──────────────────────────────────────────────────────────────

  addContact(entityId: string, sourceId: string, contactType: string, contactValue: string): string {
    const contactId = makeStableId("contact", entityId, contactValue);
    const now = new Date().toISOString();
    this.db
      .insert(entityContacts)
      .values({
        id: contactId,
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
    const conditions = [eq(entityContacts.entityId, entityId)];
    if (contactType) conditions.push(eq(entityContacts.contactType, contactType));
    return this.db.select().from(entityContacts).where(and(...conditions)).all();
  }

  // ── Links ─────────────────────────────────────────────────────────────────

  addLink(entityId: string, sourceId: string, url: string, linkType: string): string {
    const linkId = makeStableId("link", entityId, url);
    const now = new Date().toISOString();
    this.db
      .insert(entityLinks)
      .values({
        id: linkId,
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
    return this.db.select().from(entityLinks).where(eq(entityLinks.entityId, entityId)).all();
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
