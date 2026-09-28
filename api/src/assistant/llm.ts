import { env } from "../env.js";
import { DEFAULT_MODEL, OPENROUTER_BASE_URL } from "../ingest/llm.js";

export interface ChatMessage {
  role: "system" | "user" | "assistant";
  content: string;
}

export class AssistantLlmError extends Error {}

// This client only ever calls the OpenRouter endpoint, so it must not fall
// back to OPENAI_API_KEY (unlike ingest/llm.ts's getApiKey) — an OpenAI
// credential sent to OpenRouter fails authentication on every request.
function getApiKey(): string | null {
  return env.OPENROUTER_API_KEY ?? null;
}

/** Plain chat completion (no JSON schema, no extraction pipeline) for the assistant. */
export async function chatCompletion(messages: ChatMessage[], model = DEFAULT_MODEL): Promise<string> {
  const apiKey = getApiKey();
  if (!apiKey) throw new AssistantLlmError("OPENROUTER_API_KEY not set");

  const resp = await fetch(`${OPENROUTER_BASE_URL}/chat/completions`, {
    method: "POST",
    headers: {
      Authorization: `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "HTTP-Referer": "https://hollywood.ponti.io",
      "X-Title": "Hollywood Assistant",
    },
    body: JSON.stringify({ model, messages, temperature: 0.3 }),
    signal: AbortSignal.timeout(60_000),
  });

  if (!resp.ok) throw new AssistantLlmError(`OpenRouter request failed: ${resp.status} ${resp.statusText}`);

  const data = (await resp.json()) as Record<string, unknown>;
  if (data["error"]) {
    const err = data["error"] as { message?: string };
    throw new AssistantLlmError(`OpenRouter error: ${err.message ?? JSON.stringify(err)}`);
  }

  const choices = data["choices"] as Array<{ message: { content: string } }> | undefined;
  if (!choices || !choices.length) throw new AssistantLlmError("OpenRouter returned no choices");
  return choices[0]!.message.content;
}
