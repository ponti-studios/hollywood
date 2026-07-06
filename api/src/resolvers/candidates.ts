import { getDb } from "../db/index.js";
import type { DbRow } from "../db/index.js";
import * as crypto from "node:crypto";

interface EntityRow extends DbRow {
  id: string;
  source_id: string;
  entity_type: string;
  name: string;
  canonical_name: string;
  bio: string | null;
  position: string | null;
  status: string;
  metadata_json: string;
}

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

function toCandidate(row: EntityRow): Record<string, unknown> {
  return {
    id: row.id,
    name: row.name,
    agencyBio: row.bio ?? null,
    position: row.position ?? "",
    status: row.status ?? "active",
    projectId: "default",
    credits: [],
    emails: [],
    phoneNumbers: [],
    notes: [],
    representatives: [],
    scripts: [],
    supportingLinks: [],
    tags: [],
    secondWriterName: null,
    secondWriterEmails: [],
    secondWriterPhoneNumbers: [],
    secondWriterSupportingLinks: [],
  };
}

function loadCredits(personId: string): Record<string, unknown>[] {
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

function loadEmails(entityId: string): { address: string; contactType: string | null }[] {
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

function loadPhoneNumbers(entityId: string): { number: string; contactType: string | null }[] {
  const db = getDb();
  const rows = db
    .prepare("SELECT contact_value, contact_type FROM entity_contacts WHERE entity_id = ? AND contact_type = 'phone'")
    .all(entityId) as ContactRow[];
  return rows.map((r) => ({ number: r.contact_value, contactType: r.contact_type }));
}

function loadRepresentatives(entityId: string): Record<string, unknown>[] {
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

function loadTags(entityId: string): { id: string; label: string; tagger: string }[] {
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

function enrichCandidate(row: EntityRow): Record<string, unknown> {
  const c = toCandidate(row);
  c.credits = loadCredits(row.id);
  c.emails = loadEmails(row.id);
  c.phoneNumbers = loadPhoneNumbers(row.id);
  c.representatives = loadRepresentatives(row.id);
  c.tags = loadTags(row.id);
  return c;
}

export const candidateResolvers = {
  Query: {
    candidate: (_parent: unknown, args: { candidateId: string }) => {
      const db = getDb();
      const row = db
        .prepare("SELECT * FROM entities WHERE id = ? AND entity_type = 'person'")
        .get(args.candidateId) as EntityRow | undefined;
      if (!row) throw new Error(`Candidate not found: ${args.candidateId}`);
      return enrichCandidate(row);
    },

    allCandidates: (_parent: unknown, args: { projectId?: string; limit?: number; offset?: number }) => {
      const db = getDb();
      const limit = args.limit ?? 50;
      const offset = args.offset ?? 0;
      const rows = db
        .prepare("SELECT * FROM entities WHERE entity_type = 'person' ORDER BY name LIMIT ? OFFSET ?")
        .all(limit, offset) as EntityRow[];
      return rows.map(enrichCandidate);
    },

    getSubmissions: (_parent: unknown, args: { projectId: string }) => {
      const db = getDb();
      const rows = db
        .prepare(
          `SELECT s.id, s.document_id, s.extraction_id, s.created_at, e.result_json
           FROM submissions s
           LEFT JOIN extraction_results e ON e.id = s.extraction_id
           ORDER BY s.created_at DESC`
        )
        .all() as DbRow[];
      return rows.map((r) => {
        let submissionJson = r.result_json ?? "{}";
        if (typeof submissionJson === "string") {
          try { submissionJson = JSON.parse(submissionJson); } catch { submissionJson = {}; }
        }
        return {
          id: r.id,
          projectId: args.projectId,
          candidateId: null,
          created: r.created_at,
          submissionJson,
          samples: [],
          rawSamples: [],
        };
      });
    },
  },

  Mutation: {
    addCandidates: (
      _parent: unknown,
      args: { projectId: string; candidates: Record<string, unknown>[] }
    ) => {
      const db = getDb();
      const now = new Date().toISOString();
      const results: Record<string, unknown>[] = [];
      for (const input of args.candidates) {
        const entityId = crypto.randomUUID();
        db.prepare(
          `INSERT INTO entities (id, source_id, entity_type, name, canonical_name, bio, position, status, license_class, created_at, updated_at)
           VALUES (?, ?, 'person', ?, ?, ?, ?, 'active', 'public', ?, ?)`
        ).run(
          entityId,
          "hollywood-api",
          input["name"] as string,
          (input["name"] as string).toLowerCase(),
          (input["agencyBio"] as string) ?? "",
          (input["position"] as string) ?? "",
          now,
          now,
        );
        results.push(
          toCandidate({
            id: entityId,
            source_id: "hollywood-api",
            entity_type: "person",
            name: input["name"] as string,
            canonical_name: (input["name"] as string).toLowerCase(),
            bio: (input["agencyBio"] as string) ?? null,
            position: (input["position"] as string) ?? null,
            status: "active",
            metadata_json: "{}",
          })
        );
      }
      return results;
    },
  },

  Candidate: {} as Record<string, unknown>,
};
