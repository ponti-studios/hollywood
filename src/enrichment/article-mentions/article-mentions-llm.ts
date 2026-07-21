import { env } from '../../env.js';
import { parseArticleMentions, SCHEMA_VERSION_V2, TITLE_ROLE_VALUES } from './article-mentions.js';
import type { ArticleMentions } from './article-mentions.js';
import { ExtractionError, OPENROUTER_BASE_URL, DEFAULT_MODEL } from '../submissions/llm.js';

// Generous headroom for reasoning models (e.g. DeepSeek): completion_tokens
// includes reasoning tokens spent before the model emits the actual JSON
// answer, so a small cap truncates the response mid-string on dense articles
// (long career retrospectives, ensemble casts) well before the JSON is done.
const MAX_TOKENS = 16000;

export type LlmProvider = 'openrouter' | 'ollama';

export interface ArticleMentionsResponse {
  rawJson: string;
  mentions: ArticleMentions;
  modelName: string;
}

function getApiKey(): string | null {
  return env.OPENROUTER_API_KEY ?? env.OPENAI_API_KEY ?? null;
}

interface ProviderRequest {
  url: string;
  headers: Record<string, string>;
}

// Ollama's OpenAI-compatible endpoint takes the same request/response shape
// as OpenRouter's chat completions, so only the base URL and auth headers
// differ — no local server API key is required.
function resolveProvider(provider: LlmProvider): ProviderRequest {
  if (provider === 'ollama') {
    return {
      url: `${env.OLLAMA_BASE_URL}/chat/completions`,
      headers: { 'Content-Type': 'application/json' },
    };
  }
  const apiKey = getApiKey();
  if (!apiKey) throw new ExtractionError('OPENROUTER_API_KEY not set');
  return {
    url: `${OPENROUTER_BASE_URL}/chat/completions`,
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': 'https://hollywood.ponti.io',
      'X-Title': 'Hollywood Article Enrichment',
    },
  };
}

// ── System prompt ────────────────────────────────────────────────────────────

function systemPrompt(promptVersion: string): string {
  return `You extract entertainment-industry people, titles, and companies mentioned in a news article.

Return only data grounded in the provided text.
- Do not invent facts. If nothing is mentioned for a category, return an empty array.
- "people" are individuals named in the article (actors, directors, writers, executives, etc.) — not the article's byline author.
- "titles" are named productions: shows, films, specials, podcasts.
- "companies" are named organizations: studios, networks, streamers, agencies, production companies.
- For each person, optionally include "related_to" entries describing their own connection to a title or company explicitly stated in the text. Use the exact name as it appears in the corresponding titles/companies list.
- When related_to targets a title, "relationship" MUST be exactly one of: ${TITLE_ROLE_VALUES.join(', ')}. Pick the closest match — do not invent other values, and do not write a sentence or phrase.
  - Use "actor" for anyone who appeared on screen (starred, played, portrayed, voiced, cast as, returned as, etc.), and put the character's name (if stated) in "character". Leave "character" null for every other relationship.
  - Describe only THIS person's own credit. Never name a co-star, castmate, or anyone else inside "relationship" or "character" — if the text says "X starred alongside Y", that is a relationship for X (type "actor") and a separate relationship for Y (type "actor"), never a relationship that mentions the other's name.
- When related_to targets a company, "relationship" is a short (2-4 word) phrase, e.g. "signed with", "produced by", "developing with".
- Do not fabricate a relationship that isn't stated or clearly implied by the text.
- Preserve the most specific name given by the text (e.g. "Warner Bros. Television" not "Warner Bros.").
- Correct obvious spelling mistakes in names, but preserve intentional spellings.
- Avoid duplicate entries in every array.

Prompt version: ${promptVersion}`;
}

// ── JSON schema ──────────────────────────────────────────────────────────────

function buildJsonSchema(): Record<string, unknown> {
  const relatedToSchema = {
    type: 'object',
    additionalProperties: false,
    properties: {
      name: {
        type: 'string',
        description: 'The name of the title, company, or person this person is connected to.',
      },
      type: {
        type: 'string',
        enum: ['title', 'company', 'person'],
        description: 'What kind of entity this is.',
      },
      relationship: {
        type: 'string',
        description:
          `When type is "title": exactly one of ${TITLE_ROLE_VALUES.join(', ')}. ` +
          `When type is "company" or "person": a short 2-4 word phrase, e.g. "signed with", "produced by".`,
      },
      character: {
        anyOf: [
          {
            type: 'string',
            description:
              "The character name, only when relationship is 'actor' and type is 'title'.",
          },
          { type: 'null' },
        ],
      },
    },
    required: ['name', 'type', 'relationship', 'character'],
  };

  const personSchema = {
    type: 'object',
    additionalProperties: false,
    properties: {
      name: { type: 'string', description: "The person's full name." },
      role_hint: {
        anyOf: [
          { type: 'string', description: "A short guess at their role, e.g. 'director', 'actor'." },
          { type: 'null' },
        ],
      },
      related_to: {
        type: 'array',
        items: relatedToSchema,
        description: 'Titles or companies this person is explicitly connected to.',
      },
    },
    required: ['name', 'role_hint', 'related_to'],
  };

  const titleSchema = {
    type: 'object',
    additionalProperties: false,
    properties: {
      name: { type: 'string', description: 'The title of the production.' },
      format_hint: {
        anyOf: [
          { type: 'string', description: "A short guess at its format, e.g. 'series', 'feature'." },
          { type: 'null' },
        ],
      },
    },
    required: ['name', 'format_hint'],
  };

  const companySchema = {
    type: 'object',
    additionalProperties: false,
    properties: {
      name: { type: 'string', description: "The company's name." },
      type_hint: {
        anyOf: [
          {
            type: 'string',
            description: "A short guess at its type, e.g. 'studio', 'streamer', 'agency'.",
          },
          { type: 'null' },
        ],
      },
    },
    required: ['name', 'type_hint'],
  };

  return {
    type: 'object',
    additionalProperties: false,
    properties: {
      schema_version: { type: 'string', const: SCHEMA_VERSION_V2 },
      people: { type: 'array', items: personSchema },
      titles: { type: 'array', items: titleSchema },
      companies: { type: 'array', items: companySchema },
    },
    required: ['schema_version', 'people', 'titles', 'companies'],
  };
}

// Some local models (e.g. Ollama's gemma4 via mlx) don't honor
// response_format strictly and wrap the JSON in a markdown code fence.
// OpenRouter-backed providers never emit this, so it's a no-op for them.
export function stripCodeFence(content: string): string {
  const trimmed = content.trim();
  const match = /^```(?:json)?\s*\n([\s\S]*?)\n?```$/.exec(trimmed);
  return match ? match[1]!.trim() : trimmed;
}

// ── OpenRouter client ────────────────────────────────────────────────────────

export async function callOpenRouterForArticleMentions(
  text: string,
  promptVersion: string,
  model?: string,
  provider: LlmProvider = 'openrouter',
): Promise<ArticleMentionsResponse> {
  const { url, headers } = resolveProvider(provider);
  const resolvedModel = model || DEFAULT_MODEL;
  const body = {
    model: resolvedModel,
    messages: [
      { role: 'system', content: systemPrompt(promptVersion) },
      { role: 'user', content: text },
    ],
    response_format: {
      type: 'json_schema',
      json_schema: { name: 'article_mentions', strict: true, schema: buildJsonSchema() },
    },
    temperature: 0,
    max_tokens: MAX_TOKENS,
  };

  const resp = await fetch(url, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
    // Reasoning models can spend a while on reasoning tokens before emitting
    // the answer, especially with the larger MAX_TOKENS budget above.
    signal: AbortSignal.timeout(180_000),
  });

  if (!resp.ok) {
    throw new ExtractionError(`${provider} request failed: ${resp.status} ${resp.statusText}`);
  }

  const data = (await resp.json()) as Record<string, unknown>;
  if (data['error']) {
    const err = data['error'] as { message?: string };
    throw new ExtractionError(`${provider} error: ${err.message ?? JSON.stringify(err)}`);
  }

  const choices = data['choices'] as Array<{ message: { content: string | null } }> | undefined;
  if (!choices || !choices.length) throw new ExtractionError(`${provider} returned no choices`);

  // Reasoning models (e.g. DeepSeek) can return a null message content
  // when they only produced reasoning tokens with no final answer.
  const rawContent = choices[0]!.message.content;
  if (!rawContent) throw new ExtractionError(`${provider} returned empty message content`);

  const content = stripCodeFence(rawContent);
  let parsed: unknown;
  try {
    parsed = JSON.parse(content);
  } catch (e) {
    throw new ExtractionError(`Failed to parse LLM response as JSON: ${(e as Error).message}`);
  }

  const mentions = parseArticleMentions(parsed);
  return { rawJson: content, mentions, modelName: resolvedModel };
}
