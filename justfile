set shell := ["zsh", "-cu"]

default:
    @just --list

clean:
    rm -rf dist/ data/

help:
    @just --list

# ── API ──────────────────────────────────────────────────────────────────────
api-setup:
    cd api && npm install

api-dev:
    cd api && npx tsx watch src/index.ts

api-typecheck:
    cd api && npx tsc --noEmit

api-lint:
    cd api && npx oxlint

api-lint-fix:
    cd api && npx oxlint --fix

api-build:
    cd api && npx tsc

api-start:
    cd api && node dist/index.js

api-docs:
    @echo "OpenAPI spec available at http://localhost:4000/openapi"
    @echo "Start the server with: just api-dev"

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
