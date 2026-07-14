import { z } from '@hono/zod-openapi';

const ErrorSchema = z.object({
  error: z.string(),
  detail: z.string().optional(),
});

export const errorResponse = {
  content: { 'application/json': { schema: ErrorSchema } },
} as const;
