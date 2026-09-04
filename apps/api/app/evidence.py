from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _sha256(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class ClaimStatus(str, Enum):
    SUPPORTED = "SUPPORTED"
    PARTIALLY_SUPPORTED = "PARTIALLY_SUPPORTED"
    CONTESTED = "CONTESTED"
    SINGLE_SOURCE = "SINGLE_SOURCE"
    STALE = "STALE"
    INFERRED = "INFERRED"
    UNSUPPORTED = "UNSUPPORTED"


class AssumptionOrigin(str, Enum):
    CUSTOMER_INPUT = "CUSTOMER_INPUT"
    SOURCE_ESTIMATE = "SOURCE_ESTIMATE"
    BENCHMARK = "BENCHMARK"
    ANALYST_ASSUMPTION = "ANALYST_ASSUMPTION"


class ReviewStatus(str, Enum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True)


class EvidenceSnapshot(FrozenModel):
    retrieved_at: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    text: str


class EvidenceSource(FrozenModel):
    source_id: str
    provider_id: str
    canonical_url: str
    title: str
    publisher: str
    publication_date: str | None = None
    source_type: str
    snapshot: EvidenceSnapshot


class EvidencePassage(FrozenModel):
    passage_id: str
    source_id: str
    text: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class ClaimEvidenceLink(FrozenModel):
    source_id: str
    passage_id: str
    relation: Literal["SUPPORTS", "CONTRADICTS", "QUALIFIES"]


class EvidenceClaim(FrozenModel):
    claim_id: str
    statement: str
    status: ClaimStatus
    evidence: list[ClaimEvidenceLink]
    independent_source_count: int = Field(ge=0)
    limitations: list[str] = Field(default_factory=list)


class EvidenceContradiction(FrozenModel):
    contradiction_id: str
    claim_id: str
    supporting_passage_ids: list[str]
    contradicting_passage_ids: list[str]
    explanation: str


class EvidenceQuality(FrozenModel):
    coverage: float = Field(ge=0, le=1)
    corroboration: float = Field(ge=0, le=1)
    freshness: float = Field(ge=0, le=1)
    source_diversity: float = Field(ge=0, le=1)
    overall_confidence: float = Field(ge=0, le=1)
    limitations: list[str] = Field(default_factory=list)


class EvidenceSubject(FrozenModel):
    submitted_name: str
    geography: str
    industry: str
    resolution_status: Literal["UNRESOLVED"] = "UNRESOLVED"


class EvidenceLineage(FrozenModel):
    predicta_version: str
    provider_versions: dict[str, str]
    retrieved_at: str
    content_hash: str = Field(pattern=r"^[a-f0-9]{64}$")


class EvidencePacket(FrozenModel):
    schema_version: Literal["analytica.evidence.v1"] = "analytica.evidence.v1"
    upstream_api_version: Literal["predicta.search.v1"]
    packet_id: str
    case_id: str
    research_run_id: str
    subject: EvidenceSubject
    query: dict[str, Any]
    sources: list[EvidenceSource]
    passages: list[EvidencePassage]
    claims: list[EvidenceClaim]
    contradictions: list[EvidenceContradiction]
    quality: EvidenceQuality
    lineage: EvidenceLineage

    @model_validator(mode="after")
    def validate_graph_links(self):
        source_ids = {source.source_id for source in self.sources}
        passage_ids = {passage.passage_id for passage in self.passages}
        for passage in self.passages:
            if passage.source_id not in source_ids:
                raise ValueError(f"passage {passage.passage_id} references unknown source")
        for claim in self.claims:
            for link in claim.evidence:
                if link.source_id not in source_ids:
                    raise ValueError(f"claim {claim.claim_id} references unknown source")
                if link.passage_id not in passage_ids:
                    raise ValueError(f"claim {claim.claim_id} references unknown passage")
        return self


class ProposedAssumption(FrozenModel):
    assumption_id: str
    packet_id: str
    metric: str
    value: float
    unit: str
    period: str
    origin: AssumptionOrigin
    transformation: str
    source_claim_ids: list[str]
    source_claim_statuses: list[ClaimStatus]
    review_status: ReviewStatus = ReviewStatus.PROPOSED
    reviewer_id: str | None = None
    reviewed_at: str | None = None


class CanonicalFinancialInput(FrozenModel):
    assumption_id: str
    metric: str
    value: float
    unit: str
    period: str
    origin: AssumptionOrigin
    transformation: str
    source_claim_ids: list[str]
    reviewer_id: str


class PredictaEvidencePort:
    """Anti-corruption adapter from Predicta search.v1 to Analytica evidence.v1."""

    def __init__(self, predicta_version: str):
        self.predicta_version = predicta_version

    def adapt(self, response: dict[str, Any], *, case_id: str, submitted_name: str, geography: str, industry: str) -> EvidencePacket:
        api_version = response.get("apiVersion")
        if api_version != "predicta.search.v1":
            raise ValueError(f"unsupported Predicta API version: {api_version!r}")

        sources: list[EvidenceSource] = []
        passages: list[EvidencePassage] = []
        for candidate in response.get("candidates", []):
            source_id = candidate["candidateId"]
            text = candidate.get("snippet", "")
            snapshot_payload = {
                "canonical_url": candidate["canonicalUrl"], "title": candidate.get("title", ""),
                "publisher": candidate.get("publisher", "Unknown publisher"),
                "publication_date": candidate.get("publicationDate"), "text": text,
            }
            snapshot_hash = _sha256(snapshot_payload)
            sources.append(EvidenceSource(
                source_id=source_id, provider_id=candidate["providerId"], canonical_url=candidate["canonicalUrl"],
                title=candidate.get("title", ""), publisher=candidate.get("publisher", "Unknown publisher"),
                publication_date=candidate.get("publicationDate"), source_type=candidate.get("sourceType", "UNKNOWN"),
                snapshot=EvidenceSnapshot(retrieved_at=candidate["retrievalDate"], content_hash=snapshot_hash, text=text),
            ))
            passages.append(EvidencePassage(
                passage_id=f"passage_{source_id}", source_id=source_id, text=text,
                content_hash=_sha256({"source_hash": snapshot_hash, "text": text}),
            ))

        claims = [EvidenceClaim(
            claim_id=claim["claimId"], statement=claim["statement"], status=claim["status"],
            evidence=[ClaimEvidenceLink(source_id=link["sourceId"], passage_id=link["passageId"], relation=link["relation"])
                      for link in claim.get("evidence", [])],
            independent_source_count=claim.get("independentSourceCount", 0), limitations=claim.get("limitations", []),
        ) for claim in response.get("claims", [])]

        contradictions = []
        for claim in claims:
            supporting = [link.passage_id for link in claim.evidence if link.relation == "SUPPORTS"]
            contradicting = [link.passage_id for link in claim.evidence if link.relation == "CONTRADICTS"]
            if contradicting:
                contradictions.append(EvidenceContradiction(
                    contradiction_id=f"contra_{claim.claim_id}", claim_id=claim.claim_id,
                    supporting_passage_ids=supporting, contradicting_passage_ids=contradicting,
                    explanation="Predicta returned evidence that contradicts or materially qualifies this claim.",
                ))

        supported = sum(claim.status not in {ClaimStatus.UNSUPPORTED, ClaimStatus.INFERRED} for claim in claims)
        corroborated = sum(claim.independent_source_count >= 2 for claim in claims)
        provider_count = len({source.provider_id for source in sources})
        coverage = supported / len(claims) if claims else 0
        corroboration = corroborated / len(claims) if claims else 0
        diversity = min(1.0, provider_count / 3)
        freshness = 1.0 if sources else 0
        overall = round((coverage * 0.35) + (corroboration * 0.3) + (freshness * 0.2) + (diversity * 0.15), 4)
        quality = EvidenceQuality(
            coverage=coverage, corroboration=corroboration, freshness=freshness, source_diversity=diversity,
            overall_confidence=overall, limitations=sorted({item for claim in claims for item in claim.limitations}),
        )

        query = response.get("query", {})
        stable_payload = {
            "case_id": case_id, "research_run_id": query.get("queryId", "unknown"),
            "subject": {"submitted_name": submitted_name, "geography": geography, "industry": industry},
            "query": query, "sources": [item.model_dump(mode="json") for item in sources],
            "passages": [item.model_dump(mode="json") for item in passages],
            "claims": [item.model_dump(mode="json") for item in claims],
            "contradictions": [item.model_dump(mode="json") for item in contradictions],
            "quality": quality.model_dump(mode="json"),
        }
        content_hash = _sha256(stable_payload)
        retrieved_at = max((source.snapshot.retrieved_at for source in sources), default="not-retrieved")
        return EvidencePacket(
            upstream_api_version=api_version, packet_id=f"ep_{content_hash[:16]}", case_id=case_id,
            research_run_id=query.get("queryId", "unknown"),
            subject=EvidenceSubject(submitted_name=submitted_name, geography=geography, industry=industry),
            query=query, sources=sources, passages=passages, claims=claims, contradictions=contradictions, quality=quality,
            lineage=EvidenceLineage(
                predicta_version=self.predicta_version,
                provider_versions={provider: "search.v1" for provider in response.get("diagnostics", {}).get("providersSucceeded", [])},
                retrieved_at=retrieved_at, content_hash=content_hash,
            ),
        )


class FinancialTruthFirewall:
    def propose(self, *, packet: EvidencePacket, claim_id: str, metric: str, value: float, unit: str,
                period: str, origin: AssumptionOrigin, transformation: str) -> ProposedAssumption:
        claim = next((item for item in packet.claims if item.claim_id == claim_id), None)
        if claim is None:
            raise ValueError(f"unknown evidence claim: {claim_id}")
        if origin == AssumptionOrigin.CUSTOMER_INPUT:
            raise ValueError("customer input cannot be attributed to a Predicta claim")
        identity = _sha256({"packet": packet.packet_id, "claim": claim_id, "metric": metric, "period": period})
        return ProposedAssumption(
            assumption_id=f"asm_{identity[:16]}", packet_id=packet.packet_id, metric=metric, value=value,
            unit=unit, period=period, origin=origin, transformation=transformation.strip(),
            source_claim_ids=[claim_id], source_claim_statuses=[claim.status],
        )

    def accept(self, proposal: ProposedAssumption, *, reviewer_id: str) -> ProposedAssumption:
        if ClaimStatus.UNSUPPORTED in proposal.source_claim_statuses:
            raise ValueError("unsupported claim cannot become a canonical financial input")
        if not reviewer_id.strip():
            raise ValueError("reviewer_id is required")
        if not proposal.transformation:
            raise ValueError("transformation is required")
        return proposal.model_copy(update={
            "review_status": ReviewStatus.ACCEPTED, "reviewer_id": reviewer_id.strip(),
            "reviewed_at": datetime.now(timezone.utc).isoformat(),
        })

    def to_canonical_input(self, proposal: ProposedAssumption) -> CanonicalFinancialInput:
        if proposal.review_status != ReviewStatus.ACCEPTED or not proposal.reviewer_id:
            raise PermissionError("financial evidence must be human-approved before canonicalization")
        return CanonicalFinancialInput(
            assumption_id=proposal.assumption_id, metric=proposal.metric, value=proposal.value, unit=proposal.unit,
            period=proposal.period, origin=proposal.origin, transformation=proposal.transformation,
            source_claim_ids=proposal.source_claim_ids, reviewer_id=proposal.reviewer_id,
        )
