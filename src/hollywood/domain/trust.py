"""Trust framework for provenance and confidence tracking.

Three-tier model (ported from kuma):
- machine_extracted — raw LLM output, not yet reviewed
- reviewed — human has verified the extraction against source
- canonical — verified and marked as the single source of truth
"""

from __future__ import annotations

from enum import StrEnum


class TrustState(StrEnum):
    MACHINE_EXTRACTED = "machine_extracted"
    REVIEWED = "reviewed"
    CANONICAL = "canonical"


class SourceFact:
    """Records a single verified fact with its provenance.

    Each fact is linked to an entity via entity_id and to the extraction
    run that produced it via extraction_result_id.
    """

    source_id: str
    entity_id: str | None
    fact_type: str
    fact_value: str
    raw_json: str
    trust_state: TrustState
    extraction_result_id: str | None

    def __init__(
        self,
        source_id: str,
        fact_type: str,
        fact_value: str,
        raw_json: str,
        entity_id: str | None = None,
        trust_state: TrustState = TrustState.MACHINE_EXTRACTED,
        extraction_result_id: str | None = None,
    ) -> None:
        self.source_id = source_id
        self.entity_id = entity_id
        self.fact_type = fact_type
        self.fact_value = fact_value
        self.raw_json = raw_json
        self.trust_state = trust_state
        self.extraction_result_id = extraction_result_id
