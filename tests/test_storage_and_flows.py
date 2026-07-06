from __future__ import annotations

from pathlib import Path

from prefect.testing.utilities import prefect_test_harness

from hollywood.adapters.base import BaseAdapter
from hollywood.config import HollywoodSettings
from hollywood.flows import ingest_source_flow, normalize_flow
from hollywood.models import (
    EntityKind,
    EntityRow,
    IngestOptions,
    LicenseClass,
    NormalizedBundle,
    RawPayload,
    SourceDefinition,
    SourceKind,
    make_stable_id,
)
from hollywood.storage import HollywoodStorage


class FakeAdapter(BaseAdapter):
    def fetch_raw_payloads(
        self, settings: HollywoodSettings, options: IngestOptions
    ) -> list[RawPayload]:
        return [
            RawPayload(
                payload_type="api_json",
                logical_id="fake-1",
                body=b'{"message":"hello"}',
                content_type="application/json",
                source_url="https://example.com/fake-1",
                metadata={"message": "hello"},
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
        entity = EntityRow(
            entity_id=make_stable_id("fake", "entity"),
            source_id=self.source.source_id,
            external_id="fake-entity",
            entity_type=EntityKind.PERSON.value,
            name="Fake Entity",
            canonical_name="fake entity",
            license_class=self.source.license_class.value,
        )
        return NormalizedBundle(entities=[entity])


def test_storage_export_round_trip(tmp_path: Path) -> None:
    settings = HollywoodSettings(
        data_dir=tmp_path / "data", db_path=tmp_path / "data" / "hollywood.duckdb"
    )
    storage = HollywoodStorage(settings.db_path)
    storage.initialize()
    storage.export_all(settings.parquet_dir, "parquet")
    assert (settings.parquet_dir / "entities.parquet").exists()


def test_flow_ingest_and_normalize_are_idempotent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    fake_source = SourceDefinition(
        source_id="fake",
        name="Fake Source",
        kind=SourceKind.API,
        description="Fixture source",
        groups=("all",),
        license_class=LicenseClass.PUBLIC_KNOWLEDGE,
        archive_modes=("api_json",),
        fetch_strategy="fixture",
    )
    settings = HollywoodSettings(
        data_dir=tmp_path / "data", db_path=tmp_path / "data" / "hollywood.duckdb"
    )
    options = IngestOptions(limit=1, full_text=False)

    monkeypatch.setattr("hollywood.flows.get_source", lambda source_id: fake_source)
    monkeypatch.setattr("hollywood.flows.get_adapter", lambda source: FakeAdapter(source))

    with prefect_test_harness():
        summary = ingest_source_flow("fake", settings, options)
        counts = normalize_flow("fake", settings)

    assert summary.raw_records == 1

    storage = HollywoodStorage(settings.db_path)
    assert storage.table_count("entities") == 1
    assert counts["entities"] == 1
    assert storage.table_count("entities") == 1
