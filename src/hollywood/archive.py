from __future__ import annotations

import hashlib
import re
from datetime import UTC

from .config import HollywoodSettings
from .models import ArchivedPayload, RawPayload, SourceDefinition, json_dumps, make_stable_id

SAFE_NAME_RE = re.compile(r"[^a-zA-Z0-9._-]+")


def _safe_name(value: str) -> str:
    cleaned = SAFE_NAME_RE.sub("-", value.strip())
    return cleaned.strip("-") or "payload"


def _extension(payload: RawPayload) -> str:
    if payload.extension:
        return payload.extension
    if payload.payload_type.endswith("xml"):
        return ".xml"
    if payload.payload_type.endswith("html"):
        return ".html"
    if payload.payload_type.endswith("text"):
        return ".txt"
    if payload.payload_type.endswith("json"):
        return ".json"
    if payload.payload_type.endswith("tsv"):
        return ".tsv"
    return ".bin"


def archive_payload(
    settings: HollywoodSettings,
    source: SourceDefinition,
    payload: RawPayload,
) -> ArchivedPayload:
    settings.ensure_directories()
    fetched = payload.fetched_at.astimezone(UTC)
    day_dir = settings.raw_dir / source.source_id / fetched.strftime("%Y/%m/%d")
    day_dir.mkdir(parents=True, exist_ok=True)

    content_hash = hashlib.sha256(payload.body).hexdigest()
    filename = (
        f"{fetched.strftime('%H%M%S')}_{_safe_name(payload.logical_id)[:80]}{_extension(payload)}"
    )
    path = day_dir / filename
    if not path.exists():
        path.write_bytes(payload.body)

    raw_record_id = make_stable_id(
        source.source_id, payload.payload_type, payload.logical_id, content_hash
    )
    return ArchivedPayload(
        raw_record_id=raw_record_id,
        source_id=source.source_id,
        source_kind=source.kind.value,
        payload_type=payload.payload_type,
        logical_id=payload.logical_id,
        content_path=str(path),
        content_hash=content_hash,
        content_type=payload.content_type,
        source_url=payload.source_url,
        canonical_url=payload.canonical_url,
        fetched_at=payload.fetched_at,
        metadata_json=json_dumps(payload.metadata),
    )
