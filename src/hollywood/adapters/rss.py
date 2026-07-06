from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import feedparser
import httpx
from dateutil import parser as date_parser

from ..config import HollywoodSettings
from ..extractors import extract_text_from_html, strip_html_fragment
from ..models import (
    ArticleBodyRow,
    ArticleEntityRow,
    ArticleRow,
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
    normalize_whitespace,
)
from ..storage import HollywoodStorage
from .base import BaseAdapter


def _entry_value(entry: dict[str, Any], key: str, default: str = "") -> str:
    value = entry.get(key, default)
    if isinstance(value, str):
        return value
    return default


class RssAdapter(BaseAdapter):
    def __init__(self, source: SourceDefinition):
        super().__init__(source)

    def fetch_raw_payloads(
        self, settings: HollywoodSettings, options: IngestOptions
    ) -> list[RawPayload]:
        headers = {"User-Agent": settings.user_agent}
        timeout = settings.request_timeout_seconds
        payloads: list[RawPayload] = []
        remaining = options.limit
        with httpx.Client(headers=headers, timeout=timeout, follow_redirects=True) as client:
            for feed_url in self.source.default_urls:
                response = client.get(feed_url)
                response.raise_for_status()
                parsed = feedparser.parse(response.content)
                entries = list(parsed.entries)
                if options.since is not None:
                    filtered = []
                    for entry in entries:
                        published = _entry_value(entry, "published") or _entry_value(
                            entry, "updated"
                        )
                        if not published:
                            filtered.append(entry)
                            continue
                        published_at = date_parser.parse(published)
                        if published_at >= options.since:
                            filtered.append(entry)
                    entries = filtered
                if remaining is not None:
                    selected_entries = entries[:remaining]
                    remaining -= len(selected_entries)
                else:
                    selected_entries = entries

                selected_urls = [
                    canonicalize_url(_entry_value(entry, "link"))
                    for entry in selected_entries
                    if _entry_value(entry, "link")
                ]
                payloads.append(
                    RawPayload(
                        payload_type="feed_xml",
                        logical_id=feed_url,
                        body=response.content,
                        content_type=response.headers.get("content-type", "application/rss+xml"),
                        source_url=feed_url,
                        metadata={
                            "feed_url": feed_url,
                            "selected_urls": selected_urls,
                        },
                        extension=".xml",
                    )
                )

                if options.full_text:
                    for entry in selected_entries:
                        link = _entry_value(entry, "link")
                        if not link:
                            continue
                        article_response = client.get(link)
                        article_response.raise_for_status()
                        canonical_url = canonicalize_url(str(article_response.url))
                        payloads.append(
                            RawPayload(
                                payload_type="article_html",
                                logical_id=canonical_url,
                                body=article_response.content,
                                content_type=article_response.headers.get(
                                    "content-type", "text/html"
                                ),
                                source_url=link,
                                canonical_url=canonical_url,
                                metadata={
                                    "feed_url": feed_url,
                                    "title": _entry_value(entry, "title"),
                                },
                                extension=".html",
                            )
                        )

                if remaining is not None and remaining <= 0:
                    break
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
            payload_type = str(record["payload_type"])
            path = Path(str(record["content_path"]))
            metadata = json.loads(str(record["metadata_json"]))
            if payload_type == "feed_xml":
                parsed = feedparser.parse(path.read_bytes())
                selected_urls = set(metadata.get("selected_urls", []))
                for entry in parsed.entries:
                    link = _entry_value(entry, "link")
                    if not link:
                        continue
                    canonical_url = canonicalize_url(link)
                    if selected_urls and canonical_url not in selected_urls:
                        continue
                    article_id = make_stable_id(self.source.source_id, canonical_url)
                    published_raw = _entry_value(entry, "published") or _entry_value(
                        entry, "updated"
                    )
                    published_at = date_parser.parse(published_raw) if published_raw else None
                    author = (
                        _entry_value(entry, "author") or _entry_value(entry, "dc_creator") or None
                    )
                    categories = [tag.get("term", "") for tag in entry.get("tags", [])]
                    article = ArticleRow(
                        article_id=article_id,
                        source_id=self.source.source_id,
                        canonical_url=canonical_url,
                        url=link,
                        title=normalize_whitespace(_entry_value(entry, "title")),
                        author=author,
                        published_at=published_at,
                        summary=strip_html_fragment(_entry_value(entry, "summary")),
                        feed_guid=_entry_value(entry, "id") or canonical_url,
                        license_class=self.source.license_class.value,
                        run_id=run_id,
                        metadata_json=json_dumps(
                            {"feed_url": metadata.get("feed_url"), "categories": categories}
                        ),
                    )
                    bundle.articles.append(article)

                    description_text = strip_html_fragment(_entry_value(entry, "summary"))
                    if description_text:
                        bundle.article_bodies.append(
                            ArticleBodyRow(
                                body_id=make_stable_id(article_id, "feed_description"),
                                article_id=article_id,
                                source_id=self.source.source_id,
                                body_kind="feed_description",
                                text=description_text,
                                raw_record_id=str(record["raw_record_id"]),
                                content_hash=str(record["content_hash"]),
                                license_class=self.source.license_class.value,
                            )
                        )

                    content_items = entry.get("content", [])
                    if content_items:
                        encoded_text = strip_html_fragment(str(content_items[0].get("value", "")))
                        if encoded_text:
                            bundle.article_bodies.append(
                                ArticleBodyRow(
                                    body_id=make_stable_id(article_id, "feed_content"),
                                    article_id=article_id,
                                    source_id=self.source.source_id,
                                    body_kind="feed_content",
                                    text=encoded_text,
                                    raw_record_id=str(record["raw_record_id"]),
                                    content_hash=str(record["content_hash"]),
                                    license_class=self.source.license_class.value,
                                )
                            )

                    if author:
                        entity_id = make_stable_id(
                            self.source.source_id, EntityKind.PERSON.value, author.lower()
                        )
                        bundle.entities.append(
                            EntityRow(
                                entity_id=entity_id,
                                source_id=self.source.source_id,
                                external_id=None,
                                entity_type=EntityKind.PERSON.value,
                                name=author,
                                canonical_name=author.casefold(),
                                license_class=self.source.license_class.value,
                                metadata_json=json_dumps({"role": "author"}),
                            )
                        )
                        bundle.entity_aliases.append(
                            EntityAliasRow(
                                entity_alias_id=make_stable_id(entity_id, author),
                                entity_id=entity_id,
                                source_id=self.source.source_id,
                                alias=author,
                            )
                        )
                        bundle.article_entities.append(
                            ArticleEntityRow(
                                article_entity_id=make_stable_id(article_id, entity_id, "author"),
                                article_id=article_id,
                                entity_id=entity_id,
                                source_id=self.source.source_id,
                                relation="author",
                            )
                        )
            elif payload_type == "article_html":
                article_url = str(record["canonical_url"] or record["source_url"])
                article_id = make_stable_id(self.source.source_id, canonicalize_url(article_url))
                extracted = extract_text_from_html(
                    path.read_text(encoding="utf-8", errors="replace")
                )
                if extracted:
                    bundle.article_bodies.append(
                        ArticleBodyRow(
                            body_id=make_stable_id(article_id, "page_extract"),
                            article_id=article_id,
                            source_id=self.source.source_id,
                            body_kind="page_extract",
                            text=extracted,
                            raw_record_id=str(record["raw_record_id"]),
                            content_hash=str(record["content_hash"]),
                            license_class=self.source.license_class.value,
                            metadata_json=json_dumps({"source_url": record["source_url"]}),
                        )
                    )
        return bundle
