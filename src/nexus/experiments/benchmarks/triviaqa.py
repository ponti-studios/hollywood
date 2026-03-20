"""
triviaqa.py — TriviaQA benchmark loader.

About TriviaQA
──────────────
TriviaQA is a large reading comprehension dataset containing over 650,000
question-answer pairs scraped from trivia websites and Wikipedia. Each
question has multiple valid answer aliases (e.g., "JFK" and "John F. Kennedy"
are both valid for the same question).

In Phase 1 (baseline), TriviaQA is used as the "knowledge-heavy" benchmark —
a test that large models dominate because they have the answers memorized in
their weights. We expect the 70B model to significantly outperform the 3B
model here.

In Phase 2 (open book), we re-run these same questions but let the 3B model
search the web for answers. The expected outcome is that the gap closes
dramatically — because the 3B model can look up what it doesn't know.

HuggingFace dataset: "trivia_qa" (config: "rc.wikipedia")
Split used: "validation" (so we never touch the test set)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

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
    samples: Optional[int] = 500,
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
        trust_remote_code=True,
    )

    if samples is not None:
        dataset = dataset.shuffle(seed=seed).select(range(min(samples, len(dataset))))

    console.print(f"  Loaded {len(dataset)} questions")

    items = []
    for row in dataset:
        # TriviaQA stores answers as {"value": str, "aliases": [str, ...]}
        answer_obj = row["answer"]
        aliases: list[str] = answer_obj.get("aliases", [])
        canonical: str = answer_obj.get("value", "")
        all_answers = list({canonical} | set(aliases))  # deduplicate

        items.append(
            TriviaQAItem(
                question_id=row["question_id"],
                question=row["question"],
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
