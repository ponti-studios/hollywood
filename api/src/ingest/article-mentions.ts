import { z } from "zod";

export const SCHEMA_VERSION_V1 = "v1_article_mentions";
export const PROMPT_VERSION_V1 = "v1";

function normalizeOptionalStr(v: string | null | undefined): string | null {
  if (v === null || v === undefined) return null;
  const s = v.trim();
  if (["null", "n/a", "none", "unknown", ""].includes(s.toLowerCase())) return null;
  return s;
}

// ── Raw (pre-validation) shapes returned by the LLM ─────────────────────────

const RawRelatedToSchema = z.object({
  name: z.string(),
  type: z.enum(["title", "company", "person"]),
  relationship: z.string(),
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

export const RawArticleMentionsSchema = z.object({
  schema_version: z.string().default(SCHEMA_VERSION_V1),
  people: z.array(RawMentionedPersonSchema).default([]),
  titles: z.array(RawMentionedTitleSchema).default([]),
  companies: z.array(RawMentionedCompanySchema).default([]),
});

// ── Validated domain types ───────────────────────────────────────────────────

export interface RelatedTo {
  name: string;
  type: "title" | "company" | "person";
  relationship: string;
}

export interface MentionedPerson {
  name: string;
  roleHint: string | null;
  relatedTo: RelatedTo[];
}

export interface MentionedTitle {
  name: string;
  formatHint: string | null;
}

export interface MentionedCompany {
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
  if (!name) throw new Error("related_to.name is required");
  const relationship = raw.relationship.trim();
  if (!relationship) throw new Error("related_to.relationship is required");
  return { name, type: raw.type, relationship };
}

function validateMentionedPerson(raw: z.infer<typeof RawMentionedPersonSchema>): MentionedPerson {
  const name = raw.name.trim();
  if (!name) throw new Error("person name is required");
  return {
    name,
    roleHint: normalizeOptionalStr(raw.role_hint),
    relatedTo: raw.related_to.map(validateRelatedTo),
  };
}

function validateMentionedTitle(raw: z.infer<typeof RawMentionedTitleSchema>): MentionedTitle {
  const name = raw.name.trim();
  if (!name) throw new Error("title name is required");
  return { name, formatHint: normalizeOptionalStr(raw.format_hint) };
}

function validateMentionedCompany(raw: z.infer<typeof RawMentionedCompanySchema>): MentionedCompany {
  const name = raw.name.trim();
  if (!name) throw new Error("company name is required");
  return { name, typeHint: normalizeOptionalStr(raw.type_hint) };
}

export function parseArticleMentions(raw: unknown): ArticleMentions {
  const parsed = RawArticleMentionsSchema.parse(raw);
  if (parsed.schema_version !== SCHEMA_VERSION_V1) {
    throw new Error(`unsupported schema_version ${parsed.schema_version}`);
  }
  return {
    schemaVersion: parsed.schema_version,
    people: parsed.people.map(validateMentionedPerson),
    titles: parsed.titles.map(validateMentionedTitle),
    companies: parsed.companies.map(validateMentionedCompany),
  };
}
