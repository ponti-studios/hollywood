import { getDb } from "../db/index.js";
import type { DbRow } from "../db/index.js";
import * as crypto from "node:crypto";

export const projectResolvers = {
  Query: {
    project: (_parent: unknown, args: { projectId?: string }) => {
      const db = getDb();
      const row = db
        .prepare("SELECT * FROM entities WHERE id = ? AND entity_type IN ('title', 'project')")
        .get(args.projectId) as DbRow | undefined;
      if (!row) {
        return {
          id: "default",
          title: "Default Project",
          season: 1,
          genres: [],
          format: null,
          imdbLink: null,
          posterLink: null,
        };
      }
      const meta = row.metadata_json ? JSON.parse(row.metadata_json as string) : {};
      return {
        id: row.id,
        title: row.name,
        season: meta.season ?? 1,
        genres: meta.genres ?? [],
        format: row.title_type ?? null,
        imdbLink: meta.imdb_link ?? null,
        posterLink: meta.poster_link ?? null,
      };
    },

    allProjectsForUser: () => {
      const db = getDb();
      const rows = db
        .prepare("SELECT * FROM entities WHERE entity_type IN ('title', 'project') ORDER BY name")
        .all() as DbRow[];
      return rows.map((row) => ({
        id: row.id,
        title: row.name,
        season: 1,
        genres: [],
        format: row.title_type ?? null,
        imdbLink: null,
        posterLink: null,
      }));
    },

    projectTags: (_parent: unknown, args: { projectId: string }) => {
      const db = getDb();
      return db
        .prepare("SELECT id, tag AS tagName FROM tags ORDER BY tag")
        .all() as { id: number; tagName: string }[];
    },
  },

  Mutation: {
    addProject: (_parent: unknown, args: { project: Record<string, unknown> }) => {
      const db = getDb();
      const entityId = crypto.randomUUID();
      const now = new Date().toISOString();
      const meta = JSON.stringify({
        genres: args.project["genres"] ?? [],
        season: args.project["season"] ?? 1,
      });
      db.prepare(
        `INSERT INTO entities (id, source_id, entity_type, name, canonical_name, title_type, metadata_json, status, license_class, created_at, updated_at)
         VALUES (?, ?, 'title', ?, ?, ?, ?, 'active', 'public', ?, ?)`
      ).run(
        entityId,
        "hollywood-api",
        args.project["title"],
        (args.project["title"] as string).toLowerCase(),
        (args.project["format"] as string) ?? null,
        meta,
        now,
        now,
      );
      return {
        id: entityId,
        title: args.project["title"],
        season: (args.project["season"] as number) ?? 1,
        genres: (args.project["genres"] as string[]) ?? [],
        format: args.project["format"] ?? null,
        imdbLink: args.project["imdbLink"] ?? null,
        posterLink: null,
      };
    },
  },
};
