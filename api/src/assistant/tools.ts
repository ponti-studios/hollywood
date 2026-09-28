import { z } from "zod";
import { tool } from "@openai/agents";
import { EntityRepository } from "../db/repositories/EntityRepository.js";

/**
 * Replaces setlist's CustomMemoryStorage (a fake in-process keyword-overlap
 * "memory" cache shared by every sub-agent) with a real lookup against the
 * hollywood entity graph. Exposed as an SDK tool rather than pre-computed
 * regex-extracted context, so the model decides when a query names a real
 * entity worth grounding in, instead of a brittle phrase heuristic.
 */
export function searchEntityGraph(query: string, entityRepo: EntityRepository = new EntityRepository()): string {
  const trimmed = query.trim();
  if (!trimmed) return "No search query provided.";

  const { rows } = entityRepo.searchByName(trimmed, 5);
  if (!rows.length) return `No entities in the hollywood graph matched "${trimmed}".`;

  // Strip line breaks so a graph-sourced name can't inject new "lines" into
  // whatever the model does with this tool output next.
  const lines = rows.map((row) => {
    const kind = (row.companyType ?? row.titleType ?? row.entityType).replace(/[\r\n]+/g, " ").trim();
    const name = row.name.replace(/[\r\n]+/g, " ").trim();
    return `- ${name} (${kind})`;
  });
  return lines.join("\n");
}

export function createSearchEntityGraphTool(entityRepo: EntityRepository = new EntityRepository()) {
  return tool({
    name: "search_entity_graph",
    description:
      "Search the hollywood entity graph for people, artists, companies, labels, titles, or venues by name. " +
      "Call this whenever the user's query names a specific person, artist, company, or project you should ground your answer in.",
    parameters: z.object({
      query: z.string().describe("The name or partial name to search for."),
    }),
    execute: async ({ query }) => searchEntityGraph(query, entityRepo),
  });
}
