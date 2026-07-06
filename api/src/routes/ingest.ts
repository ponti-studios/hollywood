import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { execSync } from "node:child_process";
import { resolve } from "node:path";
import * as crypto from "node:crypto";

// ── Schemas ─────────────────────────────────────────────────────────────────

const CreditSchema = z.object({
  role: z.string(),
  type: z.string().nullable(),
  production: z.string(),
  network: z.string().nullable(),
});

const CandidateSummarySchema = z.object({
  id: z.string(),
  name: z.string(),
  bio: z.string(),
  position: z.string(),
  num_credits: z.number().int(),
  num_tags: z.number().int(),
  num_orgs: z.number().int(),
});

const IngestResultSchema = z.object({
  run_id: z.string(),
  model_name: z.string(),
  candidates: z.array(CandidateSummarySchema),
});

const IngestInputSchema = z.object({
  text: z.string().min(1).openapi({ example: "Jane Doe is a writer on THE SHOW..." }),
});

// ── Routes ──────────────────────────────────────────────────────────────────

const ingestRoute = createRoute({
  method: "post",
  path: "/ingest",
  request: {
    body: { content: { "application/json": { schema: IngestInputSchema } } },
  },
  responses: {
    200: {
      content: { "application/json": { schema: IngestResultSchema } },
      description: "Ingestion result with materialized candidates",
    },
    500: { description: "Extraction failed" },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();

router.openapi(ingestRoute, async (c) => {
  const { text } = c.req.valid("json");
  const hollywoodRoot = resolve(process.cwd(), "..");

  let raw: string;
  try {
    raw = execSync(
      `uv run python -m hollywood.ingest_doc`,
      {
        input: text,
        encoding: "utf-8",
        timeout: 120000,
        cwd: hollywoodRoot,
        maxBuffer: 10 * 1024 * 1024,
      },
    );
  } catch (e: unknown) {
    const msg = e instanceof Error ? e.message : String(e);
    console.error("Ingest failed:", msg);
    return c.json({ error: "Extraction failed", detail: msg } as any, 500);
  }

  try {
    const parsed = JSON.parse(raw);
    return c.json(parsed, 200);
  } catch {
    return c.json({ error: "Failed to parse extraction result", raw } as any, 500);
  }
});

export default router;
