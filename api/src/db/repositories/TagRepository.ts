import { getDrizzle } from "../index.js";
import { tags, entityTaggings } from "../schema.js";
import { eq } from "drizzle-orm";
import type { BetterSQLite3Database } from "drizzle-orm/better-sqlite3";
import * as schema from "../schema.js";
import { makeStableId } from "./EntityRepository.js";

type Db = BetterSQLite3Database<typeof schema>;

export class TagRepository {
  constructor(private db: Db = getDrizzle()) {}

  /** Ensure a tag exists, return its ID. Idempotent. */
  ensure(tagText: string): { id: string; tag: string; normalizedTag: string } {
    const norm = tagText.toLowerCase().replace(/ /g, "_");
    const tagId = makeStableId("tag", tagText);
    const now = new Date().toISOString();

    this.db
      .insert(tags)
      .values({ id: tagId, tag: tagText, normalizedTag: norm, createdAt: now })
      .onConflictDoNothing()
      .run();

    // Return the actual row (in case a conflict meant another ID was already there)
    const row = this.db
      .select({ id: tags.id, tag: tags.tag, normalizedTag: tags.normalizedTag })
      .from(tags)
      .where(eq(tags.normalizedTag, norm))
      .get()!;
    return row;
  }

  /** Tag an entity. Idempotent. */
  tagEntity(entityId: string, tagId: string, sourceId: string): string {
    const taggingId = makeStableId("tagging", entityId, tagId);
    const now = new Date().toISOString();
    const entityType = this.resolveEntityType(entityId);
    this.db
      .insert(entityTaggings)
      .values({ id: taggingId, tagId, entityType, entityId, sourceId, trustState: "machine_extracted", createdAt: now })
      .onConflictDoNothing()
      .run();
    return taggingId;
  }

  /** Look up which gold table an id belongs to. Defaults to "person" if not found. */
  private resolveEntityType(entityId: string): string {
    if (this.db.select({ id: schema.people.id }).from(schema.people).where(eq(schema.people.id, entityId)).get()) return "person";
    if (this.db.select({ id: schema.titles.id }).from(schema.titles).where(eq(schema.titles.id, entityId)).get()) return "title";
    if (this.db.select({ id: schema.companies.id }).from(schema.companies).where(eq(schema.companies.id, entityId)).get()) return "company";
    return "person";
  }

  /** Find all tags for an entity. */
  findByEntity(entityId: string) {
    return this.db
      .select({ id: tags.id, tag: tags.tag, normalizedTag: tags.normalizedTag })
      .from(entityTaggings)
      .innerJoin(tags, eq(tags.id, entityTaggings.tagId))
      .where(eq(entityTaggings.entityId, entityId))
      .all();
  }

  /** List all tags. */
  findAll() {
    return this.db
      .select({ id: tags.id, tagName: tags.tag })
      .from(tags)
      .orderBy(tags.tag)
      .all();
  }

  /** Find a tag by its ID. */
  findById(id: string) {
    return this.db.select().from(tags).where(eq(tags.id, id)).get() ?? null;
  }

  /** Find a tag by normalized name. */
  findByNormalized(normalizedTag: string) {
    return this.db.select().from(tags).where(eq(tags.normalizedTag, normalizedTag)).get() ?? null;
  }
}
