from __future__ import annotations

import json
import re
import time
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from ..config import HollywoodSettings
from ..models import (
    CreditRow,
    EntityAliasRow,
    EntityKind,
    EntityRow,
    IngestOptions,
    NormalizedBundle,
    RawPayload,
    SourceDefinition,
    canonicalize_url,
    json_dumps,
    make_stable_id,
)
from ..storage import HollywoodStorage
from .base import BaseAdapter

SEARCH_INPUT_SELECTORS = (
    "#Filter_Keyword",
    "input[name='Filter.Keyword']",
    "input[placeholder='Search writer or project here...']",
)
SEARCH_TYPE_BUTTON_SELECTORS = ("#search-type", "button#search-type")
SEARCH_BUTTON_SELECTORS = ("#searchBtn", "button#searchBtn")
STARTS_WITH_ITEM_SELECTOR = "a.dropdown-item[data-value='2']"
CREDIT_COUNT_RE = re.compile(r"^(?P<count>\d+)\s+Credits?$")


class SelectorError(RuntimeError):
    """Raised when the WGA page shape does not match expected selectors."""


def writer_key(url: str) -> str:
    return make_stable_id("wga", canonicalize_url(url))


def normalize_prefixes(raw: str) -> list[str]:
    value = raw.strip()
    if not value:
        raise ValueError("prefixes must not be empty")
    prefixes = [part.strip() for part in value.split(",")] if "," in value else list(value)
    cleaned = [prefix for prefix in prefixes if prefix]
    if not cleaned:
        raise ValueError("prefixes must contain at least one non-empty prefix")
    return cleaned


def unique_profile_urls(urls: Iterable[str]) -> list[str]:
    return sorted({canonicalize_url(url) for url in urls})


def _selector_error(page: Any, description: str, selectors: Sequence[str]) -> SelectorError:
    selector_list = ", ".join(selectors)
    return SelectorError(
        f"Could not find {description} on {page.url!r} using selectors: {selector_list}"
    )


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


def _extract_writer_name(profile: Any) -> str:
    for selector in ("h1", "main h1", ".page-title h1"):
        locator = profile.locator(selector)
        if locator.count():
            text = locator.first.inner_text().strip()
            if text:
                return text
    title = profile.title().strip()
    return title.split("|")[0].strip() if title else "Unknown Writer"


def _parse_wga_credits(text: str, person_entity_id: str) -> list[CreditRow]:
    credits: list[CreditRow] = []
    previous_title: str | None = None
    for line in [line.strip() for line in text.splitlines() if line.strip()]:
        match = CREDIT_COUNT_RE.match(line)
        if match and previous_title:
            count = int(match.group("count"))
            credits.append(
                CreditRow(
                    credit_id=make_stable_id("wga", person_entity_id, previous_title, str(count)),
                    source_id="wga",
                    person_entity_id=person_entity_id,
                    person_name=None,
                    title_name=previous_title,
                    title_external_id=None,
                    role="writer_credit_summary",
                    billing=count,
                    metadata_json=json_dumps({"source": "wga_profile_text"}),
                )
            )
            previous_title = None
            continue
        if (
            not line.startswith("Created by:")
            and not line.startswith("Written by:")
            and "Writers Guild" not in line
            and "Jump To" not in line
            and "(" in line
        ):
            previous_title = line
    return credits


class WgaAdapter(BaseAdapter):
    def __init__(self, source: SourceDefinition):
        super().__init__(source)

    def fetch_raw_payloads(
        self, settings: HollywoodSettings, options: IngestOptions
    ) -> list[RawPayload]:
        try:
            from playwright.sync_api import sync_playwright
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("Playwright is required for the WGA source.") from exc

        payloads: list[RawPayload] = []
        seen: set[str] = set()
        prefixes = options.prefixes or normalize_prefixes(
            str(self.source.metadata.get("default_prefixes", "abcdefghijklmnopqrstuvwxyz"))
        )
        emitted = 0

        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(user_agent=settings.user_agent)
            try:
                page = context.new_page()
                for prefix in prefixes:
                    if options.limit is not None and emitted >= options.limit:
                        break
                    page.goto(self.source.default_urls[0], wait_until="networkidle")
                    search_prefix(page, prefix)
                    page.wait_for_load_state("networkidle")
                    for url in collect_profile_urls(page):
                        if url in seen:
                            continue
                        seen.add(url)
                        profile = context.new_page()
                        try:
                            profile.goto(url, wait_until="networkidle")
                            html = profile.content()
                            text = profile.locator("body").inner_text()
                            name = _extract_writer_name(profile)
                        finally:
                            profile.close()
                        canonical_url = canonicalize_url(url)
                        writer_id = writer_key(canonical_url)
                        metadata = {
                            "profile_url": canonical_url,
                            "writer_id": writer_id,
                            "writer_name": name,
                            "prefix": prefix,
                        }
                        payloads.append(
                            RawPayload(
                                payload_type="browser_html",
                                logical_id=writer_id,
                                body=html.encode("utf-8"),
                                content_type="text/html",
                                source_url=canonical_url,
                                canonical_url=canonical_url,
                                metadata=metadata,
                                extension=".html",
                            )
                        )
                        payloads.append(
                            RawPayload(
                                payload_type="browser_text",
                                logical_id=writer_id,
                                body=text.encode("utf-8"),
                                content_type="text/plain",
                                source_url=canonical_url,
                                canonical_url=canonical_url,
                                metadata=metadata,
                                extension=".txt",
                            )
                        )
                        emitted += 1
                        if options.limit is not None and emitted >= options.limit:
                            break
                        time.sleep(2)
            finally:
                context.close()
                browser.close()
        return payloads

    def normalize_raw_records(
        self,
        settings: HollywoodSettings,
        storage: HollywoodStorage,
        run_id: str,
        raw_records: list[dict[str, object]],
    ) -> NormalizedBundle:
        bundle = NormalizedBundle()
        for record in raw_records:
            if str(record["payload_type"]) != "browser_text":
                continue
            path = Path(str(record["content_path"]))
            metadata = json.loads(str(record["metadata_json"]))
            text = path.read_text(encoding="utf-8", errors="replace")
            writer_name = metadata.get("writer_name", "Unknown Writer")
            writer_id = metadata.get(
                "writer_id", writer_key(str(record["canonical_url"] or record["source_url"]))
            )
            entity_id = make_stable_id("wga", EntityKind.PERSON.value, str(writer_id))
            bundle.entities.append(
                EntityRow(
                    entity_id=entity_id,
                    source_id=self.source.source_id,
                    external_id=str(writer_id),
                    entity_type=EntityKind.PERSON.value,
                    name=str(writer_name),
                    canonical_name=str(writer_name).casefold(),
                    license_class=self.source.license_class.value,
                    metadata_json=json_dumps(
                        {
                            "profile_url": metadata.get("profile_url"),
                            "raw_record_id": record["id"],
                        }
                    ),
                )
            )
            bundle.entity_aliases.append(
                EntityAliasRow(
                    entity_alias_id=make_stable_id(entity_id, str(writer_name)),
                    entity_id=entity_id,
                    source_id=self.source.source_id,
                    alias=str(writer_name),
                )
            )
            bundle.credits.extend(_parse_wga_credits(text, entity_id))
        return bundle
