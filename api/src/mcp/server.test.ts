import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { EntityRepository } from "../db/repositories/EntityRepository.js";
import { setupTestDb } from "../db/test-utils.js";
import { buildMcpServer } from "./server.js";

describe("hollywood MCP server", () => {
  let entityRepo: EntityRepository;
  let cleanup: () => void;
  let client: Client;

  beforeEach(async () => {
    const test = setupTestDb();
    entityRepo = new EntityRepository(test.db);
    cleanup = test.cleanup;

    entityRepo.upsert({
      sourceId: "spotify",
      entityType: "artist",
      name: "Nova Bright",
      canonicalName: "nova bright",
      licenseClass: "api_terms",
      metadataJson: JSON.stringify({ genre: "synth-pop" }),
    });

    const server = buildMcpServer(entityRepo);
    const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
    client = new Client({ name: "test-client", version: "1.0.0" });
    await Promise.all([client.connect(clientTransport), server.connect(serverTransport)]);
  });

  afterEach(async () => {
    await client.close();
    cleanup();
  });

  it("lists search_entities, list_sources, and chat as available tools", async () => {
    const { tools } = await client.listTools();
    expect(tools.map((t) => t.name).sort()).toEqual(["chat", "list_sources", "search_entities"]);
  });

  it("search_entities returns matching entities including metadata", async () => {
    const result = await client.callTool({ name: "search_entities", arguments: { query: "Nova Bright" } });
    const content = result.content as Array<{ type: string; text: string }>;
    expect(content[0]?.text).toContain("Nova Bright (artist)");
    expect(content[0]?.text).toContain("genre: synth-pop");
  });

  it("list_sources returns the built-in ingest sources", async () => {
    const result = await client.callTool({ name: "list_sources" });
    const content = result.content as Array<{ type: string; text: string }>;
    expect(content[0]?.text).toContain("spotify: Spotify Web API");
    expect(content[0]?.text).toContain("tmdb: TMDb API");
  });
});
