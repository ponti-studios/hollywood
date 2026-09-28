import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { setupTestDb } from "../db/test-utils.js";
import { EntityRepository } from "../db/repositories/EntityRepository.js";
import { AssistantService } from "./service.js";
import type { ChatMessage } from "./llm.js";

describe("AssistantService", () => {
  let entityRepo: EntityRepository;
  let cleanup: () => void;

  beforeEach(() => {
    const test = setupTestDb();
    entityRepo = new EntityRepository(test.db);
    cleanup = test.cleanup;

    entityRepo.upsert({
      sourceId: "spotify",
      entityType: "artist",
      name: "Artist One",
      canonicalName: "artist one",
      licenseClass: "api_terms",
    });
  });

  afterEach(() => cleanup());

  it("routes to a sub-agent and grounds it in matching graph entities", async () => {
    const calls: ChatMessage[][] = [];
    const chat = async (messages: ChatMessage[]) => {
      calls.push(messages);
      if (calls.length === 1) return "touring";
      return "Artist One's tour budget looks healthy.";
    };

    const service = new AssistantService(entityRepo, chat);
    const result = await service.chat("What's the tour budget for Artist One?");

    expect(result.agent).toBe("Touring Agent");
    expect(result.response).toBe("Artist One's tour budget looks healthy.");
    expect(calls).toHaveLength(2);
    const subAgentSystemPrompt = calls[1]![0]!.content;
    expect(subAgentSystemPrompt).toContain("Touring Agent");
    expect(subAgentSystemPrompt).toContain("Artist One");
  });

  it("lets the director answer directly when no sub-agent fits", async () => {
    const calls: ChatMessage[][] = [];
    const chat = async (messages: ChatMessage[]) => {
      calls.push(messages);
      if (calls.length === 1) return "none";
      return "I'm not sure, can you clarify?";
    };

    const service = new AssistantService(entityRepo, chat);
    const result = await service.chat("What's the meaning of life?");

    expect(result.agent).toBe("director");
    expect(result.response).toBe("I'm not sure, can you clarify?");
  });

  it("throws when the director response is unresolved", async () => {
    const chat = async () => "banana";
    const service = new AssistantService(entityRepo, chat);
    await expect(service.chat("???")).rejects.toThrow("could not route");
  });
});
