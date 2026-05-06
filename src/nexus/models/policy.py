from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

GEMMA_TEXT_MODEL_ID = "google/gemma-4-E2B-it"
QWEN_TTS_MODEL_ID = "Qwen/Qwen3-TTS-12Hz-1.7B-CustomVoice"
MODEL_MANIFEST_FILENAME = "nexus-model.json"
SUPPORTED_CHECKPOINT_KINDS = {"full", "merged"}


def _manifest_path(model_dir: Path) -> Path:
    return model_dir / MODEL_MANIFEST_FILENAME


def _load_manifest(model_dir: Path) -> dict[str, Any]:
    manifest_file = _manifest_path(model_dir)
    if not manifest_file.exists():
        raise ValueError(
            f"{model_dir} is not a Nexus-managed Gemma checkpoint: missing {MODEL_MANIFEST_FILENAME}."
        )

    try:
        payload = json.loads(manifest_file.read_text())
    except json.JSONDecodeError as exc:
        raise ValueError(f"{manifest_file} is not valid JSON.") from exc

    if not isinstance(payload, dict):
        raise ValueError(f"{manifest_file} must contain a JSON object.")

    return payload


def write_model_manifest(
    output_dir: str | Path,
    *,
    base_model_id: str = GEMMA_TEXT_MODEL_ID,
    checkpoint_kind: Literal["full", "merged", "adapter"] = "merged",
) -> Path:
    """Write the canonical Nexus model manifest next to a saved checkpoint."""

    path = Path(output_dir)
    path.mkdir(parents=True, exist_ok=True)

    manifest = {
        "policy_version": 1,
        "family": "gemma-4",
        "base_model_id": base_model_id,
        "checkpoint_kind": checkpoint_kind,
        "created_at": datetime.now(UTC).isoformat(),
    }
    manifest_path = _manifest_path(path)
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    return manifest_path


def validate_text_model_reference(model_id: str) -> str:
    """Allow only the approved Gemma 4 text model or a Nexus Gemma checkpoint.

    The repo policy is intentionally narrow:
      - direct remote loads must use google/gemma-4-E2B-it
      - local checkpoint directories must carry a Nexus manifest proving they
        were produced from the same base model
    """

    if model_id == GEMMA_TEXT_MODEL_ID:
        return model_id

    model_path = Path(model_id)
    if not model_path.exists():
        raise ValueError(
            f"Unsupported model '{model_id}'. Use {GEMMA_TEXT_MODEL_ID} or a Nexus Gemma checkpoint."
        )
    if not model_path.is_dir():
        raise ValueError(f"{model_id} must be a directory containing a Gemma checkpoint.")

    manifest = _load_manifest(model_path)
    base_model_id = manifest.get("base_model_id")
    checkpoint_kind = manifest.get("checkpoint_kind")

    if base_model_id != GEMMA_TEXT_MODEL_ID:
        raise ValueError(
            f"{model_id} was trained from '{base_model_id}', not {GEMMA_TEXT_MODEL_ID}."
        )

    if checkpoint_kind not in SUPPORTED_CHECKPOINT_KINDS:
        raise ValueError(
            f"{model_id} is an adapter-only checkpoint; merge it before loading."
        )

    return model_id
