# The Experiments Layer — How the Pieces Fit Together

## The Core Idea

The benchmark runners, the agentic loop, and the double-check loop are three powerful components. But components alone don't answer scientific questions — experiments do. The experiments layer is the scaffolding that runs each phase in a controlled, repeatable way, records the results honestly, and makes sure that when you see a number go up, you actually know *why*.

Think of the experiments layer as the lab notebook of the project. Anyone who runs it gets the same results. Every trial is logged. Nothing is ambiguous or hidden in a Jupyter notebook cell that someone forgot to run.

---

## Why a Separate Experiments Layer?

It might seem simpler to just have one big script that runs everything. The problem is that "one big script" thinking produces results you can't trust — because you don't know which part of the script caused which effect.

Good experimental design separates three things:

```mdx
┌─────────────────────────────────────────────────────────────────┐
│              SEPARATION OF CONCERNS                             │
│                                                                 │
│  ┌─────────────────┐    ┌─────────────────┐    ┌────────────┐  │
│  │  INFRASTRUCTURE │    │    EXPERIMENT   │    │   RESULTS  │  │
│  │                 │    │                 │    │            │  │
│  │  - Model loader │    │  - Which model? │    │  - Scores  │  │
│  │  - Tools        │    │  - Which data?  │    │  - Logs    │  │
│  │  - Datasets     │    │  - Which loop?  │    │  - Charts  │  │
│  │  - Trainers     │    │  - With tools?  │    │  - Tables  │  │
│  │                 │    │  - With review? │    │            │  │
│  │  (Nexus core)   │    │                 │    │  (W&B)     │  │
│  └─────────────────┘    └─────────────────┘    └────────────┘  │
│           ▲                      │                    ▲        │
│           │    uses              │  produces          │        │
│           └──────────────────────┘────────────────────┘        │
└─────────────────────────────────────────────────────────────────┘
```

The Nexus core handles the heavy lifting: loading models, running inference, managing datasets. The experiment scripts control *what* to run and *how* to compare it. The results go to Weights & Biases, where they're stored permanently and visualized automatically.

This means a teammate (or your future self, three months from now) can open the W&B dashboard and see exactly what configuration produced each result, re-run any experiment with one command, and compare runs side by side.

---

## The Directory Structure

```
experiments/
├── exp_01_baseline.py        # Phase 1: 3B vs 70B, raw
├── exp_02_open_book.py       # Phase 2: 3B + tools vs 70B
├── exp_03_reflection.py      # Phase 3: Draft → Critique → Refine
├── configs/
│   ├── exp_01.yaml           # Which model, dataset, sample count
│   ├── exp_02.yaml           # Tool config, search limits
│   └── exp_03.yaml           # Loop config, reflection depth
├── results/
│   ├── exp_01_results.json   # Raw scores (auto-generated)
│   ├── exp_02_results.json
│   └── exp_03_results.json
└── shared/
    ├── runner.py             # Base class all experiments inherit
    ├── scoring.py            # Accuracy, correction delta, tool stats
    └── logger.py             # W&B integration, local file logging
```

Each experiment is a self-contained script. You can run `python experiments/exp_01_baseline.py` and get results without touching anything else in the repository.

---

## The Shared Runner

Every experiment inherits from a base `ExperimentRunner` class. This is what makes all experiments consistent:

```
ExperimentRunner
│
├── load_config()          Read the YAML config for this experiment
├── setup_models()         Load the small model and optionally the large model
├── setup_datasets()       Pull the right benchmark dataset(s)
├── run()                  The main loop — must be implemented by each experiment
├── score()                Calculate accuracy and any experiment-specific metrics
└── log_results()          Push everything to W&B + write local JSON
```

Each individual experiment overrides the `run()` method with its specific logic — the baseline just queries models directly, the open-book experiment injects the tool loop, the reflection experiment runs the three-stage critique cycle.

This pattern means you never write the same boilerplate twice. The infrastructure for model loading, dataset batching, rate limiting, progress bars, and result logging is written once and shared.

---

## How a Single Experiment Run Flows

```
                    $ python experiments/exp_02_open_book.py

                              │
                              ▼
                    ┌─────────────────────┐
                    │  Load exp_02.yaml   │
                    │                     │
                    │  model: gemma-3-4b  │
                    │  dataset: triviaqa  │
                    │  samples: 500       │
                    │  tools: [web, rag]  │
                    │  max_tool_calls: 3  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Initialize W&B run │
                    │  (auto-named)       │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Load 500 TriviaQA  │
                    │  questions          │
                    └──────────┬──────────┘
                               │
                    ┌──────────▼──────────┐
                    │  For each question: │◄──────────────────┐
                    │                     │                   │
                    │  1. Format prompt   │                   │
                    │  2. Run agentic     │                   │
                    │     loop (3B model) │                   │
                    │  3. Score answer    │                   │
                    │  4. Log to W&B      │                   │
                    └──────────┬──────────┘                   │
                               │                              │
                               │ next question ───────────────┘
                               │
                               │ all done
                               ▼
                    ┌─────────────────────┐
                    │  Compute summary    │
                    │  statistics         │
                    │                     │
                    │  Overall accuracy   │
                    │  Tool call rate     │
                    │  Avg tool calls/Q   │
                    │  Hallucination rate │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  Save results.json  │
                    │  Upload to W&B      │
                    │  Print summary      │
                    └─────────────────────┘
```

---

## Configuration-Driven Design

Every experiment is controlled entirely by its YAML config file. This is important because it means changing an experiment doesn't require editing code — you edit a config and re-run.

```yaml
# configs/exp_02.yaml
experiment:
  name: "open-book-triviaqa-v1"
  description: "3B model with web search on TriviaQA"

model:
  small: "google/gemma-3-4b-it"
  large: null                    # No large model comparison in this run

data:
  dataset: "trivia_qa"
  split: "validation"
  samples: 500
  seed: 42                       # Fixed seed = reproducible sampling

tools:
  enabled: ["web_search", "doc_retrieval"]
  max_calls_per_question: 3
  search_backend: "duckduckgo"   # or "local_index" for offline runs

logging:
  wandb_project: "3b-logic-broker"
  save_local: true
  output_dir: "experiments/results/"
```

The `seed: 42` line might seem like a small detail, but it's crucial. With a fixed seed, every run samples the exact same 500 questions from the dataset. That means when you change a config option and re-run, you're comparing apples to apples — same questions, same ground truth, different approach.

## Caching the Reference Model

For large-model comparisons, you usually do not want to pay the full inference cost on every run. The reference model changes rarely, while the 3B model, prompts, and tool loops may change every day. So the better design is to treat the large model as a cached baseline.

The baseline runner supports that pattern:

- It computes a deterministic signature for each benchmark slice using the question IDs, formatted prompts, expected answers, and scoring version.
- It stores the large model's per-question results under `experiments/cache/exp_01_baseline/`.
- On later runs, if the benchmark signature matches, it reuses the cached large-model transcripts instead of loading or querying the large model again.
- If the sample size, seed, prompt format, or scoring version changes, the signature changes too, so the cache is ignored automatically.

The cache file format and file-management helpers live in a shared module so future Phase 2 and Phase 3 runners can reuse the same lifecycle instead of inventing their own cache layout.

That gives you fast, repeatable comparisons without mixing incompatible runs together.

CLI controls:

- `nexus experiment run --large-model ...` uses cached reference results by default
- `nexus experiment run --refresh-reference-cache --large-model ...` recomputes and overwrites the cache
- `nexus experiment run --no-reference-cache --large-model ...` forces a live large-model run without consulting cache
- `nexus experiment cache list` shows cached reference entries
- `nexus experiment cache inspect <cache-file>` shows the metadata and a short preview of cached results
- `nexus experiment cache purge <cache-file> --yes` deletes one cache entry
- `nexus experiment cache purge --experiment exp_01_baseline --model meta-llama/... --yes` deletes matching entries in bulk

---

## Comparing Experiments in the Dashboard

Once multiple runs exist in W&B, the comparison view becomes the main interface for understanding the project's progress:

```
W&B Dashboard — Experiment Comparison
────────────────────────────────────────────────────────────────────
Run Name              │ TriviaQA │ MMLU  │ Logic │ Tool Rate
──────────────────────┼──────────┼───────┼───────┼───────────
exp_01 / 3B baseline  │  38.2%   │ 44.1% │ 61.4% │ n/a
exp_01 / 70B baseline │  81.5%   │ 76.2% │ 67.3% │ n/a
exp_02 / 3B + tools   │  63.7%   │ 59.8% │ 62.1% │ 78%
exp_03 / 3B + reflect │    —     │   —   │ 71.4% │ n/a
────────────────────────────────────────────────────────────────────
```

The pattern that matters: the 3B model starts at 38% on TriviaQA and climbs to 64% with tools — closing most of the gap with the 70B. Meanwhile, the logic score barely changes between the baseline 3B (61%) and the tool-equipped 3B (62%), which is exactly what we'd expect — you don't need to look up facts to do logical deduction.

The local terminal summary now also prints a side-by-side comparison table whenever both a small and large model are present for the same benchmark. Each side is labeled `live` or `cached`, so you can immediately see whether the reference row came from a fresh run or the saved baseline cache.

---

## How the Experiments Layer Connects to Fine-Tuning

The experiments aren't just producing benchmark scores — they're also generating training data for Phase 4.

Every time the model goes through the Draft → Critique → Refine loop in Phase 3, we capture the full transcript: the draft, the critique, the refined answer, and whether the refined answer was actually better. The cases where the model successfully caught and fixed its own error are *gold*. Those transcripts become training examples for the fine-tuning phase, teaching the model to internalize the self-correction habit rather than needing a three-stage prompt to trigger it.

```
Experiment runs
      │
      ▼
Successful reflection transcripts saved
      │
      ▼
Curated into fine-tuning dataset
      │
      ▼
QLoRA training run (Phase 4)
      │
      ▼
Fine-tuned model re-evaluated using same experiment configs
      │
      ▼
Final comparison: can the fine-tuned 3B beat zero-shot GPT-4?
```

This loop — experiment, observe, distill, retrain, re-evaluate — is the complete scientific cycle the project is designed to run. The experiments layer is the connective tissue that makes it coherent.
