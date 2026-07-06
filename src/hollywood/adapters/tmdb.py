from __future__ import annotations

import json
from pathlib import Path

import httpx

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
    json_dumps,
    make_stable_id,
)
from ..storage import HollywoodStorage
from .base import BaseAdapter


class TmdbAdapter(BaseAdapter):
    def __init__(self, source: SourceDefinition):
        super().__init__(source)

    def _client(self, settings: HollywoodSettings) -> httpx.Client:
        if not settings.tmdb_api_key:
            raise RuntimeError("TMDB_API_KEY is required for the tmdb source.")
        return httpx.Client(
            base_url="https://api.themoviedb.org/3",
            params={"api_key": settings.tmdb_api_key},
            headers={"User-Agent": settings.user_agent},
            timeout=settings.request_timeout_seconds,
            follow_redirects=True,
        )

    def fetch_raw_payloads(
        self, settings: HollywoodSettings, options: IngestOptions
    ) -> list[RawPayload]:
        payloads: list[RawPayload] = []
        limit = options.limit or 5
        with self._client(settings) as client:
            trending = client.get("/trending/all/day").json()
            items = trending.get("results", [])[:limit]
            payloads.append(
                RawPayload(
                    payload_type="api_json",
                    logical_id="trending_all_day",
                    body=json.dumps(trending, ensure_ascii=False).encode("utf-8"),
                    content_type="application/json",
                    source_url="https://api.themoviedb.org/3/trending/all/day",
                    metadata={"endpoint": "/trending/all/day"},
                    extension=".json",
                )
            )
            for item in items:
                media_type = item.get("media_type")
                item_id = item.get("id")
                if media_type not in {"movie", "tv", "person"} or item_id is None:
                    continue
                if media_type == "person":
                    endpoint = f"/person/{item_id}"
                    detail = client.get(
                        endpoint, params={"append_to_response": "external_ids"}
                    ).json()
                else:
                    endpoint = f"/{media_type}/{item_id}"
                    detail = client.get(
                        endpoint, params={"append_to_response": "credits,external_ids"}
                    ).json()
                detail["media_type"] = media_type
                payloads.append(
                    RawPayload(
                        payload_type="api_json",
                        logical_id=f"{media_type}-{item_id}",
                        body=json.dumps(detail, ensure_ascii=False).encode("utf-8"),
                        content_type="application/json",
                        source_url=f"https://api.themoviedb.org/3{endpoint}",
                        metadata={"endpoint": endpoint, "media_type": media_type},
                        extension=".json",
                    )
                )
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
            if str(record["payload_type"]) != "api_json":
                continue
            metadata = json.loads(str(record["metadata_json"]))
            if metadata.get("endpoint") == "/trending/all/day":
                continue
            document = json.loads(Path(str(record["content_path"])).read_text(encoding="utf-8"))
            media_type = metadata.get("media_type", document.get("media_type"))
            if media_type == "person":
                person_id = str(document["id"])
                name = str(document.get("name") or person_id)
                entity_id = make_stable_id("tmdb", "person", person_id)
                bundle.entities.append(
                    EntityRow(
                        entity_id=entity_id,
                        source_id=self.source.source_id,
                        external_id=person_id,
                        entity_type=EntityKind.PERSON.value,
                        name=name,
                        canonical_name=name.casefold(),
                        license_class=self.source.license_class.value,
                        metadata_json=json_dumps(
                            {
                                "known_for_department": document.get("known_for_department"),
                                "external_ids": document.get("external_ids", {}),
                            }
                        ),
                    )
                )
                for alias in document.get("also_known_as", [])[:5]:
                    if alias:
                        bundle.entity_aliases.append(
                            EntityAliasRow(
                                entity_alias_id=make_stable_id(entity_id, str(alias)),
                                entity_id=entity_id,
                                source_id=self.source.source_id,
                                alias=str(alias),
                            )
                        )
            elif media_type in {"movie", "tv"}:
                title_id = str(document["id"])
                title_name = str(document.get("title") or document.get("name") or title_id)
                title_entity_id = make_stable_id("tmdb", media_type, title_id)
                bundle.entities.append(
                    EntityRow(
                        entity_id=title_entity_id,
                        source_id=self.source.source_id,
                        external_id=title_id,
                        entity_type=EntityKind.TITLE.value,
                        name=title_name,
                        canonical_name=title_name.casefold(),
                        license_class=self.source.license_class.value,
                        metadata_json=json_dumps(
                            {
                                "media_type": media_type,
                                "external_ids": document.get("external_ids", {}),
                            }
                        ),
                    )
                )
                credits = document.get("credits", {})
                for cast_member in credits.get("cast", [])[:20]:
                    person_name = cast_member.get("name")
                    person_id = cast_member.get("id")
                    if not person_name or person_id is None:
                        continue
                    person_entity_id = make_stable_id("tmdb", "person", str(person_id))
                    bundle.entities.append(
                        EntityRow(
                            entity_id=person_entity_id,
                            source_id=self.source.source_id,
                            external_id=str(person_id),
                            entity_type=EntityKind.PERSON.value,
                            name=str(person_name),
                            canonical_name=str(person_name).casefold(),
                            license_class=self.source.license_class.value,
                            metadata_json=json_dumps(
                                {"known_for_department": cast_member.get("known_for_department")}
                            ),
                        )
                    )
                    bundle.credits.append(
                        CreditRow(
                            credit_id=make_stable_id(
                                "tmdb",
                                title_id,
                                str(person_id),
                                str(cast_member.get("credit_id", "")),
                            ),
                            source_id=self.source.source_id,
                            person_entity_id=person_entity_id,
                            person_name=str(person_name),
                            title_name=title_name,
                            title_external_id=title_id,
                            role=str(cast_member.get("character") or "cast"),
                            billing=int(cast_member.get("order"))
                            if cast_member.get("order") is not None
                            else None,
                            metadata_json=json_dumps({"credit_type": "cast"}),
                        )
                    )
                for crew_member in credits.get("crew", [])[:20]:
                    person_name = crew_member.get("name")
                    person_id = crew_member.get("id")
                    if not person_name or person_id is None:
                        continue
                    person_entity_id = make_stable_id("tmdb", "person", str(person_id))
                    bundle.entities.append(
                        EntityRow(
                            entity_id=person_entity_id,
                            source_id=self.source.source_id,
                            external_id=str(person_id),
                            entity_type=EntityKind.PERSON.value,
                            name=str(person_name),
                            canonical_name=str(person_name).casefold(),
                            license_class=self.source.license_class.value,
                            metadata_json=json_dumps({"department": crew_member.get("department")}),
                        )
                    )
                    bundle.credits.append(
                        CreditRow(
                            credit_id=make_stable_id(
                                "tmdb",
                                title_id,
                                str(person_id),
                                str(crew_member.get("credit_id", "")),
                            ),
                            source_id=self.source.source_id,
                            person_entity_id=person_entity_id,
                            person_name=str(person_name),
                            title_name=title_name,
                            title_external_id=title_id,
                            role=str(
                                crew_member.get("job") or crew_member.get("department") or "crew"
                            ),
                            billing=None,
                            metadata_json=json_dumps({"credit_type": "crew"}),
                        )
                    )
        return bundle
