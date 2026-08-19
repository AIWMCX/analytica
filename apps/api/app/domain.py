from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


class AnalysisStatus(str, Enum):
    CREATED = "CREATED"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    QUEUED = "QUEUED"
    DISCOVERING_COMPANIES = "DISCOVERING_COMPANIES"
    COLLECTING_EVIDENCE = "COLLECTING_EVIDENCE"
    NORMALIZING = "NORMALIZING"
    SCORING = "SCORING"
    GENERATING_FINDINGS = "GENERATING_FINDINGS"
    RENDERING_RESULT = "RENDERING_RESULT"
    COMPLETED = "COMPLETED"
    FAILED_RETRYABLE = "FAILED_RETRYABLE"
    FAILED_PERMANENT = "FAILED_PERMANENT"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    CANCELLED = "CANCELLED"


class ConfidenceClass(str, Enum):
    VERIFIED_OBSERVATION = "verified_observation"
    CORRELATION = "correlation"
    EVIDENCE_SUPPORTED_EXPLANATION = "evidence_supported_explanation"
    ANALYTICAL_INFERENCE = "analytical_inference"


class EvidenceItem(BaseModel):
    evidence_id: str
    company_id: str
    source_type: str
    source_title: str
    publisher: str
    source_uri: str | None = None
    publication_date: str
    period: int
    fact: str
    normalized_fact: str
    confidence: float = Field(ge=0, le=1)
    verification_status: Literal["fixture_verified", "fixture_inference"]


class TrajectoryPoint(BaseModel):
    year: int
    performance_score: float = Field(ge=0, le=100)
    risk_score: float = Field(ge=0, le=1)
    state: Literal["red", "yellow", "blue", "green"]
    evidence_ids: list[str] = Field(default_factory=list)


class CompanyTrajectory(BaseModel):
    company_id: str
    display_name: str
    status: Literal["active", "distressed", "failed", "high_performer"]
    comparability_score: float = Field(ge=0, le=1)
    trajectory: list[TrajectoryPoint]

    @model_validator(mode="after")
    def validate_trajectory(self):
        years = [point.year for point in self.trajectory]
        if len(years) > 10:
            raise ValueError("trajectory cannot contain more than ten annual points")
        if years != sorted(set(years)):
            raise ValueError("trajectory years must be unique and ascending")
        return self


class Finding(BaseModel):
    finding_id: str
    title: str
    summary: str
    confidence: ConfidenceClass
    evidence_ids: list[str]
    impact: Literal["positive", "negative", "mixed", "context"]


class Lesson(BaseModel):
    priority: int = Field(ge=1)
    title: str
    action: str
    confidence: ConfidenceClass
    evidence_ids: list[str]


class CohortSummary(BaseModel):
    target_size: int = 100
    fixture_company_count: int
    active_count: int
    distressed_count: int
    failed_count: int
    high_performer_count: int
    note: str


class AnalysisReport(BaseModel):
    analysis_id: str
    business_activity: str
    geography: str
    market_scope: str
    status: AnalysisStatus
    readiness_label: str
    disclaimer: str
    cohort: CohortSummary
    companies: list[CompanyTrajectory]
    evidence: list[EvidenceItem]
    findings: list[Finding]
    lessons: list[Lesson]
