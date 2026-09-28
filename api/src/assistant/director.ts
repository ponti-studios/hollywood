import { AGENT_IDS, isAgentId } from "./agents.js";
import type { AgentId } from "./agents.js";
import { chatCompletion } from "./llm.js";
import type { ChatMessage } from "./llm.js";

const DIRECTOR_SYSTEM_PROMPT =
  "You are an intelligent assistant managing sub-agents: calendar, financial, marketing, and touring. " +
  "Your task is to decide if the query fits one of these sub-agents. Return ONLY the sub-agent name " +
  `('${AGENT_IDS.join("', '")}') or 'none' if it does not fit any sub-agent. ` +
  "Do NOT provide verbose responses. Do NOT answer the query yourself.";

export type DirectorDecision = { kind: "agent"; agentId: AgentId } | { kind: "none" } | { kind: "unresolved"; rawResponse: string };

/**
 * Parses the director LLM's routing response. Ported from setlist's
 * main.py::director_agent — take the first ~10 tokens, return the first one
 * that names a sub-agent, else fall back to "none" if that word appears.
 */
export function parseDirectorResponse(rawResponse: string): DirectorDecision {
  const words = rawResponse
    .trim()
    .toLowerCase()
    .split(/\s+/)
    .map((word) => word.replace(/[^a-z]/g, ""))
    .slice(0, 10);
  const matched = words.find(isAgentId);
  if (matched) return { kind: "agent", agentId: matched };
  if (words.includes("none")) return { kind: "none" };
  return { kind: "unresolved", rawResponse };
}

export async function routeQuery(query: string, chat: (messages: ChatMessage[]) => Promise<string> = chatCompletion): Promise<DirectorDecision> {
  const raw = await chat([
    { role: "system", content: DIRECTOR_SYSTEM_PROMPT },
    { role: "user", content: query },
  ]);
  return parseDirectorResponse(raw);
}
