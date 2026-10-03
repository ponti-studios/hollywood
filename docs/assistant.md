# Assistant (Director + sub-agents)

`POST /assistant/chat` ports setlist's Director/sub-agent pattern
(`backend/main.py`, `backend/agents/*.py`) to TypeScript on top of the
[OpenAI Agents SDK](https://openai.github.io/openai-agents-js/) (`@openai/agents`),
talking to OpenRouter instead of OpenAI's own endpoint, and reading the
hollywood entity graph directly instead of setlist's own Postgres/Clerk stack
or its in-memory "memory" store.

## Architecture

- `assistant/model.ts` — `configureOpenRouter()` points the SDK's default
  model provider at OpenRouter: an `openai` client constructed with
  OpenRouter's `baseURL`, `setOpenAIAPI('chat_completions')` (OpenRouter
  doesn't implement OpenAI's newer Responses API), and tracing disabled
  (tracing would otherwise try to export run traces to OpenAI's platform
  using the OpenRouter key). Called lazily, on first request, not at module
  load — the whole API must still boot without `OPENROUTER_API_KEY` set.
- `assistant/agents.ts` — builds one `Agent` per sub-agent (Touring/
  Financial/Marketing/Calendar) and a Director `Agent` with `handoffs` to
  all four. The SDK's native handoff mechanism replaces the hand-rolled
  Director routing/parsing this slice originally shipped with.
- `assistant/tools.ts` — `search_entity_graph`, an SDK `tool()` wrapping
  `EntityRepository.searchByName`. Every sub-agent gets it, and the model
  decides when to call it, instead of a regex heuristic pre-extracting
  "name-shaped phrases" from the query.
- `assistant/service.ts` — `AssistantService.chat(query)` calls
  `run(directorAgent, query)` and returns `{ agent, response }` from the
  result's `lastAgent`/`finalOutput`. Also logs every run via `costLog.ts`.
- `assistant/costLog.ts` — appends one entry per `chat()` call to
  `${HOLLYWOOD_DATA_DIR}/assistant-runs.jsonl` as JSON Lines (`appendFileSync`,
  one `JSON.parse`-able object per line — not a JSON array file, on purpose:
  an array requires reading, parsing, and rewriting the entire file on every
  call, which is quadratic I/O as history grows and runs synchronously on the
  request thread; a caught bug in review before this shipped). Read it back
  with `jq -s . assistant-runs.jsonl` for a proper array. Each entry:
  timestamp, model, query, responding agent, response text, and `metrics`
  (aggregated `requests`/`inputTokens`/`outputTokens`/
  `totalTokens` from `RunResult.runContext.usage`, plus `costUsd` summed from
  OpenRouter's per-request `cost` field). That `cost` field is an
  OpenRouter-specific extension to the OpenAI-compatible response, only
  present when the request opts in — `model.ts`'s
  `COST_TRACKING_MODEL_SETTINGS` sets `providerData.usage.include = true` on
  every agent and `preserveRawUsage: true` so the SDK keeps the raw value on
  `ModelResponse.rawUsage` instead of discarding it during normalization.
  Logging failures are caught and never fail the chat response itself.

## Model

Runs on `openai/gpt-5.6-luna` via OpenRouter (`model.ts`'s `ASSISTANT_MODEL`),
not `ingest/llm.ts`'s `DEFAULT_MODEL` (`openai/gpt-4o-mini`, used only for
submission extraction) — the two are independent and can move separately.

## What carried over from setlist

- The Director → sub-agent shape itself: one router agent, four
  specialists (Touring/Financial/Marketing/Calendar).
- Each sub-agent's `role`/`goal`/`backstory` framing, ported verbatim from
  `backend/agents/*.py` into `agents.ts`'s `SUB_AGENT_DEFINITIONS` and
  folded into each `Agent`'s `instructions`.

## What did not carry over

- CrewAI's `Agent`/`Task`/`Crew` plumbing and Cloudflare Workers AI
  per-agent model selection — replaced with `@openai/agents` + OpenRouter.
- The hand-rolled Director routing/parsing this slice shipped with
  initially (`director.ts`'s word-extraction logic) — replaced by the
  SDK's native `handoffs`.
- `CustomMemoryStorage`, setlist's in-process keyword-overlap "memory" —
  every sub-agent in setlist was byte-for-byte identical CrewAI boilerplate
  with no real data access. Replaced with the `search_entity_graph` tool,
  a real lookup against the entity graph the model calls on its own terms.

## Deliberately out of scope for this slice

- Persistent conversation history (setlist didn't have this either — its
  "memory" was a per-process dictionary, not durable). The SDK has a
  `Session` concept for this; not wired up yet.
- Tool-calling beyond entity lookup (e.g. an agent that can write a
  `deals`/`representation` row, or query `credits` for a specific artist's
  discography).
- A chat UI — this ships as an API only, matching hollywood's existing
  API-only posture.

## MCP server

`POST /mcp` (Hono route in `src/index.ts`, server built in `mcp/server.ts`)
exposes hollywood to any MCP-compatible chat client — Claude Desktop, a
WhatsApp bot fronted by an MCP client, etc. — as three tools, built on
`@modelcontextprotocol/sdk`'s `McpServer` mounted via `@hono/mcp`'s
`StreamableHTTPTransport`:

- `search_entities` — wraps `assistant/tools.ts`'s `searchEntityGraph`
  directly (same formatting/prompt-injection stripping as the agent tool).
- `list_sources` — read-only listing of `ingest/registry.ts`'s
  `BUILTIN_SOURCES`.
- `chat` — wraps `AssistantService.chat`, i.e. the same Director/sub-agent
  routing `POST /assistant/chat` uses. Needs `OPENROUTER_API_KEY`, checked
  lazily on first call, same as the REST route.

One `McpServer`/`StreamableHTTPTransport` pair per process — `connect()` is
a one-time bind, not per-request, so the route guards it with
`isConnected()`. Deliberately minimal and read-safe/conversational for now:
no ingest-triggering or write tools, and no WhatsApp-specific integration —
that's a separate, not-yet-started piece of work that would sit in front of
this server as its own MCP client.

Tested with the MCP SDK's `InMemoryTransport` + `Client` in
`mcp/server.test.ts` (real protocol round-trip, not just calling the
handler functions directly), and live over real HTTP against a scratch DB
(`initialize` → `tools/list` → `tools/call`).

## Known gaps from manual testing

- ~~`search_entity_graph`'s output only ever includes each matched entity's
  name and type/kind, never `metadataJson`~~ — fixed: `tools.ts`'s
  `formatMetadata` now renders metadata's flat key/value pairs (dropping
  nested objects/arrays, capped at 300 chars, line breaks stripped same as
  entity names). Re-tested live against the same seeded artist
  (`metadata_json: {"genre": "synth-pop"}`) — the assistant now correctly
  answers "synth-pop" instead of "doesn't specify a genre."
- Earlier manual testing (on `openai/gpt-4o-mini`) showed the model
  confidently hallucinating facts about both real and fabricated entities
  instead of calling `search_entity_graph` at all. The same test prompts
  against `openai/gpt-5.6-luna` correctly called the tool and answered
  honestly, including admitting "no matching entity" for a fabricated name.
  Two manual runs isn't a rigorous comparison — noted here as an observation
  worth re-testing if tool-calling reliability regresses, not a closed issue.
