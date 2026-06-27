from __future__ import annotations

import json

import pytest

from hollywood.crawler import (
    build_row,
    normalize_prefixes,
    serialize_row,
    unique_profile_urls,
    writer_key,
)


def test_writer_key_is_stable_and_truncated() -> None:
    url = "https://directories.wga.org/member/example/"
    assert writer_key(url) == "abb3d7d08c83e20f"
    assert writer_key(url + "/") == writer_key(url)


def test_normalize_prefixes_supports_compact_and_csv_input() -> None:
    assert normalize_prefixes("abc") == ["a", "b", "c"]
    assert normalize_prefixes("a,b, c") == ["a", "b", "c"]


def test_normalize_prefixes_rejects_empty_input() -> None:
    with pytest.raises(ValueError):
        normalize_prefixes("   ")


def test_unique_profile_urls_dedupes_and_sorts() -> None:
    urls = [
        "https://directories.wga.org/member/b/",
        "https://directories.wga.org/member/a/",
        "https://directories.wga.org/member/b/",
    ]
    assert unique_profile_urls(urls) == [
        "https://directories.wga.org/member/a/",
        "https://directories.wga.org/member/b/",
    ]


def test_jsonl_row_format_round_trips() -> None:
    row = build_row("https://directories.wga.org/member/example/", "snapshot text")
    assert json.loads(serialize_row(row)) == row
