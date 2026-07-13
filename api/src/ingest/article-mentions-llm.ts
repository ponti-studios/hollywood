import { parseArticleMentions, SCHEMA_VERSION_V1 } from "./article-mentions.js";
import type { ArticleMentions } from "./article-mentions.js";
import { env } from "../env.js";
import { ExtractionError, OPENROUTER_BASE_URL, DEFAULT_MODEL } from "./llm.js";

const MAX_TOKENS = 4000;

export interface ArticleMentionsResponse {
  rawJson: string;
  mentions: ArticleMentions;
  modelName: string;
}

function getApiKey(): string | null {
  return env.OPENROUTER_API_KEY ?? env.OPENAI_API_KEY ?? null;
}

// ── System prompt ────────────────────────────────────────────────────────────

function systemPrompt(promptVersion: string): string {
  return `You extract entertainment-industry people, titles, and companies mentioned in a news article.

Return only data grounded in the provided text.
- Do not invent facts. If nothing is mentioned for a category, return an empty array.
- "people" are individuals named in the article (actors, directors, writers, executives, etc.) — not the article's byline author.
- "titles" are named productions: shows, films, specials, podcasts.
- "companies" are named organizations: studios, networks, streamers, agencies, production companies.
- For each person, optionally include "related_to" entries describing their connection to a title or company explicitly stated in the text (e.g. "attached to direct", "cast in", "signed with", "executive producing"). Use the exact name as it appears in the corresponding titles/companies list.
- Do not fabricate a relationship that isn't stated or clearly implied by the text.
- Preserve the most specific name given by the text (e.g. "Warner Bros. Television" not "Warner Bros.").
- Correct obvious spelling mistakes in names, but preserve intentional spellings.
- Avoid duplicate entries in every array.

Prompt version: ${promptVersion}`;
}

// ── JSON schema ──────────────────────────────────────────────────────────────

function buildJsonSchema(): Record<string, unknown> {
  const relatedToSchema = {
    type: "object",
    additionalProperties: false,
    properties: {
      name: { type: "string", description: "The name of the title or company this person is connected to." },
      type: { type: "string", enum: ["title", "company", "person"], description: "What kind of entity this is." },
      relationship: { type: "string", description: "The stated relationship, e.g. 'attached to direct', 'cast in', 'signed with'." },
    },
    required: ["name", "type", "relationship"],
  };

  const personSchema = {
    type: "object",
    additionalProperties: false,
    properties: {
      name: { type: "string", description: "The person's full name." },
      role_hint: { anyOf: [{ type: "string", description: "A short guess at their role, e.g. 'director', 'actor'." }, { type: "null" }] },
      related_to: { type: "array", items: relatedToSchema, description: "Titles or companies this person is explicitly connected to." },
    },
    required: ["name", "role_hint", "related_to"],
  };

  const titleSchema = {
    type: "object",
    additionalProperties: false,
    properties: {
      name: { type: "string", description: "The title of the production." },
      format_hint: { anyOf: [{ type: "string", description: "A short guess at its format, e.g. 'series', 'feature'." }, { type: "null" }] },
    },
    required: ["name", "format_hint"],
  };

  const companySchema = {
    type: "object",
    additionalProperties: false,
    properties: {
      name: { type: "string", description: "The company's name." },
      type_hint: { anyOf: [{ type: "string", description: "A short guess at its type, e.g. 'studio', 'streamer', 'agency'." }, { type: "null" }] },
    },
    required: ["name", "type_hint"],
  };

  return {
    type: "object",
    additionalProperties: false,
    properties: {
      schema_version: { type: "string", const: SCHEMA_VERSION_V1 },
      people: { type: "array", items: personSchema },
      titles: { type: "array", items: titleSchema },
      companies: { type: "array", items: companySchema },
    },
    required: ["schema_version", "people", "titles", "companies"],
  };
}

// ── OpenRouter client ────────────────────────────────────────────────────────

export async function callOpenRouterForArticleMentions(
  text: string,
  promptVersion: string,
  model?: string,
): Promise<ArticleMentionsResponse> {
  const apiKey = getApiKey();
  if (!apiKey) throw new ExtractionError("OPENROUTER_API_KEY not set");

  const resolvedModel = model || DEFAULT_MODEL;
  const body = {
    model: resolvedModel,
    messages: [
      { role: "system", content: systemPrompt(promptVersion) },
      { role: "user", content: text },
    ],
    response_format: {
      type: "json_schema",
      json_schema: { name: "article_mentions", strict: true, schema: buildJsonSchema() },
    },
    temperature: 0,
    max_tokens: MAX_TOKENS,
  };

  const resp = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://hollywood.ponti.io",
      "X-Title": "Hollywood Article Enrichment",
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(90_000),
  });

  if (!resp.ok) {
    throw new ExtractionError(`OpenRouter request failed: ${resp.status} ${resp.statusText}`);
  }

  const data = (await resp.json()) as Record<string, unknown>;
  if (data["error"]) {
    const err = data["error"] as { message?: string };
    throw new ExtractionError(`OpenRouter error: ${err.message ?? JSON.stringify(err)}`);
  }

  const choices = data["choices"] as Array<{ message: { content: string } }> | undefined;
  if (!choices || !choices.length) throw new ExtractionError("OpenRouter returned no choices");

  const content = choices[0]!.message.content;
  let parsed: unknown;
  try {
    parsed = JSON.parse(content);
  } catch (e) {
    throw new ExtractionError(`Failed to parse LLM response as JSON: ${(e as Error).message}`);
  }

  const mentions = parseArticleMentions(parsed);
  return { rawJson: content, mentions, modelName: resolvedModel };
}
