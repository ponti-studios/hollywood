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

// Constructed lazily (not at module load) so the whole API doesn't fail to
// start when OPENROUTER_API_KEY is unset — only this endpoint does, on the
// first request that hits it.
let assistantService: AssistantService | null = null;
function getAssistantService(): AssistantService {
  if (!assistantService) assistantService = new AssistantService();
  return assistantService;
}

router.openapi(chatRoute, async (c) => {
  const { query } = c.req.valid("json");
  try {
    const result = await getAssistantService().chat(query);
    return c.json(result, 200);
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return c.json({ error: "Assistant failed", detail: msg } as any, 500);
  }
});

export default router;
