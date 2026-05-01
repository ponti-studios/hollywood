#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
UVICORN_HOST="${UVICORN_HOST:-127.0.0.1}"
UVICORN_PORT="${UVICORN_PORT:-8787}"

if [ "$(uname -s)" = "Darwin" ]; then
  DEFAULT_UV_PYTHON="cpython-3.12.13-macos-aarch64-none"
else
  DEFAULT_UV_PYTHON="3.12"
fi
UV_PYTHON="${UV_PYTHON:-$DEFAULT_UV_PYTHON}"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  rm -rf "$VENV_DIR"
  uv venv --python "$UV_PYTHON" "$VENV_DIR"
fi

uv pip install --python "$VENV_DIR/bin/python" -r "$ROOT_DIR/requirements.txt"

exec "$VENV_DIR/bin/python" -m uvicorn app:app --host "$UVICORN_HOST" --port "$UVICORN_PORT" --reload
