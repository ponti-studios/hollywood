#!/bin/sh
set -eu

ROOT_DIR="$PWD"
WORK_DIR="$ROOT_DIR/.work"
REPO_DIR="$WORK_DIR/VibeVoice"
VENV_DIR="$ROOT_DIR/.venv"

mkdir -p "$WORK_DIR" "$ROOT_DIR/outputs" "$ROOT_DIR/cache"

if [ ! -d "$REPO_DIR/.git" ]; then
  git clone https://github.com/microsoft/VibeVoice.git "$REPO_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
  uv venv --python cpython-3.12.13-macos-aarch64-none "$VENV_DIR"
fi

uv pip install --python "$VENV_DIR/bin/python" -e "$REPO_DIR[streamingtts]"

"$ROOT_DIR/generate.sh" "$ROOT_DIR/input.txt" "$ROOT_DIR/outputs" Carter
