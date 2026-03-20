"""
judge.py — LLM-as-judge evaluation using MLX (local, free, private).

What is LLM-as-judge?
──────────────────────
Traditional metrics like BLEU and ROUGE measure surface-level text similarity.
They don't capture whether a response is actually helpful, accurate, or safe.

LLM-as-judge uses a language model to score responses based on criteria
like helpfulness, accuracy, coherence, and harmlessness.

The judge model reads:
  - The original prompt
  - The response to evaluate
  - A scoring rubric

And outputs a score (typically 1–10) plus a brief justification.

Why use a local judge?
  - Free (no API costs)
  - Private (your data never leaves your machine)
  - Fast on Apple Silicon via MLX

This approach is used in many modern research papers (MT-Bench, AlpacaEval, etc.)
and is now the de-facto standard for evaluating instruction-following quality.

The limitation: the judge model is itself imperfect. A larger judge = more
reliable scores. We use Gemma 3 4B as judge by default since it's powerful
enough for basic evaluation while fitting comfortably in Mac RAM.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Optional

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
    score: float          # 1.0 – 10.0
    reasoning: str
    judge_model: str


def parse_judge_output(output: str) -> tuple[float, str]:
    """Extract the numeric score and reasoning from the judge's raw output.

    The judge is prompted to follow a strict format, but LLMs don't always
    comply perfectly, so we use a regex to extract what we need.
    """
    score_match = re.search(r"SCORE:\s*(\d+(?:\.\d+)?)", output)
    reasoning_match = re.search(r"REASONING:\s*(.+?)(?:\n|$)", output, re.DOTALL)

    score = float(score_match.group(1)) if score_match else 5.0
    reasoning = reasoning_match.group(1).strip() if reasoning_match else "No reasoning provided."

    # Clamp to valid range
    score = max(1.0, min(10.0, score))
    return score, reasoning


def judge_responses(
    examples: list[dict[str, str]],
    judge_model_id: str = "google/gemma-3-4b-it",
) -> list[JudgeResult]:
    """Use a local MLX model to judge a list of (prompt, response) pairs.

    Args:
        examples: list of dicts with "prompt" and "response" keys
        judge_model_id: HuggingFace model ID for the judge

    Returns:
        List of JudgeResult objects with scores and reasoning.

    Note: This uses mlx-lm for inference (fast Apple Silicon path).
          The judge model is loaded separately from the model being evaluated.
    """
    try:
        from mlx_lm import generate, load
    except ImportError:
        raise ImportError(
            "mlx-lm is required for local LLM-as-judge evaluation. "
            "Install it with: pip install mlx-lm"
        )

    console.print(f"\n[bold]Loading judge model:[/bold] {judge_model_id}")
    judge_model, judge_tokenizer = load(judge_model_id)

    results = []
    for i, example in enumerate(examples):
        prompt = example["prompt"]
        response = example["response"]

        judge_input = JUDGE_PROMPT.format(prompt=prompt, response=response)

        # Generate the judge's evaluation using MLX (fast local inference)
        raw_output = generate(
            judge_model,
            judge_tokenizer,
            prompt=judge_input,
            max_tokens=200,
            verbose=False,
        )

        score, reasoning = parse_judge_output(raw_output)
        results.append(JudgeResult(
            prompt=prompt,
            response=response,
            score=score,
            reasoning=reasoning,
            judge_model=judge_model_id,
        ))

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

    # Distribution: count how many fall in each bucket
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

    console.print(f"\n[bold]Judge Evaluation Summary[/bold]")
    console.print(f"  Total evaluated: {len(results)}")
    console.print(f"  Average score:   [green]{avg_score:.2f}[/green] / 10")
    console.print(f"  Distribution:")
    for label, count in buckets.items():
        bar = "█" * count
        console.print(f"    {label:20s} {bar} ({count})")

    # Show a few examples
    console.print(f"\n[bold]Sample results:[/bold]")
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
