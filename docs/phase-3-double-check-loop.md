# Phase 3: The Double-Check Loop — Teaching a Model to Catch Its Own Mistakes

## The Core Idea

Every good software engineer has learned this lesson the hard way: the first version of your code is probably wrong. Not because you're bad at your job — but because complex problems have hidden edge cases, and your brain fills in gaps automatically when you're in "writing mode." The fix is to switch modes: put the keyboard down, read what you actually wrote (not what you meant to write), and find the holes.

Phase 3 builds this exact habit into our 3B model. Instead of generating one answer and submitting it, the model goes through three explicit stages: **Draft, Critique, Refine**. The same model plays two different roles — first as the engineer who writes the solution, then as the code reviewer who tears it apart.

This is sometimes called "System 2 thinking" — slow, deliberate reasoning that double-checks the output of fast intuition. It's one of the core traits of expert problem-solving in humans, and we're going to measure whether a small model can pull it off.

---

## The Three Stages

```
┌──────────────────────────────────────────────────────────────────┐
│                    THE DOUBLE-CHECK LOOP                         │
│                                                                  │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  STAGE 1: DRAFT                                          │  │
│   │                                                          │  │
│   │  Model receives the problem and generates its            │  │
│   │  best first attempt — code, reasoning, or answer         │  │
│   │                                                          │  │
│   │  Prompt style: "Solve the following problem..."          │  │
│   └──────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│                              │ Draft output passed forward       │
│                              ▼                                   │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  STAGE 2: CRITIQUE                                       │  │
│   │                                                          │  │
│   │  The SAME model reads the draft as if it's someone       │  │
│   │  else's work and looks specifically for problems         │  │
│   │                                                          │  │
│   │  Prompt style: "Review this solution. Do NOT re-solve    │  │
│   │  it. Find flaws, edge cases, errors, or missing steps."  │  │
│   │                                                          │  │
│   │  Output: A structured list of issues found               │  │
│   └──────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│                              │ Critique passed forward           │
│                              ▼                                   │
│   ┌──────────────────────────────────────────────────────────┐  │
│   │  STAGE 3: REFINE                                         │  │
│   │                                                          │  │
│   │  The model rewrites the solution, using the critique     │  │
│   │  as a checklist of things to fix                         │  │
│   │                                                          │  │
│   │  Prompt style: "Here is your original solution and a     │  │
│   │  list of flaws. Write an improved version."              │  │
│   │                                                          │  │
│   │  Output: Final, corrected solution                       │  │
│   └──────────────────────────┬───────────────────────────────┘  │
│                              │                                   │
│                              ▼                                   │
│                     Score Draft vs Refined                       │
│                     Δ accuracy = the signal                      │
└──────────────────────────────────────────────────────────────────┘
```

---

## A Concrete Example

Here's what this looks like on a real coding task:

**The Problem:**
> Write a Python function that takes a list of integers and returns the second-largest unique value.

**Stage 1 — Draft:**
```python
def second_largest(nums):
    nums.sort(reverse=True)
    return nums[1]
```

This looks reasonable at first glance. But it has two bugs.

**Stage 2 — Critique:**
The model switches into reviewer mode and is asked to find problems, not fix them:

```
Issues found:
1. If the list has duplicate largest values (e.g., [5, 5, 3]),
   nums[1] returns 5 again, not 3. The problem asks for the
   second-largest *unique* value.

2. If the list has fewer than 2 unique values (e.g., [7, 7]),
   this will return the wrong answer or crash with no error.

3. No handling for an empty list — nums[1] would raise an
   IndexError.
```

**Stage 3 — Refine:**
```python
def second_largest(nums):
    unique = sorted(set(nums), reverse=True)
    if len(unique) < 2:
        raise ValueError("Need at least 2 unique values")
    return unique[1]
```

All three bugs caught and fixed. The model improved its own work without any human in the loop.

---

## Why "Don't Solve It, Just Critique" Matters

The most important constraint in Stage 2 is the instruction *not* to re-solve the problem. This sounds counterintuitive — why would you hold back a solution if you see one?

The reason is cognitive mode separation. When a model is in "generation mode," it tends to produce fluent, confident text that follows naturally from what came before. This is great for writing but terrible for finding errors — the model will complete the thought pattern rather than question it.

By explicitly entering "critic mode," we force a different kind of attention:

```
Generation mode asks:  "What comes next?"
Critic mode asks:      "What is wrong with this?"
```

These are fundamentally different cognitive operations. The first is pattern completion. The second is adversarial evaluation. A model that can genuinely switch between them is demonstrating something close to executive function.

---

## What We Measure: The Correction Delta

The key metric for Phase 3 is called the **Correction Delta (Δ)** — the percentage point improvement from Draft to Refined answer.

```
┌────────────────────────────────────────────────────────────────┐
│                 Correction Delta Breakdown                     │
│                                                                │
│  Categories of outcomes per question:                         │
│                                                                │
│  ✓ Correct → Correct     Draft was right, stayed right        │
│  ✓ Correct → Wrong       Introduced a new bug (bad)           │
│  ✗ Wrong   → Correct     Caught and fixed its mistake (goal)  │
│  ✗ Wrong   → Wrong       Failed to catch the error            │
│                                                                │
│  Δ = (Wrong→Correct) − (Correct→Wrong)                        │
│                                                                │
│  A positive Δ means the loop is helping.                      │
│  A Δ near zero means it's not doing anything useful.          │
│  A negative Δ means the model is breaking correct answers.    │
└────────────────────────────────────────────────────────────────┘
```

A strong Δ (say, +15 percentage points) would be significant evidence that the 3B model has genuine self-correction capability — not just that it's fluently generating plausible-sounding revisions.

---

## The Benchmark Tasks

We run the loop on two task types that have ground-truth correctness signals:

**HumanEval** — 164 handcrafted Python programming problems, each with hidden test cases. The model's code is *executed*, not just read. There's no ambiguity: it either passes the tests or it doesn't. This is an ideal benchmark because correct/incorrect is binary and objective.

**SWE-bench Lite** — Real GitHub issues from open-source Python projects. The model has to write a patch that fixes an actual reported bug. This is harder and more realistic — it requires reading code, understanding what's broken, and producing a working fix.

---

## Failure Modes to Watch For

Not all critique is useful. We track several ways the loop can go wrong:

**Phantom criticism** — The model finds problems that don't exist:
> "The function should handle negative numbers" (the problem never involved negatives)

**Shallow critique** — The model identifies surface issues but misses the real bug:
> "Variable names could be more descriptive" (while a logic error sits unnoticed)

**Over-editing** — The refined version is longer and more complex but no more correct:
> Adds five edge-case checks, none of which address the actual bug

Tracking these failure modes tells us *how* the model is failing, not just *that* it fails — and that information feeds directly into Phase 4, where we fine-tune the model to critique better.

---

## What Comes Next

If Phase 3 shows a meaningful Correction Delta, we have strong evidence that iterative self-reflection is a genuinely useful capability — not just a trick that sounds good in a demo.

Phase 4 takes this further by training the model specifically to think this way from the start. Instead of needing three separate prompts to draft, critique, and refine, a fine-tuned model would learn to embed this internal double-check loop into its very first response — the way an experienced engineer catches their own bugs almost automatically before hitting commit.
