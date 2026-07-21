import { createRoute, z } from '@hono/zod-openapi';
import { OpenAPIHono } from '@hono/zod-openapi';

import { listSources } from '../ingestion/registry.js';

const SourceSchema = z.object({
  source_id: z.string(),
  name: z.string(),
  kind: z.string(),
  groups: z.array(z.string()),
  license_class: z.string(),
  default_full_text: z.boolean(),
  api_key_env: z.string().nullable(),
});

const sourcesRoute = createRoute({
  method: 'get',
  path: '/sources',
  responses: {
    200: {
      content: { 'application/json': { schema: z.array(SourceSchema) } },
      description: 'Built-in ingest sources',
    },
  },
});

const router = new OpenAPIHono();

router.openapi(sourcesRoute, (c) => {
  const sources = listSources().map((source) => ({
    source_id: source.sourceId,
    name: source.name,
    kind: source.kind,
    groups: [...source.groups],
    license_class: source.licenseClass,
    default_full_text: source.defaultFullText,
    api_key_env: source.apiKeyEnv ?? null,
  }));
  return c.json(sources, 200);
});

export default router;
