import { z } from 'zod';

export const SCHEMA_VERSION_V2 = 'v2_article_mentions';
export const PROMPT_VERSION_V2 = 'v2';

// Controlled vocabulary for a person's relationship to a title. Keeping this
// closed (rather than free text) is what makes the resulting `credits.role`
// usable — v1 let the LLM write full sentences ("starred alongside Nicole
// Kidman", "returned as Alan Grant") straight into `role`, which also
// leaked co-star names into a field meant to describe one person's own
// credit. "actor" + the separate `character` field replaces all of that.
export const TITLE_ROLE_VALUES = [
  'director',
  'writer',
  'executive_producer',
  'producer',
  'showrunner',
  'creator',
  'actor',
  'host',
  'editor',
  'cinematographer',
  'composer',
  'author',
  'other',
] as const;

function normalizeOptionalStr(v: string | null | undefined): string | null {
  if (v === null || v === undefined) return null;
  const s = v.trim();
  if (['null', 'n/a', 'none', 'unknown', ''].includes(s.toLowerCase())) return null;
  return s;
}

// ── Raw (pre-validation) shapes returned by the LLM ─────────────────────────

const RawRelatedToSchema = z.object({
  name: z.string(),
  type: z.enum(['title', 'company', 'person']),
  relationship: z.string(),
  character: z.string().nullable().optional(),
});

const RawMentionedPersonSchema = z.object({
  name: z.string(),
  role_hint: z.string().nullable().optional(),
  related_to: z.array(RawRelatedToSchema).default([]),
});

const RawMentionedTitleSchema = z.object({
  name: z.string(),
  format_hint: z.string().nullable().optional(),
});

const RawMentionedCompanySchema = z.object({
  name: z.string(),
  type_hint: z.string().nullable().optional(),
});

const RawArticleMentionsSchema = z.object({
  schema_version: z.string().default(SCHEMA_VERSION_V2),
  people: z.array(RawMentionedPersonSchema).default([]),
  titles: z.array(RawMentionedTitleSchema).default([]),
  companies: z.array(RawMentionedCompanySchema).default([]),
});

// ── Validated domain types ───────────────────────────────────────────────────

interface RelatedTo {
  name: string;
  type: 'title' | 'company' | 'person';
  relationship: string;
  /** Character name — only ever set when type is "title" and relationship is "actor". */
  character: string | null;
}

interface MentionedPerson {
  name: string;
  roleHint: string | null;
  relatedTo: RelatedTo[];
}

interface MentionedTitle {
  name: string;
  formatHint: string | null;
}

interface MentionedCompany {
  name: string;
  typeHint: string | null;
}

export interface ArticleMentions {
  schemaVersion: string;
  people: MentionedPerson[];
  titles: MentionedTitle[];
  companies: MentionedCompany[];
}

function validateRelatedTo(raw: z.infer<typeof RawRelatedToSchema>): RelatedTo {
  const name = raw.name.trim();
  if (!name) throw new Error('related_to.name is required');
  const relationship = raw.relationship.trim();
  if (!relationship) throw new Error('related_to.relationship is required');

  if (raw.type === 'title' && !(TITLE_ROLE_VALUES as readonly string[]).includes(relationship)) {
    throw new Error(
      `related_to.relationship must be one of ${TITLE_ROLE_VALUES.join(', ')} when type is "title", got "${relationship}"`,
    );
  }

  // character is only meaningful for an on-screen credit; silently drop it
  // otherwise rather than rejecting an LLM response over a minor overshoot.
  const character = relationship === 'actor' ? normalizeOptionalStr(raw.character) : null;

  return { name, type: raw.type, relationship, character };
}

function validateMentionedPerson(raw: z.infer<typeof RawMentionedPersonSchema>): MentionedPerson {
  const name = raw.name.trim();
  if (!name) throw new Error('person name is required');
  return {
    name,
    roleHint: normalizeOptionalStr(raw.role_hint),
    relatedTo: raw.related_to.map(validateRelatedTo),
  };
}

function validateMentionedTitle(raw: z.infer<typeof RawMentionedTitleSchema>): MentionedTitle {
  const name = raw.name.trim();
  if (!name) throw new Error('title name is required');
  return { name, formatHint: normalizeOptionalStr(raw.format_hint) };
}

function validateMentionedCompany(
  raw: z.infer<typeof RawMentionedCompanySchema>,
): MentionedCompany {
  const name = raw.name.trim();
  if (!name) throw new Error('company name is required');
  return { name, typeHint: normalizeOptionalStr(raw.type_hint) };
}

export function parseArticleMentions(raw: unknown): ArticleMentions {
  const parsed = RawArticleMentionsSchema.parse(raw);
  if (parsed.schema_version !== SCHEMA_VERSION_V2) {
    throw new Error(`unsupported schema_version ${parsed.schema_version}`);
  }
  return {
    schemaVersion: parsed.schema_version,
    people: parsed.people.map(validateMentionedPerson),
    titles: parsed.titles.map(validateMentionedTitle),
    companies: parsed.companies.map(validateMentionedCompany),
  };
}
