# Experiment

An experiment is a structured comparison. It groups runs, benchmarks, and evaluations under a single question or hypothesis so results can be compared and a winner identified.

The current implementation lives in `src/nexus/experiments/` with a durable store and schema. Records are persisted immediately on submit and updated through execution. Completed experiments carry linked `evaluation_ids` and a `summary` with scores.

An experiment compares. An evaluation measures. A run records one execution.
