import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { getDb } from "../db/index.js";
import type { DbRow } from "../db/index.js";
import { enrichCandidate } from "../db/helpers.js";
import * as crypto from "node:crypto";

// ── Schemas ─────────────────────────────────────────────────────────────────

const CreditSchema = z.object({
  id: z.string().openapi({ example: "cr-001" }),
  role: z.string().openapi({ example: "co-executive producer" }),
  type: z.string().nullable().openapi({ example: "tv" }),
  production: z.string().openapi({ example: "THE NEIGHBORHOOD" }),
  network: z.string().nullable().openapi({ example: "CBS" }),
  season: z.number().int().nullable(),
  seasons: z.array(z.number().int()),
  year: z.number().int(),
  years: z.array(z.number().int()),
});

const EmailSchema = z.object({
  address: z.string().openapi({ example: "alyson@agency.com" }),
  contactType: z.string().nullable().openapi({ example: "work" }),
});

const PhoneNumberSchema = z.object({
  number: z.string().openapi({ example: "+1-310-555-0123" }),
  contactType: z.string().nullable().openapi({ example: "mobile" }),
});

const RepresentativeSchema = z.object({
  id: z.string(),
  name: z.string(),
  organization: z.string(),
  representationType: z.string().nullable(),
  emails: z.array(EmailSchema),
  phoneNumbers: z.array(PhoneNumberSchema),
});

const ScriptSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  url: z.string(),
  pageCount: z.number().int(),
  ratings: z.array(z.object({
    scriptId: z.string(),
    raterUserId: z.string(),
    score: z.number().int(),
  })),
});

const SupportingLinkSchema = z.object({
  url: z.string(),
  description: z.string().nullable(),
  linkType: z.string().nullable(),
});

const TagSchema = z.object({
  id: z.string(),
  label: z.string(),
  tagger: z.string(),
});

const CandidateSchema = z.object({
  id: z.string().uuid().openapi({ example: "629100a4-9d5f-4b6e-a9ef-daa66f4933d5" }),
  name: z.string().openapi({ example: "Alyson Fouse" }),
  agencyBio: z.string().nullable().openapi({ example: "Alyson recently was a Co-Executive Producer..." }),
  position: z.string().openapi({ example: "writer" }),
  status: z.string().openapi({ example: "active" }),
  credits: z.array(CreditSchema),
  emails: z.array(EmailSchema),
  phoneNumbers: z.array(PhoneNumberSchema),
  notes: z.array(z.unknown()),
  representatives: z.array(RepresentativeSchema),
  scripts: z.array(ScriptSchema),
  supportingLinks: z.array(SupportingLinkSchema),
  tags: z.array(TagSchema),
  secondWriterName: z.string().nullable(),
  secondWriterEmails: z.array(EmailSchema),
  secondWriterPhoneNumbers: z.array(PhoneNumberSchema),
  secondWriterSupportingLinks: z.array(SupportingLinkSchema),
});

const CreateCandidateInputSchema = z.object({
  name: z.string().min(1),
  agencyBio: z.string().optional(),
  position: z.string().optional(),
  representatives: z
    .array(z.object({
      name: z.string(),
      organization: z.string().optional(),
      emails: z.array(z.object({ address: z.string(), contactType: z.string().optional() })).optional(),
      phoneNumbers: z.array(z.object({ number: z.string(), contactType: z.string().optional() })).optional(),
    }))
    .optional(),
  supportingLinks: z
    .array(z.object({ url: z.string(), description: z.string().optional(), linkType: z.string().optional() }))
    .optional(),
  tags: z.array(z.string()).optional(),
  status: z.string().optional(),
  secondWriterName: z.string().optional(),
  secondWriterEmails: z.array(z.object({ address: z.string(), contactType: z.string().optional() })).optional(),
  secondWriterPhoneNumbers: z.array(z.object({ number: z.string(), contactType: z.string().optional() })).optional(),
  secondWriterSupportingLinks: z
    .array(z.object({ url: z.string(), description: z.string().optional(), linkType: z.string().optional() }))
    .optional(),
});

const UpdateCandidateInputSchema = z.object({
  name: z.string().optional(),
  agencyBio: z.string().optional(),
  position: z.string().optional(),
  status: z.string().optional(),
});

// ── Routes ──────────────────────────────────────────────────────────────────

const listRoute = createRoute({
  method: "get",
  path: "/candidates",
  request: {
    query: z.object({
      limit: z.coerce.number().int().min(1).max(200).default(50).openapi({ example: 50 }),
      offset: z.coerce.number().int().min(0).default(0).openapi({ example: 0 }),
    }),
  },
  responses: {
    200: { content: { "application/json": { schema: z.array(CandidateSchema) } }, description: "List of candidates" },
  },
});

const getRoute = createRoute({
  method: "get",
  path: "/candidates/{id}",
  request: {
    params: z.object({ id: z.string().uuid() }),
  },
  responses: {
    200: { content: { "application/json": { schema: CandidateSchema } }, description: "Candidate details" },
    404: { description: "Candidate not found" },
  },
});

const createRoute_ = createRoute({
  method: "post",
  path: "/candidates",
  request: {
    body: { content: { "application/json": { schema: z.array(CreateCandidateInputSchema) } } },
  },
  responses: {
    201: { content: { "application/json": { schema: z.array(CandidateSchema) } }, description: "Created candidates" },
  },
});

const updateRoute = createRoute({
  method: "patch",
  path: "/candidates/{id}",
  request: {
    params: z.object({ id: z.string().uuid() }),
    body: { content: { "application/json": { schema: UpdateCandidateInputSchema } } },
  },
  responses: {
    200: { content: { "application/json": { schema: CandidateSchema } }, description: "Updated candidate" },
    404: { description: "Candidate not found" },
  },
});

const deleteRoute = createRoute({
  method: "delete",
  path: "/candidates/{id}",
  request: {
    params: z.object({ id: z.string().uuid() }),
  },
  responses: {
    204: { description: "Deleted successfully" },
    404: { description: "Candidate not found" },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();

router.openapi(listRoute, (c) => {
  const { limit, offset } = c.req.valid("query");
  const db = getDb();
  const rows = db
    .prepare("SELECT * FROM entities WHERE entity_type = 'person' ORDER BY name LIMIT ? OFFSET ?")
    .all(limit, offset) as DbRow[];
  return c.json(rows.map(enrichCandidate) as z.infer<typeof CandidateSchema>[], 200);
});

router.openapi(getRoute, (c) => {
  const { id } = c.req.valid("param");
  const db = getDb();
  const row = db
    .prepare("SELECT * FROM entities WHERE id = ? AND entity_type = 'person'")
    .get(id) as DbRow | undefined;
  if (!row) return c.json({ error: "Candidate not found" } as any, 404);
  return c.json(enrichCandidate(row) as z.infer<typeof CandidateSchema>, 200);
});

router.openapi(createRoute_, (c) => {
  const inputs = c.req.valid("json");
  const db = getDb();
  const now = new Date().toISOString();
  const results: Record<string, unknown>[] = [];
  for (const input of inputs) {
    const entityId = crypto.randomUUID();
    db.prepare(
      `INSERT INTO entities (id, source_id, entity_type, name, canonical_name, bio, position, status, license_class, created_at, updated_at)
       VALUES (?, 'hollywood-api', 'person', ?, ?, ?, ?, 'active', 'public', ?, ?)`
    ).run(
      entityId,
      input.name,
      input.name.toLowerCase(),
      input.agencyBio ?? "",
      input.position ?? "",
      now,
      now,
    );
    results.push(enrichCandidate({ id: entityId, name: input.name, bio: input.agencyBio ?? null, position: input.position ?? "", status: "active" } as any));
  }
  return c.json(results as z.infer<typeof CandidateSchema>[], 201);
});

router.openapi(updateRoute, (c) => {
  const { id } = c.req.valid("param");
  const input = c.req.valid("json");
  const db = getDb();
  const existing = db.prepare("SELECT * FROM entities WHERE id = ? AND entity_type = 'person'").get(id) as DbRow | undefined;
  if (!existing) return c.json({ error: "Candidate not found" } as any, 404);
  const now = new Date().toISOString();
  const sets: string[] = [];
  const vals: unknown[] = [];
  if (input.name !== undefined) { sets.push("name = ?"); vals.push(input.name); sets.push("canonical_name = ?"); vals.push(input.name.toLowerCase()); }
  if (input.agencyBio !== undefined) { sets.push("bio = ?"); vals.push(input.agencyBio); }
  if (input.position !== undefined) { sets.push("position = ?"); vals.push(input.position); }
  if (input.status !== undefined) { sets.push("status = ?"); vals.push(input.status); }
  sets.push("updated_at = ?");
  vals.push(now);
  vals.push(id);
  db.prepare(`UPDATE entities SET ${sets.join(", ")} WHERE id = ?`).run(...vals);
  const updated = db.prepare("SELECT * FROM entities WHERE id = ?").get(id) as DbRow;
  return c.json(enrichCandidate(updated) as z.infer<typeof CandidateSchema>, 200);
});

router.openapi(deleteRoute, (c) => {
  const { id } = c.req.valid("param");
  const db = getDb();
  const existing = db.prepare("SELECT id FROM entities WHERE id = ? AND entity_type = 'person'").get(id);
  if (!existing) return c.json({ error: "Candidate not found" } as any, 404);
  db.prepare("DELETE FROM entities WHERE id = ?").run(id);
  return c.body(null, 204);
});

export default router;
