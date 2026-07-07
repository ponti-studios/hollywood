import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { SubmissionService } from "../db/services/SubmissionService.js";

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
const submissionService = new SubmissionService();

router.openapi(listRoute, (c) => {
  const projectId = c.req.query("projectId") ?? undefined;
  const result = submissionService.list(projectId);
  return c.json(result as any, 200);
});

router.openapi(deleteRoute, (c) => {
  const { id } = c.req.valid("param");
  const result = submissionService.delete(id);
  if (!result.deleted) return c.json({ error: "Submission not found" }, 404 as const);
  return c.json(result, 200);
});

router.openapi(createCandidateRoute, (c) => {
  const { id } = c.req.valid("param");
  const { position } = c.req.valid("json");
  const result = submissionService.createCandidate(id, position);
  if (!result) return c.json({ error: "Submission not found" }, 404 as const);
  return c.json(result, 201);
});

export default router;
