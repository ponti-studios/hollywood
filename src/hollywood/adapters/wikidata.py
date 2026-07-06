from __future__ import annotations

import json
from pathlib import Path

import httpx

from ..config import HollywoodSettings
from ..models import (
    EntityAliasRow,
    EntityKind,
    EntityRow,
    IngestOptions,
    NormalizedBundle,
    RawPayload,
    SourceDefinition,
    json_dumps,
    make_stable_id,
)
from ..storage import HollywoodStorage
from .base import BaseAdapter

WIKIDATA_QUERY = """
SELECT ?item ?itemLabel ?occupationLabel ?imdb WHERE {
  VALUES ?occupation { wd:Q33999 wd:Q2526255 wd:Q28389 }
  ?item wdt:P31 wd:Q5;
        wdt:P106 ?occupation.
  OPTIONAL { ?item wdt:P345 ?imdb. }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
LIMIT {limit}
"""


class WikidataAdapter(BaseAdapter):
    def __init__(self, source: SourceDefinition):
        super().__init__(source)

    def fetch_raw_payloads(
        self, settings: HollywoodSettings, options: IngestOptions
    ) -> list[RawPayload]:
        limit = options.limit or 25
        query = WIKIDATA_QUERY.format(limit=limit)
        response = httpx.get(
            self.source.default_urls[0],
            params={"query": query, "format": "json"},
            headers={
                "Accept": "application/sparql-results+json",
                "User-Agent": settings.user_agent,
            },
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
        )
        response.raise_for_status()
        return [
            RawPayload(
                payload_type="api_json",
                logical_id=f"wikidata-{limit}",
                body=response.content,
                content_type=response.headers.get("content-type", "application/json"),
                source_url=str(response.url),
                metadata={"query": query, "limit": limit},
                extension=".json",
            )
        ]

    def normalize_raw_records(
        self,
        settings: HollywoodSettings,
        storage: HollywoodStorage,
        run_id: str,
        raw_records: list[dict[str, object]],
    ) -> NormalizedBundle:
        bundle = NormalizedBundle()
        for record in raw_records:
            if str(record["payload_type"]) != "api_json":
                continue
            document = json.loads(Path(str(record["content_path"])).read_text(encoding="utf-8"))
            bindings = document.get("results", {}).get("bindings", [])
            for item in bindings:
                item_url = item.get("item", {}).get("value")
                label = item.get("itemLabel", {}).get("value")
                imdb_id = item.get("imdb", {}).get("value")
                occupation = item.get("occupationLabel", {}).get("value")
                if not item_url or not label:
                    continue
                qid = item_url.rsplit("/", 1)[-1]
                entity_id = make_stable_id("wikidata", qid)
                bundle.entities.append(
                    EntityRow(
                        entity_id=entity_id,
                        source_id=self.source.source_id,
                        external_id=qid,
                        entity_type=EntityKind.PERSON.value,
                        name=label,
                        canonical_name=label.casefold(),
                        license_class=self.source.license_class.value,
                        metadata_json=json_dumps({"occupation": occupation, "imdb_id": imdb_id}),
                    )
                )
                bundle.entity_aliases.append(
                    EntityAliasRow(
                        entity_alias_id=make_stable_id(entity_id, label),
                        entity_id=entity_id,
                        source_id=self.source.source_id,
                        alias=label,
                    )
                )
        return bundle
