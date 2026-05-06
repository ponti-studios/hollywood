"""
triviaqa.py — TriviaQA benchmark loader.

About TriviaQA
──────────────
TriviaQA is a large reading comprehension dataset containing over 650,000
question-answer pairs scraped from trivia websites and Wikipedia. Each
question has multiple valid answer aliases (e.g., "JFK" and "John F. Kennedy"
are both valid for the same question).

In Phase 1 (baseline), TriviaQA is used as the "knowledge-heavy" benchmark —
a test that the Gemma 4 E2B-it text model must answer from memory rather than
from tools or search.

In Phase 2 (open book), we re-run these same questions but allow the model to
use search before answering. The expected outcome is that the gap closes
because the model can look up what it doesn't know.

HuggingFace dataset: "trivia_qa" (config: "rc.wikipedia")
Split used: "validation" (so we never touch the test set)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast

from datasets import load_dataset
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()


@dataclass
class TriviaQAItem:
    """A single TriviaQA question with its canonical answers.

    question_id: unique identifier from the original dataset
    question:    the question text
    answers:     list of valid answer strings (multiple aliases accepted)
    """

    question_id: str
    question: str
    answers: list[str]


def load_triviaqa(
    samples: int | None = 500,
    seed: int = 42,
) -> list[TriviaQAItem]:
    """Load a sample of TriviaQA validation questions.

    Downloads from HuggingFace on first use, cached locally afterward.
    We use the "rc.wikipedia" config which includes Wikipedia evidence
    documents — we ignore those documents in Phase 1 (closed-book) but
    they become useful context in Phase 2 (open-book).

    Args:
        samples: how many questions to load. None = load all (~7,993).
        seed:    random seed for reproducible sampling.

    Returns:
        List of TriviaQAItem objects, ready for the benchmark runner.
    """
    console.print("[bold]Loading TriviaQA[/bold] (validation split) …")

    dataset = load_dataset(
        "trivia_qa",
        "rc.wikipedia",
        split="validation",
    )

    if samples is not None:
        dataset = dataset.shuffle(seed=seed).select(range(min(samples, len(dataset))))

    console.print(f"  Loaded {len(dataset)} questions")

    items = []
    for row in dataset:
        row_data = cast(dict[str, Any], dict(row))

        # TriviaQA stores answers as {"value": str, "aliases": [str, ...]}
        answer_obj = row_data.get("answer", {})
        if not isinstance(answer_obj, dict):
            answer_obj = {}
        aliases_raw = answer_obj.get("aliases", [])
        aliases = [str(alias) for alias in aliases_raw] if isinstance(aliases_raw, list) else []
        canonical = str(answer_obj.get("value", ""))
        all_answers = list({canonical} | set(aliases))  # deduplicate

        items.append(
            TriviaQAItem(
                question_id=str(row_data.get("question_id", "")),
                question=str(row_data.get("question", "")),
                answers=all_answers,
            )
        )

    return items


def format_prompt(item: TriviaQAItem) -> str:
    """Format a TriviaQA item as a zero-shot prompt.

    We keep the prompt minimal and direct — no few-shot examples in
    Phase 1 so we're measuring what the model already knows, not its
    ability to pattern-match from examples.
    """
    return (
        f"Answer the following question as concisely as possible. "
        f"Give only the answer, no explanation.\n\n"
        f"Question: {item.question}\n"
        f"Answer:"
    )
