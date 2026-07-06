from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
from urllib.parse import parse_qsl, urlsplit, urlunsplit

from pydantic import BaseModel, Field

TRACKING_QUERY_KEYS = {
    "fbclid",
    "gclid",
    "mc_cid",
    "mc_eid",
    "ref",
    "source",
    "utm_campaign",
    "utm_content",
    "utm_medium",
    "utm_source",
    "utm_term",
}


def make_stable_id(*parts: str) -> str:
    joined = "::".join(part.strip() for part in parts if part)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()[:24]


def canonicalize_url(url: str) -> str:
    split = urlsplit(url.strip())
    query_items = [
        (key, value)
        for key, value in parse_qsl(split.query, keep_blank_values=True)
        if key.lower() not in TRACKING_QUERY_KEYS
    ]
    path = split.path.rstrip("/") or "/"
    return urlunsplit(
        (
            split.scheme.lower(),
            split.netloc.lower(),
            path,
            "&".join(f"{k}={v}" for k, v in query_items),
            "",
        )
    )


def normalize_whitespace(text: str) -> str:
    return " ".join(text.split())


class SourceKind(StrEnum):
    RSS = "rss"
    API = "api"
    DATASET = "dataset"
    BROWSER = "browser"


class LicenseClass(StrEnum):
    RESEARCH_NON_COMMERCIAL = "research_non_commercial"
    WEB_COPYRIGHT = "web_copyright"
    API_TERMS = "api_terms"
    PUBLIC_KNOWLEDGE = "public_knowledge"


class EntityKind(StrEnum):
    PERSON = "person"
    TITLE = "title"
    COMPANY = "company"
    ORGANIZATION = "organization"
    AWARD = "award"


class RunStatus(StrEnum):
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class SourceDefinition(BaseModel):
    source_id: str
    name: str
    kind: SourceKind
    description: str
    groups: tuple[str, ...]
    default_urls: tuple[str, ...] = ()
    license_class: LicenseClass
    archive_modes: tuple[str, ...]
    fetch_strategy: str
    rate_limit_per_minute: int | None = None
    api_key_env: str | None = None
    default_full_text: bool = True
    metadata: dict[str, Any] = Field(default_factory=dict)


class IngestOptions(BaseModel):
    limit: int | None = None
    since: datetime | None = None
    full_text: bool = True
    prefixes: list[str] | None = None


class RawPayload(BaseModel):
    payload_type: str
    logical_id: str
    body: bytes
    content_type: str
    source_url: str | None = None
    canonical_url: str | None = None
    fetched_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = Field(default_factory=dict)
    extension: str | None = None


class ArchivedPayload(BaseModel):
    raw_record_id: str
    source_id: str
    source_kind: str
    payload_type: str
    logical_id: str
    content_path: str
    content_hash: str
    content_type: str
    source_url: str | None = None
    canonical_url: str | None = None
    fetched_at: datetime
    metadata_json: str


class ArticleRow(BaseModel):
    article_id: str
    source_id: str
    canonical_url: str
    url: str
    title: str
    author: str | None = None
    published_at: datetime | None = None
    summary: str | None = None
    feed_guid: str | None = None
    license_class: str
    run_id: str
    metadata_json: str = "{}"


class ArticleContentRow(BaseModel):
    content_id: str
    article_id: str
    source_id: str
    content_kind: str
    text: str
    raw_record_id: str
    content_hash: str
    license_class: str
    metadata_json: str = "{}"


class EntityRow(BaseModel):
    entity_id: str
    source_id: str
    external_id: str | None = None
    entity_type: str
    name: str
    canonical_name: str
    license_class: str
    metadata_json: str = "{}"


class EntityAliasRow(BaseModel):
    entity_alias_id: str
    entity_id: str
    source_id: str
    alias: str
    metadata_json: str = "{}"
    created_at: str = ""


class ArticleEntityRow(BaseModel):
    article_entity_id: str
    article_id: str
    entity_id: str
    source_id: str
    relation: str
    metadata_json: str = "{}"


class CreditRow(BaseModel):
    credit_id: str
    source_id: str
    person_entity_id: str | None = None
    title_entity_id: str | None = None
    person_name: str | None = None
    title_name: str | None = None
    title_external_id: str | None = None
    role: str
    billing: int | None = None
    metadata_json: str = "{}"


class NormalizedBundle(BaseModel):
    articles: list[ArticleRow] = Field(default_factory=list)
    article_content: list[ArticleContentRow] = Field(default_factory=list)
    entities: list[EntityRow] = Field(default_factory=list)
    entity_aliases: list[EntityAliasRow] = Field(default_factory=list)
    article_entities: list[ArticleEntityRow] = Field(default_factory=list)
    credits: list[CreditRow] = Field(default_factory=list)

    def extend(self, other: NormalizedBundle) -> None:
        self.articles.extend(other.articles)
        self.article_content.extend(other.article_content)
        self.entities.extend(other.entities)
        self.entity_aliases.extend(other.entity_aliases)
        self.article_entities.extend(other.article_entities)
        self.credits.extend(other.credits)

    def counts(self) -> dict[str, int]:
        return {
            "articles": len(self.articles),
            "article_content": len(self.article_content),
            "entities": len(self.entities),
            "entity_aliases": len(self.entity_aliases),
            "article_entities": len(self.article_entities),
            "credits": len(self.credits),
        }


class RunSummary(BaseModel):
    run_id: str
    source_id: str
    status: RunStatus
    raw_records: int
    normalized: dict[str, int]


class DoctorCheck(BaseModel):
    name: str
    ok: bool
    detail: str


def json_dumps(data: dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, sort_keys=True)
