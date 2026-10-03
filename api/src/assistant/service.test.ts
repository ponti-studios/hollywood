import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { setupTestDb } from "../db/test-utils.js";
import { EntityRepository } from "../db/repositories/EntityRepository.js";
import { AssistantService } from "./service.js";
import type { AssistantRunLogEntry } from "./costLog.js";

function fakeUsage(overrides: Partial<{ requests: number; inputTokens: number; outputTokens: number; totalTokens: number }> = {}) {
  return { requests: 1, inputTokens: 10, outputTokens: 5, totalTokens: 15, ...overrides };
}

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
      runContext: { usage: fakeUsage() } as any,
      rawResponses: [],
    });

    const service = new AssistantService(entityRepo, runAgent, () => {});
    const result = await service.chat("What's the tour budget for Artist One?");

    expect(result).toEqual({ agent: "Touring Agent", response: "Artist One's tour budget looks healthy." });
  });

  it("falls back to the director's own name when no sub-agent handled the run", async () => {
    const runAgent = async () => ({
      finalOutput: "I'm not sure, can you clarify?",
      lastAgent: undefined,
      runContext: { usage: fakeUsage() } as any,
      rawResponses: [],
    });

    const service = new AssistantService(entityRepo, runAgent, () => {});
    const result = await service.chat("What's the meaning of life?");

    expect(result.agent).toBe("Director");
    expect(result.response).toBe("I'm not sure, can you clarify?");
  });

  it("stringifies a non-string final output rather than throwing", async () => {
    const runAgent = async () => ({
      finalOutput: { note: "structured" },
      lastAgent: { name: "Director" } as any,
      runContext: { usage: fakeUsage() } as any,
      rawResponses: [],
    });

    const service = new AssistantService(entityRepo, runAgent, () => {});
    const result = await service.chat("anything");

    expect(result.response).toBe(JSON.stringify({ note: "structured" }));
  });

  it("does not require OPENROUTER_API_KEY when a custom runAgent is injected", () => {
    const runAgent = async () => ({ finalOutput: "ok", lastAgent: undefined, runContext: { usage: fakeUsage() } as any, rawResponses: [] });
    expect(() => new AssistantService(entityRepo, runAgent, () => {})).not.toThrow();
  });

  it("logs the query, response, agent, and usage/cost metrics for every run", async () => {
    const runAgent = async () => ({
      finalOutput: "Artist One's tour budget looks healthy.",
      lastAgent: { name: "Touring Agent" } as any,
      runContext: { usage: fakeUsage({ requests: 2, inputTokens: 120, outputTokens: 40, totalTokens: 160 }) } as any,
      rawResponses: [{ rawUsage: { cost: 0.0004 } } as any, { rawUsage: { cost: 0.0002 } } as any],
    });

    const logged: AssistantRunLogEntry[] = [];
    const service = new AssistantService(entityRepo, runAgent, (entry) => {
      logged.push(entry);
    });

    await service.chat("What's the tour budget for Artist One?");

    expect(logged).toHaveLength(1);
    expect(logged[0]).toMatchObject({
      model: "openai/gpt-5.6-luna",
      query: "What's the tour budget for Artist One?",
      agent: "Touring Agent",
      response: "Artist One's tour budget looks healthy.",
      metrics: { requests: 2, inputTokens: 120, outputTokens: 40, totalTokens: 160, costUsd: 0.0006000000000000001 },
    });
    expect(logged[0]!.timestamp).toMatch(/^\d{4}-\d{2}-\d{2}T/);
  });

  it("does not fail the chat response when logging itself throws", async () => {
    const runAgent = async () => ({
      finalOutput: "fine",
      lastAgent: undefined,
      runContext: { usage: fakeUsage() } as any,
      rawResponses: [],
    });

    const service = new AssistantService(entityRepo, runAgent, () => {
      throw new Error("disk full");
    });

    await expect(service.chat("anything")).resolves.toEqual({ agent: "Director", response: "fine" });
  });
});
