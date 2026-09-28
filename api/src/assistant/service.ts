import { run } from "@openai/agents";
import type { Agent, RunResult } from "@openai/agents";
import { EntityRepository } from "../db/repositories/EntityRepository.js";
import { buildDirectorAgent } from "./agents.js";
import { configureOpenRouter } from "./model.js";

export interface AssistantChatResult {
  agent: string;
  response: string;
}

type RunAgentFn = (agent: Agent<any, any>, query: string) => Promise<Pick<RunResult<any, any>, "finalOutput" | "lastAgent">>;

export class AssistantService {
  private directorAgent: Agent;

  constructor(
    entityRepo: EntityRepository = new EntityRepository(),
    private runAgent: RunAgentFn = run,
  ) {
    // Only configure the real OpenRouter client when actually running against
    // it — tests inject their own runAgent and never need OPENROUTER_API_KEY.
    if (runAgent === run) configureOpenRouter();
    this.directorAgent = buildDirectorAgent(entityRepo);
  }

  async chat(query: string): Promise<AssistantChatResult> {
    const result = await this.runAgent(this.directorAgent, query);
    const response = typeof result.finalOutput === "string" ? result.finalOutput : JSON.stringify(result.finalOutput ?? "");
    const agent = result.lastAgent?.name ?? this.directorAgent.name;
    return { agent, response };
  }
}
