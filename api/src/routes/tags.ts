import { createRoute, z } from '@hono/zod-openapi';
import { OpenAPIHono } from '@hono/zod-openapi';

import { TagRepository } from '../db/repositories/TagRepository.js';

const listRoute = createRoute({
  method: 'get',
  path: '/tags',
  responses: {
    200: {
      content: {
        'application/json': { schema: z.array(z.object({ id: z.string(), tagName: z.string() })) },
      },
      description: 'List of tags',
    },
  },
});

const router = new OpenAPIHono();

const tagRepo = new TagRepository();

router.openapi(listRoute, (c) => {
  const tags = tagRepo.findAll();
  return c.json(tags, 200);
});

export default router;
