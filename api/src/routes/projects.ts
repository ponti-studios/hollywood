import { createRoute, z } from '@hono/zod-openapi';
import { OpenAPIHono } from '@hono/zod-openapi';

import { ProjectService } from '../db/services/ProjectService.js';

// ── Schemas ─────────────────────────────────────────────────────────────────

const ProjectSchema = z.object({
  id: z.string(),
  title: z.string(),
  season: z.number().int(),
  genres: z.array(z.string()),
  format: z.string().nullable(),
  imdbLink: z.string().nullable(),
  posterLink: z.string().nullable(),
});

const CreateProjectSchema = z.object({
  title: z.string().min(1),
  format: z.string().optional(),
  genres: z.array(z.string()).optional(),
  season: z.number().int().optional(),
  imdbLink: z.string().optional(),
});

const UpdateProjectSchema = z.object({
  title: z.string().optional(),
  format: z.string().optional(),
  genres: z.array(z.string()).optional(),
  season: z.number().int().optional(),
  imdbLink: z.string().optional(),
});

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
    404: { description: 'Project not found' },
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
    404: { description: 'Project not found' },
  },
});

// ── Router ──────────────────────────────────────────────────────────────────

const router = new OpenAPIHono();
const projectService = new ProjectService();

router.openapi(listRoute, (c) => {
  const projects = projectService.list();
  return c.json(projects as z.infer<typeof ProjectSchema>[], 200);
});

router.openapi(getRoute, (c) => {
  const { id } = c.req.valid('param');
  const project = projectService.get(id);
  if (!project) return c.json({ error: 'Project not found' } as any, 404);
  return c.json(project as z.infer<typeof ProjectSchema>, 200);
});

router.openapi(createRoute_, (c) => {
  const input = c.req.valid('json');
  const project = projectService.create(input);
  return c.json(project as z.infer<typeof ProjectSchema>, 201);
});

router.openapi(updateRoute, (c) => {
  const { id } = c.req.valid('param');
  const input = c.req.valid('json');
  const result = projectService.update(id, input);
  if (!result) return c.json({ error: 'Project not found' } as any, 404);
  return c.json(result as z.infer<typeof ProjectSchema>, 200);
});

export default router;
