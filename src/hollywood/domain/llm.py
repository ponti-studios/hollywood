"""LLM extraction client for SubmissionPacket — ported from kuma internal/llm."""

from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx
from dotenv import load_dotenv

from .extraction import (
    SCHEMA_VERSION_V1,
    PROMPT_VERSION_V1,
    Candidate,
    Credit,
    Link,
    Organization,
    SubmissionPacket,
)

load_dotenv()

# Matches company-like names in bios: "CBS Studios", "Warner Brothers Animation", etc.
_ORGANIZATION_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9&+.'’:-]*(?:\s+[A-Z][A-Za-z0-9&+.'’:-]*){0,4}\s"
    r"(?:Studios|Studio|TV|Television|Animation|Media|Productions|Entertainment|Network|Networks|Pictures|Films|Film|Labs|Lab))\b"
)

OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_MODEL = "openai/gpt-4o-mini"
MAX_TOKENS = 8000


class ExtractionError(Exception):
    """Raised when LLM extraction fails."""


class ExtractionResponse:
    raw_json: bytes
    packet: SubmissionPacket
    model_name: str

    def __init__(self, raw_json: bytes, packet: SubmissionPacket, model_name: str) -> None:
        self.raw_json = raw_json
        self.packet = packet
        self.model_name = model_name


def _get_api_key() -> str | None:
    return os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")


# ── System prompt ───────────────────────────────────────────────────────────

def _system_prompt(prompt_version: str) -> str:
    return f"""You extract structured submission data from writer/talent submission emails.

Return only data grounded in the provided text.
- Do not invent facts.
- If a scalar field is unknown, use null.
- If a list field has no supported values, return an empty array.
- Return one candidate object for each explicitly presented candidate.
- Do not include the email sender, recipients, forwarders, or other non-candidate people unless the body explicitly presents them as submission talent.
- Representatives are agents, managers, assistants, or publicists associated with the candidate.
- Credits should only include projects explicitly supported by the text.
- Organizations are a required entity index for each candidate, not a summary.
- Include companies, studios, networks, streamers, agencies, production companies, publishers, platforms, and similar groups explicitly tied to the candidate.
- For every non-null credits[].network value, add the same organization to organizations[] unless an equivalent organization is already present.
- Do not omit an organization from organizations[] just because it also appears in a credit's network field, the candidate bio, or parentheses after a production title.
- Also extract organizations from relationship phrases in the bio, including "sold development to", "developing with", "developed at", "staffed on", "currently on", "produced by", "with [company] producing", "for [company]", "streaming on", and parenthetical project sources like "(Peacock/Pacific Electric)".
- Preserve the most specific organization name given by the text. Do not shorten "CBS Studios" to "CBS", "Warner Brothers Animation" to "Warner Brothers", or "Paramount TV" to "Paramount".
- Use organization types like "network", "studio", "streamer", "agency", "production company", "publisher", "platform", or "company".
- Tags should be concise and relevant to the candidate's work.
- Avoid duplicate entries in every array.
- Correct obvious spelling mistakes in names or titles, but preserve intentional spellings and formatting.
- Expand common industry abbreviations in the bio when helpful, but keep original forms in other fields.
- Preserve the exact JSON schema and top-level shape.
- Ignore forwarding wrappers, sender signatures, email recipients, cc lines, and mailing metadata.
- Never treat the forwarder, original sender, recipient, executive, producer, or buyer as a candidate unless the text explicitly presents them as submission talent.
- Names appearing in From/To/Cc/Subject/header blocks are not candidates by default.
- In staffing submission emails, candidates are usually the people listed under sections like upper level, lower level, writer submission, client, candidate, or followed by a biography, credits, or attached sample mention.
- If the email says someone is submitting material for another person, the submitter is a representative, not a candidate.
- Prefer false negatives over false positives for candidate identity. Do not include a person unless the body presents them as being considered for the role or staffing opportunity.
- Before returning JSON, check each candidate: if any credit has a network, streamer, studio, platform, or company, organizations[] must contain that entity.
- Before returning JSON, check each candidate bio for explicitly named companies, studios, networks, streamers, platforms, agencies, publishers, and production companies. organizations[] must contain those entities when they are tied to the candidate's work, development, staffing, production, or representation.

Prompt version: {prompt_version}"""


# ── JSON Schema ─────────────────────────────────────────────────────────────

def _build_json_schema() -> dict[str, Any]:
    """Build the JSON schema for structured output — mirrors kuma's submissionPacketJSONSchema()."""

    def optional_string(description: str) -> dict[str, Any]:
        return {
            "anyOf": [
                {"type": "string", "description": description},
                {"type": "null"},
            ]
        }

    def optional_email(description: str) -> dict[str, Any]:
        return {
            "anyOf": [
                {"type": "string", "description": description, "format": "email"},
                {"type": "null"},
            ]
        }

    def optional_phone(description: str) -> dict[str, Any]:
        return {
            "anyOf": [
                {"type": "string", "description": description, "pattern": r"^\d{3}-\d{3}-\d{4}$"},
                {"type": "null"},
            ]
        }

    credit_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "role": {"type": "string", "description": "The candidate's role on the project. Use lowercase."},
            "type": {"type": "string", "enum": ["tv", "movie", "novel", "magazine", "podcast"], "description": "The type of project. Use lowercase."},
            "production": {"type": "string", "description": "The name of the production or project."},
            "network": optional_string("The network, streamer, studio, platform, publisher, or company associated with the project."),
        },
        "required": ["role", "type", "production", "network"],
    }

    organization_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string", "description": "The exact name of the organization."},
            "type": {"type": "string", "description": "The organization type: network, studio, streamer, agency, etc."},
        },
        "required": ["name", "type"],
    }

    associate_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string", "description": "The name of the associate."},
            "production": optional_string("The production the associate worked on with the candidate."),
        },
        "required": ["name", "production"],
    }

    link_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "url": {"type": "string", "description": "The full URL of the link."},
            "type": {"type": "string", "enum": ["IMDB", "Twitter", "Instagram", "Facebook", "LinkedIn", "Other"], "description": "The type of link."},
        },
        "required": ["url", "type"],
    }

    rep_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string", "description": "The full name of the representative."},
            "title": {"type": "string", "description": "The representative's job title. Use lowercase."},
            "organization": optional_string("The company or organization the representative is associated with."),
            "email": optional_email("The email address of the representative."),
            "phone_number": optional_phone("The phone number of the representative."),
        },
        "required": ["name", "title", "organization", "email", "phone_number"],
    }

    candidate_schema: dict[str, Any] = {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string", "description": "The full name of the candidate."},
            "bio": {"type": "string", "description": "A comprehensive summary of the candidate."},
            "email": optional_email("The candidate's email address."),
            "phone_number": optional_phone("The candidate's phone number."),
            "position": optional_string("The candidate's primary job title."),
            "tags": {"type": "array", "items": {"type": "string"}, "description": "4-5 concise tags."},
            "credits": {"type": "array", "items": credit_schema, "description": "Projects in the candidate's bio."},
            "organizations": {"type": "array", "items": organization_schema, "description": "Organizations tied to the candidate."},
            "associates": {"type": "array", "items": associate_schema, "description": "People who have worked with the candidate."},
            "links": {"type": "array", "items": link_schema, "description": "URLs for the candidate."},
            "representatives": {"type": "array", "items": rep_schema, "description": "Agents, managers, assistants, or publicists."},
        },
        "required": ["name", "bio", "email", "phone_number", "position", "tags", "credits", "organizations", "associates", "links", "representatives"],
    }

    return {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "schema_version": {"type": "string", "const": SCHEMA_VERSION_V1},
            "candidates": {"type": "array", "items": candidate_schema},
        },
        "required": ["schema_version", "candidates"],
    }


# ── OpenRouter client ───────────────────────────────────────────────────────

def _call_openrouter(
    text: str,
    prompt_version: str,
    model: str | None = None,
    api_key: str | None = None,
    base_url: str | None = None,
    http_client: httpx.Client | None = None,
) -> ExtractionResponse:
    api_key = api_key or _get_api_key()
    if not api_key:
        raise ExtractionError("OPENROUTER_API_KEY not set")

    model = model or DEFAULT_MODEL
    base_url = base_url or OPENROUTER_BASE_URL

    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": _system_prompt(prompt_version)},
            {"role": "user", "content": text},
        ],
        "response_format": {
            "type": "json_schema",
            "json_schema": {
                "name": "submission_packet",
                "strict": True,
                "schema": _build_json_schema(),
            },
        },
        "temperature": 0,
        "max_tokens": MAX_TOKENS,
    }

    client = http_client or httpx.Client(timeout=90)
    try:
        if http_client is None:
            client = httpx.Client(timeout=90)

        resp = client.post(
            f"{base_url}/chat/completions",
            json=body,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://hollywood.ponti.io",
                "X-Title": "Hollywood Extraction",
            },
        )
        resp.raise_for_status()
        data = resp.json()

        if "error" in data:
            raise ExtractionError(f"OpenRouter error: {data['error'].get('message', str(data['error']))}")

        choices = data.get("choices", [])
        if not choices:
            raise ExtractionError("OpenRouter returned no choices")

        content = choices[0]["message"]["content"]
        raw_json = content.encode("utf-8")

        parsed = json.loads(content)
        packet = SubmissionPacket.model_validate(parsed)
        packet = normalize_packet(packet)

        return ExtractionResponse(raw_json=raw_json, packet=packet, model_name=model)
    except json.JSONDecodeError as e:
        raise ExtractionError(f"Failed to parse LLM response as JSON: {e}") from e
    finally:
        if http_client is None:
            client.close()


# ── Normalization ───────────────────────────────────────────────────────────

def normalize_packet(packet: SubmissionPacket) -> SubmissionPacket:
    if not packet.schema_version.strip():
        packet.schema_version = SCHEMA_VERSION_V1
    packet.candidates = [normalize_candidate(c) for c in packet.candidates]
    return packet


def normalize_candidate(c: Candidate) -> Candidate:
    c.name = c.name.strip()
    c.bio = c.bio.strip()

    # Normalize credits
    for credit in c.credits:
        credit.role = credit.role.strip().lower()
        credit.type = credit.type.strip().lower()
        credit.production = credit.production.strip()
    c.credits = _dedupe_credits(c.credits)

    # Normalize organizations
    for org in c.organizations:
        org.name = org.name.strip()
        org.type = org.type.strip()
    c.organizations += _organizations_from_credits(c.credits)
    c.organizations += _organizations_from_bio(c.bio)
    c.organizations = _dedupe_organizations(c.organizations)

    # Normalize associates
    for assoc in c.associates:
        assoc.name = assoc.name.strip()
    c.associates = _dedupe_associates(c.associates)

    # Normalize links
    for link in c.links:
        link.url = link.url.strip()
        link.type = _normalize_link_type(link.type)
    c.links = _dedupe_links(c.links)

    # Normalize representatives
    for rep in c.representatives:
        rep.name = rep.name.strip()
        rep.title = rep.title.strip().lower()
    c.representatives = _dedupe_reps(c.representatives)

    # Synthesize bio if empty
    if not c.bio and c.name:
        c.bio = _synthesize_bio(c)

    return c


def _organizations_from_credits(credits: list[Credit]) -> list[Organization]:
    orgs: list[Organization] = []
    for credit in credits:
        if credit.network:
            name = credit.network.strip()
            if name:
                orgs.append(Organization(name=name, type=_classify_org_type(name)))
    return orgs


def _organizations_from_bio(bio: str) -> list[Organization]:
    orgs: list[Organization] = []
    for match in _ORGANIZATION_PATTERN.findall(bio):
        name = _clean_org_name(match)
        if name:
            orgs.append(Organization(name=name, type=_classify_org_type(name)))
    return orgs


def _clean_org_name(name: str) -> str:
    name = name.strip()
    name = re.sub(r"'s$", "", name)
    name = re.sub(r"\u2019s$", "", name)  # smart apostrophe
    return name.strip(" \t\n\r.,;:()")


def _classify_org_type(name: str) -> str:
    lower = name.lower().strip()
    if "network" in lower:
        return "network"
    if "studio" in lower or "animation" in lower or " tv" in lower or lower.endswith("tv"):
        return "studio"
    if "productions" in lower or "production" in lower:
        return "production company"
    if "media" in lower or "entertainment" in lower or "pictures" in lower or "films" in lower or "film" in lower:
        return "production company"
    return "company"


def _normalize_link_type(link_type: str) -> str:
    mapping = {
        "imdb": "IMDB",
        "twitter": "Twitter",
        "instagram": "Instagram",
        "facebook": "Facebook",
        "linkedin": "LinkedIn",
    }
    return mapping.get(link_type.strip().lower(), "Other")


def _synthesize_bio(c: Candidate) -> str:
    parts = [c.name]
    if c.position:
        parts.append(f"is identified as a {c.position}")
    else:
        parts.append("is mentioned in the submission")
    if c.credits:
        parts.append(f"with {len(c.credits)} referenced credits")
    if c.tags:
        parts.append("and associated tags including " + ", ".join(c.tags))
    return " ".join(parts) + "."


# ── Deduplication helpers ───────────────────────────────────────────────────

def _dedupe_credits(values: list[Credit]) -> list[Credit]:
    seen: set[str] = set()
    result: list[Credit] = []
    for v in values:
        key = "|".join([v.role.lower(), v.type.lower(), v.production, (v.network or "").lower()])
        if key not in seen:
            seen.add(key)
            result.append(v)
    return result


def _dedupe_organizations(values: list[Organization]) -> list[Organization]:
    seen: set[str] = set()
    result: list[Organization] = []
    for v in values:
        key = v.name.lower()
        if key not in seen:
            seen.add(key)
            result.append(v)
    return result


def _dedupe_associates(values: list[Associate]) -> list[Associate]:
    seen: set[str] = set()
    result: list[Associate] = []
    for v in values:
        key = "|".join([v.name.lower(), (v.production or "").lower()])
        if key not in seen:
            seen.add(key)
            result.append(v)
    return result


def _dedupe_links(values: list[Link]) -> list[Link]:
    seen: set[str] = set()
    result: list[Link] = []
    for v in values:
        key = "|".join([v.url.lower(), v.type.lower()])
        if key not in seen:
            seen.add(key)
            result.append(v)
    return result


def _dedupe_reps(values: list["Representative"]) -> list["Representative"]:  # noqa: F821
    from .extraction import Representative  # deferred import to avoid circular

    seen: set[tuple[str, ...]] = set()
    result: list[Representative] = []
    for v in values:
        key = (
            v.name.lower(),
            v.title.lower(),
            (v.organization or "").lower(),
            (v.email or "").lower(),
            (v.phone_number or "").lower(),
        )
        if key not in seen:
            seen.add(key)
            result.append(v)
    return result
