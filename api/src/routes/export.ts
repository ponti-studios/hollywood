import { resolve } from 'node:path';

import { createRoute, z } from '@hono/zod-openapi';
import { OpenAPIHono } from '@hono/zod-openapi';

import { ExportService } from '../db/services/ExportService.js';
import { env } from '../env.js';
import { errorResponse } from './errors.js';

const ExportQuerySchema = z.object({
  table: z.string().optional().openapi({ example: 'entities' }),
  all: z.coerce.boolean().optional().openapi({ example: true }),
  format: z.enum(['parquet', 'jsonl']).default('parquet').openapi({ example: 'jsonl' }),
});

const exportRoute = createRoute({
  method: 'get',
  path: '/export',
  request: { query: ExportQuerySchema },
  responses: {
    200: {
      content: { 'application/json': { schema: z.object({ files: z.array(z.string()) }) } },
      description: 'Exported file paths',
    },
    400: { ...errorResponse, description: 'Pass ?all=true or ?table=<name>' },
    500: { ...errorResponse, description: 'Export failed' },
  },
});

const router = new OpenAPIHono();
const exportService = new ExportService();

router.openapi(exportRoute, (c) => {
  const { table, all, format } = c.req.valid('query');
  if (!all && !table) {
    return c.json({ error: 'Pass ?all=true or ?table=<name>' }, 400);
  }
  const outputDir = resolve(env.HOLLYWOOD_DATA_DIR, 'parquet');
  try {
    const files = all
      ? exportService.exportAll(outputDir, format)
      : [exportService.exportTable(table!, outputDir, format)];
    return c.json({ files }, 200);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return c.json({ error: 'Export failed', detail: msg }, 500);
  }
});

export default router;
