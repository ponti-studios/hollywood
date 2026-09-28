import { EntityRepository } from "../db/repositories/EntityRepository.js";

export interface GroundedEntity {
  name: string;
  entityType: string;
  companyType: string | null;
  titleType: string | null;
}

const CAPITALIZED_PHRASE = /\b[A-Z][\w'&-]*(?:\s+[A-Z][\w'&-]*){0,3}\b/g;
const STOPWORD_PHRASES = new Set(["I", "What", "How", "When", "Where", "Why", "Who"]);

/**
 * Pulls capitalized name-shaped phrases out of a query (e.g. "Artist One",
 * "Warner Records") and looks them up against the entity graph. This is what
 * replaces setlist's CustomMemoryStorage keyword-overlap cache: sub-agents
 * get grounded in real entities from the graph instead of a per-process
 * in-memory guess.
 */
export function extractCandidatePhrases(query: string): string[] {
  const matches = query.match(CAPITALIZED_PHRASE) ?? [];
  const seen = new Set<string>();
  const phrases: string[] = [];
  for (const raw of matches) {
    // Strip a trailing possessive ("What's" -> "What") so contractions of
    // stopwords aren't mistaken for name-shaped phrases.
    const match = raw.replace(/'s$/i, "");
    if (!match || STOPWORD_PHRASES.has(match)) continue;
    const key = match.toLowerCase();
    if (seen.has(key)) continue;
    seen.add(key);
    phrases.push(match);
  }
  return phrases;
}

export function findGroundedEntities(query: string, entityRepo: EntityRepository = new EntityRepository(), limit = 5): GroundedEntity[] {
  const phrases = extractCandidatePhrases(query);
  const seenIds = new Set<string>();
  const found: GroundedEntity[] = [];

  for (const phrase of phrases) {
    if (found.length >= limit) break;
    const { rows } = entityRepo.searchByName(phrase, limit);
    for (const row of rows) {
      if (found.length >= limit) break;
      if (seenIds.has(row.id)) continue;
      seenIds.add(row.id);
      found.push({
        name: row.name,
        entityType: row.entityType,
        companyType: row.companyType,
        titleType: row.titleType,
      });
    }
  }

  return found;
}

export function formatGroundedContext(entities: GroundedEntity[]): string | null {
  if (!entities.length) return null;
  const lines = entities.map((e) => {
    const kind = e.companyType ?? e.titleType ?? e.entityType;
    return `- ${e.name} (${kind})`;
  });
  return `Known entities from the hollywood graph relevant to this query:\n${lines.join("\n")}`;
}
