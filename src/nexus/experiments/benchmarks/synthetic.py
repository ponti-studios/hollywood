"""
synthetic.py — Procedurally generated logic puzzles for Phase 1.

Why synthetic puzzles?
──────────────────────
When we test a model on TriviaQA or MMLU, we can't be sure whether a
correct answer came from genuine reasoning or from pattern-matching to
something seen during training. Maybe the model answered "1887" for "When
was the Eiffel Tower built?" because it actually worked it out from first
principles — or maybe that fact is just burned into its weights.

Synthetic puzzles eliminate this ambiguity. We generate questions using
completely made-up words ("Wumble", "Frobb", "Glark") that the model has
never seen in training. Any correct answer must come from applying logical
rules, not from memorized facts.

This is the scientific control for Phase 1: it isolates *reasoning* from
*memory*, letting us measure each independently.

Puzzle types
────────────
1. Syllogism   — transitive chains: "All A are B. All B are C. Is X a C?"
2. Conditional — modus ponens: "If it is a Wumble, it has a Frobb. X is a Wumble. Does X have a Frobb?"
3. Negation    — modus tollens: "No Wumbles are Frobbs. X is a Wumble. Is X a Frobb?"

All puzzles use nonsense words drawn from a fixed vocabulary to prevent
the model from relying on semantic associations. "Dogs are mammals" gives
away the answer through world knowledge; "Zarps are Blivets" does not.
"""

from __future__ import annotations

import logging
import random
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# Nonsense vocabulary
# ──────────────────────────────────────────────────────────────────────────────

# 200 pronounceable nonsense words, evenly split between noun-like and
# name-like forms. Carefully chosen to be unambiguously meaningless in English.
NOUNS: list[str] = [
    "Wumble",
    "Frobb",
    "Glark",
    "Tixby",
    "Zorn",
    "Pleeb",
    "Varg",
    "Snirp",
    "Blivet",
    "Zarp",
    "Quibb",
    "Florp",
    "Nerg",
    "Spudd",
    "Drimp",
    "Clurp",
    "Fwobb",
    "Grix",
    "Hulb",
    "Jarv",
    "Klerp",
    "Lurb",
    "Mirv",
    "Nurp",
    "Olb",
    "Pirg",
    "Quorp",
    "Rorb",
    "Slurv",
    "Triff",
    "Urvp",
    "Virb",
    "Wolb",
    "Xurp",
    "Yerb",
    "Zurv",
    "Ablorp",
    "Briff",
    "Clurb",
    "Dreff",
    "Eblorp",
    "Frinx",
    "Glorb",
    "Humf",
    "Iklorp",
    "Jirv",
    "Klorb",
    "Leff",
    "Morv",
    "Nulb",
    "Orfp",
    "Prulb",
    "Querb",
    "Riff",
    "Sluff",
    "Trulb",
    "Uplorb",
    "Virff",
    "Wulb",
    "Xorb",
    "Yulb",
    "Zurff",
    "Abliff",
    "Brinx",
    "Cleff",
    "Drulb",
    "Eplorf",
    "Frorb",
    "Gliff",
    "Hurb",
    "Iplorf",
    "Jirff",
    "Klorff",
    "Lorb",
    "Murff",
    "Nulff",
    "Orpf",
    "Prulff",
    "Querff",
    "Riff",
    "Slulb",
    "Trurb",
    "Upluff",
    "Virbb",
    "Wulff",
    "Xorff",
    "Yulff",
    "Zurbb",
    "Ablimp",
    "Brimp",
    "Climp",
    "Drimp",
    "Eplimp",
    "Frimp",
    "Glimp",
    "Hulimp",
    "Iplimp",
    "Jimp",
    "Klimp",
    "Limp",
    "Mulimp",
    "Nulimp",
    "Olimp",
    "Primp",
    "Quimp",
    "Rimp",
    "Slimp",
    "Trimp",
    "Ulimp",
    "Vimp",
    "Wulimp",
    "Xolimp",
]

NAMES: list[str] = [
    "Blarkon",
    "Drixel",
    "Forvath",
    "Grunzel",
    "Hixby",
    "Jorbel",
    "Kelvon",
    "Lorrex",
    "Mivzor",
    "Norbel",
    "Orvath",
    "Prexon",
    "Quorvel",
    "Rivzon",
    "Sorbel",
    "Trevox",
    "Ulvon",
    "Vorvex",
    "Worbel",
    "Xorvon",
    "Yelvex",
    "Zorvath",
    "Axbel",
    "Brolvon",
    "Crixel",
    "Delvath",
    "Exorb",
    "Frolvon",
    "Grexon",
    "Horbel",
    "Ivzon",
    "Jolvex",
    "Kribel",
    "Lorzon",
    "Morbex",
    "Nelvon",
    "Orxel",
    "Prelvath",
    "Quixon",
    "Rorbel",
    "Solvex",
    "Tixon",
    "Ulvath",
    "Vrelbel",
    "Wixon",
    "Xolvex",
    "Yorbel",
    "Zorxon",
    "Axolvon",
]


# ──────────────────────────────────────────────────────────────────────────────
# Puzzle data structures
# ──────────────────────────────────────────────────────────────────────────────


@dataclass
class LogicPuzzle:
    """A single procedurally generated logic puzzle.

    question_id:    unique identifier encoding type + seed + depth
    puzzle_type:    "syllogism", "conditional", or "negation"
    depth:          number of reasoning steps required
    premises:       list of factual statements provided to the model
    question:       the question to answer given the premises
    answer:         the correct answer ("Yes", "No", or an entity name)
    explanation:    the reasoning chain (used to verify the puzzle is correct,
                    not shown to the model)
    """

    question_id: str
    puzzle_type: Literal["syllogism", "conditional", "negation"]
    depth: int
    premises: list[str]
    question: str
    answer: str
    explanation: str


# ──────────────────────────────────────────────────────────────────────────────
# Generators
# ──────────────────────────────────────────────────────────────────────────────


def _sample_nouns(rng: random.Random, n: int) -> list[str]:
    """Sample n unique nouns without replacement."""
    return rng.sample(NOUNS, n)


def _sample_name(rng: random.Random) -> str:
    """Sample a unique proper name."""
    return rng.choice(NAMES)


def _generate_syllogism(rng: random.Random, depth: int, idx: int) -> LogicPuzzle:
    """Generate a transitive syllogism chain of the given depth.

    depth=2: All A are B. All B are C. Is [Name] a C?   (given [Name] is an A)
    depth=3: All A are B. All B are C. All C are D. Is [Name] a D?

    The answer is always "Yes" — we ensure the chain is valid.
    """
    nouns = _sample_nouns(rng, depth + 1)  # A, B, C, ... (depth+1 nouns)
    name = _sample_name(rng)

    premises = [f"All {nouns[i]}s are {nouns[i + 1]}s." for i in range(depth)]
    premises.append(f"{name} is a {nouns[0]}.")

    question = f"Is {name} a {nouns[-1]}?"
    answer = "Yes"

    explanation_steps = [f"{name} is a {nouns[0]}"]
    for i in range(depth):
        explanation_steps.append(
            f"All {nouns[i]}s are {nouns[i + 1]}s → {name} is a {nouns[i + 1]}"
        )
    explanation = ". ".join(explanation_steps) + f". Therefore {name} is a {nouns[-1]}."

    return LogicPuzzle(
        question_id=f"syllogism_d{depth}_{idx}",
        puzzle_type="syllogism",
        depth=depth,
        premises=premises,
        question=question,
        answer=answer,
        explanation=explanation,
    )


def _generate_conditional(rng: random.Random, depth: int, idx: int) -> LogicPuzzle:
    """Generate a modus ponens chain.

    depth=2: If X is a Wumble, then X has a Frobb. X is a Wumble. Does X have a Frobb?

    depth=3 adds one more conditional link:
      If X has a Frobb, then X is a Glark.
      → Does X have a Frobb AND is X a Glark?
    """
    nouns = _sample_nouns(rng, depth + 1)
    name = _sample_name(rng)

    premises = [f"If something is a {nouns[0]}, then it is also a {nouns[1]}."]
    for i in range(1, depth):
        premises.append(f"If something is a {nouns[i]}, then it is also a {nouns[i + 1]}.")
    premises.append(f"{name} is a {nouns[0]}.")

    question = f"Is {name} a {nouns[-1]}?"
    answer = "Yes"

    explanation = (
        f"{name} is a {nouns[0]}. "
        + " ".join(f"Being a {nouns[i]} implies being a {nouns[i + 1]}." for i in range(depth))
        + f" Therefore {name} is a {nouns[-1]}."
    )

    return LogicPuzzle(
        question_id=f"conditional_d{depth}_{idx}",
        puzzle_type="conditional",
        depth=depth,
        premises=premises,
        question=question,
        answer=answer,
        explanation=explanation,
    )


def _generate_negation(rng: random.Random, depth: int, idx: int) -> LogicPuzzle:
    """Generate a negation (modus tollens or simple exclusion) puzzle.

    For depth=2 (simple):
      "No Wumbles are Frobbs. Tixby is a Wumble. Is Tixby a Frobb?"
      Answer: No

    For depth=3 (chain with negation at the end):
      "All Wumbles are Frobbs. No Frobbs are Glarks. Tixby is a Wumble. Is Tixby a Glark?"
      Answer: No
    """
    nouns = _sample_nouns(rng, depth + 1)
    name = _sample_name(rng)

    if depth == 2:
        premises = [
            f"No {nouns[0]}s are {nouns[1]}s.",
            f"{name} is a {nouns[0]}.",
        ]
        question = f"Is {name} a {nouns[1]}?"
        answer = "No"
        explanation = (
            f"No {nouns[0]}s are {nouns[1]}s, and {name} is a {nouns[0]}, "
            f"so {name} cannot be a {nouns[1]}."
        )
    else:
        # Chain: All A are B. All B are C. ... No (last-1) are (last). Is name a (last)?
        chain_depth = depth - 1
        premises = [f"All {nouns[i]}s are {nouns[i + 1]}s." for i in range(chain_depth)]
        premises.append(f"No {nouns[chain_depth]}s are {nouns[chain_depth + 1]}s.")
        premises.append(f"{name} is a {nouns[0]}.")

        question = f"Is {name} a {nouns[-1]}?"
        answer = "No"
        chain = " → ".join(f"{name} is a {nouns[i + 1]}" for i in range(chain_depth))
        explanation = (
            f"{name} is a {nouns[0]}. "
            f"{chain}. "
            f"But no {nouns[chain_depth]}s are {nouns[chain_depth + 1]}s, "
            f"so {name} cannot be a {nouns[-1]}."
        )

    return LogicPuzzle(
        question_id=f"negation_d{depth}_{idx}",
        puzzle_type="negation",
        depth=depth,
        premises=premises,
        question=question,
        answer=answer,
        explanation=explanation,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Public interface
# ──────────────────────────────────────────────────────────────────────────────

_GENERATORS = {
    "syllogism": _generate_syllogism,
    "conditional": _generate_conditional,
    "negation": _generate_negation,
}


def generate_puzzles(
    n: int = 500,
    seed: int = 42,
    depth_range: tuple[int, int] = (2, 4),
    puzzle_types: Sequence[str] | None = None,
) -> list[LogicPuzzle]:
    """Generate n synthetic logic puzzles.

    Puzzles are distributed evenly across types and depths. With the same
    seed you always get the exact same puzzles — essential for comparing
    results across different model runs.

    Args:
        n:            total number of puzzles to generate
        seed:         random seed for full reproducibility
        depth_range:  (min_depth, max_depth) inclusive
        puzzle_types: which types to generate. None = all three types.

    Returns:
        List of LogicPuzzle objects, shuffled randomly.
    """

    puzzle_types = puzzle_types or ["syllogism", "conditional", "negation"]
    rng = random.Random(seed)
    puzzles: list[LogicPuzzle] = []
    depths = list(range(depth_range[0], depth_range[1] + 1))

    idx = 0
    while len(puzzles) < n:
        ptype = rng.choice(puzzle_types)
        depth = rng.choice(depths)
        generator = _GENERATORS[ptype]
        try:
            puzzle = generator(rng, depth, idx)
            puzzles.append(puzzle)
        except Exception as e:
            logger.debug(f"Puzzle generation failed (type={ptype}, depth={depth}): {e}")
        idx += 1

    rng.shuffle(puzzles)
    logger.info(f"Generated {len(puzzles)} synthetic logic puzzles (seed={seed})")
    return puzzles[:n]


def format_prompt(puzzle: LogicPuzzle) -> str:
    """Format a logic puzzle as a zero-shot prompt.

    The model sees only the premises and the question — not the explanation
    or the answer. We ask for a one-word answer to make extraction easy.
    """
    premises_text = "\n".join(f"  - {p}" for p in puzzle.premises)
    return (
        f"Read the following statements carefully and answer the question. "
        f"Answer with only 'Yes' or 'No'.\n\n"
        f"Statements:\n{premises_text}\n\n"
        f"Question: {puzzle.question}\n"
        f"Answer:"
    )
