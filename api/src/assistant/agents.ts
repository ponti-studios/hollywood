import { Agent } from "@openai/agents";
import { EntityRepository } from "../db/repositories/EntityRepository.js";
import { ASSISTANT_MODEL, COST_TRACKING_MODEL_SETTINGS } from "./model.js";
import { createSearchEntityGraphTool } from "./tools.js";

export interface SubAgentDefinition {
  id: "touring" | "financial" | "marketing" | "calendar";
  name: string;
  role: string;
  goal: string;
  backstory: string;
}

/**
 * role/goal/backstory carried over verbatim from setlist's CrewAI agents
 * (backend/agents/*.py) — that framing is the one part of setlist worth
 * keeping. Everything about *how* they run (Cloudflare Workers AI models,
 * CrewAI's Task/Crew plumbing, the fake keyword-overlap memory store) does
 * not carry over; these are now plain @openai/agents Agents talking to
 * OpenRouter, grounded in the real entity graph via search_entity_graph.
 */
export const SUB_AGENT_DEFINITIONS: SubAgentDefinition[] = [
  {
    id: "touring",
    name: "Touring Agent",
    role: "Handles touring queries",
    goal: "Assist with touring logistics and planning.",
    backstory: "Specialized in touring assistance.",
  },
  {
    id: "financial",
    name: "Financial Agent",
    role: "Handles financial queries",
    goal: "Provide insights and manage financial tasks.",
    backstory: "Specialized in finance and budget management.",
  },
  {
    id: "marketing",
    name: "Marketing Agent",
    role: "Handles marketing queries",
    goal: "Assist with marketing strategies and planning.",
    backstory: "Specialized in marketing and audience engagement.",
  },
  {
    id: "calendar",
    name: "Calendar Agent",
    role: "Handles calendar queries",
    goal: "Assist with scheduling and calendar management.",
    backstory: "Specialized in organizing and managing schedules.",
  },
];

function subAgentInstructions(def: SubAgentDefinition): string {
  return [
    `You are the ${def.name}. Role: ${def.role}. Goal: ${def.goal}`,
    def.backstory,
    "Use the search_entity_graph tool whenever the query names a specific person, artist, company, or project, and ground your answer in what it returns instead of guessing.",
  ].join("\n\n");
}

export function buildDirectorAgent(entityRepo: EntityRepository = new EntityRepository()): Agent {
  const searchEntityGraphTool = createSearchEntityGraphTool(entityRepo);

  const subAgents = SUB_AGENT_DEFINITIONS.map(
    (def) =>
      new Agent({
        name: def.name,
        model: ASSISTANT_MODEL,
        modelSettings: COST_TRACKING_MODEL_SETTINGS,
        instructions: subAgentInstructions(def),
        tools: [searchEntityGraphTool],
      }),
  );

  return new Agent({
    name: "Director",
    model: ASSISTANT_MODEL,
    modelSettings: COST_TRACKING_MODEL_SETTINGS,
    instructions:
      "You are the Director of an entertainment-industry assistant. Decide whether the user's query " +
      "belongs to one of your sub-agents — Touring, Financial, Marketing, or Calendar — and hand off to " +
      "it. If none of them fit, answer the query directly and concisely yourself.",
    handoffs: subAgents,
  });
}
