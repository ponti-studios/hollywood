import { createYoga, createSchema } from "graphql-yoga";
import { createServer } from "node:http";
import * as crypto from "node:crypto";
import { typeDefs } from "./schema.js";
import { candidateResolvers } from "./resolvers/candidates.js";
import { projectResolvers } from "./resolvers/projects.js";
import { userResolvers } from "./resolvers/users.js";
import { getDb, closeDb } from "./db/index.js";
import type { DbRow } from "./db/index.js";

const PORT = parseInt(process.env["PORT"] ?? process.env["HOLLYWOOD_API_PORT"] ?? "4000", 10);
const HOST = process.env["HOST"] ?? "0.0.0.0";

// ── Hollywood-specific extensions ───────────────────────────────────────────
const hollywoodQueryExtensions = {
  search: async (_parent: unknown, args: { query: string; limit?: number; offset?: number }) => {
    const db = getDb();
    const limit = args.limit ?? 20;
    const offset = args.offset ?? 0;
    const pattern = `%${args.query}%`;
    const total = (
      db.prepare("SELECT COUNT(*) AS count FROM entities WHERE name LIKE ?").get(pattern) as { count: number }
    ).count;
    const entities = db
      .prepare("SELECT id, name, bio, position, status FROM entities WHERE name LIKE ? ORDER BY name LIMIT ? OFFSET ?")
      .all(pattern, limit, offset) as DbRow[];
    return {
      total,
      entities: entities.map((row: any) => ({
        id: row.id,
        name: row.name,
        agencyBio: row.bio ?? null,
        position: row.position ?? "",
        status: row.status ?? "active",
        projectId: "search",
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
      })),
      projects: [],
    };
  },
};

const hollywoodMutations = {
  ingestDocument: async (_parent: unknown, args: { text: string; source?: string }) => {
    const { execSync } = await import("node:child_process");
    const result = execSync(
      `cd "${process.cwd()}" && uv run hollywood extract - --dry-run`,
      { input: args.text, encoding: "utf-8", timeout: 120000 }
    );
    const id = crypto.randomUUID();
    return { id, candidates: [], modelName: "openai/gpt-4o-mini", rawJson: result };
  },

  deleteSubmission: (_parent: unknown, args: { submissionId: string }) => {
    const db = getDb();
    const result = db.prepare("DELETE FROM submissions WHERE id = ?").run(args.submissionId);
    return result.changes > 0;
  },

  createSubmissionCandidate: (_parent: unknown, args: { submissionId: string; position: string }) => {
    const db = getDb();
    const sub = db.prepare(
      `SELECT s.id, s.document_id, e.result_json
       FROM submissions s
       LEFT JOIN extraction_results e ON e.id = s.extraction_id
       WHERE s.id = ?`
    ).get(args.submissionId) as DbRow | undefined;
    if (!sub) throw new Error(`Submission not found: ${args.submissionId}`);
    const entityId = crypto.randomUUID();
    const now = new Date().toISOString();
    let name = "Unknown";
    if (sub.result_json) {
      try { const j = JSON.parse(sub.result_json as string); if (j.name) name = j.name; } catch {}
    }
    db.prepare(
      `INSERT INTO entities (id, source_id, entity_type, name, canonical_name, bio, position, status, license_class, created_at, updated_at)
       VALUES (?, 'hollywood-api', 'person', ?, ?, '', ?, 'active', 'public', ?, ?)`
    ).run(entityId, name, name.toLowerCase(), args.position, now, now);
    return {
      id: entityId,
      name,
      agencyBio: null,
      position: args.position,
      status: "active",
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
  },

  deleteCandidates: (_parent: unknown, args: { candidateIds: string[] }) => {
    const db = getDb();
    for (const cid of args.candidateIds) {
      db.prepare("DELETE FROM entities WHERE id = ?").run(cid);
    }
    return args.candidateIds.map((id) => ({ id }));
  },

  updateCandidates: (_parent: unknown, args: { candidates: Record<string, unknown>[] }) => {
    return args.candidates.map((c) => ({
      id: c["candidateId"],
      name: c["name"] ?? "Updated",
      agencyBio: null,
      position: c["position"] ?? "",
      status: "active",
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
    }));
  },

  addCandidateScript: () => true,
  removeCandidateScript: () => true,
};

// ── Merge all resolvers ─────────────────────────────────────────────────────
const resolvers = {
  Query: {
    ...candidateResolvers.Query,
    ...projectResolvers.Query,
    ...userResolvers.Query,
    ...hollywoodQueryExtensions,
  },
  Mutation: {
    ...candidateResolvers.Mutation,
    ...projectResolvers.Mutation,
    ...userResolvers.Mutation,
    ...hollywoodMutations,
  },
  // Field-level resolvers for types needing lazy resolution
  Candidate: candidateResolvers.Candidate ?? {},
  Submission: {
    submissionJson: (parent: { submissionJson: Record<string, unknown> }) => parent.submissionJson,
    samples: () => [],
    rawSamples: () => [],
  },
};

const schema = createSchema({
  typeDefs,
  resolvers,
});

const yoga = createYoga({ schema });
const server = createServer(yoga);

server.listen(PORT, HOST, () => {
  console.log(`🎬 Hollywood GraphQL API running at http://${HOST}:${PORT}/graphql`);
  const dbPath = process.env["HOLLYWOOD_DB_PATH"] ?? "~/.hominem/hollywood.db";
  const dbVersion = process.env["HOLLYWOOD_API_PORT"] ?? "default";
  console.log(`   Database: ${dbPath}`);
});

process.on("SIGINT", () => {
  console.log("\nShutting down...");
  closeDb();
  server.close();
  process.exit(0);
});

process.on("SIGTERM", () => {
  closeDb();
  server.close();
  process.exit(0);
});
