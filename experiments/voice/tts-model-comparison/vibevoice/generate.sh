#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="$ROOT_DIR/.work"
REPO_DIR="$WORK_DIR/VibeVoice"
VENV_DIR="$ROOT_DIR/.venv"
TEXT_FILE="${1:?text file path is required}"
OUTPUT_DIR="${2:?output directory is required}"
SPEAKER_NAME="${3:-Carter}"
DEVICE="${VIBEVOICE_DEVICE:-mps}"

if [ "$(uname -s)" = "Darwin" ]; then
  DEFAULT_UV_PYTHON="cpython-3.12.13-macos-aarch64-none"
else
  DEFAULT_UV_PYTHON="3.12"
fi
UV_PYTHON="${UV_PYTHON:-$DEFAULT_UV_PYTHON}"

mkdir -p "$WORK_DIR" "$OUTPUT_DIR" "$ROOT_DIR/cache"

if [ ! -d "$REPO_DIR/.git" ]; then
  git clone https://github.com/microsoft/VibeVoice.git "$REPO_DIR"
fi

if [ ! -d "$VENV_DIR" ]; then
  uv venv --python "$UV_PYTHON" "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -c "import vibevoice" >/dev/null 2>&1; then
  uv pip install --python "$VENV_DIR/bin/python" -e "$REPO_DIR[streamingtts]"
fi

HF_HOME="$ROOT_DIR/cache" \
  "$VENV_DIR/bin/python" "$REPO_DIR/demo/realtime_model_inference_from_file.py" \
    --model_path microsoft/VibeVoice-Realtime-0.5B \
    --txt_path "$TEXT_FILE" \
    --speaker_name "$SPEAKER_NAME" \
    --output_dir "$OUTPUT_DIR" \
    --device "$DEVICE"
