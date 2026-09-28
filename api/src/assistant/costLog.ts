import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import type { Agent, ModelResponse, RunResult } from "@openai/agents";
import { env } from "../env.js";

export interface RunMetrics {
  requests: number;
  inputTokens: number;
  outputTokens: number;
  totalTokens: number;
  /** Sum of each request's OpenRouter-reported cost (USD). Undefined if no
   * request reported a cost (e.g. COST_TRACKING_MODEL_SETTINGS wasn't applied,
   * or the provider that served the request doesn't return one). */
  costUsd: number | undefined;
}

export interface AssistantRunLogEntry {
  timestamp: string;
  model: string;
  query: string;
  agent: string;
  response: string;
  metrics: RunMetrics;
}

type RunResultLike = Pick<RunResult<any, any>, "runContext" | "rawResponses">;

/** OpenRouter's usage-include extension adds `cost` to the raw (pre-normalization)
 * usage object on each response — not part of the OpenAI Chat Completions spec,
 * so it only shows up in ModelResponse.rawUsage when preserveRawUsage is set. */
function extractCost(rawResponses: ModelResponse[]): number | undefined {
  let total = 0;
  let found = false;
  for (const response of rawResponses) {
    const cost = response.rawUsage?.["cost"];
    if (typeof cost === "number") {
      total += cost;
      found = true;
    }
  }
  return found ? total : undefined;
}

export function extractRunMetrics(result: RunResultLike): RunMetrics {
  const usage = result.runContext.usage;
  return {
    requests: usage.requests,
    inputTokens: usage.inputTokens,
    outputTokens: usage.outputTokens,
    totalTokens: usage.totalTokens,
    costUsd: extractCost(result.rawResponses),
  };
}

function defaultLogPath(): string {
  return resolve(env.HOLLYWOOD_DATA_DIR, "assistant-runs.json");
}

/**
 * Appends one entry to a JSON array file for manual cost/quality investigation.
 * Read-modify-write, not append-only — fine for this tool's actual usage
 * (a person running a handful of test queries locally), not built for
 * concurrent writers.
 */
export function recordRun(entry: AssistantRunLogEntry, logPath: string = defaultLogPath()): void {
  mkdirSync(dirname(logPath), { recursive: true });

  let entries: AssistantRunLogEntry[] = [];
  try {
    entries = JSON.parse(readFileSync(logPath, "utf-8"));
  } catch {
    entries = [];
  }

  entries.push(entry);
  writeFileSync(logPath, JSON.stringify(entries, null, 2) + "\n");
}

export function buildLogEntry(params: {
  model: string;
  query: string;
  agent: Agent | undefined;
  response: string;
  result: RunResultLike;
}): AssistantRunLogEntry {
  return {
    timestamp: new Date().toISOString(),
    model: params.model,
    query: params.query,
    agent: params.agent?.name ?? "unknown",
    response: params.response,
    metrics: extractRunMetrics(params.result),
  };
}
