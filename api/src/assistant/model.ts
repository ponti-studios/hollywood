import OpenAI from "openai";
import { setDefaultOpenAIClient, setOpenAIAPI, setTracingDisabled } from "@openai/agents";
import { env } from "../env.js";
import { DEFAULT_MODEL, OPENROUTER_BASE_URL } from "../ingest/llm.js";

export { DEFAULT_MODEL };

let configured = false;

/**
 * Points the OpenAI Agents SDK at OpenRouter instead of api.openai.com.
 * OpenRouter only implements the Chat Completions API, not OpenAI's newer
 * Responses API, so setOpenAIAPI('chat_completions') is required — without
 * it every agent run 404s against OpenRouter. Tracing is disabled since it
 * would otherwise try to export run traces to platform.openai.com using the
 * same (OpenRouter) key.
 */
export function configureOpenRouter(): void {
  if (configured) return;
  if (!env.OPENROUTER_API_KEY) {
    throw new Error("OPENROUTER_API_KEY is required to run the assistant.");
  }

  const client = new OpenAI({
    apiKey: env.OPENROUTER_API_KEY,
    baseURL: OPENROUTER_BASE_URL,
    defaultHeaders: {
      "HTTP-Referer": "https://hollywood.ponti.io",
      "X-Title": "Hollywood Assistant",
    },
  });

  setDefaultOpenAIClient(client);
  setOpenAIAPI("chat_completions");
  setTracingDisabled(true);
  configured = true;
}
