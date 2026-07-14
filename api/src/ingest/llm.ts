import { env } from '../env.js';
import {
  ALLOWED_CREDIT_TYPES,
  ALLOWED_LINK_TYPES,
  SCHEMA_VERSION_V1,
  parseSubmissionPacket,
} from './extraction.js';
import type {
  Associate,
  Candidate,
  Credit,
  Link,
  Organization,
  SubmissionPacket,
} from './extraction.js';

const ORGANIZATION_PATTERN =
  /\b([A-Z][A-Za-z0-9&+.'’:-]*(?:\s+[A-Z][A-Za-z0-9&+.'’:-]*){0,4}\s(?:Studios|Studio|TV|Television|Animation|Media|Productions|Entertainment|Network|Networks|Pictures|Films|Film|Labs|Lab))\b/g;

export const OPENROUTER_BASE_URL = 'https://openrouter.ai/api/v1';
export const DEFAULT_MODEL = 'openai/gpt-4o-mini';
const MAX_TOKENS = 8000;

export class ExtractionError extends Error {}

export interface ExtractionResponse {
  rawJson: string;
  packet: SubmissionPacket;
  modelName: string;
}

function getApiKey(): string | null {
  return env.OPENROUTER_API_KEY ?? env.OPENAI_API_KEY ?? null;
}

// ── System prompt ────────────────────────────────────────────────────────────

function systemPrompt(promptVersion: string): string {
  return `You extract structured submission data from writer/talent submission emails.

Return only data grounded in the provided text.
- Do not invent facts.
- If a scalar field is unknown, use null.
- If a list field has no supported values, return an empty array.
- Return one candidate object for each explicitly presented candidate.
- Do not include the email sender, recipients, forwarders, or other non-candidate people unless the body explicitly presents them as submission talent.
- Representatives are agents, managers, assistants, or publicists associated with the candidate.
- Credits should only include projects explicitly supported by the text.
- Organizations are a required entity index for each candidate, not a summary.
- Include companies, studios, networks, streamers, agencies, production companies, publishers, platforms, and similar groups explicitly tied to the candidate.
- For every non-null credits[].network value, add the same organization to organizations[] unless an equivalent organization is already present.
- Do not omit an organization from organizations[] just because it also appears in a credit's network field, the candidate bio, or parentheses after a production title.
- Also extract organizations from relationship phrases in the bio, including "sold development to", "developing with", "developed at", "staffed on", "currently on", "produced by", "with [company] producing", "for [company]", "streaming on", and parenthetical project sources like "(Peacock/Pacific Electric)".
- Preserve the most specific organization name given by the text. Do not shorten "CBS Studios" to "CBS", "Warner Brothers Animation" to "Warner Brothers", or "Paramount TV" to "Paramount".
- Use organization types like "network", "studio", "streamer", "agency", "production company", "publisher", "platform", or "company".
- Tags should be concise and relevant to the candidate's work.
- Avoid duplicate entries in every array.
- Correct obvious spelling mistakes in names or titles, but preserve intentional spellings and formatting.
- Expand common industry abbreviations in the bio when helpful, but keep original forms in other fields.
- Preserve the exact JSON schema and top-level shape.
- Ignore forwarding wrappers, sender signatures, email recipients, cc lines, and mailing metadata.
- Never treat the forwarder, original sender, recipient, executive, producer, or buyer as a candidate unless the text explicitly presents them as submission talent.
- Names appearing in From/To/Cc/Subject/header blocks are not candidates by default.
- In staffing submission emails, candidates are usually the people listed under sections like upper level, lower level, writer submission, client, candidate, or followed by a biography, credits, or attached sample mention.
- If the email says someone is submitting material for another person, the submitter is a representative, not a candidate.
- Prefer false negatives over false positives for candidate identity. Do not include a person unless the body presents them as being considered for the role or staffing opportunity.
- Before returning JSON, check each candidate: if any credit has a network, streamer, studio, platform, or company, organizations[] must contain that entity.
- Before returning JSON, check each candidate bio for explicitly named companies, studios, networks, streamers, platforms, agencies, publishers, and production companies. organizations[] must contain those entities when they are tied to the candidate's work, development, staffing, production, or representation.

Prompt version: ${promptVersion}`;
}

// ── JSON schema (mirrors _build_json_schema in llm.py) ──────────────────────

function optionalString(description: string) {
  return { anyOf: [{ type: 'string', description }, { type: 'null' }] };
}
function optionalEmail(description: string) {
  return { anyOf: [{ type: 'string', description, format: 'email' }, { type: 'null' }] };
}
function optionalPhone(description: string) {
  return {
    anyOf: [{ type: 'string', description, pattern: '^\\d{3}-\\d{3}-\\d{4}$' }, { type: 'null' }],
  };
}

function buildJsonSchema(): Record<string, unknown> {
  const creditSchema = {
    type: 'object',
    additionalProperties: false,
    properties: {
      role: { type: 'string', description: "The candidate's role on the project. Use lowercase." },
      type: {
        type: 'string',
        enum: ALLOWED_CREDIT_TYPES,
        description: 'The type of project. Use lowercase.',
      },
      production: { type: 'string', description: 'The name of the production or project.' },
      network: optionalString(
        'The network, streamer, studio, platform, publisher, or company associated with the project.',
      ),
    },
    required: ['role', 'type', 'production', 'network'],
  };

  const organizationSchema = {
    type: 'object',
    additionalProperties: false,
    properties: {
      name: { type: 'string', description: 'The exact name of the organization.' },
      type: {
        type: 'string',
        description: 'The organization type: network, studio, streamer, agency, etc.',
      },
    },
    required: ['name', 'type'],
  };

  const associateSchema = {
    type: 'object',
    additionalProperties: false,
    properties: {
      name: { type: 'string', description: 'The name of the associate.' },
      production: optionalString('The production the associate worked on with the candidate.'),
    },
    required: ['name', 'production'],
  };

  const linkSchema = {
    type: 'object',
    additionalProperties: false,
    properties: {
      url: { type: 'string', description: 'The full URL of the link.' },
      type: { type: 'string', enum: ALLOWED_LINK_TYPES, description: 'The type of link.' },
    },
    required: ['url', 'type'],
  };

  const repSchema = {
    type: 'object',
    additionalProperties: false,
    properties: {
      name: { type: 'string', description: 'The full name of the representative.' },
      title: { type: 'string', description: "The representative's job title. Use lowercase." },
      organization: optionalString(
        'The company or organization the representative is associated with.',
      ),
      email: optionalEmail('The email address of the representative.'),
      phone_number: optionalPhone('The phone number of the representative.'),
    },
    required: ['name', 'title', 'organization', 'email', 'phone_number'],
  };

  const candidateSchema = {
    type: 'object',
    additionalProperties: false,
    properties: {
      name: { type: 'string', description: 'The full name of the candidate.' },
      bio: { type: 'string', description: 'A comprehensive summary of the candidate.' },
      email: optionalEmail("The candidate's email address."),
      phone_number: optionalPhone("The candidate's phone number."),
      position: optionalString("The candidate's primary job title."),
      tags: { type: 'array', items: { type: 'string' }, description: '4-5 concise tags.' },
      credits: {
        type: 'array',
        items: creditSchema,
        description: "Projects in the candidate's bio.",
      },
      organizations: {
        type: 'array',
        items: organizationSchema,
        description: 'Organizations tied to the candidate.',
      },
      associates: {
        type: 'array',
        items: associateSchema,
        description: 'People who have worked with the candidate.',
      },
      links: { type: 'array', items: linkSchema, description: 'URLs for the candidate.' },
      representatives: {
        type: 'array',
        items: repSchema,
        description: 'Agents, managers, assistants, or publicists.',
      },
    },
    required: [
      'name',
      'bio',
      'email',
      'phone_number',
      'position',
      'tags',
      'credits',
      'organizations',
      'associates',
      'links',
      'representatives',
    ],
  };

  return {
    type: 'object',
    additionalProperties: false,
    properties: {
      schema_version: { type: 'string', const: SCHEMA_VERSION_V1 },
      candidates: { type: 'array', items: candidateSchema },
    },
    required: ['schema_version', 'candidates'],
  };
}

// ── OpenRouter client ────────────────────────────────────────────────────────

export async function callOpenRouter(
  text: string,
  promptVersion: string,
  model?: string,
): Promise<ExtractionResponse> {
  const apiKey = getApiKey();
  if (!apiKey) throw new ExtractionError('OPENROUTER_API_KEY not set');

  const resolvedModel = model || DEFAULT_MODEL;
  const body = {
    model: resolvedModel,
    messages: [
      { role: 'system', content: systemPrompt(promptVersion) },
      { role: 'user', content: text },
    ],
    response_format: {
      type: 'json_schema',
      json_schema: { name: 'submission_packet', strict: true, schema: buildJsonSchema() },
    },
    temperature: 0,
    max_tokens: MAX_TOKENS,
  };

  const resp = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${apiKey}`,
      'Content-Type': 'application/json',
      'HTTP-Referer': 'https://hollywood.ponti.io',
      'X-Title': 'Hollywood Extraction',
    },
    body: JSON.stringify(body),
    signal: AbortSignal.timeout(90_000),
  });

  if (!resp.ok) {
    throw new ExtractionError(`OpenRouter request failed: ${resp.status} ${resp.statusText}`);
  }

  const data = (await resp.json()) as Record<string, unknown>;
  if (data['error']) {
    const err = data['error'] as { message?: string };
    throw new ExtractionError(`OpenRouter error: ${err.message ?? JSON.stringify(err)}`);
  }

  const choices = data['choices'] as Array<{ message: { content: string } }> | undefined;
  if (!choices || !choices.length) throw new ExtractionError('OpenRouter returned no choices');

  const content = choices[0]!.message.content;
  let parsed: unknown;
  try {
    parsed = JSON.parse(content);
  } catch (e) {
    throw new ExtractionError(`Failed to parse LLM response as JSON: ${(e as Error).message}`);
  }

  const packet = normalizePacket(parseSubmissionPacket(parsed));
  return { rawJson: content, packet, modelName: resolvedModel };
}

// ── Normalization ────────────────────────────────────────────────────────────

function normalizePacket(packet: SubmissionPacket): SubmissionPacket {
  return {
    schema_version: packet.schema_version.trim() ? packet.schema_version : SCHEMA_VERSION_V1,
    candidates: packet.candidates.map(normalizeCandidate),
  };
}

function normalizeCandidate(c: Candidate): Candidate {
  const name = c.name.trim();
  let bio = c.bio.trim();

  const credits = dedupeCredits(
    c.credits.map((credit) => ({
      ...credit,
      role: credit.role.trim().toLowerCase(),
      type: credit.type.trim().toLowerCase(),
      production: credit.production.trim(),
    })),
  );

  let organizations = c.organizations.map((org) => ({
    ...org,
    name: org.name.trim(),
    type: org.type.trim(),
  }));
  organizations = organizations.concat(
    organizationsFromCredits(credits),
    organizationsFromBio(bio),
  );
  organizations = dedupeOrganizations(organizations);

  const associates = dedupeAssociates(c.associates.map((a) => ({ ...a, name: a.name.trim() })));

  const links = dedupeLinks(
    c.links.map((link) => ({ ...link, url: link.url.trim(), type: normalizeLinkType(link.type) })),
  );

  const representatives = dedupeReps(
    c.representatives.map((rep) => ({
      ...rep,
      name: rep.name.trim(),
      title: rep.title.trim().toLowerCase(),
    })),
  );

  if (!bio && name) bio = synthesizeBio({ ...c, name, credits, tags: c.tags });

  return { ...c, name, bio, credits, organizations, associates, links, representatives };
}

function organizationsFromCredits(credits: Credit[]): Organization[] {
  const orgs: Organization[] = [];
  for (const credit of credits) {
    if (credit.network) {
      const name = credit.network.trim();
      if (name) orgs.push({ name, type: classifyOrgType(name) });
    }
  }
  return orgs;
}

function organizationsFromBio(bio: string): Organization[] {
  const orgs: Organization[] = [];
  for (const match of bio.matchAll(ORGANIZATION_PATTERN)) {
    const name = cleanOrgName(match[1] ?? '');
    if (name) orgs.push({ name, type: classifyOrgType(name) });
  }
  return orgs;
}

function cleanOrgName(name: string): string {
  let cleaned = name.trim();
  cleaned = cleaned.replace(/'s$/, '').replace(/’s$/, '');
  return cleaned.trim().replace(/^[\s\t\n\r.,;:()]+|[\s\t\n\r.,;:()]+$/g, '');
}

function classifyOrgType(name: string): string {
  const lower = name.toLowerCase().trim();
  if (lower.includes('network')) return 'network';
  if (
    lower.includes('studio') ||
    lower.includes('animation') ||
    lower.includes(' tv') ||
    lower.endsWith('tv')
  )
    return 'studio';
  if (lower.includes('productions') || lower.includes('production')) return 'production company';
  if (
    lower.includes('media') ||
    lower.includes('entertainment') ||
    lower.includes('pictures') ||
    lower.includes('films') ||
    lower.includes('film')
  ) {
    return 'production company';
  }
  return 'company';
}

function normalizeLinkType(linkType: string): string {
  const mapping: Record<string, string> = {
    imdb: 'IMDB',
    twitter: 'Twitter',
    instagram: 'Instagram',
    facebook: 'Facebook',
    linkedin: 'LinkedIn',
  };
  return mapping[linkType.trim().toLowerCase()] ?? 'Other';
}

function synthesizeBio(c: Candidate): string {
  const parts = [c.name];
  parts.push(c.position ? `is identified as a ${c.position}` : 'is mentioned in the submission');
  if (c.credits.length) parts.push(`with ${c.credits.length} referenced credits`);
  if (c.tags.length) parts.push('and associated tags including ' + c.tags.join(', '));
  return parts.join(' ') + '.';
}

// ── Deduplication ────────────────────────────────────────────────────────────

function dedupeCredits(values: Credit[]): Credit[] {
  const seen = new Set<string>();
  const result: Credit[] = [];
  for (const v of values) {
    const key = [
      v.role.toLowerCase(),
      v.type.toLowerCase(),
      v.production,
      (v.network ?? '').toLowerCase(),
    ].join('|');
    if (!seen.has(key)) {
      seen.add(key);
      result.push(v);
    }
  }
  return result;
}

function dedupeOrganizations(values: Organization[]): Organization[] {
  const seen = new Set<string>();
  const result: Organization[] = [];
  for (const v of values) {
    const key = v.name.toLowerCase();
    if (!seen.has(key)) {
      seen.add(key);
      result.push(v);
    }
  }
  return result;
}

function dedupeAssociates(values: Associate[]): Associate[] {
  const seen = new Set<string>();
  const result: Associate[] = [];
  for (const v of values) {
    const key = [v.name.toLowerCase(), (v.production ?? '').toLowerCase()].join('|');
    if (!seen.has(key)) {
      seen.add(key);
      result.push(v);
    }
  }
  return result;
}

function dedupeLinks(values: Link[]): Link[] {
  const seen = new Set<string>();
  const result: Link[] = [];
  for (const v of values) {
    const key = [v.url.toLowerCase(), v.type.toLowerCase()].join('|');
    if (!seen.has(key)) {
      seen.add(key);
      result.push(v);
    }
  }
  return result;
}

function dedupeReps<
  T extends {
    name: string;
    title: string;
    organization: string | null;
    email: string | null;
    phone_number: string | null;
  },
>(values: T[]): T[] {
  const seen = new Set<string>();
  const result: T[] = [];
  for (const v of values) {
    const key = [
      v.name.toLowerCase(),
      v.title.toLowerCase(),
      (v.organization ?? '').toLowerCase(),
      (v.email ?? '').toLowerCase(),
      (v.phone_number ?? '').toLowerCase(),
    ].join('|');
    if (!seen.has(key)) {
      seen.add(key);
      result.push(v);
    }
  }
  return result;
}
