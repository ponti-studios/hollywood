import { appendFileSync, mkdirSync, mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { buildLogEntry, extractRunMetrics, recordRun } from "./costLog.js";
import type { AssistantRunLogEntry } from "./costLog.js";

function fakeResult(overrides: { usage?: object; rawResponses?: object[] } = {}) {
  return {
    runContext: { usage: { requests: 1, inputTokens: 10, outputTokens: 5, totalTokens: 15, ...overrides.usage } } as any,
    rawResponses: (overrides.rawResponses ?? []) as any,
  };
}

function readEntries(logPath: string): AssistantRunLogEntry[] {
  const text = readFileSync(logPath, "utf-8");
  return text
    .split("\n")
    .filter((line) => line.trim())
    .map((line) => JSON.parse(line));
}

describe("extractRunMetrics", () => {
  it("reads aggregated token usage from runContext.usage", () => {
    const metrics = extractRunMetrics(fakeResult({ usage: { requests: 3, inputTokens: 100, outputTokens: 50, totalTokens: 150 } }));
    expect(metrics).toMatchObject({ requests: 3, inputTokens: 100, outputTokens: 50, totalTokens: 150 });
  });

  it("sums OpenRouter's per-request cost across every raw response", () => {
    const metrics = extractRunMetrics(fakeResult({ rawResponses: [{ rawUsage: { cost: 0.001 } }, { rawUsage: { cost: 0.002 } }] }));
    expect(metrics.costUsd).toBeCloseTo(0.003, 10);
  });

  it("leaves costUsd undefined when no raw response reports a cost", () => {
    const metrics = extractRunMetrics(fakeResult({ rawResponses: [{ rawUsage: {} }, {}] }));
    expect(metrics.costUsd).toBeUndefined();
  });

  it("ignores a non-numeric cost field rather than throwing", () => {
    const metrics = extractRunMetrics(fakeResult({ rawResponses: [{ rawUsage: { cost: "not a number" } }] }));
    expect(metrics.costUsd).toBeUndefined();
  });
});

describe("recordRun", () => {
  let dir: string;
  let logPath: string;

  beforeEach(() => {
    dir = mkdtempSync(join(tmpdir(), "hollywood-costlog-test-"));
    logPath = join(dir, "nested", "assistant-runs.jsonl");
  });

  afterEach(() => rmSync(dir, { recursive: true, force: true }));

  it("creates the log file (and parent dir) with the first entry", () => {
    const entry = buildLogEntry({
      model: "openai/gpt-5.6-luna",
      query: "test query",
      agent: { name: "Director" } as any,
      response: "test response",
      result: fakeResult(),
    });

    recordRun(entry, logPath);

    expect(readEntries(logPath)).toEqual([entry]);
  });

  it("appends subsequent entries as new lines instead of rewriting the file", () => {
    const first = buildLogEntry({ model: "m", query: "q1", agent: undefined, response: "r1", result: fakeResult() });
    const second = buildLogEntry({ model: "m", query: "q2", agent: undefined, response: "r2", result: fakeResult() });

    recordRun(first, logPath);
    recordRun(second, logPath);

    expect(readEntries(logPath)).toEqual([first, second]);
  });

  it("never reads the existing file back, so a malformed earlier line can't break a later append", () => {
    mkdirSync(dirname(logPath), { recursive: true });
    appendFileSync(logPath, "not json\n");

    const entry = buildLogEntry({ model: "m", query: "q", agent: undefined, response: "r", result: fakeResult() });
    recordRun(entry, logPath);

    const lines = readFileSync(logPath, "utf-8").trim().split("\n");
    expect(lines[0]).toBe("not json");
    expect(JSON.parse(lines[1]!)).toEqual(entry);
  });
});

describe("buildLogEntry", () => {
  it("falls back to 'unknown' when no agent is given", () => {
    const entry = buildLogEntry({ model: "m", query: "q", agent: undefined, response: "r", result: fakeResult() });
    expect(entry.agent).toBe("unknown");
  });
});
