from __future__ import annotations

import html
import re

import trafilatura

from .models import normalize_whitespace

HTML_TAG_RE = re.compile(r"<[^>]+>")


def strip_html_fragment(value: str | None) -> str:
    if not value:
        return ""
    unescaped = html.unescape(value)
    stripped = HTML_TAG_RE.sub(" ", unescaped)
    return normalize_whitespace(stripped)


def extract_text_from_html(document: str) -> str:
    extracted = trafilatura.extract(
        document,
        include_comments=False,
        include_links=False,
        include_tables=False,
        favor_precision=True,
    )
    if extracted:
        return normalize_whitespace(extracted)
    return strip_html_fragment(document)
