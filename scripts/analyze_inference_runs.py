#!/usr/bin/env python3
"""
analyze_inference_runs.py — Inspect and summarize inference test results.

Usage:
    python scripts/analyze_inference_runs.py [--db .data/api/inference.db] [--limit 50]

This script:
  - Connects to the inference database
  - Summarizes test pass/fail by counting specific result values
  - Reports latency statistics
  - Flags any transcript issues (role prefixes, excessive length)
"""

from __future__ import annotations

import argparse
from pathlib import Path

from nexus.api.store import InferenceStore


def analyze_runs() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--db",
        default=".data/api/inference.db",
        help="Path to the inference database.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=50,
        help="Maximum number of records to analyze.",
    )
    parser.add_argument(
        "--model",
        help="Filter by model ID.",
    )
    args = parser.parse_args()

    db_path = Path(args.db)
    if not db_path.exists():
        print(f"[ERROR] Database not found: {db_path}")
        print("\nRun the inference tests first:")
        print("  uv run pytest tests/test_tool_calls.py -v -s --run-inference\n")
        return

    store = InferenceStore(db_path)
    records = store.list(model_id=args.model, limit=args.limit)

    if not records:
        print("[INFO] No records found in the database.")
        return

    # Summarize by model
    model_summary: dict[str, dict] = {}
    for record in records:
        mid = record.model_id
        if mid not in model_summary:
            model_summary[mid] = {
                "count": 0,
                "latencies": [],
                "issues": [],
                "tool_calls": 0,
                "direct_answers": 0,
            }

        model_summary[mid]["count"] += 1
        model_summary[mid]["latencies"].append(record.latency_ms)

        # Check for issues
        if record.response.startswith(("ASSISTANT:", "USER:", "SYSTEM:")):
            model_summary[mid]["issues"].append(
                f"  ⚠ {record.id[:8]}: Response starts with role prefix"
            )
        if len(record.response) > 500:
            model_summary[mid]["issues"].append(
                f"  ⚠ {record.id[:8]}: Response too long ({len(record.response)} chars)"
            )

        # Count tool calls vs direct answers
        if '{"tool_call"' in record.response:
            model_summary[mid]["tool_calls"] += 1
        else:
            model_summary[mid]["direct_answers"] += 1

    # Print summary
    print("\n" + "=" * 70)
    print("INFERENCE TEST SUMMARY")
    print("=" * 70)

    for model_id, stats in sorted(model_summary.items()):
        latencies = stats["latencies"]
        avg_lat = sum(latencies) / len(latencies) if latencies else 0
        min_lat = min(latencies) if latencies else 0
        max_lat = max(latencies) if latencies else 0

        print(f"\n[{model_id}]")
        print(f"  Runs: {stats['count']}")
        print(f"  Tool calls: {stats['tool_calls']} | Direct answers: {stats['direct_answers']}")
        print(f"  Latency: {avg_lat:.0f}ms avg (min: {min_lat:.0f}, max: {max_lat:.0f})")

        if stats["issues"]:
            print(f"  Issues ({len(stats['issues'])})")
            for issue in stats["issues"][:5]:  # Show first 5
                print(issue)
            if len(stats["issues"]) > 5:
                print(f"  ... and {len(stats['issues']) - 5} more")
        else:
            print("  ✓ No issues detected")

    print(f"\n{'=' * 70}")
    print(
        f"Total records: {sum(s['count'] for s in model_summary.values())} "
        f"| Models: {len(model_summary)}"
    )
    print(f"Database: {db_path}\n")


if __name__ == "__main__":
    analyze_runs()
