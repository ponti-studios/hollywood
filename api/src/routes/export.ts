import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { resolve } from "node:path";
import { env } from "../env.js";
import { exportFlow } from "../ingest/flows.js";

const ExportQuerySchema = z.object({
  table: z.string().optional().openapi({ example: "entities" }),
  all: z.coerce.boolean().optional().openapi({ example: true }),
  format: z.enum(["parquet", "jsonl"]).default("parquet").openapi({ example: "jsonl" }),
});

const exportRoute = createRoute({
  method: "get",
  path: "/export",
  request: { query: ExportQuerySchema },
  responses: {
    200: { content: { "application/json": { schema: z.object({ files: z.array(z.string()) }) } }, description: "Exported file paths" },
    400: { description: "Pass ?all=true or ?table=<name>" },
    500: { description: "Export failed" },
  },
});

const router = new OpenAPIHono();

router.openapi(exportRoute, (c) => {
  const { table, all, format } = c.req.valid("query");
  if (!all && !table) {
    return c.json({ error: "Pass ?all=true or ?table=<name>" } as any, 400);
  }
  const outputDir = resolve(env.HOLLYWOOD_DATA_DIR, "parquet");
  try {
    const files = exportFlow(format, outputDir, all ? undefined : table);
    return c.json({ files }, 200);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return c.json({ error: "Export failed", detail: msg } as any, 500);
  }
});

export default router;
