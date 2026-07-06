import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { getDb } from "../db/index.js";
import type { DbRow } from "../db/index.js";
import { enrichCandidate, loadCredits } from "../db/helpers.js";

// ── Schemas ─────────────────────────────────────────────────────────────────

const CreditSchema = z.object({
  id: z.string(),
  role: z.string(),
  type: z.string().nullable(),
  production: z.string(),
  network: z.string().nullable(),
  season: z.number().int().nullable(),
  seasons: z.array(z.number().int()),
  year: z.number().int(),
  years: z.array(z.number().int()),
});

const SearchResultEntitySchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  agencyBio: z.string().nullable(),
  position: z.string(),
  status: z.string(),
  credits: z.array(CreditSchema),
});

const SearchResultsSchema = z.object({
  total: z.number().int(),
  entities: z.array(SearchResultEntitySchema),
});

// ── Routes ──────────────────────────────────────────────────────────────────

const searchRoute = createRoute({
  method: "get",
  path: "/search",
  request: {
    query: z.object({
      q: z.string().min(1).openapi({ example: "Alyson" }),
      limit: z.coerce.number().int().min(1).max(200).default(20).openapi({ example: 20 }),
      offset: z.coerce.number().int().min(0).default(0).openapi({ example: 0 }),
    }),
  },
  responses: {
    200: { content: { "application/json": { schema: SearchResultsSchema } }, description: "Search results" },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();

router.openapi(searchRoute, (c) => {
  const { q, limit, offset } = c.req.valid("query");
  const db = getDb();
  const pattern = `%${q}%`;
  const total = (db.prepare("SELECT COUNT(*) AS count FROM entities WHERE name LIKE ?").get(pattern) as { count: number }).count;
  const entities = db
    .prepare("SELECT id, name, bio, position, status FROM entities WHERE name LIKE ? ORDER BY name LIMIT ? OFFSET ?")
    .all(pattern, limit, offset) as DbRow[];

  return c.json({
    total,
    entities: entities.map((row) => ({
      id: row.id,
      name: row.name,
      agencyBio: row.bio ?? null,
      position: row.position ?? "",
      status: row.status ?? "active",
      credits: loadCredits(row.id as string),
    })),
  } as z.infer<typeof SearchResultsSchema>, 200);
});

export default router;
