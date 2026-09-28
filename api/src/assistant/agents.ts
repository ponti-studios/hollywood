export type AgentId = "touring" | "financial" | "marketing" | "calendar";

export interface AgentDefinition {
  id: AgentId;
  name: string;
  role: string;
  goal: string;
  backstory: string;
}

/**
 * Ported from setlist's CrewAI agents (backend/agents/*.py). Role/goal/backstory
 * are carried over verbatim; the Cloudflare Workers AI models and the fake
 * keyword-overlap "memory" store are not — this reads the real hollywood
 * entity graph instead (see grounding.ts).
 */
export const AGENT_DEFINITIONS: Record<AgentId, AgentDefinition> = {
  touring: {
    id: "touring",
    name: "Touring Agent",
    role: "Handles touring queries",
    goal: "Assist with touring logistics and planning.",
    backstory: "Specialized in touring assistance.",
  },
  financial: {
    id: "financial",
    name: "Financial Agent",
    role: "Handles financial queries",
    goal: "Provide insights and manage financial tasks.",
    backstory: "Specialized in finance and budget management.",
  },
  marketing: {
    id: "marketing",
    name: "Marketing Agent",
    role: "Handles marketing queries",
    goal: "Assist with marketing strategies and planning.",
    backstory: "Specialized in marketing and audience engagement.",
  },
  calendar: {
    id: "calendar",
    name: "Calendar Agent",
    role: "Handles calendar queries",
    goal: "Assist with scheduling and calendar management.",
    backstory: "Specialized in organizing and managing schedules.",
  },
};

export const AGENT_IDS = Object.keys(AGENT_DEFINITIONS) as AgentId[];

export function isAgentId(value: string): value is AgentId {
  return (AGENT_IDS as string[]).includes(value);
}
