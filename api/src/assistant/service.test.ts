import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { setupTestDb } from "../db/test-utils.js";
import { EntityRepository } from "../db/repositories/EntityRepository.js";
import { AssistantService } from "./service.js";

describe("AssistantService", () => {
  let entityRepo: EntityRepository;
  let cleanup: () => void;

  beforeEach(() => {
    const test = setupTestDb();
    entityRepo = new EntityRepository(test.db);
    cleanup = test.cleanup;
  });

  afterEach(() => cleanup());

  it("returns the responding agent's name and final output", async () => {
    const runAgent = async () => ({
      finalOutput: "Artist One's tour budget looks healthy.",
      lastAgent: { name: "Touring Agent" } as any,
    });

    const service = new AssistantService(entityRepo, runAgent);
    const result = await service.chat("What's the tour budget for Artist One?");

    expect(result).toEqual({ agent: "Touring Agent", response: "Artist One's tour budget looks healthy." });
  });

  it("falls back to the director's own name when no sub-agent handled the run", async () => {
    const runAgent = async () => ({ finalOutput: "I'm not sure, can you clarify?", lastAgent: undefined });

    const service = new AssistantService(entityRepo, runAgent);
    const result = await service.chat("What's the meaning of life?");

    expect(result.agent).toBe("Director");
    expect(result.response).toBe("I'm not sure, can you clarify?");
  });

  it("stringifies a non-string final output rather than throwing", async () => {
    const runAgent = async () => ({ finalOutput: { note: "structured" }, lastAgent: { name: "Director" } as any });

    const service = new AssistantService(entityRepo, runAgent);
    const result = await service.chat("anything");

    expect(result.response).toBe(JSON.stringify({ note: "structured" }));
  });

  it("does not require OPENROUTER_API_KEY when a custom runAgent is injected", () => {
    expect(() => new AssistantService(entityRepo, async () => ({ finalOutput: "ok", lastAgent: undefined }))).not.toThrow();
  });
});
