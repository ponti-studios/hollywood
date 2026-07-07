import { createRoute, z } from "@hono/zod-openapi";
import { OpenAPIHono } from "@hono/zod-openapi";
import { SearchService } from "../db/services/SearchService.js";

const CreditSchema = z.object({
  id: z.string(),
  role: z.string(),
  type: z.string().nullable(),
  production: z.string(),
  network: z.string().nullable(),
});

const SearchResultEntitySchema = z.object({
  id: z.string(),
  name: z.string(),
  agencyBio: z.string().nullable(),
  position: z.string(),
  status: z.string(),
  credits: z.array(CreditSchema),
});

const SearchResultsSchema = z.object({
  total: z.number().int(),
  entities: z.array(SearchResultEntitySchema),
});

const searchRoute = createRoute({
  method: "get",
  path: "/search",
  request: {
    query: z.object({
      q: z.string().min(1).openapi({ example: "Alyson" }),
      limit: z.coerce.number().int().min(1).max(200).default(20).openapi({ example: 20 }),
      offset: z.coerce.number().int().min(0).default(0).openapi({ example: 0 }),
    }),
  },
  responses: {
    200: { content: { "application/json": { schema: SearchResultsSchema } }, description: "Search results" },
  },
});

const router = new OpenAPIHono();

const searchService = new SearchService();

router.openapi(searchRoute, (c) => {
  const { q, limit, offset } = c.req.valid("query");
  const results = searchService.search(q, limit, offset);
  return c.json(results, 200);
});

export default router;
