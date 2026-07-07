import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { getDb } from "../db/index.js";
import type { DbRow } from "../db/index.js";
import { parseSubmissionJson, enrichCandidate } from "../db/helpers.js";
import * as crypto from "node:crypto";

// ── Schemas ─────────────────────────────────────────────────────────────────

const SubmissionCreditSchema = z.object({
  role: z.string().nullable(),
  type: z.string().nullable(),
  production: z.string().nullable(),
  network: z.string().nullable(),
});

const SubmissionRepresentativeSchema = z.object({
  name: z.string().nullable(),
  title: z.string().nullable(),
  agency: z.string().nullable(),
  email: z.string().nullable(),
});

const SubmissionLinkSchema = z.object({
  url: z.string().nullable(),
  type: z.string().nullable(),
});

const SubmissionJsonSchema = z.object({
  name: z.string(),
  bio: z.string().nullable(),
  email: z.string().nullable(),
  phoneNumber: z.string().nullable(),
  tags: z.array(z.string()).nullable(),
  organizations: z.array(z.string()).nullable(),
  credits: z.array(SubmissionCreditSchema).nullable(),
  representatives: z.array(SubmissionRepresentativeSchema).nullable(),
  links: z.array(SubmissionLinkSchema).nullable(),
  attachments: z.array(z.string()).nullable(),
});

const SubmissionSchema = z.object({
  id: z.string(),
  projectId: z.string(),
  candidateId: z.string().nullable(),
  created: z.string(),
  submissionJson: SubmissionJsonSchema,
  samples: z.array(z.unknown()),
  rawSamples: z.array(z.unknown()),
});

// ── Routes ──────────────────────────────────────────────────────────────────

const listRoute = createRoute({
  method: "get",
  path: "/submissions",
  responses: {
    200: { content: { "application/json": { schema: z.array(SubmissionSchema) } }, description: "List of submissions" },
  },
});

const deleteRoute = createRoute({
  method: "delete",
  path: "/submissions/{id}",
  tags: ["mutating"],
  request: { params: z.object({ id: z.string().min(1) }) },
  responses: {
    200: { content: { "application/json": { schema: z.object({ deleted: z.boolean() }) } }, description: "Deleted submission" },
    404: { description: "Submission not found" },
  },
});

const createCandidateRoute = createRoute({
  method: "post",
  path: "/submissions/{id}/candidate",
  tags: ["mutating"],
  request: {
    params: z.object({ id: z.string().min(1) }),
    body: { content: { "application/json": { schema: z.object({ position: z.string() }) } } },
  },
  responses: {
    201: {
      content: { "application/json": { schema: z.object({ id: z.string(), name: z.string(), position: z.string(), status: z.string() }) } },
      description: "Created candidate from submission",
    },
    404: { description: "Submission not found" },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();

router.openapi(listRoute, (c) => {
  const projectId = c.req.query("projectId") ?? "default";
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT s.id, s.document_id, s.extraction_id, s.created_at, e.result_json
       FROM submissions s
       LEFT JOIN extraction_results e ON e.id = s.extraction_id
       ORDER BY s.created_at DESC`
    )
    .all() as DbRow[];
  const result = rows.map((r) => ({
    id: r.id,
    projectId,
    candidateId: null,
    created: r.created_at,
    submissionJson: parseSubmissionJson((r.result_json as string) ?? "{}"),
    samples: [],
    rawSamples: [],
  }));
  return c.json(result as any, 200);
});

router.openapi(deleteRoute, (c) => {
  const { id } = c.req.valid("param");
  const db = getDb();
  const existing = db.prepare("SELECT id FROM submissions WHERE id = ?").get(id);
  if (!existing) return c.json({ error: "Submission not found" }, 404);
  const result = db.prepare("DELETE FROM submissions WHERE id = ?").run(id);
  return c.json({ deleted: result.changes > 0 }, 200);
});

router.openapi(createCandidateRoute, (c) => {
  const { id } = c.req.valid("param");
  const { position } = c.req.valid("json");
  const db = getDb();
  const sub = db.prepare(
    `SELECT s.id, s.document_id, e.result_json
     FROM submissions s
     LEFT JOIN extraction_results e ON e.id = s.extraction_id
     WHERE s.id = ?`
  ).get(id) as DbRow | undefined;
  if (!sub) return c.json({ error: "Submission not found" }, 404);

  const entityId = crypto.randomUUID();
  const now = new Date().toISOString();
  const sj = parseSubmissionJson((sub.result_json as string) ?? "{}");
  const name = (sj.name as string) ?? "Unknown";

  db.prepare(
    `INSERT INTO entities (id, source_id, entity_type, name, canonical_name, bio, position, status, license_class, created_at, updated_at)
     VALUES (?, 'hollywood-api', 'person', ?, ?, ?, ?, 'active', 'public', ?, ?)`
  ).run(entityId, name, name.toLowerCase(), (sj.bio as string) ?? "", position, now, now);

  return c.json({ id: entityId, name, position, status: "active" }, 201);
});

export default router;
