import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { AssistantService } from "../assistant/service.js";

const ChatInputSchema = z.object({
  query: z.string().min(1).openapi({ example: "What's our budget for the March tour?" }),
});

const ChatResponseSchema = z.object({
  agent: z.string(),
  response: z.string(),
});

const chatRoute = createRoute({
  method: "post",
  path: "/assistant/chat",
  tags: ["mutating"],
  request: { body: { content: { "application/json": { schema: ChatInputSchema } } } },
  responses: {
    200: { content: { "application/json": { schema: ChatResponseSchema } }, description: "Director-routed assistant response" },
    500: { description: "Assistant failed to route or respond" },
  },
});

const router = new OpenAPIHono();
const assistantService = new AssistantService();

router.openapi(chatRoute, async (c) => {
  const { query } = c.req.valid("json");
  try {
    const result = await assistantService.chat(query);
    return c.json(result, 200);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return c.json({ error: "Assistant failed", detail: msg } as any, 500);
  }
});

export default router;
