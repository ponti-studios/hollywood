import { createRoute, OpenAPIHono, z } from '@hono/zod-openapi';

import {
  CandidateSchema,
  CandidateService,
  CreateCandidateInputSchema,
  UpdateCandidateInputSchema,
} from '../services/CandidateService.js';
import { errorResponse } from './errors.js';

// ── Routes ──────────────────────────────────────────────────────────────────

const listRoute = createRoute({
  method: 'get',
  path: '/candidates',
  request: {
    query: z.object({
      limit: z.coerce.number().int().min(1).max(200).default(50).openapi({ example: 50 }),
      offset: z.coerce.number().int().min(0).default(0).openapi({ example: 0 }),
    }),
  },
  responses: {
    200: {
      content: { 'application/json': { schema: z.array(CandidateSchema) } },
      description: 'List of candidates',
    },
  },
});

const getRoute = createRoute({
  method: 'get',
  path: '/candidates/{id}',
  request: { params: z.object({ id: z.string() }) },
  responses: {
    200: {
      content: { 'application/json': { schema: CandidateSchema } },
      description: 'Candidate details',
    },
    404: { ...errorResponse, description: 'Candidate not found' },
  },
});

const createRoute_ = createRoute({
  method: 'post',
  path: '/candidates',
  tags: ['mutating'],
  request: {
    body: { content: { 'application/json': { schema: z.array(CreateCandidateInputSchema) } } },
  },
  responses: {
    201: {
      content: { 'application/json': { schema: z.array(CandidateSchema) } },
      description: 'Created candidates',
    },
  },
});

const updateRoute = createRoute({
  method: 'patch',
  path: '/candidates/{id}',
  tags: ['mutating'],
  request: {
    params: z.object({ id: z.string() }),
    body: { content: { 'application/json': { schema: UpdateCandidateInputSchema } } },
  },
  responses: {
    200: {
      content: { 'application/json': { schema: CandidateSchema } },
      description: 'Updated candidate',
    },
    404: { ...errorResponse, description: 'Candidate not found' },
  },
});

const deleteRoute = createRoute({
  method: 'delete',
  path: '/candidates/{id}',
  tags: ['mutating'],
  request: { params: z.object({ id: z.string() }) },
  responses: {
    204: { description: 'Deleted successfully' },
    404: { ...errorResponse, description: 'Candidate not found' },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();
const candidateService = new CandidateService();

router.openapi(listRoute, (c) => {
  const { limit, offset } = c.req.valid('query');
  const candidates = candidateService.list(limit, offset);
  return c.json(candidates, 200);
});

router.openapi(getRoute, (c) => {
  const { id } = c.req.valid('param');
  const candidate = candidateService.get(id);
  if (!candidate) return c.json({ error: 'Candidate not found' }, 404);
  return c.json(candidate, 200);
});

router.openapi(createRoute_, (c) => {
  const inputs = c.req.valid('json');
  const results = candidateService.create(inputs);
  return c.json(results, 201);
});

router.openapi(updateRoute, (c) => {
  const { id } = c.req.valid('param');
  const input = c.req.valid('json');
  const result = candidateService.update(id, input);
  if (!result) return c.json({ error: 'Candidate not found' }, 404);
  return c.json(result, 200);
});

router.openapi(deleteRoute, (c) => {
  const { id } = c.req.valid('param');
  const deleted = candidateService.delete(id);
  if (!deleted) return c.json({ error: 'Candidate not found' }, 404);
  return c.body(null, 204);
});

export default router;
