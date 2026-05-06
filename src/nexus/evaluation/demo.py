from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from nexus.providers.gemini import GeminiClient


@dataclass(slots=True)
class DemoCase:
    name: str
    prompt: str
    scorer: Callable[[str], tuple[float, str]]
    temperature: float = 0.0
    max_tokens: int = 256


@dataclass(slots=True)
class DemoResult:
    name: str
    score: float
    passed: bool
    response: str
    details: str


DEMO_CASES: list[DemoCase] = [
    DemoCase(
        name="email_extraction",
        prompt="Extract the email address from this sentence and return only the email: Reach me at ada@example.com.",
        scorer=lambda text: _score_exact(text, "ada@example.com"),
    ),
    DemoCase(
        name="classification",
        prompt="Classify the message as support, sales, or other. Reply with only one label. Message: I need help resetting my password.",
        scorer=lambda text: _score_label(text, "support"),
    ),
    DemoCase(
        name="json_format",
        prompt=(
            "Return JSON with keys 'answer' and 'confidence' for the question: What is 2+2? "
            "Do not include markdown."
        ),
        scorer=lambda text: _score_valid_json(text),
    ),
]


async def run_demo_evals(model: str | None = None) -> list[DemoResult]:
    client = GeminiClient(text_model=model or None)
    try:
        results: list[DemoResult] = []
        for case in DEMO_CASES:
            output = await client.reply(
                prompt=case.prompt,
                model=model,
                temperature=case.temperature,
                max_tokens=case.max_tokens,
            )
            score, details = case.scorer(output.text.strip())
            results.append(
                DemoResult(
                    name=case.name,
                    score=score,
                    passed=score >= 1.0,
                    response=output.text.strip(),
                    details=details,
                )
            )
        return results
    finally:
        await client.aclose()


def save_results(results: list[DemoResult], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "name": result.name,
            "score": result.score,
            "passed": result.passed,
            "response": result.response,
            "details": result.details,
        }
        for result in results
    ]
    path.write_text(json.dumps(payload, indent=2) + "\n")


def _score_exact(text: str, expected: str) -> tuple[float, str]:
    normalized = text.strip().lower()
    target = expected.strip().lower()
    if normalized == target:
        return 1.0, f"matched expected value '{expected}'"
    return 0.0, f"expected '{expected}' but got '{text}'"


def _score_label(text: str, expected: str) -> tuple[float, str]:
    normalized = text.strip().lower()
    target = expected.strip().lower()
    if normalized == target or normalized.startswith(f"{target} ") or normalized.startswith(f"{target}."):
        return 1.0, f"matched label '{expected}'"
    return 0.0, f"expected label '{expected}' but got '{text}'"


def _score_valid_json(text: str) -> tuple[float, str]:
    try:
        payload = json.loads(text)
    except Exception as exc:
        return 0.0, f"invalid JSON: {exc}"

    if not isinstance(payload, dict):
        return 0.0, "JSON response must be an object"

    missing = [key for key in ("answer", "confidence") if key not in payload]
    if missing:
        return 0.0, f"missing keys: {', '.join(missing)}"

    return 1.0, "valid JSON with required keys"
