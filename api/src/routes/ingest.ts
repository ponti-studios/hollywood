import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import * as crypto from "node:crypto";

// ── Schemas ─────────────────────────────────────────────────────────────────

const ExtractionResultSchema = z.object({
  id: z.string().uuid(),
  candidates: z.array(z.unknown()),
  modelName: z.string(),
  rawJson: z.string(),
});

const IngestInputSchema = z.object({
  text: z.string().min(1),
  source: z.string().optional(),
});

// ── Routes ──────────────────────────────────────────────────────────────────

const ingestRoute = createRoute({
  method: "post",
  path: "/ingest",
  request: { body: { content: { "application/json": { schema: IngestInputSchema } } } },
  responses: {
    200: {
      content: { "application/json": { schema: ExtractionResultSchema } },
      description: "Extraction result",
    },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();

router.openapi(ingestRoute, async (c) => {
  const { text, source } = c.req.valid("json");
  const { execSync } = await import("node:child_process");
  const result = execSync(
    `uv run hollywood extract - --dry-run`,
    { input: text, encoding: "utf-8", timeout: 120000, cwd: process.cwd() }
  );
  const id = crypto.randomUUID();
  return c.json({ id, candidates: [], modelName: "openai/gpt-4o-mini", rawJson: result }, 200);
});

export default router;
