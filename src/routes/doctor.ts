import { existsSync } from 'node:fs';

import { createRoute, z } from '@hono/zod-openapi';
import { OpenAPIHono } from '@hono/zod-openapi';

import { env } from '../env.js';
import { sourceDoctorChecks } from '../ingestion/flows.js';
import { EntityRepository } from '../domain/repositories/EntityRepository.js';

const DoctorCheckSchema = z.object({
  name: z.string(),
  ok: z.boolean(),
  detail: z.string(),
});

const doctorRoute = createRoute({
  method: 'get',
  path: '/doctor',
  responses: {
    200: {
      content: { 'application/json': { schema: z.array(DoctorCheckSchema) } },
      description: 'Health checks',
    },
  },
});

const router = new OpenAPIHono();

router.openapi(doctorRoute, (c) => {
  const entityRepo = new EntityRepository();
  const entityCollisions = entityRepo.countCrossSourceCollisions();
  const checks = [
    { name: 'data_dir', ok: existsSync(env.HOLLYWOOD_DATA_DIR), detail: env.HOLLYWOOD_DATA_DIR },
    { name: 'db_path', ok: existsSync(env.HOLLYWOOD_DB_PATH), detail: env.HOLLYWOOD_DB_PATH },
    {
      name: 'entity_dedup',
      ok: entityCollisions === 0,
      detail: entityCollisions === 0 ? 'No cross-source name collisions' : `${entityCollisions} canonical_name collisions across sources`,
    },
    {
      name: 'tmdb_api_key',
      ok: Boolean(env.TMDB_API_KEY),
      detail: env.TMDB_API_KEY ? 'Configured' : 'Missing',
    },
    {
      name: 'openrouter_api_key',
      ok: Boolean(env.OPENROUTER_API_KEY ?? env.OPENAI_API_KEY),
      detail: env.OPENROUTER_API_KEY || env.OPENAI_API_KEY ? 'Configured' : 'Missing',
    },
    ...sourceDoctorChecks(),
  ];
  return c.json(checks, 200);
});

export default router;
