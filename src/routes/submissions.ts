import { createRoute, z } from '@hono/zod-openapi';
import { OpenAPIHono } from '@hono/zod-openapi';

import { SubmissionSchema, SubmissionService } from '../services/SubmissionService.js';

// ── Routes ──────────────────────────────────────────────────────────────────

const listRoute = createRoute({
  method: 'get',
  path: '/submissions',
  responses: {
    200: {
      content: { 'application/json': { schema: z.array(SubmissionSchema) } },
      description: 'List of submissions',
    },
  },
});

const deleteRoute = createRoute({
  method: 'delete',
  path: '/submissions/{id}',
  tags: ['mutating'],
  request: { params: z.object({ id: z.string().min(1) }) },
  responses: {
    200: {
      content: { 'application/json': { schema: z.object({ deleted: z.boolean() }) } },
      description: 'Deleted submission',
    },
    404: { description: 'Submission not found' },
  },
});

const createCandidateRoute = createRoute({
  method: 'post',
  path: '/submissions/{id}/candidate',
  tags: ['mutating'],
  request: {
    params: z.object({ id: z.string().min(1) }),
    body: { content: { 'application/json': { schema: z.object({ position: z.string() }) } } },
  },
  responses: {
    201: {
      content: {
        'application/json': {
          schema: z.object({
            id: z.string(),
            name: z.string(),
            position: z.string(),
            status: z.string(),
          }),
        },
      },
      description: 'Created candidate from submission',
    },
    404: { description: 'Submission not found' },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();
const submissionService = new SubmissionService();

router.openapi(listRoute, (c) => {
  const projectId = c.req.query('projectId') ?? undefined;
  const result = submissionService.list(projectId);
  return c.json(result, 200);
});

router.openapi(deleteRoute, (c) => {
  const { id } = c.req.valid('param');
  const result = submissionService.delete(id);
  if (!result.deleted) return c.json({ error: 'Submission not found' }, 404 as const);
  return c.json(result, 200);
});

router.openapi(createCandidateRoute, (c) => {
  const { id } = c.req.valid('param');
  const { position } = c.req.valid('json');
  const result = submissionService.createCandidate(id, position);
  if (!result) return c.json({ error: 'Submission not found' }, 404 as const);
  return c.json(result, 201);
});

export default router;
