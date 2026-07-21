set shell := ["zsh", "-cu"]

default:
    @just --list

clean:
    rm -rf dist/ data/

help:
    @just --list

# ── API ──────────────────────────────────────────────────────────────────────
api-setup:
    npm install

api-dev:
    npx tsx watch src/index.ts

api-typecheck:
    npx tsc --noEmit

api-lint:
    npx oxlint

api-lint-fix:
    npx oxlint --fix

api-build:
    npx tsc

api-start:
    node dist/index.js

api-docs:
    @echo "OpenAPI spec available at http://localhost:4000/openapi"
    @echo "Start the server with: just api-dev"

# Wipes the dev SQLite db, recreates it from the Drizzle migrations, then
# ingests every source from scratch, capped at `limit` records per source
# (default 3 — enough to prove the pipeline works, not a mass ingest). Pass
# 0 for an unbounded full ingest. Destructive — dev use only.
db-refresh limit="3":
    npx tsx src/scripts/refresh-db.ts --limit={{limit}}

# ── Bruno ────────────────────────────────────────────────────────────────────
bruno-import:
    rm -rf .bruno
    npx --yes @usebruno/cli import openapi \
    --source http://localhost:4000/openapi \
    --output .bruno \
    --group-by tags

bruno-run:
    cd .bruno && npx --yes @usebruno/cli run -r --env "Local development" --exclude-tags mutating

bruno-run-all:
    cd .bruno && npx --yes @usebruno/cli run -r --env "Local development"
