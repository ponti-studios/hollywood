"""SubmissionPacket extraction models — ported from kuma internal/schema."""

from __future__ import annotations

import re
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field, model_validator

SCHEMA_VERSION_V1 = "v1_submission_packet"
PROMPT_VERSION_V1 = "v1"
PROMPT_VERSION_V2 = "v2"

_PHONE_PATTERN = re.compile(r"^\d{3}-\d{3}-\d{4}$")
_ORGANIZATION_PATTERN = re.compile(
    r"\b([A-Z][A-Za-z0-9&+.'’:-]*(?:\s+[A-Z][A-Za-z0-9&+.'’:-]*){0,4}\s"
    r"(?:Studios|Studio|TV|Television|Animation|Media|Productions|Entertainment|Network|Networks|Pictures|Films|Film|Labs|Lab))\b"
)

ALLOWED_CREDIT_TYPES = {"tv", "movie", "novel", "magazine", "podcast"}
ALLOWED_LINK_TYPES = {"IMDB", "Twitter", "Instagram", "Facebook", "LinkedIn", "Other"}


def _normalize_optional_str(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    if v.lower() in ("null", "n/a", "none", "unknown", ""):
        return None
    return v


def _normalize_email(v: str | None) -> str | None:
    v = _normalize_optional_str(v)
    if v is None:
        return None
    try:
        local, domain = v.rsplit("@", 1)
        if "." not in domain:
            return None
        return v.lower()
    except ValueError:
        return None


def _normalize_phone(v: str | None) -> str | None:
    v = _normalize_optional_str(v)
    if v is None:
        return None
    if not _PHONE_PATTERN.match(v):
        return None
    return v


OptStr = Annotated[str | None, BeforeValidator(_normalize_optional_str)]


class Credit(BaseModel):
    role: str
    type: str
    production: str
    network: OptStr = None

    @model_validator(mode="after")
    def _validate(self) -> Credit:
        if not self.role.strip():
            raise ValueError("role is required")
        self.role = self.role.strip().lower()
        if self.type not in ALLOWED_CREDIT_TYPES:
            raise ValueError(f"type must be one of {sorted(ALLOWED_CREDIT_TYPES)}")
        if not self.production.strip():
            raise ValueError("production is required")
        self.production = self.production.strip()
        return self


class Organization(BaseModel):
    name: str
    type: str  # network, studio, agency, production company, etc.

    @model_validator(mode="after")
    def _validate(self) -> Organization:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("name is required")
        self.type = self.type.strip()
        if not self.type:
            raise ValueError("type is required")
        return self


class Associate(BaseModel):
    name: str
    production: OptStr = None

    @model_validator(mode="after")
    def _validate(self) -> Associate:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("name is required")
        return self


class Link(BaseModel):
    url: str
    type: str  # IMDB, Twitter, Instagram, etc.

    @model_validator(mode="after")
    def _validate(self) -> Link:
        self.url = self.url.strip()
        if not self.url:
            raise ValueError("url is required")
        self.type = self.type.strip()
        if self.type not in ALLOWED_LINK_TYPES:
            raise ValueError(f"type must be one of {sorted(ALLOWED_LINK_TYPES)}")
        return self


class Representative(BaseModel):
    name: str
    title: str
    organization: OptStr = None
    email: Annotated[str | None, BeforeValidator(_normalize_email)] = None
    phone_number: Annotated[str | None, BeforeValidator(_normalize_phone)] = None

    @model_validator(mode="after")
    def _validate(self) -> Representative:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("name is required")
        self.title = self.title.strip().lower()
        if not self.title:
            raise ValueError("title is required")
        return self


class Candidate(BaseModel):
    name: str
    bio: str
    email: Annotated[str | None, BeforeValidator(_normalize_email)] = None
    phone_number: Annotated[str | None, BeforeValidator(_normalize_phone)] = None
    position: OptStr = None
    tags: list[str] = Field(default_factory=list)
    credits: list[Credit] = Field(default_factory=list)
    organizations: list[Organization] = Field(default_factory=list)
    associates: list[Associate] = Field(default_factory=list)
    links: list[Link] = Field(default_factory=list)
    representatives: list[Representative] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> Candidate:
        self.name = self.name.strip()
        if not self.name:
            raise ValueError("name is required")
        self.bio = self.bio.strip()
        if not self.bio:
            raise ValueError("bio is required")
        self.tags = [t.strip() for t in self.tags if t.strip()]
        return self


class SubmissionPacket(BaseModel):
    schema_version: str = SCHEMA_VERSION_V1
    candidates: list[Candidate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _validate(self) -> SubmissionPacket:
        if self.schema_version != SCHEMA_VERSION_V1:
            raise ValueError(f"unsupported schema_version {self.schema_version!r}")
        return self
