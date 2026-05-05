"""
mmlu.py — MMLU (Massive Multitask Language Understanding) benchmark loader.

About MMLU
──────────
MMLU tests knowledge across 57 academic subjects, from elementary mathematics
to professional medicine and law. All questions are 4-choice multiple choice.
It's the most widely cited benchmark for measuring a model's breadth of
academic knowledge.

MMLU is "knowledge-heavy" in the same way TriviaQA is: the model needs to
have the information stored in its weights to answer correctly. You can't
reason your way to the right answer for "What is the half-life of Carbon-14?"
without having been trained on that fact.

Subjects are grouped into four categories:
  STEM        — math, physics, chemistry, biology, computer science
  Humanities  — history, philosophy, law, literature
  Social Sci  — economics, psychology, sociology, politics
  Other       — medicine, nutrition, business, professional topics

For Phase 1 experiments, we use a curated subset of subjects to keep
runtime manageable. The default set covers one subject per category.

HuggingFace dataset: "cais/mmlu"
Split used: "validation"
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from datasets import concatenate_datasets, load_dataset
from rich.console import Console

logger = logging.getLogger(__name__)
console = Console()

# Full list of MMLU subjects — 57 total
ALL_SUBJECTS: list[str] = [
    "abstract_algebra",
    "anatomy",
    "astronomy",
    "business_ethics",
    "clinical_knowledge",
    "college_biology",
    "college_chemistry",
    "college_computer_science",
    "college_mathematics",
    "college_medicine",
    "college_physics",
    "computer_security",
    "conceptual_physics",
    "econometrics",
    "electrical_engineering",
    "elementary_mathematics",
    "formal_logic",
    "global_facts",
    "high_school_biology",
    "high_school_chemistry",
    "high_school_computer_science",
    "high_school_european_history",
    "high_school_geography",
    "high_school_government_and_politics",
    "high_school_macroeconomics",
    "high_school_mathematics",
    "high_school_microeconomics",
    "high_school_physics",
    "high_school_psychology",
    "high_school_statistics",
    "high_school_us_history",
    "high_school_world_history",
    "human_aging",
    "human_sexuality",
    "international_law",
    "jurisprudence",
    "logical_fallacies",
    "machine_learning",
    "management",
    "marketing",
    "medical_genetics",
    "miscellaneous",
    "moral_disputes",
    "moral_scenarios",
    "nutrition",
    "philosophy",
    "prehistory",
    "professional_accounting",
    "professional_law",
    "professional_medicine",
    "professional_psychology",
    "public_relations",
    "security_studies",
    "sociology",
    "us_foreign_policy",
    "virology",
    "world_religions",
]

# A representative 12-subject subset — one per broad domain area — used
# when you want faster runs without losing cross-domain coverage.
DEFAULT_SUBJECTS: list[str] = [
    "high_school_mathematics",  # STEM — math
    "high_school_physics",  # STEM — physical science
    "college_computer_science",  # STEM — CS
    "high_school_biology",  # STEM — life science
    "high_school_us_history",  # Humanities — history
    "philosophy",  # Humanities — reasoning
    "high_school_psychology",  # Social Science
    "econometrics",  # Social Science — quant
    "professional_medicine",  # Other — medicine
    "nutrition",  # Other — applied science
    "logical_fallacies",  # Tests reasoning over knowledge
    "machine_learning",  # CS + math hybrid
]

# Letter choices for the 4-way multiple choice format
CHOICES = ["A", "B", "C", "D"]


@dataclass
class MMLUItem:
    """A single MMLU question.

    question_id: synthetic ID we generate (subject + index)
    subject:     which of the 57 subjects this came from
    question:    the question text
    choices:     list of 4 answer strings ["choice A text", "choice B text", ...]
    answer:      the correct letter, one of "A", "B", "C", "D"
    """

    question_id: str
    subject: str
    question: str
    choices: list[str]
    answer: str


def load_mmlu(
    subjects: list[str] | None = None,
    samples: int | None = 500,
    seed: int = 42,
) -> list[MMLUItem]:
    """Load MMLU questions from one or more subjects.

    Args:
        subjects: list of subject names to load. None = DEFAULT_SUBJECTS.
                  Pass ALL_SUBJECTS to use the full 57-subject benchmark.
        samples:  total questions to sample across all subjects. None = load all.
        seed:     random seed for reproducible sampling.

    Returns:
        List of MMLUItem objects, ready for the benchmark runner.
    """
    subjects = subjects or DEFAULT_SUBJECTS
    console.print(f"[bold]Loading MMLU[/bold] ({len(subjects)} subjects, validation split) …")

    all_datasets = []
    for subject in subjects:
        try:
            ds = load_dataset("cais/mmlu", subject, split="validation", trust_remote_code=True)
            all_datasets.append(ds)
        except Exception as e:
            logger.warning(f"Could not load MMLU subject '{subject}': {e}")

    if not all_datasets:
        raise RuntimeError("No MMLU subjects could be loaded. Check your internet connection.")

    combined = concatenate_datasets(all_datasets)

    if samples is not None:
        combined = combined.shuffle(seed=seed).select(range(min(samples, len(combined))))

    console.print(f"  Loaded {len(combined)} questions across {len(subjects)} subjects")

    items = []
    for i, row in enumerate(combined):
        subject = row.get("subject", "unknown")
        # MMLU stores choices as a list of 4 strings
        choices: list[str] = row["choices"]
        # Answer is stored as an integer index (0=A, 1=B, 2=C, 3=D)
        answer_idx: int = row["answer"]
        answer_letter = CHOICES[answer_idx]

        items.append(
            MMLUItem(
                question_id=f"mmlu_{subject}_{i}",
                subject=subject,
                question=row["question"],
                choices=choices,
                answer=answer_letter,
            )
        )

    return items


def format_prompt(item: MMLUItem) -> str:
    """Format an MMLU item as a zero-shot multiple-choice prompt.

    We present the question with labeled choices and ask the model to
    respond with only the letter. The "Only respond with the letter"
    instruction makes extraction reliable.
    """
    choices_text = "\n".join(f"  {letter}. {text}" for letter, text in zip(CHOICES, item.choices))
    return (
        f"The following is a multiple choice question. "
        f"Answer with only the letter of the correct choice (A, B, C, or D).\n\n"
        f"Question: {item.question}\n"
        f"{choices_text}\n\n"
        f"Answer:"
    )
