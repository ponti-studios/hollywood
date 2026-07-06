import { getDb } from "./index.js";
import type { DbRow } from "./index.js";

// ── Row interfaces ──────────────────────────────────────────────────────────

interface CreditRow extends DbRow {
  id: string;
  person_id: string;
  title_id: string;
  role: string;
  credit_type: string;
  title_name?: string;
}

interface AliasRow extends DbRow {
  id: string;
  alias: string;
}

interface ContactRow extends DbRow {
  id: string;
  contact_type: string;
  contact_value: string;
}

interface RepRow extends DbRow {
  id: string;
  rep_id: string;
  rep_name?: string;
  rep_type: string;
  title: string;
  email: string;
  phone: string;
}

interface TagRow extends DbRow {
  id: string;
  tag: string;
}

// ── Helpers ──────────────────────────────────────────────────────────────────

export function loadCredits(personId: string): Record<string, unknown>[] {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT c.id, c.person_id, c.title_id, c.role, c.credit_type, e.name AS title_name
       FROM credits c
       LEFT JOIN entities e ON e.id = c.title_id
       WHERE c.person_id = ?
       ORDER BY c.created_at DESC`
    )
    .all(personId) as CreditRow[];
  return rows.map((r) => ({
    id: r.id,
    role: r.role,
    type: r.credit_type ?? null,
    production: r.title_name ?? "Unknown",
    network: null,
    season: null,
    seasons: [],
    year: 0,
    years: [],
  }));
}

export function loadEmails(entityId: string): { address: string; contactType: string | null }[] {
  const db = getDb();
  const aliases = db
    .prepare("SELECT alias FROM entity_aliases WHERE entity_id = ?")
    .all(entityId) as AliasRow[];
  const contacts = db
    .prepare("SELECT contact_value FROM entity_contacts WHERE entity_id = ? AND contact_type = 'email'")
    .all(entityId) as ContactRow[];
  const results: { address: string; contactType: string | null }[] = [];
  for (const a of aliases) results.push({ address: a.alias, contactType: "alias" });
  for (const c of contacts) results.push({ address: c.contact_value, contactType: "email" });
  return results;
}

export function loadPhoneNumbers(entityId: string): { number: string; contactType: string | null }[] {
  const db = getDb();
  const rows = db
    .prepare("SELECT contact_value, contact_type FROM entity_contacts WHERE entity_id = ? AND contact_type = 'phone'")
    .all(entityId) as ContactRow[];
  return rows.map((r) => ({ number: r.contact_value, contactType: r.contact_type }));
}

export function loadRepresentatives(entityId: string): Record<string, unknown>[] {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT r.id, r.rep_id, r.rep_type, r.title, r.email, r.phone, e.name AS rep_name
       FROM representation r
       LEFT JOIN entities e ON e.id = r.rep_id
       WHERE r.client_id = ?`
    )
    .all(entityId) as RepRow[];
  return rows.map((r) => ({
    id: r.id,
    name: r.rep_name ?? "Unknown",
    organization: "",
    representationType: r.rep_type?.toUpperCase() ?? null,
    emails: r.email ? [{ address: r.email, contactType: "work" }] : [],
    phoneNumbers: r.phone ? [{ number: r.phone, contactType: "work" }] : [],
  }));
}

export function loadTags(entityId: string): { id: string; label: string; tagger: string }[] {
  const db = getDb();
  const rows = db
    .prepare(
      `SELECT t.id, t.tag
       FROM tags t
       JOIN entity_taggings et ON et.tag_id = t.id
       WHERE et.entity_id = ?`
    )
    .all(entityId) as TagRow[];
  return rows.map((r) => ({ id: r.id, label: r.tag, tagger: "system" }));
}

/** Build the full candidate payload from an entity row. */
export function enrichCandidate(row: DbRow): Record<string, unknown> {
  return {
    id: row.id,
    name: row.name,
    agencyBio: row.bio ?? null,
    position: row.position ?? "",
    status: row.status ?? "active",
    credits: loadCredits(row.id as string),
    emails: loadEmails(row.id as string),
    phoneNumbers: loadPhoneNumbers(row.id as string),
    notes: [],
    representatives: loadRepresentatives(row.id as string),
    scripts: [],
    supportingLinks: [],
    tags: loadTags(row.id as string),
    secondWriterName: null,
    secondWriterEmails: [],
    secondWriterPhoneNumbers: [],
    secondWriterSupportingLinks: [],
  };
}

/** Build a project payload from an entity row. */
export function enrichProject(row: DbRow): Record<string, unknown> {
  const meta = row.metadata_json ? JSON.parse(row.metadata_json as string) : {};
  return {
    id: row.id,
    title: row.name,
    season: meta.season ?? 1,
    genres: meta.genres ?? [],
    format: row.title_type ?? null,
    imdbLink: meta.imdb_link ?? null,
    posterLink: meta.poster_link ?? null,
  };
}

/** Parse a SubmissionPacket or direct SubmissionJson from extraction result JSON. */
export function parseSubmissionJson(raw: string | Record<string, unknown>): Record<string, unknown> {
  let obj: Record<string, unknown>;
  if (typeof raw === "string") {
    try { obj = JSON.parse(raw); } catch { return { name: "Unknown" }; }
  } else {
    obj = raw;
  }

  // SubmissionPacket format: { candidates: [{ name, bio, credits, ... }] }
  if (obj.candidates && Array.isArray(obj.candidates) && obj.candidates.length > 0) {
    const c = obj.candidates[0] as Record<string, unknown>;
    return {
      name: (c.name as string) ?? "Unknown",
      bio: (c.bio as string) ?? null,
      email: (c.email as string) ?? null,
      phoneNumber: (c.phone_number as string) ?? null,
      tags: (c.tags as string[]) ?? [],
      organizations: ((c.organizations as Record<string, unknown>[]) ?? []).map((o) => o.name),
      credits: ((c.credits as Record<string, unknown>[]) ?? []).map((cr) => ({
        role: (cr.role as string) ?? null,
        type: (cr.type as string) ?? null,
        production: (cr.production as string) ?? null,
        network: (cr.network as string) ?? null,
      })),
      representatives: ((c.representatives as Record<string, unknown>[]) ?? []).map((rep) => ({
        name: (rep.name as string) ?? null,
        title: (rep.title as string) ?? null,
        agency: (rep.organization as string) ?? null,
        email: (rep.email as string) ?? null,
      })),
      links: ((c.links as Record<string, unknown>[]) ?? []).map((l) => ({
        url: (l.url as string) ?? null,
        type: (l.type as string) ?? null,
      })),
      attachments: [],
    };
  }

  // Direct SubmissionJson format
  return { name: "Unknown", ...obj };
}
