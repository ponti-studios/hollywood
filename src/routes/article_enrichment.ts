import { createRoute, z } from '@hono/zod-openapi';
import { OpenAPIHono } from '@hono/zod-openapi';

import { ArticleEnrichmentService } from '../services/ArticleEnrichmentService.js';
import { errorResponse } from './errors.js';

const EnrichSummarySchema = z.object({
  articles_processed: z.number().int(),
  articles_failed: z.number().int(),
  people_created: z.number().int(),
  people_matched: z.number().int(),
  titles_created: z.number().int(),
  titles_matched: z.number().int(),
  companies_created: z.number().int(),
  companies_matched: z.number().int(),
  credits_created: z.number().int(),
  company_relations_created: z.number().int(),
  mentions_recorded: z.number().int(),
});

// `limit` has an explicit small example so auto-generated API collections
// don't trigger unbounded LLM calls.
const EnrichArticlesInputSchema = z.object({
  limit: z.number().int().optional().openapi({ example: 5 }),
  model: z.string().optional(),
  prompt_version: z.string().optional(),
  provider: z.enum(['openrouter', 'ollama']).optional(),
});

const enrichArticlesRoute = createRoute({
  method: 'post',
  path: '/articles/enrich',
  tags: ['mutating'],
  request: { body: { content: { 'application/json': { schema: EnrichArticlesInputSchema } } } },
  responses: {
    200: {
      content: { 'application/json': { schema: EnrichSummarySchema } },
      description: 'Article enrichment summary',
    },
    500: { ...errorResponse, description: 'Enrichment failed' },
  },
});

const router = new OpenAPIHono();

router.openapi(enrichArticlesRoute, async (c) => {
  const { limit, model, prompt_version, provider } = c.req.valid('json');
  try {
    const service = new ArticleEnrichmentService();
    const summary = await service.enrichNext({
      limit: limit ?? 5,
      model,
      promptVersion: prompt_version,
      provider,
    });
    return c.json(
      {
        articles_processed: summary.articlesProcessed,
        articles_failed: summary.articlesFailed,
        people_created: summary.peopleCreated,
        people_matched: summary.peopleMatched,
        titles_created: summary.titlesCreated,
        titles_matched: summary.titlesMatched,
        companies_created: summary.companiesCreated,
        companies_matched: summary.companiesMatched,
        credits_created: summary.creditsCreated,
        company_relations_created: summary.companyRelationsCreated,
        mentions_recorded: summary.mentionsRecorded,
      },
      200,
    );
  } catch (e) {
    const msg = e instanceof Error ? e.message : String(e);
    return c.json({ error: 'Enrichment failed', detail: msg }, 500);
  }
});

export default router;
