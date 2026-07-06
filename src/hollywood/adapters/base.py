from __future__ import annotations

from abc import ABC, abstractmethod

from ..config import HollywoodSettings
from ..models import DoctorCheck, IngestOptions, NormalizedBundle, RawPayload, SourceDefinition
from ..storage import HollywoodStorage


class BaseAdapter(ABC):
    def __init__(self, source: SourceDefinition):
        self.source = source

    @abstractmethod
    def fetch_raw_payloads(
        self, settings: HollywoodSettings, options: IngestOptions
    ) -> list[RawPayload]:
        raise NotImplementedError

    @abstractmethod
    def normalize_raw_records(
        self,
        settings: HollywoodSettings,
        storage: HollywoodStorage,
        run_id: str,
        raw_records: list[dict[str, object]],
    ) -> NormalizedBundle:
        raise NotImplementedError

    def doctor_checks(self, settings: HollywoodSettings) -> list[DoctorCheck]:
        return [
            DoctorCheck(
                name=f"{self.source.source_id}:config",
                ok=True,
                detail=f"Configured fetch strategy: {self.source.fetch_strategy}",
            )
        ]
