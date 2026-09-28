# Assistant (Director + sub-agents)

`POST /assistant/chat` ports setlist's Director/sub-agent pattern
(`backend/main.py`, `backend/agents/*.py`) to TypeScript, reading the
hollywood entity graph directly instead of setlist's own Postgres/Clerk
stack or its in-memory "memory" store.

## What carried over from setlist

- The Director → sub-agent routing shape: an LLM classifies the query into
  `calendar` | `financial` | `marketing` | `touring` | `none`, ported
  token-for-token from `main.py::director_agent`'s parsing logic
  (`assistant/director.ts::parseDirectorResponse`).
- Each sub-agent's `role`/`goal`/`backstory` framing, ported verbatim from
  `backend/agents/*.py` (`assistant/agents.ts`).

## What did not carry over

- Cloudflare Workers AI per-agent model selection — replaced with hollywood's
  existing OpenRouter client (`assistant/llm.ts`, reusing `ingest/llm.ts`'s
  `OPENROUTER_BASE_URL`/`DEFAULT_MODEL`).
- `CustomMemoryStorage`, setlist's in-process keyword-overlap "memory" —
  every sub-agent in setlist was byte-for-byte identical CrewAI boilerplate
  with no real data access. Replaced with `assistant/grounding.ts`: it pulls
  capitalized name-shaped phrases out of the query and looks them up against
  the real entity graph (`EntityRepository.searchByName`), so a query about
  "Artist One" gets grounded in whatever hollywood actually knows about that
  entity, not a fabricated per-process cache.

## Deliberately out of scope for this slice

- Persistent conversation history (setlist didn't have this either — its
  "memory" was a per-process dictionary, not durable).
- Tool-calling beyond entity lookup (e.g. an agent that can write a
  `deals`/`representation` row, or query `credits` for a specific artist's
  discography).
- A chat UI — this ships as an API only, matching hollywood's existing
  API-only posture.
