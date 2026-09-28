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
  `${HOLLYWOOD_DATA_DIR}/assistant-runs.json` (a JSON array; read-modify-write,
  not built for concurrent writers — this is a local investigation tool, not
  production telemetry): timestamp, model, query, responding agent, response
  text, and `metrics` (aggregated `requests`/`inputTokens`/`outputTokens`/
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

## Known gaps from manual testing

- `search_entity_graph`'s output (`tools.ts`) only ever includes each
  matched entity's name and type/kind — never `metadataJson` (bio, genre,
  external links, etc.). A live test against a seeded artist with
  `metadata_json: {"genre": "synth-pop"}` got "the available information
  doesn't specify a genre" back — an honest non-hallucination, but the tool
  really could have answered correctly if it surfaced metadata. Not fixed
  yet.
- Earlier manual testing (on `openai/gpt-4o-mini`) showed the model
  confidently hallucinating facts about both real and fabricated entities
  instead of calling `search_entity_graph` at all. The same test prompts
  against `openai/gpt-5.6-luna` correctly called the tool and answered
  honestly, including admitting "no matching entity" for a fabricated name.
  Two manual runs isn't a rigorous comparison — noted here as an observation
  worth re-testing if tool-calling reliability regresses, not a closed issue.
