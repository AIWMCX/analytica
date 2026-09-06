"""Internal, auditable case-cost telemetry. It never sets a public price."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Iterator
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field, model_validator


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _money(value: float) -> float:
    return round(value, 2)


class MeasurementStatus(str, Enum):
    MEASURED = "MEASURED"
    ESTIMATED = "ESTIMATED"
    UNKNOWN = "UNKNOWN"


class CostMetric(str, Enum):
    PROVIDER_COST = "PROVIDER_COST"
    SEARCH_COUNT = "SEARCH_COUNT"
    TOKENS = "TOKENS"
    MODEL_COST = "MODEL_COST"
    COMPUTE_TIME_SECONDS = "COMPUTE_TIME_SECONDS"
    WORKER_TIME_SECONDS = "WORKER_TIME_SECONDS"
    STORAGE_GB_MONTHS = "STORAGE_GB_MONTHS"
    STORAGE_BYTES = "STORAGE_BYTES"
    HUMAN_QA_MINUTES = "HUMAN_QA_MINUTES"
    REVISIONS = "REVISIONS"
    DELIVERY_DURATION_SECONDS = "DELIVERY_DURATION_SECONDS"
    PROVIDER_FAILURES = "PROVIDER_FAILURES"
    CASE_REVENUE = "CASE_REVENUE"


_COST_BUCKETS: dict[str, set[CostMetric]] = {
    "research": {CostMetric.PROVIDER_COST, CostMetric.SEARCH_COUNT},
    "ai": {CostMetric.MODEL_COST},
    "human_review": {CostMetric.HUMAN_QA_MINUTES},
    "direct_variable": {
        CostMetric.PROVIDER_COST, CostMetric.SEARCH_COUNT, CostMetric.MODEL_COST,
        CostMetric.COMPUTE_TIME_SECONDS, CostMetric.WORKER_TIME_SECONDS,
        CostMetric.STORAGE_GB_MONTHS, CostMetric.HUMAN_QA_MINUTES,
    },
}
_REQUIRED_METRICS = tuple(metric for metric in CostMetric if metric != CostMetric.CASE_REVENUE)
_DEFAULT_UNITS = {
    CostMetric.PROVIDER_COST: "USD", CostMetric.SEARCH_COUNT: "searches", CostMetric.TOKENS: "tokens",
    CostMetric.MODEL_COST: "USD", CostMetric.COMPUTE_TIME_SECONDS: "seconds",
    CostMetric.WORKER_TIME_SECONDS: "seconds", CostMetric.STORAGE_GB_MONTHS: "GB-months",
    CostMetric.STORAGE_BYTES: "bytes",
    CostMetric.HUMAN_QA_MINUTES: "minutes", CostMetric.REVISIONS: "revisions",
    CostMetric.DELIVERY_DURATION_SECONDS: "seconds", CostMetric.PROVIDER_FAILURES: "failures",
    CostMetric.CASE_REVENUE: "USD",
}


class CostMeasurement(BaseModel):
    """One current measurement. A replacement is retained as an audit event."""

    model_config = ConfigDict(frozen=True)
    metric: CostMetric
    status: MeasurementStatus
    unit: str = Field(min_length=1, max_length=40)
    quantity: float | None = Field(default=None, ge=0)
    unit_cost_usd: float | None = Field(default=None, ge=0)
    amount_usd: float | None = Field(default=None, ge=0)
    provider_id: str | None = Field(default=None, max_length=160)
    source: str | None = Field(default=None, max_length=240)
    note: str | None = Field(default=None, max_length=1000)
    captured_at: str = Field(default_factory=_now)

    @model_validator(mode="after")
    def validate_value(self):
        if self.status == MeasurementStatus.UNKNOWN:
            if self.amount_usd is not None or self.unit_cost_usd is not None:
                raise ValueError("unknown measurements cannot contain a cost")
            return self
        if self.amount_usd is None and self.quantity is None:
            raise ValueError("measured or estimated measurements require an amount or quantity")
        return self

    @classmethod
    def money(cls, metric: CostMetric, amount_usd: float, status: MeasurementStatus, **kwargs) -> "CostMeasurement":
        return cls(metric=metric, amount_usd=amount_usd, status=status, unit="USD", **kwargs)

    @classmethod
    def measured_quantity(cls, metric: CostMetric, quantity: float, unit: str, status: MeasurementStatus, **kwargs) -> "CostMeasurement":
        return cls(metric=metric, quantity=quantity, unit=unit, status=status, **kwargs)

    @classmethod
    def unknown(cls, metric: CostMetric, unit: str, note: str | None = None, **kwargs) -> "CostMeasurement":
        return cls(metric=metric, status=MeasurementStatus.UNKNOWN, unit=unit, note=note, **kwargs)

    @property
    def key(self) -> str:
        return f"{self.metric.value}:{self.provider_id or 'case'}"

    @property
    def cost_usd(self) -> float | None:
        if self.amount_usd is not None:
            return _money(self.amount_usd)
        if self.quantity is not None and self.unit_cost_usd is not None:
            return _money(self.quantity * self.unit_cost_usd)
        return None


class CostBucket(BaseModel):
    known_amount_usd: float | None
    status: MeasurementStatus
    unknown_metrics: list[CostMetric] = Field(default_factory=list)
    estimated_metrics: list[CostMetric] = Field(default_factory=list)


class GrossContribution(BaseModel):
    known_amount_usd: float | None
    status: MeasurementStatus
    unknown_metrics: list[CostMetric] = Field(default_factory=list)


class BreakEvenPrice(BaseModel):
    target_contribution_margin: float
    lower_bound_price_usd: float | None
    upper_bound_price_usd: float | None
    status: MeasurementStatus
    unknown_cost_metrics: list[CostMetric] = Field(default_factory=list)
    selected_price: None = None


class CaseCostReport(BaseModel):
    case_id: str
    measurements: list[CostMeasurement]
    research_cost: CostBucket
    ai_cost: CostBucket
    human_review_cost: CostBucket
    direct_variable_cost: CostBucket
    gross_contribution: GrossContribution
    break_even_prices: list[BreakEvenPrice]


class CostLedgerEvent(BaseModel):
    event_id: str
    case_id: str
    occurred_at: str
    measurement: CostMeasurement


class CaseCostLedger(BaseModel):
    """Current per-case figures; revisions are held separately in the event log."""

    case_id: str
    measurements: dict[str, CostMeasurement] = Field(default_factory=dict)
    created_at: str = Field(default_factory=_now)
    updated_at: str = Field(default_factory=_now)

    @classmethod
    def open(cls, case_id: str, *, track_all_metrics: bool = False) -> "CaseCostLedger":
        ledger = cls(case_id=case_id)
        if not track_all_metrics:
            return ledger
        entries = {
            f"{metric.value}:case": CostMeasurement.unknown(metric, _DEFAULT_UNITS[metric], "not yet instrumented")
            for metric in _REQUIRED_METRICS
        }
        return ledger.model_copy(update={"measurements": entries})

    def record(self, measurement: CostMeasurement) -> "CaseCostLedger":
        current = dict(self.measurements)
        current[measurement.key] = measurement
        return self.model_copy(update={"measurements": current, "updated_at": _now()})

    def report(self) -> CaseCostReport:
        values = list(self.measurements.values())
        research = self._bucket(_COST_BUCKETS["research"])
        ai = self._bucket(_COST_BUCKETS["ai"])
        human = self._bucket(_COST_BUCKETS["human_review"])
        direct = self._bucket(_COST_BUCKETS["direct_variable"])
        revenue = [value for value in values if value.metric == CostMetric.CASE_REVENUE]
        contribution = self._contribution(revenue, direct)
        return CaseCostReport(
            case_id=self.case_id, measurements=sorted(values, key=lambda item: item.key),
            research_cost=research, ai_cost=ai, human_review_cost=human,
            direct_variable_cost=direct, gross_contribution=contribution,
            break_even_prices=[self._break_even(direct, margin) for margin in (0.5, 0.7, 0.8)],
        )

    def _bucket(self, metrics: set[CostMetric]) -> CostBucket:
        values = [value for value in self.measurements.values() if value.metric in metrics]
        total = _money(sum(value.cost_usd or 0 for value in values))
        unknown = sorted({value.metric for value in values if value.status == MeasurementStatus.UNKNOWN or (value.status != MeasurementStatus.UNKNOWN and value.cost_usd is None)}, key=lambda item: item.value)
        estimated = sorted({value.metric for value in values if value.status == MeasurementStatus.ESTIMATED}, key=lambda item: item.value)
        status = MeasurementStatus.UNKNOWN if unknown else MeasurementStatus.ESTIMATED if estimated else MeasurementStatus.MEASURED
        return CostBucket(known_amount_usd=total, status=status, unknown_metrics=unknown, estimated_metrics=estimated)

    @staticmethod
    def _contribution(revenue: list[CostMeasurement], direct: CostBucket) -> GrossContribution:
        if not revenue:
            return GrossContribution(known_amount_usd=None, status=MeasurementStatus.UNKNOWN, unknown_metrics=[CostMetric.CASE_REVENUE])
        current = revenue[-1]
        if current.cost_usd is None or current.status == MeasurementStatus.UNKNOWN:
            return GrossContribution(known_amount_usd=None, status=MeasurementStatus.UNKNOWN, unknown_metrics=[CostMetric.CASE_REVENUE])
        status = MeasurementStatus.UNKNOWN if direct.status == MeasurementStatus.UNKNOWN else MeasurementStatus.ESTIMATED if (current.status == MeasurementStatus.ESTIMATED or direct.status == MeasurementStatus.ESTIMATED) else MeasurementStatus.MEASURED
        return GrossContribution(known_amount_usd=_money(current.cost_usd - (direct.known_amount_usd or 0)), status=status, unknown_metrics=direct.unknown_metrics)

    @staticmethod
    def _break_even(direct: CostBucket, margin: float) -> BreakEvenPrice:
        lower = _money((direct.known_amount_usd or 0) / (1 - margin))
        return BreakEvenPrice(
            target_contribution_margin=margin, lower_bound_price_usd=lower,
            upper_bound_price_usd=None if direct.status == MeasurementStatus.UNKNOWN else lower,
            status=direct.status, unknown_cost_metrics=direct.unknown_metrics,
        )


class CaseCostLedgerRepository:
    """SQLite persistence with immutable correction events for founder-scale operations."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS case_cost_ledgers (
                    case_id TEXT PRIMARY KEY, ledger_json TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS case_cost_events (
                    event_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, occurred_at TEXT NOT NULL,
                    event_json TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS idx_case_cost_events_case_time
                    ON case_cost_events(case_id, occurred_at, event_id);
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

    def open_case(self, case_id: str) -> CaseCostLedger:
        existing = self.get(case_id)
        if existing is not None:
            return existing
        ledger = CaseCostLedger.open(case_id, track_all_metrics=True)
        with self.connection() as db:
            db.execute("INSERT INTO case_cost_ledgers VALUES (?,?)", (case_id, ledger.model_dump_json()))
        return ledger

    def get(self, case_id: str) -> CaseCostLedger | None:
        with self.connection() as db:
            row = db.execute("SELECT ledger_json FROM case_cost_ledgers WHERE case_id=?", (case_id,)).fetchone()
        return CaseCostLedger.model_validate_json(row["ledger_json"]) if row else None

    def record(self, case_id: str, measurement: CostMeasurement) -> CaseCostLedger:
        ledger = self.open_case(case_id).record(measurement)
        event = CostLedgerEvent(event_id=f"cost_{uuid4().hex}", case_id=case_id, occurred_at=_now(), measurement=measurement)
        with self.connection() as db:
            db.execute("UPDATE case_cost_ledgers SET ledger_json=? WHERE case_id=?", (ledger.model_dump_json(), case_id))
            db.execute("INSERT INTO case_cost_events VALUES (?,?,?,?)", (event.event_id, case_id, event.occurred_at, event.model_dump_json()))
        return ledger

    def increment_count(self, case_id: str, metric: CostMetric, unit: str, *, source: str) -> CaseCostLedger:
        ledger = self.open_case(case_id)
        current = ledger.measurements.get(f"{metric.value}:case")
        quantity = (current.quantity if current and current.status != MeasurementStatus.UNKNOWN else 0) or 0
        return self.record(case_id, CostMeasurement.measured_quantity(
            metric, quantity + 1, unit, MeasurementStatus.MEASURED, source=source,
        ))

    def report(self, case_id: str) -> CaseCostReport:
        ledger = self.get(case_id)
        if ledger is None:
            raise KeyError(case_id)
        return ledger.report()

    def events(self, case_id: str) -> list[CostLedgerEvent]:
        with self.connection() as db:
            rows = db.execute("SELECT event_json FROM case_cost_events WHERE case_id=? ORDER BY occurred_at,event_id", (case_id,)).fetchall()
        return [CostLedgerEvent.model_validate_json(row["event_json"]) for row in rows]
