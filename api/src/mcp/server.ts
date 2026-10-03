import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { z } from "zod";
import { EntityRepository } from "../db/repositories/EntityRepository.js";
import { searchEntityGraph } from "../assistant/tools.js";
import { AssistantService } from "../assistant/service.js";
import { BUILTIN_SOURCES } from "../ingest/registry.js";

/**
 * Exposes hollywood to any MCP-compatible chat client (Claude Desktop, a
 * WhatsApp bot fronted by an MCP client, etc.) as two tools: a direct graph
 * lookup, and the same Director/sub-agent assistant the REST API's
 * POST /assistant/chat uses. Deliberately read-only/conversational — no
 * ingest-triggering or write tools yet.
 */
export function buildMcpServer(entityRepo: EntityRepository = new EntityRepository()): McpServer {
  const server = new McpServer({ name: "hollywood", version: "0.1.0" });

  server.registerTool(
    "search_entities",
    {
      title: "Search entity graph",
      description:
        "Search the hollywood entity graph for people, artists, companies, labels, titles, or venues by name.",
      inputSchema: { query: z.string().describe("The name or partial name to search for.") },
      annotations: { readOnlyHint: true },
    },
    async ({ query }) => ({ content: [{ type: "text", text: searchEntityGraph(query, entityRepo) }] }),
  );

  server.registerTool(
    "list_sources",
    {
      title: "List ingest sources",
      description: "List the data sources hollywood's entity graph is built from (e.g. tmdb, spotify, wga).",
      annotations: { readOnlyHint: true },
    },
    async () => ({
      content: [
        {
          type: "text",
          text: BUILTIN_SOURCES.map((s) => `- ${s.sourceId}: ${s.name}`).join("\n"),
        },
      ],
    }),
  );

  // Constructed lazily so the MCP server can start (and search_entities/list_sources
  // still work) without OPENROUTER_API_KEY set — only chat needs it.
  let assistantService: AssistantService | null = null;
  function getAssistantService(): AssistantService {
    if (!assistantService) assistantService = new AssistantService(entityRepo);
    return assistantService;
  }

  server.registerTool(
    "chat",
    {
      title: "Ask the hollywood assistant",
      description:
        "Ask hollywood's Director assistant a question in natural language (touring, financial, marketing, or " +
        "calendar topics). It routes to the right specialist and can look up entities in the graph.",
      inputSchema: { query: z.string().min(1).describe("The question or request, in natural language.") },
    },
    async ({ query }) => {
      const result = await getAssistantService().chat(query);
      return { content: [{ type: "text", text: result.response }] };
    },
  );

  return server;
}
