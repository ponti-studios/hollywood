import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { normalizeFlow } from "../ingest/flows.js";

const NormalizeInputSchema = z.object({
  source_id: z.string().optional().openapi({ example: "variety" }),
});

const normalizeRoute = createRoute({
  method: "post",
  path: "/normalize",
  tags: ["mutating"],
  request: {
    body: { content: { "application/json": { schema: NormalizeInputSchema } } },
  },
  responses: {
    200: { content: { "application/json": { schema: z.record(z.string(), z.number()) } }, description: "Row counts by table" },
    500: { description: "Normalization failed" },
  },
});

const router = new OpenAPIHono();

router.openapi(normalizeRoute, async (c) => {
  const { source_id } = c.req.valid("json");
  try {
    const counts = await normalizeFlow(source_id);
    return c.json(counts, 200);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return c.json({ error: "Normalization failed", detail: msg } as any, 500);
  }
});

export default router;
