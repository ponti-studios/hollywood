import { run } from "@openai/agents";
import type { Agent, RunResult } from "@openai/agents";
import { EntityRepository } from "../db/repositories/EntityRepository.js";
import { buildDirectorAgent } from "./agents.js";
import { buildLogEntry, recordRun } from "./costLog.js";
import { ASSISTANT_MODEL, configureOpenRouter } from "./model.js";

export interface AssistantChatResult {
  agent: string;
  response: string;
}

type RunAgentFn = (
  agent: Agent<any, any>,
  query: string,
) => Promise<Pick<RunResult<any, any>, "finalOutput" | "lastAgent" | "runContext" | "rawResponses">>;

export class AssistantService {
  private directorAgent: Agent;

  constructor(
    entityRepo: EntityRepository = new EntityRepository(),
    private runAgent: RunAgentFn = run,
    private logRun: typeof recordRun = recordRun,
  ) {
    // Only configure the real OpenRouter client when actually running against
    // it — tests inject their own runAgent and never need OPENROUTER_API_KEY.
    if (runAgent === run) configureOpenRouter();
    this.directorAgent = buildDirectorAgent(entityRepo);
  }

  async chat(query: string): Promise<AssistantChatResult> {
    const result = await this.runAgent(this.directorAgent, query);
    const response = typeof result.finalOutput === "string" ? result.finalOutput : JSON.stringify(result.finalOutput ?? "");
    const agent = result.lastAgent ?? this.directorAgent;

    try {
      this.logRun(buildLogEntry({ model: ASSISTANT_MODEL, query, agent, response, result }));
    } catch (e) {
      // Investigation logging must never break a real chat response.
      console.error("assistant cost/response logging failed:", e);
    }

    return { agent: agent.name, response };
  }
}
