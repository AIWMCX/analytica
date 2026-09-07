"""Small, auditable concierge-review workflow for Analytica delivery gates."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from pydantic import BaseModel, Field

from .cost_ledger import CaseCostLedgerRepository, CostMeasurement, CostMetric, MeasurementStatus
from .entities import ResolutionDecision, ResolutionStatus
from .evidence import ClaimStatus, EvidencePacket, FinancialTruthFirewall, ProposedAssumption, ReviewStatus
from .evidence_repository import SQLiteEvidenceRepository
from .financial import FinancialResult


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ReviewActionType(str, Enum):
    APPROVE_ENTITY = "APPROVE_ENTITY"
    REJECT_ENTITY = "REJECT_ENTITY"
    REQUEST_ADDITIONAL_RESEARCH = "REQUEST_ADDITIONAL_RESEARCH"
    ACCEPT_ASSUMPTION = "ACCEPT_ASSUMPTION"
    REJECT_ASSUMPTION = "REJECT_ASSUMPTION"
    EDIT_RECOMMENDATION = "EDIT_RECOMMENDATION"
    RETURN_FOR_REVISION = "RETURN_FOR_REVISION"
    APPROVE_DELIVERY = "APPROVE_DELIVERY"
    REJECT_DELIVERY = "REJECT_DELIVERY"


class EntityReviewStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class DeliveryStatus(str, Enum):
    IN_REVIEW = "IN_REVIEW"
    RESEARCH_REQUESTED = "RESEARCH_REQUESTED"
    REVISION_REQUIRED = "REVISION_REQUIRED"
    DELIVERABLE = "DELIVERABLE"
    DELIVERY_REJECTED = "DELIVERY_REJECTED"


class ReviewerAction(BaseModel):
    action_id: str
    case_id: str
    action_type: ReviewActionType
    reviewer_id: str
    occurred_at: str
    reason: str | None = None
    assumption_id: str | None = None
    recommendation_text: str | None = None


class ReviewerCase(BaseModel):
    case_id: str
    entity: ResolutionDecision
    entity_review_status: EntityReviewStatus = EntityReviewStatus.PENDING
    entity_reviewer_id: str | None = None
    packet_ids: list[str] = Field(default_factory=list)
    assumptions: list[ProposedAssumption] = Field(default_factory=list)
    financial_results: list[FinancialResult] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    source_recommendation: str
    reviewer_recommendation: str | None = None
    delivery_status: DeliveryStatus = DeliveryStatus.IN_REVIEW
    qa_approved_by: str | None = None
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)


class PacketInspection(BaseModel):
    packet_id: str
    providers: list[str]
    source_count: int
    passage_count: int
    claim_count: int
    contradiction_count: int
    hash_valid: bool


class DeliveryGate(BaseModel):
    eligible: bool
    blockers: list[str]


class ReviewerInspection(BaseModel):
    case: ReviewerCase
    packets: list[PacketInspection]
    # Full packets remain immutable evidence records. The reviewer sees them
    # directly instead of a second editable representation of source facts.
    evidence_packets: list[EvidencePacket]
    providers: list[str]
    delivery_gate: DeliveryGate
    audit_actions: list[ReviewerAction]


class SQLiteReviewerRepository:
    """Mutable case state plus an append-only reviewer-action log."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS reviewer_cases (
                    case_id TEXT PRIMARY KEY,
                    case_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS reviewer_actions (
                    action_id TEXT PRIMARY KEY,
                    case_id TEXT NOT NULL,
                    occurred_at TEXT NOT NULL,
                    action_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_reviewer_actions_case_time
                    ON reviewer_actions(case_id, occurred_at, action_id);
            """)

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    def create_case(self, case: ReviewerCase) -> None:
        with self.connection() as db:
            db.execute("INSERT INTO reviewer_cases VALUES (?,?)", (case.case_id, case.model_dump_json()))

    def get_case(self, case_id: str) -> ReviewerCase | None:
        with self.connection() as db:
            row = db.execute("SELECT case_json FROM reviewer_cases WHERE case_id=?", (case_id,)).fetchone()
        return ReviewerCase.model_validate_json(row["case_json"]) if row else None

    def save_case(self, case: ReviewerCase) -> None:
        with self.connection() as db:
            cursor = db.execute("UPDATE reviewer_cases SET case_json=? WHERE case_id=?", (case.model_dump_json(), case.case_id))
            if cursor.rowcount != 1:
                raise KeyError(case.case_id)

    def append_action(self, action: ReviewerAction) -> None:
        with self.connection() as db:
            db.execute(
                "INSERT INTO reviewer_actions VALUES (?,?,?,?)",
                (action.action_id, action.case_id, action.occurred_at, action.model_dump_json()),
            )

    def list_actions(self, case_id: str) -> list[ReviewerAction]:
        with self.connection() as db:
            rows = db.execute(
                "SELECT action_json FROM reviewer_actions WHERE case_id=? ORDER BY occurred_at, action_id", (case_id,),
            ).fetchall()
        return [ReviewerAction.model_validate_json(row["action_json"]) for row in rows]


class ReviewerWorkflow:
    """Enforces delivery gates for a founder-led concierge review queue."""

    def __init__(self, repository: SQLiteReviewerRepository, evidence: SQLiteEvidenceRepository, cost_ledger: CaseCostLedgerRepository | None = None):
        self.repository = repository
        self.evidence = evidence
        self.cost_ledger = cost_ledger

    def open_case(
        self,
        *,
        case_id: str,
        entity: ResolutionDecision,
        packet_ids: list[str],
        assumptions: list[ProposedAssumption],
        financial_results: list[FinancialResult],
        findings: list[str],
        recommendation: str,
    ) -> ReviewerCase:
        if self.repository.get_case(case_id):
            raise ValueError("review case already exists")
        case = ReviewerCase(
            case_id=case_id, entity=entity, packet_ids=packet_ids, assumptions=assumptions,
            financial_results=financial_results, findings=findings, source_recommendation=recommendation,
        )
        self.repository.create_case(case)
        return case

    def inspect(self, case_id: str) -> ReviewerInspection:
        case = self._case(case_id)
        packets: list[PacketInspection] = []
        evidence_packets: list[EvidencePacket] = []
        provider_ids: set[str] = set()
        for packet_id in case.packet_ids:
            packet = self.evidence.get_packet(packet_id)
            if packet is None:
                packets.append(PacketInspection(packet_id=packet_id, providers=[], source_count=0, passage_count=0, claim_count=0, contradiction_count=0, hash_valid=False))
                continue
            providers = sorted({source.provider_id for source in packet.sources})
            provider_ids.update(providers)
            evidence_packets.append(packet)
            packets.append(PacketInspection(
                packet_id=packet_id, providers=providers, source_count=len(packet.sources), passage_count=len(packet.passages),
                claim_count=len(packet.claims), contradiction_count=len(packet.contradictions),
                hash_valid=self.evidence.verify_packet_hash(packet_id),
            ))
        return ReviewerInspection(
            case=case, packets=packets, evidence_packets=evidence_packets, providers=sorted(provider_ids),
            delivery_gate=self._delivery_gate(case), audit_actions=self.audit_log(case_id),
        )

    def audit_log(self, case_id: str) -> list[ReviewerAction]:
        self._case(case_id)
        return self.repository.list_actions(case_id)

    def apply(
        self,
        case_id: str,
        action_type: ReviewActionType,
        *,
        reviewer_id: str,
        reason: str | None = None,
        assumption_id: str | None = None,
        recommendation_text: str | None = None,
    ) -> ReviewerCase:
        reviewer_id = reviewer_id.strip()
        if not reviewer_id:
            raise ValueError("reviewer_id is required")
        case = self._case(case_id)
        updated = self._apply_transition(
            case, action_type, reviewer_id=reviewer_id, reason=reason, assumption_id=assumption_id,
            recommendation_text=recommendation_text,
        )
        occurred_at = _now()
        updated = updated.model_copy(update={"updated_at": occurred_at})
        action = ReviewerAction(
            action_id=f"qaa_{uuid4().hex}", case_id=case_id, action_type=action_type,
            reviewer_id=reviewer_id, occurred_at=occurred_at, reason=reason.strip() if reason else None,
            assumption_id=assumption_id, recommendation_text=recommendation_text.strip() if recommendation_text else None,
        )
        self.repository.save_case(updated)
        self.repository.append_action(action)
        self._record_operating_telemetry(updated, action_type, occurred_at)
        return updated

    def _record_operating_telemetry(self, case: ReviewerCase, action_type: ReviewActionType, occurred_at: str) -> None:
        if self.cost_ledger is None:
            return
        self.cost_ledger.open_case(case.case_id)
        if action_type == ReviewActionType.RETURN_FOR_REVISION:
            self.cost_ledger.increment_count(case.case_id, CostMetric.REVISIONS, "revisions", source="reviewer return-for-revision action")
        if action_type == ReviewActionType.APPROVE_DELIVERY:
            created = datetime.fromisoformat(case.created_at)
            delivered = datetime.fromisoformat(occurred_at)
            self.cost_ledger.record(case.case_id, CostMeasurement.measured_quantity(
                CostMetric.DELIVERY_DURATION_SECONDS, max(0, (delivered - created).total_seconds()), "seconds",
                MeasurementStatus.MEASURED, source="reviewer delivery approval timestamp",
            ))

    def _apply_transition(
        self,
        case: ReviewerCase,
        action_type: ReviewActionType,
        *,
        reviewer_id: str,
        reason: str | None,
        assumption_id: str | None,
        recommendation_text: str | None,
    ) -> ReviewerCase:
        if action_type == ReviewActionType.APPROVE_ENTITY:
            if case.entity.status != ResolutionStatus.RESOLVED or not case.entity.entity_id:
                raise PermissionError("entity is not resolved")
            return case.model_copy(update={"entity_review_status": EntityReviewStatus.APPROVED, "entity_reviewer_id": reviewer_id})
        if action_type == ReviewActionType.REJECT_ENTITY:
            self._reason_required(reason)
            return case.model_copy(update={"entity_review_status": EntityReviewStatus.REJECTED, "entity_reviewer_id": reviewer_id, "delivery_status": DeliveryStatus.REVISION_REQUIRED})
        if action_type == ReviewActionType.REQUEST_ADDITIONAL_RESEARCH:
            self._reason_required(reason)
            return case.model_copy(update={"delivery_status": DeliveryStatus.RESEARCH_REQUESTED, "qa_approved_by": None})
        if action_type in {ReviewActionType.ACCEPT_ASSUMPTION, ReviewActionType.REJECT_ASSUMPTION}:
            if not assumption_id:
                raise ValueError("assumption_id is required")
            assumptions = list(case.assumptions)
            index = next((index for index, item in enumerate(assumptions) if item.assumption_id == assumption_id), None)
            if index is None:
                raise KeyError("assumption not found")
            proposal = assumptions[index]
            if proposal.review_status != ReviewStatus.PROPOSED:
                raise PermissionError("assumption has already been reviewed")
            if action_type == ReviewActionType.ACCEPT_ASSUMPTION:
                proposal = FinancialTruthFirewall().accept(proposal, reviewer_id=reviewer_id)
                self.evidence.save_assumption(proposal)
            else:
                self._reason_required(reason)
                proposal = proposal.model_copy(update={"review_status": ReviewStatus.REJECTED, "reviewer_id": reviewer_id, "reviewed_at": _now()})
            assumptions[index] = proposal
            return case.model_copy(update={"assumptions": assumptions})
        if action_type == ReviewActionType.EDIT_RECOMMENDATION:
            if not (recommendation_text or "").strip():
                raise ValueError("recommendation_text is required")
            return case.model_copy(update={"reviewer_recommendation": recommendation_text.strip()})
        if action_type == ReviewActionType.RETURN_FOR_REVISION:
            self._reason_required(reason)
            return case.model_copy(update={"delivery_status": DeliveryStatus.REVISION_REQUIRED, "qa_approved_by": None})
        if action_type == ReviewActionType.APPROVE_DELIVERY:
            gate = self._delivery_gate(case)
            if not gate.eligible:
                raise PermissionError("; ".join(gate.blockers))
            return case.model_copy(update={"delivery_status": DeliveryStatus.DELIVERABLE, "qa_approved_by": reviewer_id})
        if action_type == ReviewActionType.REJECT_DELIVERY:
            self._reason_required(reason)
            return case.model_copy(update={"delivery_status": DeliveryStatus.DELIVERY_REJECTED, "qa_approved_by": None})
        raise ValueError(f"unsupported review action: {action_type}")

    def _delivery_gate(self, case: ReviewerCase) -> DeliveryGate:
        blockers: list[str] = []
        if case.entity.status != ResolutionStatus.RESOLVED or not case.entity.entity_id:
            blockers.append("entity is not resolved")
        if case.entity_review_status != EntityReviewStatus.APPROVED:
            blockers.append("entity approval is required")
        if not case.packet_ids:
            blockers.append("no evidence packet is attached")
        for packet_id in case.packet_ids:
            packet = self.evidence.get_packet(packet_id)
            if packet is None:
                blockers.append(f"evidence packet {packet_id} is missing")
                continue
            if not self.evidence.verify_packet_hash(packet_id):
                blockers.append(f"evidence packet {packet_id} hash is invalid")
            source_ids = {source.source_id for source in packet.sources}
            passage_ids = {passage.passage_id for passage in packet.passages}
            for claim in packet.claims:
                if claim.status in {ClaimStatus.UNSUPPORTED, ClaimStatus.INFERRED}:
                    continue
                if not claim.evidence or any(link.source_id not in source_ids or link.passage_id not in passage_ids for link in claim.evidence):
                    blockers.append(f"material claim {claim.claim_id} lacks source lineage")
        for assumption in case.assumptions:
            if assumption.review_status == ReviewStatus.ACCEPTED and (not assumption.reviewer_id or not assumption.reviewed_at):
                blockers.append(f"accepted assumption {assumption.assumption_id} lacks a named reviewer")
        if not case.financial_results:
            blockers.append("no financial reconciliation result is attached")
        elif any(not result.reconciliation.passed for result in case.financial_results):
            blockers.append("financial reconciliation did not pass")
        return DeliveryGate(eligible=not blockers, blockers=blockers)

    def _case(self, case_id: str) -> ReviewerCase:
        case = self.repository.get_case(case_id)
        if case is None:
            raise KeyError(case_id)
        return case

    @staticmethod
    def _reason_required(reason: str | None) -> None:
        if not (reason or "").strip():
            raise ValueError("reason is required")
