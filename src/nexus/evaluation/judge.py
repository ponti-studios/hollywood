"""
judge.py — LLM-as-judge evaluation using the Nexus API text worker.

The judge model is served through the public Nexus control plane, so local
evaluation stays aligned with the compose-backed runtime and does not require
any local serving stack.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass

import httpx
from rich.console import Console
from rich.table import Table

logger = logging.getLogger(__name__)
console = Console()

JUDGE_PROMPT = """\
You are an expert evaluator of AI assistant responses.
Score the following response on a scale of 1 to 10 based on these criteria:
- Helpfulness: Does it directly address the user's question?
- Accuracy: Is the information correct?
- Clarity: Is it easy to understand?
- Completeness: Does it cover the key points?

USER PROMPT:
{prompt}

AI RESPONSE:
{response}

Provide your evaluation in this exact format:
SCORE: [number 1-10]
REASONING: [one sentence explaining the score]
"""


@dataclass
class JudgeResult:
    """The result of judging a single (prompt, response) pair."""

    prompt: str
    response: str
    score: float
    reasoning: str
    judge_model: str


def parse_judge_output(output: str) -> tuple[float, str]:
    """Extract the numeric score and reasoning from the judge's output."""
    score_match = re.search(r"SCORE:\s*(\d+(?:\.\d+)?)", output)
    reasoning_match = re.search(r"REASONING:\s*(.+?)(?:\n|$)", output, re.DOTALL)

    score = float(score_match.group(1)) if score_match else 5.0
    reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided."
    score = max(1.0, min(10.0, score))
    return score, reasoning


def _api_base_url() -> str:
    return os.getenv("NEXUS_API_URL", "http://127.0.0.1:8787").rstrip("/")


def judge_responses(
    examples: list[dict[str, str]],
    judge_model_id: str = "HuggingFaceTB/SmolLM2-135M-Instruct",
) -> list[JudgeResult]:
    """Use the Nexus API text worker to judge prompt/response pairs."""
    api_base = _api_base_url()
    results: list[JudgeResult] = []

    console.print(f"\n[bold]Judging with API model:[/bold] {judge_model_id}")
    with httpx.Client(base_url=api_base, timeout=None) as client:
        for i, example in enumerate(examples):
            prompt = example["prompt"]
            response = example["response"]
            judge_input = JUDGE_PROMPT.format(prompt=prompt, response=response)

            payload = {
                "model": judge_model_id,
                "messages": [{"role": "user", "content": judge_input}],
                "max_tokens": 200,
                "temperature": 0.0,
            }
            res = client.post("/v1/chat/completions", json=payload)
            res.raise_for_status()
            body = res.json()
            raw_output = str(body["choices"][0]["message"]["content"])

            score, reasoning = parse_judge_output(raw_output)
            results.append(
                JudgeResult(
                    prompt=prompt,
                    response=response,
                    score=score,
                    reasoning=reasoning,
                    judge_model=judge_model_id,
                )
            )

            if (i + 1) % 10 == 0:
                avg = sum(r.score for r in results) / len(results)
                console.print(f"  Judged {i + 1}/{len(examples)} — avg score: {avg:.2f}")

    return results


def print_judge_summary(results: list[JudgeResult]) -> None:
    """Print a rich table summarising judge evaluation results."""
    if not results:
        console.print("[yellow]No results to display.[/yellow]")
        return

    avg_score = sum(r.score for r in results) / len(results)

    buckets = {"1–3 (poor)": 0, "4–6 (ok)": 0, "7–8 (good)": 0, "9–10 (excellent)": 0}
    for r in results:
        if r.score <= 3:
            buckets["1–3 (poor)"] += 1
        elif r.score <= 6:
            buckets["4–6 (ok)"] += 1
        elif r.score <= 8:
            buckets["7–8 (good)"] += 1
        else:
            buckets["9–10 (excellent)"] += 1

    console.print("\n[bold]Judge Evaluation Summary[/bold]")
    console.print(f"  Total evaluated: {len(results)}")
    console.print(f"  Average score:   [green]{avg_score:.2f}[/green] / 10")
    console.print("  Distribution:")
    for label, count in buckets.items():
        bar = "█" * count
        console.print(f"    {label:20s} {bar} ({count})")

    console.print("\n[bold]Sample results:[/bold]")
    table = Table(show_header=True)
    table.add_column("Score", style="cyan", width=6)
    table.add_column("Prompt", width=30)
    table.add_column("Reasoning", width=50)

    for r in sorted(results, key=lambda x: x.score, reverse=True)[:5]:
        table.add_row(
            str(r.score),
            r.prompt[:80] + ("…" if len(r.prompt) > 80 else ""),
            r.reasoning[:100] + ("…" if len(r.reasoning) > 100 else ""),
        )

    console.print(table)
