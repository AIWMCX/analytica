from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class ResolutionStatus(str, Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"
    UNRESOLVED = "UNRESOLVED"
    HUMAN_REVIEW = "HUMAN_REVIEW"


class BusinessEntity(BaseModel):
    entity_id: str
    canonical_name: str
    legal_name: str
    domains: list[str] = Field(default_factory=list)
    states: list[str] = Field(default_factory=list)
    industry: str
    naics: str | None = None
    aliases: list[str] = Field(default_factory=list)
    external_identifiers: dict[str, str] = Field(default_factory=dict)


class ResolutionDecision(BaseModel):
    status: ResolutionStatus
    entity_id: str | None
    confidence: float = Field(ge=0, le=1)
    matching_signals: int
    candidate_ids: list[str] = Field(default_factory=list)
