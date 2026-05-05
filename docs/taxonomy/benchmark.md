# Benchmark

A benchmark is a reusable test definition. It specifies what to test, how to score it, and what constitutes a valid answer. Benchmarks are consumed by experiments and evaluations.

Current benchmark logic lives in `src/nexus/experiments/benchmarks/` with configs in `configs/benchmarks/`. Benchmarks do not yet have a first-class durable store or stable platform IDs.

A benchmark defines the test. An evaluation records a score against it. An experiment organizes multiple benchmark runs for comparison.
