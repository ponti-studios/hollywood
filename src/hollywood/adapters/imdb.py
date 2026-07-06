from __future__ import annotations

import csv
import io
import json
import urllib.request
from pathlib import Path

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


class ImdbAdapter(BaseAdapter):
    def __init__(self, source: SourceDefinition):
        super().__init__(source)

    def fetch_raw_payloads(
        self, settings: HollywoodSettings, options: IngestOptions
    ) -> list[RawPayload]:
        payloads: list[RawPayload] = []
        row_limit = options.limit
        for url in self.source.default_urls:
            dataset_name = url.rsplit("/", 1)[-1].replace(".tsv.gz", "")
            rows: list[str] = []
            request = urllib.request.Request(url, headers={"User-Agent": settings.user_agent})
            with urllib.request.urlopen(
                request, timeout=settings.request_timeout_seconds
            ) as response:
                import gzip

                with gzip.GzipFile(fileobj=response) as gz_file:
                    for index, line in enumerate(io.TextIOWrapper(gz_file, encoding="utf-8")):
                        rows.append(line.rstrip("\n"))
                        if row_limit is not None and index >= row_limit:
                            break
            body = ("\n".join(rows) + "\n").encode("utf-8")
            payloads.append(
                RawPayload(
                    payload_type="dataset_tsv",
                    logical_id=dataset_name,
                    body=body,
                    content_type="text/tab-separated-values",
                    source_url=url,
                    metadata={"dataset_name": dataset_name},
                    extension=".tsv",
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
        seen_entities: set[str] = set()
        for record in raw_records:
            if str(record["payload_type"]) != "dataset_tsv":
                continue
            path = Path(str(record["content_path"]))
            metadata = json.loads(str(record["metadata_json"]))
            dataset_name = metadata["dataset_name"]
            frame_rows = list(csv.DictReader(path.read_text(encoding="utf-8").splitlines(), delimiter="\t"))
            if dataset_name == "name.basics":
                for row in frame_rows:
                    name = row.get("primaryName")
                    nconst = row.get("nconst")
                    if not name or not nconst or nconst == r"\N":
                        continue
                    entity_id = make_stable_id("imdb", str(nconst))
                    if entity_id not in seen_entities:
                        seen_entities.add(entity_id)
                        bundle.entities.append(
                            EntityRow(
                                entity_id=entity_id,
                                source_id=self.source.source_id,
                                external_id=str(nconst),
                                entity_type=EntityKind.PERSON.value,
                                name=str(name),
                                canonical_name=str(name).casefold(),
                                license_class=self.source.license_class.value,
                                metadata_json=json_dumps(
                                    {
                                        "birthYear": row.get("birthYear"),
                                        "deathYear": row.get("deathYear"),
                                        "primaryProfession": row.get("primaryProfession"),
                                        "knownForTitles": row.get("knownForTitles"),
                                    }
                                ),
                            )
                        )
                    bundle.entity_aliases.append(
                        EntityAliasRow(
                            entity_alias_id=make_stable_id(entity_id, str(name)),
                            entity_id=entity_id,
                            source_id=self.source.source_id,
                            alias=str(name),
                        )
                    )
            elif dataset_name == "title.basics":
                for row in frame_rows:
                    title = row.get("primaryTitle")
                    tconst = row.get("tconst")
                    if not title or not tconst or tconst == r"\N":
                        continue
                    entity_id = make_stable_id("imdb", str(tconst))
                    if entity_id not in seen_entities:
                        seen_entities.add(entity_id)
                        bundle.entities.append(
                            EntityRow(
                                entity_id=entity_id,
                                source_id=self.source.source_id,
                                external_id=str(tconst),
                                entity_type=EntityKind.TITLE.value,
                                name=str(title),
                                canonical_name=str(title).casefold(),
                                license_class=self.source.license_class.value,
                                metadata_json=json_dumps(
                                    {
                                        "titleType": row.get("titleType"),
                                        "originalTitle": row.get("originalTitle"),
                                        "startYear": row.get("startYear"),
                                        "genres": row.get("genres"),
                                    }
                                ),
                            )
                        )
            elif dataset_name == "title.principals":
                for row in frame_rows:
                    tconst = row.get("tconst")
                    nconst = row.get("nconst")
                    role = row.get("category")
                    ordering = row.get("ordering")
                    if not tconst or not nconst or not role or tconst == r"\N" or nconst == r"\N":
                        continue
                    person_eid = make_stable_id("imdb", str(nconst))
                    title_eid = make_stable_id("imdb", str(tconst))
                    # Create stub entities for FK references that don't exist yet
                    for eid, ename, etype in [
                        (person_eid, str(nconst), EntityKind.PERSON),
                        (title_eid, str(tconst), EntityKind.TITLE),
                    ]:
                        if eid not in seen_entities:
                            seen_entities.add(eid)
                            bundle.entities.append(
                                EntityRow(
                                    entity_id=eid,
                                    source_id=self.source.source_id,
                                    external_id=ename,
                                    entity_type=etype.value,
                                    name=ename,
                                    canonical_name=ename.casefold(),
                                    license_class=self.source.license_class.value,
                                    metadata_json=json_dumps({"stub": True}),
                                )
                            )
                    bundle.credits.append(
                        CreditRow(
                            credit_id=make_stable_id(
                                "imdb",
                                str(tconst),
                                str(nconst),
                                str(role),
                                str(row.get("ordering")),
                            ),
                            source_id=self.source.source_id,
                            person_entity_id=person_eid,
                            title_entity_id=title_eid,
                            person_name=None,
                            title_name=None,
                            title_external_id=str(tconst),
                            role=str(role),
                            billing=int(ordering) if ordering is not None else None,
                            metadata_json=json_dumps(
                                {"job": row.get("job"), "characters": row.get("characters")}
                            ),
                        )
                    )
        return bundle
