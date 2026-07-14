import { z } from '@hono/zod-openapi';

export const ErrorSchema = z.object({
  error: z.string(),
  detail: z.string().optional(),
});

export const errorResponse = {
  content: { 'application/json': { schema: ErrorSchema } },
} as const;
