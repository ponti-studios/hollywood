import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { PROMPT_VERSION_V1 } from "../ingest/extraction.js";
import { parseEml } from "../ingest/eml.js";
import { ExtractionError, callOpenRouter } from "../ingest/llm.js";
import { IngestService } from "../db/services/IngestService.js";
import type { Candidate } from "../ingest/extraction.js";

// ── Schemas ─────────────────────────────────────────────────────────────────

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
  text: z.string().min(1).optional(),
  documents: z.array(z.string().min(1)).optional(),
  model: z.string().optional().openapi({ example: "openai/gpt-4o-mini" }),
  prompt_version: z.string().optional().openapi({ example: "v1" }),
});

const IngestUploadSchema = z.object({
  file: z.instanceof(File).openapi({ type: "string", format: "binary" }),
  model: z.string().optional(),
  prompt_version: z.string().optional(),
});

// ── Routes ──────────────────────────────────────────────────────────────────

const ingestRoute = createRoute({
  method: "post",
  path: "/ingest",
  tags: ["mutating"],
  request: {
    body: {
      content: {
        "application/json": { schema: IngestInputSchema },
        "multipart/form-data": { schema: IngestUploadSchema },
      },
    },
  },
  responses: {
    200: {
      content: { "application/json": { schema: IngestResultSchema } },
      description: "Ingestion result with materialized candidates",
    },
    400: { description: "Missing text, documents, or file" },
    500: { description: "Extraction failed" },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();
const ingestService = new IngestService();

function summarize(entityId: string, candidate: Candidate) {
  return {
    id: entityId,
    name: candidate.name,
    bio: candidate.bio,
    position: candidate.position ?? "",
    num_credits: candidate.credits.length,
    num_tags: candidate.tags.length,
    num_orgs: candidate.organizations.length,
  };
}

router.openapi(ingestRoute, async (c) => {
  const contentType = c.req.header("content-type") ?? "";
  let texts: string[];
  let model: string | undefined;
  let promptVersion: string;

  if (contentType.startsWith("multipart/form-data")) {
    const { file, model: uploadModel, prompt_version } = c.req.valid("form") as z.infer<typeof IngestUploadSchema>;
    const cleaned = await parseEml(Buffer.from(await file.arrayBuffer()));
    texts = cleaned ? [cleaned] : [];
    model = uploadModel;
    promptVersion = prompt_version ?? PROMPT_VERSION_V1;
  } else {
    const { text, documents, model: jsonModel, prompt_version } = c.req.valid("json") as z.infer<typeof IngestInputSchema>;
    texts = documents && documents.length ? documents : text ? [text] : [];
    model = jsonModel;
    promptVersion = prompt_version ?? PROMPT_VERSION_V1;
  }

  if (!texts.length) {
    return c.json({ error: "Provide either 'text', 'documents', or 'file'" } as any, 400);
  }

  const runId = ingestService.startRunRaw("extraction", { source: "api_ingest" });
  const candidatesOut: ReturnType<typeof summarize>[] = [];
  let modelName = model ?? "";

  try {
    for (const doc of texts) {
      const result = await callOpenRouter(doc, promptVersion, model);
      modelName = result.modelName;

      const rawId = ingestService.insertExtractionRawRecord(runId, "api_ingest", "api_ingest", String(hashText(doc)));

      for (const candidate of result.packet.candidates) {
        ingestService.saveExtractionResult(runId, "api_ingest", candidate, result.modelName, promptVersion, result.rawJson, rawId);
        const entityId = ingestService.materializeCandidate(candidate, "api_ingest");
        candidatesOut.push(summarize(entityId, candidate));
      }
    }
  } catch (e) {
    const msg = e instanceof ExtractionError || e instanceof Error ? e.message : String(e);
    console.error("Ingest failed:", msg);
    return c.json({ error: "Extraction failed", detail: msg } as any, 500);
  }

  return c.json({ run_id: runId, model_name: modelName, candidates: candidatesOut }, 200);
});

function hashText(text: string): number {
  let hash = 0;
  for (let i = 0; i < text.length; i++) {
    hash = (Math.imul(31, hash) + text.charCodeAt(i)) | 0;
  }
  return hash;
}

export default router;
