# Evaluation

An evaluation is a quality measurement record. It answers "how good was this?" for a specific subject — a run, an experiment, or a model — against some scorer or rubric.

The current implementation lives in `src/nexus/evaluation/` with schema and durable store. Benchmark scores from completed experiments are automatically written as evaluation records, linked back to the experiment via `evaluation_ids`.

An evaluation measures. An experiment compares. A benchmark defines what to test against.
