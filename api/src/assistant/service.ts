import { EntityRepository } from "../db/repositories/EntityRepository.js";
import { AGENT_DEFINITIONS } from "./agents.js";
import type { AgentId } from "./agents.js";
import { routeQuery } from "./director.js";
import { findGroundedEntities, formatGroundedContext } from "./grounding.js";
import { chatCompletion } from "./llm.js";
import type { ChatMessage } from "./llm.js";

const DIRECTOR_FALLBACK_PROMPT =
  "You are the Director of an entertainment-industry assistant. Answer the user's query directly and concisely.";

export interface AssistantChatResult {
  agent: string;
  response: string;
}

export class AssistantService {
  constructor(
    private entityRepo: EntityRepository = new EntityRepository(),
    private chatFn: (messages: ChatMessage[]) => Promise<string> = chatCompletion,
  ) {}

  async chat(query: string): Promise<AssistantChatResult> {
    const decision = await routeQuery(query, this.chatFn);

    if (decision.kind === "agent") {
      return this.runSubAgent(decision.agentId, query);
    }

    if (decision.kind === "none") {
      const response = await this.chatFn([
        { role: "system", content: DIRECTOR_FALLBACK_PROMPT },
        { role: "user", content: query },
      ]);
      return { agent: "director", response };
    }

    throw new Error("Director could not route or respond to the query.");
  }

  private async runSubAgent(agentId: AgentId, query: string): Promise<AssistantChatResult> {
    const definition = AGENT_DEFINITIONS[agentId];
    const grounded = findGroundedEntities(query, this.entityRepo);
    const groundedContext = formatGroundedContext(grounded);

    const systemLines = [
      `You are the ${definition.name}. Role: ${definition.role}. Goal: ${definition.goal}`,
      definition.backstory,
    ];
    if (groundedContext) systemLines.push(groundedContext);

    const response = await this.chatFn([
      { role: "system", content: systemLines.join("\n\n") },
      { role: "user", content: query },
    ]);

    return { agent: definition.name, response };
  }
}
