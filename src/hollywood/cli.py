from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path

from .crawler import (
    DEFAULT_OUTPUT,
    DEFAULT_PREFIXES,
    DEFAULT_USER_AGENT,
    crawl_profiles,
    normalize_prefixes,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crawl WGA writer directory profiles and emit JSONL snapshots.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--output",
        default=DEFAULT_OUTPUT,
        help="Output JSONL file path",
    )
    parser.add_argument(
        "--prefixes",
        default=DEFAULT_PREFIXES,
        help="Prefix set to crawl. Pass contiguous letters like 'abc' or comma-separated values like 'a,b,c'",
    )
    parser.add_argument(
        "--delay-seconds",
        type=float,
        default=2.0,
        help="Delay between profile fetches in seconds",
    )
    parser.add_argument(
        "--user-agent",
        default=DEFAULT_USER_AGENT,
        help="User agent string for browser requests",
    )
    parser.add_argument(
        "--max-profiles",
        type=int,
        default=None,
        help="Stop after writing this many unique profiles",
    )
    parser.add_argument(
        "--headless",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Run Chromium headless",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    prefixes = normalize_prefixes(args.prefixes)
    emitted = crawl_profiles(
        prefixes,
        Path(args.output),
        headless=args.headless,
        user_agent=args.user_agent,
        delay_seconds=args.delay_seconds,
        max_profiles=args.max_profiles,
        show_progress=sys.stderr.isatty(),
    )
    print(f"Saved {emitted} writer profiles to {args.output}")
    return 0
