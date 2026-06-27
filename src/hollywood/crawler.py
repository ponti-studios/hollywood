from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

BASE_URL = "https://directories.wga.org/"
DEFAULT_OUTPUT = "wga_writers.jsonl"
DEFAULT_PREFIXES = "abcdefghijklmnopqrstuvwxyz"
DEFAULT_USER_AGENT = "ResearchBot/0.1 contact@example.com"

SEARCH_INPUT_SELECTORS = (
    "#Filter_Keyword",
    "input[name='Filter.Keyword']",
    "input[placeholder='Search writer or project here...']",
)
SEARCH_TYPE_BUTTON_SELECTORS = (
    "#search-type",
    "button#search-type",
)
SEARCH_BUTTON_SELECTORS = (
    "#searchBtn",
    "button#searchBtn",
)
STARTS_WITH_ITEM_SELECTOR = "a.dropdown-item[data-value='2']"


class SelectorError(RuntimeError):
    """Raised when the WGA page shape does not match our selectors."""


def writer_key(url: str) -> str:
    return hashlib.sha256(url.rstrip("/").encode("utf-8")).hexdigest()[:16]


def normalize_prefixes(raw: str) -> list[str]:
    value = raw.strip()
    if not value:
        raise ValueError("prefixes must not be empty")

    if "," in value:
        prefixes = [part.strip() for part in value.split(",")]
    else:
        prefixes = list(value)

    cleaned = [prefix for prefix in prefixes if prefix]
    if not cleaned:
        raise ValueError("prefixes must contain at least one non-empty prefix")
    return cleaned


def unique_profile_urls(urls: Iterable[str]) -> list[str]:
    return sorted(set(urls))


def build_row(url: str, text: str) -> dict[str, str]:
    return {
        "writer_id": writer_key(url),
        "profile_url": url,
        "raw_text_snapshot": text,
    }


def serialize_row(row: dict[str, str]) -> str:
    return json.dumps(row, ensure_ascii=False)


def _selector_error(page: Any, description: str, selectors: Sequence[str]) -> SelectorError:
    selector_list = ", ".join(selectors)
    return SelectorError(f"Could not find {description} on {page.url!r} using selectors: {selector_list}")


def _click(page: Any, selectors: Sequence[str], description: str) -> None:
    for selector in selectors:
        locator = page.locator(selector)
        for index in range(locator.count()):
            candidate = locator.nth(index)
            if candidate.is_visible():
                candidate.click()
                return
    raise _selector_error(page, description, selectors)


def _fill(page: Any, selectors: Sequence[str], value: str, description: str) -> None:
    for selector in selectors:
        locator = page.locator(selector)
        for index in range(locator.count()):
            candidate = locator.nth(index)
            if candidate.is_visible():
                candidate.fill(value)
                return
    raise _selector_error(page, description, selectors)


def search_prefix(page: Any, prefix: str) -> None:
    _click(page, SEARCH_TYPE_BUTTON_SELECTORS, "the search type dropdown")
    _click(page, (STARTS_WITH_ITEM_SELECTOR,), "the 'Starts With' option")
    _fill(page, SEARCH_INPUT_SELECTORS, prefix, "the search input")
    _click(page, SEARCH_BUTTON_SELECTORS, "the 'Search' control")


def collect_profile_urls(page: Any) -> list[str]:
    urls = page.locator("a[href*='/member/']").evaluate_all("els => els.map(a => a.href)")
    return unique_profile_urls(urls)


def crawl_profiles(
    prefixes: Iterable[str],
    output_path: Path,
    *,
    headless: bool = True,
    user_agent: str = DEFAULT_USER_AGENT,
    delay_seconds: float = 2.0,
    max_profiles: int | None = None,
    show_progress: bool = True,
) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - exercised when dependency is missing
        raise RuntimeError(
            "Playwright is required. Install the package with `uv pip install -e \".[dev]\"`."
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)

    prefix_list = list(prefixes)
    emitted = 0
    seen: set[str] = set()

    def crawl(page: Any, handle: Any, progress: Any = None, prefix_task: Any = None, profile_task: Any = None) -> int:
        nonlocal emitted
        for prefix in prefix_list:
            if max_profiles is not None and emitted >= max_profiles:
                break

            page.goto(BASE_URL, wait_until="networkidle")
            search_prefix(page, prefix)
            page.wait_for_load_state("networkidle")

            for url in collect_profile_urls(page):
                if url in seen:
                    continue
                seen.add(url)

                profile = page.context.new_page()
                try:
                    profile.goto(url, wait_until="networkidle")
                    snapshot = profile.locator("body").inner_text()
                finally:
                    profile.close()

                handle.write(serialize_row(build_row(url, snapshot)) + "\n")
                handle.flush()
                emitted += 1

                if progress is not None and profile_task is not None:
                    progress.advance(profile_task)

                if delay_seconds:
                    time.sleep(delay_seconds)

                if max_profiles is not None and emitted >= max_profiles:
                    break

            if progress is not None and prefix_task is not None:
                progress.advance(prefix_task)

        return emitted

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=headless)
        context = browser.new_context(user_agent=user_agent)
        try:
            page = context.new_page()
            with output_path.open("a", encoding="utf-8") as handle:
                if show_progress:
                    from rich.progress import (
                        BarColumn,
                        Progress,
                        SpinnerColumn,
                        TextColumn,
                        TimeElapsedColumn,
                    )

                    with Progress(
                        SpinnerColumn(),
                        TextColumn("{task.description}"),
                        BarColumn(),
                        TextColumn("{task.completed}/{task.total}"),
                        TimeElapsedColumn(),
                        transient=True,
                    ) as progress:
                        prefix_task = progress.add_task("prefixes", total=len(prefix_list))
                        profile_task = progress.add_task(
                            "profiles",
                            total=max_profiles if max_profiles is not None else None,
                        )
                        crawl(page, handle, progress, prefix_task, profile_task)
                else:
                    crawl(page, handle)
        finally:
            context.close()
            browser.close()

    return emitted
