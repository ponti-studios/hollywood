import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { getDb } from "../db/index.js";
import type { DbRow } from "../db/index.js";
import { enrichProject } from "../db/helpers.js";
import * as crypto from "node:crypto";

// ── Schemas ─────────────────────────────────────────────────────────────────

const ProjectSchema = z.object({
  id: z.string().uuid().openapi({ example: "878f1f90-a9da-497b-85f8-ce8dddf5989d" }),
  title: z.string().openapi({ example: "THE NEIGHBORHOOD" }),
  season: z.number().int().openapi({ example: 1 }),
  genres: z.array(z.string()).openapi({ example: ["comedy"] }),
  format: z.string().nullable().openapi({ example: "tv" }),
  imdbLink: z.string().nullable(),
  posterLink: z.string().nullable(),
});

const CreateProjectSchema = z.object({
  title: z.string().min(1),
  format: z.string().optional(),
  genres: z.array(z.string()).optional(),
  season: z.number().int().optional(),
  imdbLink: z.string().optional(),
});

const UpdateProjectSchema = z.object({
  title: z.string().optional(),
  format: z.string().optional(),
  genres: z.array(z.string()).optional(),
  season: z.number().int().optional(),
  imdbLink: z.string().optional(),
});

// ── Routes ──────────────────────────────────────────────────────────────────

const listRoute = createRoute({
  method: "get",
  path: "/projects",
  responses: {
    200: { content: { "application/json": { schema: z.array(ProjectSchema) } }, description: "List of projects" },
  },
});

const getRoute = createRoute({
  method: "get",
  path: "/projects/{id}",
  request: { params: z.object({ id: z.string().uuid() }) },
  responses: {
    200: { content: { "application/json": { schema: ProjectSchema } }, description: "Project details" },
    404: { description: "Project not found" },
  },
});

const createRoute_ = createRoute({
  method: "post",
  path: "/projects",
  tags: ["mutating"],
  request: { body: { content: { "application/json": { schema: CreateProjectSchema } } } },
  responses: {
    201: { content: { "application/json": { schema: ProjectSchema } }, description: "Created project" },
  },
});

const updateRoute = createRoute({
  method: "patch",
  path: "/projects/{id}",
  tags: ["mutating"],
  request: {
    params: z.object({ id: z.string().uuid() }),
    body: { content: { "application/json": { schema: UpdateProjectSchema } } },
  },
  responses: {
    200: { content: { "application/json": { schema: ProjectSchema } }, description: "Updated project" },
    404: { description: "Project not found" },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();

router.openapi(listRoute, (c) => {
  const db = getDb();
  const rows = db
    .prepare("SELECT * FROM entities WHERE entity_type IN ('title', 'project') ORDER BY name")
    .all() as DbRow[];
  return c.json(rows.map(enrichProject) as z.infer<typeof ProjectSchema>[], 200);
});

router.openapi(getRoute, (c) => {
  const { id } = c.req.valid("param");
  const db = getDb();
  const row = db
    .prepare("SELECT * FROM entities WHERE id = ? AND entity_type IN ('title', 'project')")
    .get(id) as DbRow | undefined;
  if (!row) return c.json({ error: "Project not found" } as any, 404);
  return c.json(enrichProject(row) as z.infer<typeof ProjectSchema>, 200);
});

router.openapi(createRoute_, (c) => {
  const input = c.req.valid("json");
  const db = getDb();
  const now = new Date().toISOString();
  const entityId = crypto.randomUUID();
  const meta = JSON.stringify({ genres: input.genres ?? [], season: input.season ?? 1 });
  db.prepare(
    `INSERT INTO entities (id, source_id, entity_type, name, canonical_name, title_type, metadata_json, status, license_class, created_at, updated_at)
     VALUES (?, 'hollywood-api', 'title', ?, ?, ?, ?, 'active', 'public', ?, ?)`
  ).run(
    entityId,
    input.title,
    input.title.toLowerCase(),
    input.format ?? null,
    meta,
    now,
    now,
  );
  return c.json({
    id: entityId,
    title: input.title,
    season: input.season ?? 1,
    genres: input.genres ?? [],
    format: input.format ?? null,
    imdbLink: input.imdbLink ?? null,
    posterLink: null,
  } as z.infer<typeof ProjectSchema>, 201);
});

router.openapi(updateRoute, (c) => {
  const { id } = c.req.valid("param");
  const input = c.req.valid("json");
  const db = getDb();
  const existing = db
    .prepare("SELECT * FROM entities WHERE id = ? AND entity_type IN ('title', 'project')")
    .get(id) as DbRow | undefined;
  if (!existing) return c.json({ error: "Project not found" } as any, 404);
  const now = new Date().toISOString();
  const sets: string[] = [];
  const vals: unknown[] = [];
  if (input.title !== undefined) { sets.push("name = ?"); vals.push(input.title); sets.push("canonical_name = ?"); vals.push(input.title.toLowerCase()); }
  if (input.format !== undefined) { sets.push("title_type = ?"); vals.push(input.format); }
  if (input.genres !== undefined || input.season !== undefined) {
    const existingMeta = existing.metadata_json ? JSON.parse(existing.metadata_json as string) : {};
    existingMeta.genres = input.genres ?? existingMeta.genres ?? [];
    existingMeta.season = input.season ?? existingMeta.season ?? 1;
    sets.push("metadata_json = ?"); vals.push(JSON.stringify(existingMeta));
  }
  if (input.imdbLink !== undefined) {
    const existingMeta = existing.metadata_json ? JSON.parse(existing.metadata_json as string) : {};
    existingMeta.imdb_link = input.imdbLink;
    sets.push("metadata_json = ?"); vals.push(JSON.stringify(existingMeta));
  }
  sets.push("updated_at = ?"); vals.push(now);
  vals.push(id);
  db.prepare(`UPDATE entities SET ${sets.join(", ")} WHERE id = ?`).run(...vals);
  const updated = db.prepare("SELECT * FROM entities WHERE id = ?").get(id) as DbRow;
  return c.json(enrichProject(updated) as z.infer<typeof ProjectSchema>, 200);
});

export default router;
