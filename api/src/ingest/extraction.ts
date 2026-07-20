import { z } from 'zod';

export const SCHEMA_VERSION_V1 = 'v1_submission_packet';
export const PROMPT_VERSION_V1 = 'v1';

const PHONE_PATTERN = /^\d{3}-\d{3}-\d{4}$/;

export const ALLOWED_CREDIT_TYPES = ['tv', 'movie', 'novel', 'magazine', 'podcast'] as const;
export const ALLOWED_LINK_TYPES = [
  'Twitter',
  'Instagram',
  'Facebook',
  'LinkedIn',
  'Other',
] as const;

function normalizeOptionalStr(v: string | null | undefined): string | null {
  if (v === null || v === undefined) return null;
  const s = v.trim();
  if (['null', 'n/a', 'none', 'unknown', ''].includes(s.toLowerCase())) return null;
  return s;
}

function normalizeEmail(v: string | null | undefined): string | null {
  const s = normalizeOptionalStr(v);
  if (s === null) return null;
  const at = s.lastIndexOf('@');
  if (at === -1) return null;
  const domain = s.slice(at + 1);
  if (!domain.includes('.')) return null;
  return s.toLowerCase();
}

function normalizePhone(v: string | null | undefined): string | null {
  const s = normalizeOptionalStr(v);
  if (s === null) return null;
  return PHONE_PATTERN.test(s) ? s : null;
}

// ── Raw (pre-validation) shapes returned by the LLM ─────────────────────────

const RawCreditSchema = z.object({
  role: z.string(),
  type: z.string(),
  production: z.string(),
  network: z.string().nullable().optional(),
});

const RawOrganizationSchema = z.object({
  name: z.string(),
  type: z.string(),
});

const RawAssociateSchema = z.object({
  name: z.string(),
  production: z.string().nullable().optional(),
});

const RawLinkSchema = z.object({
  url: z.string(),
  type: z.string(),
});

const RawRepresentativeSchema = z.object({
  name: z.string(),
  title: z.string(),
  organization: z.string().nullable().optional(),
  email: z.string().nullable().optional(),
  phone_number: z.string().nullable().optional(),
});

const RawCandidateSchema = z.object({
  name: z.string(),
  bio: z.string(),
  email: z.string().nullable().optional(),
  phone_number: z.string().nullable().optional(),
  position: z.string().nullable().optional(),
  tags: z.array(z.string()).default([]),
  credits: z.array(RawCreditSchema).default([]),
  organizations: z.array(RawOrganizationSchema).default([]),
  associates: z.array(RawAssociateSchema).default([]),
  links: z.array(RawLinkSchema).default([]),
  representatives: z.array(RawRepresentativeSchema).default([]),
});

const RawSubmissionPacketSchema = z.object({
  schema_version: z.string().default(SCHEMA_VERSION_V1),
  candidates: z.array(RawCandidateSchema).default([]),
});

// ── Validated domain types (post model_validator equivalents) ───────────────

export interface Credit {
  role: string;
  type: string;
  production: string;
  network: string | null;
}

export interface Organization {
  name: string;
  type: string;
}

export interface Associate {
  name: string;
  production: string | null;
}

export interface Link {
  url: string;
  type: string;
}

interface Representative {
  name: string;
  title: string;
  organization: string | null;
  email: string | null;
  phone_number: string | null;
}

export interface Candidate {
  name: string;
  bio: string;
  email: string | null;
  phone_number: string | null;
  position: string | null;
  tags: string[];
  credits: Credit[];
  organizations: Organization[];
  associates: Associate[];
  links: Link[];
  representatives: Representative[];
}

export interface SubmissionPacket {
  schema_version: string;
  candidates: Candidate[];
}

function validateCredit(raw: z.infer<typeof RawCreditSchema>): Credit {
  const role = raw.role.trim();
  if (!role) throw new Error('role is required');
  if (!ALLOWED_CREDIT_TYPES.includes(raw.type as (typeof ALLOWED_CREDIT_TYPES)[number])) {
    throw new Error(`type must be one of ${ALLOWED_CREDIT_TYPES.join(', ')}`);
  }
  const production = raw.production.trim();
  if (!production) throw new Error('production is required');
  return {
    role: role.toLowerCase(),
    type: raw.type,
    production,
    network: normalizeOptionalStr(raw.network),
  };
}

function validateOrganization(raw: z.infer<typeof RawOrganizationSchema>): Organization {
  const name = raw.name.trim();
  if (!name) throw new Error('name is required');
  const type = raw.type.trim();
  if (!type) throw new Error('type is required');
  return { name, type };
}

function validateAssociate(raw: z.infer<typeof RawAssociateSchema>): Associate {
  const name = raw.name.trim();
  if (!name) throw new Error('name is required');
  return { name, production: normalizeOptionalStr(raw.production) };
}

function validateLink(raw: z.infer<typeof RawLinkSchema>): Link {
  const url = raw.url.trim();
  if (!url) throw new Error('url is required');
  const type = raw.type.trim();
  if (!ALLOWED_LINK_TYPES.includes(type as (typeof ALLOWED_LINK_TYPES)[number])) {
    throw new Error(`type must be one of ${ALLOWED_LINK_TYPES.join(', ')}`);
  }
  return { url, type };
}

function validateRepresentative(raw: z.infer<typeof RawRepresentativeSchema>): Representative {
  const name = raw.name.trim();
  if (!name) throw new Error('name is required');
  const title = raw.title.trim().toLowerCase();
  if (!title) throw new Error('title is required');
  return {
    name,
    title,
    organization: normalizeOptionalStr(raw.organization),
    email: normalizeEmail(raw.email),
    phone_number: normalizePhone(raw.phone_number),
  };
}

function validateCandidate(raw: z.infer<typeof RawCandidateSchema>): Candidate {
  const name = raw.name.trim();
  if (!name) throw new Error('name is required');
  const bio = raw.bio.trim();
  if (!bio) throw new Error('bio is required');
  return {
    name,
    bio,
    email: normalizeEmail(raw.email),
    phone_number: normalizePhone(raw.phone_number),
    position: normalizeOptionalStr(raw.position),
    tags: raw.tags.map((t) => t.trim()).filter(Boolean),
    credits: raw.credits.map(validateCredit),
    organizations: raw.organizations.map(validateOrganization),
    associates: raw.associates.map(validateAssociate),
    links: raw.links.map(validateLink),
    representatives: raw.representatives.map(validateRepresentative),
  };
}

export function parseSubmissionPacket(raw: unknown): SubmissionPacket {
  const parsed = RawSubmissionPacketSchema.parse(raw);
  if (parsed.schema_version !== SCHEMA_VERSION_V1) {
    throw new Error(`unsupported schema_version ${parsed.schema_version}`);
  }
  return {
    schema_version: parsed.schema_version,
    candidates: parsed.candidates.map(validateCandidate),
  };
}
