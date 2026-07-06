"""Ingest a document for extraction and materialization.

Called by the API server as a subprocess. Reads document text from
stdin, runs LLM extraction, saves results + materialized entities
to the database, and outputs a JSON summary to stdout.
"""

from __future__ import annotations

import json
import sys

from .config import HollywoodSettings
from .domain.llm import _call_openrouter
from .storage import HollywoodStorage


def main() -> None:
    text = sys.stdin.read()
    if not text.strip():
        print(json.dumps({"error": "No input text"}))
        sys.exit(1)

    # Run LLM extraction
    result = _call_openrouter(text, prompt_version="v1")
    packet = result.packet
    raw_json = result.raw_json.decode("utf-8")

    # Save to database
    settings = HollywoodSettings()
    storage = HollywoodStorage(settings.resolved_db_path)
    storage.initialize()

    run_id = storage.start_run_raw("extraction", {"source": "api_ingest"})
    raw_id = storage.insert_extraction_raw_record(
        run_id=run_id,
        source_id="api_ingest",
        content_path="api_ingest",
        content_hash=hash(text),
    )

    candidates_out: list[dict] = []
    for candidate in packet.candidates:
        storage.save_extraction_result(
            run_id=run_id,
            raw_record_id=raw_id,
            source_id="api_ingest",
            candidate=candidate,
            model_name=result.model_name,
            prompt_version="v1",
            raw_json=raw_json,
        )
        entity_id = storage.materialize_candidate(
            candidate,
            source_id="api_ingest",
            raw_record_id=raw_id,
        )
        candidates_out.append({
            "id": entity_id,
            "name": candidate.name,
            "bio": candidate.bio,
            "position": candidate.position or "",
            "num_credits": len(candidate.credits),
            "num_tags": len(candidate.tags),
            "num_orgs": len(candidate.organizations),
        })

    storage.close()

    print(json.dumps({
        "run_id": run_id,
        "model_name": result.model_name,
        "candidates": candidates_out,
    }, indent=2))


if __name__ == "__main__":
    main()
