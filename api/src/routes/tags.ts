import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { getDb } from "../db/index.js";

// ── Routes ──────────────────────────────────────────────────────────────────

const listRoute = createRoute({
  method: "get",
  path: "/tags",
  responses: {
    200: {
      content: { "application/json": { schema: z.array(z.object({ id: z.number().int(), tagName: z.string() })) } },
      description: "List of tags",
    },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();

router.openapi(listRoute, (c) => {
  const db = getDb();
  const tags = db.prepare("SELECT id, tag AS tagName FROM tags ORDER BY tag").all() as { id: number; tagName: string }[];
  return c.json(tags, 200);
});

export default router;
