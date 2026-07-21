import { createRoute, z } from '@hono/zod-openapi';
import { OpenAPIHono } from '@hono/zod-openapi';

import {
  CreateProjectSchema,
  ProjectSchema,
  ProjectService,
  UpdateProjectSchema,
} from '../services/ProjectService.js';
import { errorResponse } from './errors.js';

// ── Routes ──────────────────────────────────────────────────────────────────

const listRoute = createRoute({
  method: 'get',
  path: '/projects',
  responses: {
    200: {
      content: { 'application/json': { schema: z.array(ProjectSchema) } },
      description: 'List of projects',
    },
  },
});

const getRoute = createRoute({
  method: 'get',
  path: '/projects/{id}',
  request: { params: z.object({ id: z.string() }) },
  responses: {
    200: {
      content: { 'application/json': { schema: ProjectSchema } },
      description: 'Project details',
    },
    404: { ...errorResponse, description: 'Project not found' },
  },
});

const createRoute_ = createRoute({
  method: 'post',
  path: '/projects',
  tags: ['mutating'],
  request: { body: { content: { 'application/json': { schema: CreateProjectSchema } } } },
  responses: {
    201: {
      content: { 'application/json': { schema: ProjectSchema } },
      description: 'Created project',
    },
  },
});

const updateRoute = createRoute({
  method: 'patch',
  path: '/projects/{id}',
  tags: ['mutating'],
  request: {
    params: z.object({ id: z.string() }),
    body: { content: { 'application/json': { schema: UpdateProjectSchema } } },
  },
  responses: {
    200: {
      content: { 'application/json': { schema: ProjectSchema } },
      description: 'Updated project',
    },
    404: { ...errorResponse, description: 'Project not found' },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();
const projectService = new ProjectService();

router.openapi(listRoute, (c) => {
  const projects = projectService.list();
  return c.json(projects, 200);
});

router.openapi(getRoute, (c) => {
  const { id } = c.req.valid('param');
  const project = projectService.get(id);
  if (!project) return c.json({ error: 'Project not found' }, 404);
  return c.json(project, 200);
});

router.openapi(createRoute_, (c) => {
  const input = c.req.valid('json');
  const project = projectService.create(input);
  return c.json(project, 201);
});

router.openapi(updateRoute, (c) => {
  const { id } = c.req.valid('param');
  const input = c.req.valid('json');
  const result = projectService.update(id, input);
  if (!result) return c.json({ error: 'Project not found' }, 404);
  return c.json(result, 200);
});

export default router;
