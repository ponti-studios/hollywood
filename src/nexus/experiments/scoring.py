"""
scoring.py — Answer scoring functions for benchmark experiments.

What does "correct" mean for a language model?
───────────────────────────────────────────────
For multiple-choice tasks (MMLU), correctness is exact match: the model's
chosen letter (A/B/C/D) either matches the ground truth or it doesn't.

For open-ended tasks (TriviaQA), we use a normalized string match: strip
punctuation, lowercase everything, and check if the expected answer appears
anywhere in the model's response. This is the same scoring used in the
original TriviaQA paper.

For logic puzzles, we extract a Yes/No (or the specific entity) from the
model output and compare to the expected answer.

Key metric — Correction Delta (Phase 3)
─────────────────────────────────────────
When the model runs the Draft → Critique → Refine loop, we track:

  Δ = (wrong_to_correct / total_initially_wrong) × 100

A positive Δ means the loop fixed errors it previously made.
A negative Δ means the loop broke answers that were originally correct.
A Δ near zero means the loop is doing nothing useful.
"""

from __future__ import annotations

import re
import string
from dataclasses import dataclass


@dataclass
class QuestionResult:
    """The outcome of running a single question through a model.

    question_id: unique identifier for reproducible tracking
    question:    the original question text
    expected:    ground truth answer
    predicted:   the model's raw output
    correct:     whether the answer was scored as correct
    model_id:    which model produced this result
    benchmark:   which dataset this came from
    tool_calls:  number of tool calls made (Phase 2+), 0 if none
    draft:       raw first-pass answer before reflection (Phase 3+)
    critique:    the model's self-critique (Phase 3+)
    """

    question_id: str
    question: str
    expected: str
    predicted: str
    correct: bool
    model_id: str
    benchmark: str
    tool_calls: int = 0
    draft: str | None = None
    critique: str | None = None


@dataclass
class BenchmarkScore:
    """Aggregate scores for one model on one benchmark dataset.

    accuracy:         fraction of questions answered correctly (0.0–1.0)
    correct_count:    raw number of correct answers
    total:            total questions evaluated
    tool_call_rate:   fraction of questions that triggered a tool call (Phase 2+)
    avg_tool_calls:   mean tool calls per question (Phase 2+)
    correction_delta: improvement from reflection loop (Phase 3+), in percentage points
    provenance:       whether this row came from live inference or cache
    """

    model_id: str
    benchmark: str
    accuracy: float
    correct_count: int
    total: int
    tool_call_rate: float = 0.0
    avg_tool_calls: float = 0.0
    correction_delta: float | None = None  # only set in Phase 3
    provenance: str = "live"

    @property
    def accuracy_pct(self) -> str:
        """Human-readable accuracy string, e.g. '61.4%'."""
        return f"{self.accuracy * 100:.1f}%"

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "benchmark": self.benchmark,
            "accuracy": round(self.accuracy, 4),
            "accuracy_pct": self.accuracy_pct,
            "correct": self.correct_count,
            "total": self.total,
            "tool_call_rate": round(self.tool_call_rate, 4),
            "avg_tool_calls": round(self.avg_tool_calls, 2),
            "correction_delta": self.correction_delta,
            "provenance": self.provenance,
        }


def normalize_answer(text: str) -> str:
    """Normalize a string for loose answer comparison.

    Lowercases, strips punctuation, and collapses whitespace. This matches
    the normalization used in the original TriviaQA evaluation code.

    Examples:
        "Mount Everest!"  → "mount everest"
        "  The  Beatles " → "the beatles"
        "1987."           → "1987"
    """
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def score_triviaqa(predicted: str, expected: str | list[str]) -> bool:
    """Score a TriviaQA answer.

    TriviaQA provides multiple valid aliases for each answer (e.g., "JFK",
    "John F. Kennedy", "John Fitzgerald Kennedy" are all valid for the same
    question). We normalize both sides and check if any alias appears in
    the predicted answer.

    This is intentionally generous — the model gets credit as long as
    the correct answer is mentioned anywhere in its response.
    """
    pred_norm = normalize_answer(predicted)
    aliases = [expected] if isinstance(expected, str) else expected
    return any(normalize_answer(alias) in pred_norm for alias in aliases)


def score_mmlu(predicted: str, expected: str) -> bool:
    """Score an MMLU answer.

    MMLU is multiple-choice (A/B/C/D). We extract the first letter from
    the model's response and compare to the ground truth letter.

    We look for patterns like:
      "A", "(A)", "A)", "Answer: A", "The answer is A"

    If no letter is found, the answer is scored as incorrect.
    """
    expected_letter = expected.strip().upper()
    # Extract the first A/B/C/D from the response
    match = re.search(r"\b([ABCD])\b", predicted.upper())
    if match:
        return match.group(1) == expected_letter
    return False


def score_logic_puzzle(predicted: str, expected: str) -> bool:
    """Score a synthetic logic puzzle answer.

    Expected answers are either:
      - "Yes" / "No" (for syllogism questions)
      - A specific entity name (for "what is X?" questions)

    We normalize both and check for substring match, so the model can
    answer "Yes, Tixby is definitely a Frobb" and still be marked correct.
    """
    return normalize_answer(expected) in normalize_answer(predicted)


def aggregate_scores(results: list[QuestionResult]) -> BenchmarkScore:
    """Compute aggregate scores from a list of question results.

    Groups results by model_id and benchmark automatically — so if you
    pass a mixed list, you get the aggregate for whatever is in the list.
    Typically called once per (model, benchmark) pair.
    """
    if not results:
        raise ValueError("Cannot aggregate an empty results list")

    model_id = results[0].model_id
    benchmark = results[0].benchmark
    correct_count = sum(1 for r in results if r.correct)
    total = len(results)
    accuracy = correct_count / total

    tool_calls = [r.tool_calls for r in results]
    tool_call_rate = sum(1 for t in tool_calls if t > 0) / total
    avg_tool_calls = sum(tool_calls) / total

    return BenchmarkScore(
        model_id=model_id,
        benchmark=benchmark,
        accuracy=accuracy,
        correct_count=correct_count,
        total=total,
        tool_call_rate=tool_call_rate,
        avg_tool_calls=avg_tool_calls,
    )


def compute_correction_delta(
    draft_results: list[QuestionResult],
    refined_results: list[QuestionResult],
) -> float:
    """Compute the Correction Delta for the Phase 3 reflection loop.

    Delta = percentage of initially-wrong answers that were fixed
            minus percentage of initially-correct answers that were broken.

    A positive delta means the loop is helping.
    This is the primary success metric for Phase 3.

    Args:
        draft_results:   results from the model's first-pass answers
        refined_results: results from the model's post-reflection answers

    Returns:
        Delta in percentage points (e.g., 12.5 means a 12.5pp improvement).
    """
    if len(draft_results) != len(refined_results):
        raise ValueError("draft and refined result lists must have the same length")

    wrong_to_correct = 0
    correct_to_wrong = 0
    initially_wrong = 0
    initially_correct = 0

    for draft, refined in zip(draft_results, refined_results):
        if not draft.correct:
            initially_wrong += 1
            if refined.correct:
                wrong_to_correct += 1
        else:
            initially_correct += 1
            if not refined.correct:
                correct_to_wrong += 1

    fix_rate = (wrong_to_correct / initially_wrong * 100) if initially_wrong > 0 else 0.0
    break_rate = (correct_to_wrong / initially_correct * 100) if initially_correct > 0 else 0.0
    return round(fix_rate - break_rate, 2)
