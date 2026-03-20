# Phase 1: Benchmark Runners — Proving the Problem

## The Core Idea

Before we try to fix anything, we need to prove that there is actually something worth fixing.

The central claim of this project is bold: small models (3 billion parameters) don't fail because they're bad at *thinking* — they fail because they don't have enough *facts* crammed into them. To prove this, we first need to build a controlled experiment that separates "knowing things" from "reasoning about things."

Phase 1 is that experiment. It's a set of benchmark runners — test harnesses that put a small model and a large model through two very different kinds of tests and measure exactly where the gap comes from.

---

## Two Kinds of Intelligence Tests

Think about two different types of exam questions:

**Type A — Knowledge questions:**
> "What year was the Eiffel Tower built?"
> "What is the capital of Burkina Faso?"
> "Which element has the atomic number 79?"

These questions have nothing to do with your ability to think. You either memorized the answer at some point, or you didn't. No amount of on-the-spot reasoning will get you to "1887" or "Ouagadougou" if those facts were never stored in your head.

**Type B — Logic questions:**
> "If all Blorps are Fleems, and all Fleems are Zargs, are all Blorps also Zargs?"
> "A train leaves Station A every 12 minutes. Another leaves Station B every 8 minutes. How often do they depart at the same time?"
> "You have a 3-gallon jug and a 5-gallon jug. How do you measure exactly 4 gallons?"

These questions test *reasoning*. You've never seen this exact problem before. There are no facts to recall. You either have the logical machinery to work through the steps, or you don't.

Phase 1 runs both types of tests on two models — a small 3B model and a large 70B+ model — and tracks exactly how they perform on each.

---

## The Three Benchmark Datasets

```
┌─────────────────────────────────────────────────────────────────┐
│                     BENCHMARK SUITE                             │
│                                                                 │
│  ┌─────────────┐   ┌──────────────┐   ┌────────────────────┐  │
│  │  TriviaQA   │   │     MMLU     │   │  Synthetic Logic   │  │
│  │             │   │              │   │    Puzzles         │  │
│  │  Pure fact  │   │ Uni-level    │   │  No facts needed   │  │
│  │  recall     │   │ subject      │   │  Made-up words     │  │
│  │             │   │ knowledge    │   │  Pure deduction    │  │
│  │  "Who       │   │ "What is     │   │  "All Wumps are    │  │
│  │  invented   │   │ mitosis?"    │   │  Glarbs. Is X      │  │
│  │  the        │   │              │   │  a Glarb?"         │  │
│  │  telephone?"│   │              │   │                    │  │
│  └─────────────┘   └──────────────┘   └────────────────────┘  │
│                                                                 │
│       ◄── Knowledge-Heavy ──►         ◄── Logic-Heavy ──►     │
└─────────────────────────────────────────────────────────────────┘
```

### TriviaQA
A massive dataset of trivia questions scraped from quiz competitions and Wikipedia. Questions like "What was the name of the horse ridden by Napoleon at Waterloo?" These are pure knowledge recall — the model either has the answer in its weights or it doesn't. We expect the big 70B model to dominate here.

### MMLU (Massive Multitask Language Understanding)
57 subjects ranging from high school math to college medicine to professional law. Multiple-choice format. This is the gold standard benchmark for academic knowledge. It's still heavily knowledge-dependent — you need to know what the difference between mitosis and meiosis is, not figure it out from first principles. Again, we expect 70B to win comfortably.

### Synthetic Logic Puzzles
This is the key differentiator. We generate puzzles using *made-up words* specifically so the model can't cheat by pattern-matching to training data. A classic example:

> "All Wumbles are Frobbs. Some Frobbs are Glarks. Tixby is a Wumble. Is Tixby definitely a Frobb? Is Tixby definitely a Glark?"

The words mean nothing. The model has to apply pure syllogistic logic. We also include Zebra-puzzle variants (the classic "the man in the red house owns a fish" style) with nonsense nouns substituted in.

---

## How the Runner Works

```
                        ┌──────────────────────┐
                        │   Benchmark Runner   │
                        └──────────┬───────────┘
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                    │
              ▼                    ▼                    ▼
     ┌────────────────┐  ┌────────────────┐  ┌────────────────┐
     │  Load Dataset  │  │  Load Dataset  │  │  Generate 500  │
     │  TriviaQA      │  │  MMLU subset   │  │  synthetic     │
     │  (500 samples) │  │  (500 samples) │  │  puzzles       │
     └───────┬────────┘  └───────┬────────┘  └───────┬────────┘
             │                   │                    │
             └───────────────────┼────────────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    For each question:   │
                    │                         │
                    │  1. Feed to 3B model    │
                    │  2. Feed to 70B model   │
                    │  3. Record both answers │
                    │  4. Score vs ground     │
                    │     truth               │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │    Results Table        │
                    │                         │
                    │  Dataset   | 3B  | 70B  │
                    │  TriviaQA  | 38% | 81%  │
                    │  MMLU      | 44% | 76%  │
                    │  Logic     | 61% | 67%  │ ← The key finding
                    └─────────────────────────┘
```

Each model gets the same prompt. No hints, no special formatting. A simple: "Answer the following question. Question: [question]. Answer:"

Results are logged to Weights & Biases so we get charts, not just numbers.

---

## What We're Looking For

The hypothesis will be confirmed if we see this pattern:

| Test Type | 3B Model | 70B Model | Gap |
|-----------|----------|-----------|-----|
| TriviaQA (facts) | ~35-40% | ~78-82% | Large |
| MMLU (knowledge) | ~42-46% | ~72-78% | Large |
| Synthetic Logic | ~58-65% | ~62-68% | **Small** |

That small gap on logic is everything. It means the 3B model is nearly as capable a *reasoner* as the 70B model — it just doesn't have the stored facts. And stored facts can be looked up.

If the gap on logic is *also* large, the hypothesis needs rethinking — it would mean the extra parameters aren't just storing facts, they're enabling better reasoning too. That's the honest outcome we're also prepared for.

---

## Synthetic Puzzle Generator

The logic puzzle generator deserves its own mention because it's doing important scientific work — it ensures the small model can't accidentally "remember" the answer from training data.

```
Puzzle Template:
  "All [NOUN_A]s are [NOUN_B]s.
   All [NOUN_B]s are [NOUN_C]s.
   [NAME] is a [NOUN_A].
   Question: Is [NAME] a [NOUN_C]?"

With nouns randomly drawn from a pool of 200 nonsense words:
  Wumble, Frobb, Glark, Tixby, Zorn, Pleeb, Varg, Snirp...

Correct answer: Yes (transitive syllogism)
```

The generator creates puzzles of varying depth (2-step, 3-step, 4-step reasoning chains) and with different logical structures (all/some/none, negations, conditionals). This gives us a rich picture of where small models start to struggle as complexity increases.

---

## Output and What Comes Next

At the end of Phase 1, you have:

1. **A performance table** — numbers that either confirm or challenge the hypothesis
2. **A breakdown by reasoning depth** — does the 3B model hold up on 2-step logic but fall apart at 4-step?
3. **A baseline to beat** — every subsequent phase will be compared against these numbers

Phase 2 takes those same knowledge-heavy tests (TriviaQA, MMLU) and lets the 3B model search for answers instead of recalling them from memory. If the search-augmented 3B model closes that big gap on trivia, we've proven that knowledge can be outsourced.
