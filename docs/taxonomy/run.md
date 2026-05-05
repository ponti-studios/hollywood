# Run

A run is the atomic execution record in Nexus. Every piece of work that happens — an inference request, a benchmark trial, an evaluation pass — should be traceable to a run.

The current implementation lives in `src/nexus/runs/` with a durable SQLite store backed by `src/nexus/runs/store.py`. Inference runs are already written here on every `/v1/chat/completions` call. A compatibility shim in `src/nexus/api/store.py` keeps older inference-only callers working.

A run records what happened. A job orchestrates work that produces runs. An experiment groups runs for comparison. An artifact is something a run produces.
