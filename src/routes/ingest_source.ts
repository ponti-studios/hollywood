import { createRoute, z } from '@hono/zod-openapi';
import { OpenAPIHono } from '@hono/zod-openapi';

import { normalizePrefixes } from '../ingestion/adapters/wga.js';
import { runIngestGroup, runIngestSource } from '../ingestion/flows.js';
import type { IngestOptions, RunSummary } from '../ingestion/models.js';
import { errorResponse } from './errors.js';

const RunSummarySchema = z.object({
  run_id: z.string(),
  source_id: z.string(),
  status: z.string(),
  raw_records: z.number().int(),
  normalized: z.record(z.string(), z.number()),
  entities_matched: z.number().int(),
  entities_created: z.number().int(),
  error: z.string().optional(),
});

function toApiSummary(summary: RunSummary) {
  return {
    run_id: summary.runId,
    source_id: summary.sourceId,
    status: summary.status,
    raw_records: summary.rawRecords,
    normalized: summary.normalized,
    entities_matched: summary.entitiesMatched,
    entities_created: summary.entitiesCreated,
    error: summary.error,
  };
}

function toOptions(body: {
  limit?: number;
  since?: string;
  full_text?: boolean;
  prefixes?: string;
}): IngestOptions {
  return {
    limit: body.limit,
    since: body.since ? new Date(body.since) : undefined,
    fullText: body.full_text ?? true,
    prefixes: body.prefixes ? normalizePrefixes(body.prefixes) : undefined,
  };
}

// ── POST /ingest/source ─────────────────────────────────────────────────────

// `limit` has an explicit small example so auto-generated API collections
// don't trigger an unbounded fetch.
const IngestSourceInputSchema = z.object({
  source_id: z.string().openapi({ example: 'variety' }),
  limit: z.number().int().optional().openapi({ example: 1 }),
  since: z.string().optional().openapi({ example: '2024-01-01' }),
  full_text: z.boolean().optional().default(true),
  prefixes: z
    .string()
    .optional()
    .openapi({
      example: 'a,b,c',
      description: 'Comma-separated or compact prefixes (WGA source only)',
    }),
});

const ingestSourceRoute = createRoute({
  method: 'post',
  path: '/ingest/source',
  tags: ['mutating'],
  request: { body: { content: { 'application/json': { schema: IngestSourceInputSchema } } } },
  responses: {
    200: {
      content: { 'application/json': { schema: RunSummarySchema } },
      description: 'Ingest run summary',
    },
    500: { ...errorResponse, description: 'Ingest failed' },
  },
});

// ── POST /ingest/group ───────────────────────────────────────────────────────

const IngestGroupInputSchema = z.object({
  group_name: z.string().openapi({ example: 'news' }),
  limit: z.number().int().optional().openapi({ example: 1 }),
  since: z.string().optional(),
  full_text: z.boolean().optional().default(true),
});

const ingestGroupRoute = createRoute({
  method: 'post',
  path: '/ingest/group',
  tags: ['mutating'],
  request: { body: { content: { 'application/json': { schema: IngestGroupInputSchema } } } },
  responses: {
    200: {
      content: { 'application/json': { schema: z.array(RunSummarySchema) } },
      description: 'Ingest run summaries',
    },
    500: { ...errorResponse, description: 'Ingest failed' },
  },
});

const router = new OpenAPIHono();

router.openapi(ingestSourceRoute, async (c) => {
  const { source_id, ...rest } = c.req.valid('json');
  try {
    const summary = await runIngestSource(source_id, toOptions(rest));
    return c.json(toApiSummary(summary), 200);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return c.json({ error: 'Ingest failed', detail: msg }, 500);
  }
});

router.openapi(ingestGroupRoute, async (c) => {
  const { group_name, ...rest } = c.req.valid('json');
  try {
    const summaries = await runIngestGroup(group_name, toOptions(rest));
    return c.json(summaries.map(toApiSummary), 200);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return c.json({ error: 'Ingest failed', detail: msg }, 500);
  }
});

export default router;
