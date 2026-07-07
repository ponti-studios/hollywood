import { createRoute, OpenAPIHono, z } from "@hono/zod-openapi";
import { CandidateService } from "../db/services/CandidateService.js";

// ── Schemas ─────────────────────────────────────────────────────────────────

const CreditSchema = z.object({
  id: z.string(),
  role: z.string(),
  type: z.string().nullable(),
  production: z.string(),
  network: z.string().nullable(),
});

const EmailSchema = z.object({
  address: z.string(),
  contactType: z.string().nullable(),
});

const PhoneNumberSchema = z.object({
  number: z.string(),
  contactType: z.string().nullable(),
});

const RepresentativeSchema = z.object({
  id: z.string(),
  name: z.string(),
  organization: z.string(),
  representationType: z.string().nullable(),
  emails: z.array(EmailSchema),
  phoneNumbers: z.array(PhoneNumberSchema),
});

const TagSchema = z.object({
  id: z.string(),
  label: z.string(),
  tagger: z.string(),
});

const LinkSchema = z.object({
  url: z.string(),
  linkType: z.string(),
});

const CandidateSchema = z.object({
  id: z.string(),
  name: z.string(),
  agencyBio: z.string().nullable(),
  position: z.string(),
  status: z.string(),
  credits: z.array(CreditSchema),
  emails: z.array(EmailSchema),
  phoneNumbers: z.array(PhoneNumberSchema),
  tags: z.array(TagSchema),
  representatives: z.array(RepresentativeSchema),
  links: z.array(LinkSchema),
});

const CreateCandidateInputSchema = z.object({
  name: z.string().min(1),
  agencyBio: z.string().optional(),
  position: z.string().optional(),
  tags: z.array(z.string()).optional(),
  supportingLinks: z
    .array(
      z.object({
        url: z.string(),
        description: z.string().optional(),
        linkType: z.string().optional(),
      }),
    )
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
    200: {
      content: { "application/json": { schema: z.array(CandidateSchema) } },
      description: "List of candidates",
    },
  },
});

const getRoute = createRoute({
  method: "get",
  path: "/candidates/{id}",
  request: { params: z.object({ id: z.string() }) },
  responses: {
    200: {
      content: { "application/json": { schema: CandidateSchema } },
      description: "Candidate details",
    },
    404: { description: "Candidate not found" },
  },
});

const createRoute_ = createRoute({
  method: "post",
  path: "/candidates",
  tags: ["mutating"],
  request: {
    body: { content: { "application/json": { schema: z.array(CreateCandidateInputSchema) } } },
  },
  responses: {
    201: {
      content: { "application/json": { schema: z.array(CandidateSchema) } },
      description: "Created candidates",
    },
  },
});

const updateRoute = createRoute({
  method: "patch",
  path: "/candidates/{id}",
  tags: ["mutating"],
  request: {
    params: z.object({ id: z.string() }),
    body: { content: { "application/json": { schema: UpdateCandidateInputSchema } } },
  },
  responses: {
    200: {
      content: { "application/json": { schema: CandidateSchema } },
      description: "Updated candidate",
    },
    404: { description: "Candidate not found" },
  },
});

const deleteRoute = createRoute({
  method: "delete",
  path: "/candidates/{id}",
  tags: ["mutating"],
  request: { params: z.object({ id: z.string() }) },
  responses: {
    204: { description: "Deleted successfully" },
    404: { description: "Candidate not found" },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();
const candidateService = new CandidateService();

router.openapi(listRoute, (c) => {
  const { limit, offset } = c.req.valid("query");
  const candidates = candidateService.list(limit, offset);
  return c.json(candidates as z.infer<typeof CandidateSchema>[], 200);
});

router.openapi(getRoute, (c) => {
  const { id } = c.req.valid("param");
  const candidate = candidateService.get(id);
  if (!candidate) return c.json({ error: "Candidate not found" } as any, 404);
  return c.json(candidate as z.infer<typeof CandidateSchema>, 200);
});

router.openapi(createRoute_, (c) => {
  const inputs = c.req.valid("json");
  const results = candidateService.create(inputs);
  return c.json(results as z.infer<typeof CandidateSchema>[], 201);
});

router.openapi(updateRoute, (c) => {
  const { id } = c.req.valid("param");
  const input = c.req.valid("json");
  const result = candidateService.update(id, input);
  if (!result) return c.json({ error: "Candidate not found" } as any, 404);
  return c.json(result as z.infer<typeof CandidateSchema>, 200);
});

router.openapi(deleteRoute, (c) => {
  const { id } = c.req.valid("param");
  const deleted = candidateService.delete(id);
  if (!deleted) return c.json({ error: "Candidate not found" } as any, 404);
  return c.body(null, 204);
});

export default router;
