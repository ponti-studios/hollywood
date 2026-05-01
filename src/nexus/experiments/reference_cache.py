from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any, Optional

from nexus.experiments.scoring import QuestionResult


CACHE_SCHEMA_VERSION = 1


def safe_model_id(model_id: str) -> str:
    return model_id.replace("/", "__")


def build_cache_path(
    cache_root: str | Path,
    experiment_name: str,
    model_id: str,
    benchmark_name: str,
    benchmark_signature: str,
) -> Path:
    root = Path(cache_root)
    return root / experiment_name / safe_model_id(model_id) / f"{benchmark_name}_{benchmark_signature}.json"


def serialize_question_result(result: QuestionResult) -> dict[str, Any]:
    return {
        "id": result.question_id,
        "question": result.question,
        "expected": result.expected,
        "predicted": result.predicted,
        "correct": result.correct,
        "model": result.model_id,
        "benchmark": result.benchmark,
        "tool_calls": result.tool_calls,
        "draft": result.draft,
        "critique": result.critique,
    }


def deserialize_question_result(payload: dict[str, Any]) -> QuestionResult:
    return QuestionResult(
        question_id=payload["id"],
        question=payload["question"],
        expected=payload["expected"],
        predicted=payload["predicted"],
        correct=payload["correct"],
        model_id=payload["model"],
        benchmark=payload["benchmark"],
        tool_calls=payload.get("tool_calls", 0),
        draft=payload.get("draft"),
        critique=payload.get("critique"),
    )


def save_reference_cache(
    path: Path,
    *,
    experiment_name: str,
    score_version: str,
    model_id: str,
    role: str,
    benchmark: str,
    benchmark_signature: str,
    results: list[QuestionResult],
    extra_metadata: Optional[dict[str, Any]] = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        payload = {
            "schema_version": CACHE_SCHEMA_VERSION,
            "created_at": int(time.time()),
            "experiment": experiment_name,
            "score_version": score_version,
            "model_id": model_id,
            "role": role,
            "benchmark": benchmark,
            "benchmark_signature": benchmark_signature,
            "results": [serialize_question_result(result) for result in results],
        }
        if extra_metadata:
            payload.update(extra_metadata)
        json.dump(payload, f, indent=2)


def load_reference_cache(
    path: Path,
    *,
    score_version: str,
    benchmark_signature: str,
) -> Optional[list[QuestionResult]]:
    if not path.exists():
        return None

    with open(path) as f:
        payload = json.load(f)

    if payload.get("schema_version") != CACHE_SCHEMA_VERSION:
        return None
    if payload.get("score_version") != score_version:
        return None
    if payload.get("benchmark_signature") != benchmark_signature:
        return None

    return [deserialize_question_result(item) for item in payload.get("results", [])]


def read_cache_metadata(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def load_cache_metadata(path: Path) -> Optional[dict[str, Any]]:
    if not path.exists():
        return None
    return read_cache_metadata(path)


def summarize_cache_file(path: Path) -> dict[str, Any]:
    payload = read_cache_metadata(path)
    results = payload.get("results", [])
    total = len(results)
    correct = sum(1 for item in results if item.get("correct"))
    accuracy = correct / total if total else 0.0
    return {
        "path": path,
        "experiment": payload.get("experiment"),
        "model_id": payload.get("model_id"),
        "role": payload.get("role"),
        "benchmark": payload.get("benchmark"),
        "benchmark_signature": payload.get("benchmark_signature"),
        "score_version": payload.get("score_version"),
        "created_at": payload.get("created_at"),
        "total": total,
        "correct": correct,
        "accuracy": accuracy,
    }


def find_reference_caches(
    cache_root: str | Path,
    *,
    experiment: Optional[str] = None,
    model: Optional[str] = None,
    benchmark: Optional[str] = None,
) -> list[Path]:
    root = Path(cache_root)
    if not root.exists():
        return []

    matches: list[Path] = []
    experiment_dirs = [root / experiment] if experiment else [path for path in root.iterdir() if path.is_dir()]

    for experiment_dir in experiment_dirs:
        if not experiment_dir.exists() or not experiment_dir.is_dir():
            continue

        model_dir_name = safe_model_id(model) if model else None
        model_dirs = [experiment_dir / model_dir_name] if model_dir_name else [path for path in experiment_dir.iterdir() if path.is_dir()]

        for model_dir in model_dirs:
            if not model_dir.exists() or not model_dir.is_dir():
                continue

            for cache_path in sorted(model_dir.glob("*.json")):
                if benchmark and not cache_path.name.startswith(f"{benchmark}_"):
                    continue
                matches.append(cache_path)

    return sorted(matches)