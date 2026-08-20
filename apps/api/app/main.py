from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .domain import AnalysisJob, AnalysisReport, AnalysisStatus
from .fixtures import build_demo_report
from .payments import DemoPaymentProvider, PaymentCheckout
from .readiness import build_readiness
from .repository import SQLiteAnalysisRepository
from .service import AnalysisService


class CheckoutRequest(BaseModel):
    email: str = Field(min_length=5, max_length=254)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("valid email is required")
        return value


class CreateAnalysisRequest(BaseModel):
    business_activity: str = Field(min_length=2, max_length=160)
    geography: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=5, max_length=254)
    payment_token: str = Field(min_length=8, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        value = value.strip().lower()
        if "@" not in value or value.startswith("@") or value.endswith("@"):
            raise ValueError("valid email is required")
        return value


class CreateAnalysisResponse(BaseModel):
    analysis_id: str
    status: str
    status_url: str
    report_url: str


def create_app(db_path: str | Path | None = None, stage_delay: float | None = None) -> FastAPI:
    app = FastAPI(
        title="Analytica API",
        version="0.2.0",
        description="Evidence-driven historical business intelligence — workable MVP prototype",
    )

    resolved_db = Path(db_path or os.environ.get("ANALYTICA_DB_PATH", ".data/analytica.db"))
    delay = float(os.environ.get("ANALYTICA_STAGE_DELAY", "0.08")) if stage_delay is None else stage_delay
    repository = SQLiteAnalysisRepository(resolved_db)
    service = AnalysisService(repository, stage_delay=delay)
    payments = DemoPaymentProvider()
    app.state.repository = repository
    app.state.analysis_service = service
    app.state.payment_provider = payments

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "service": "analytica-api", "version": app.version, "stage": "workable_mvp_prototype"}

    @app.get("/readiness")
    def readiness() -> dict:
        return build_readiness()

    @app.get("/pricing")
    def pricing() -> dict:
        return {
            "initial_analysis_amount_cents": 100,
            "follow_up_question_amount_cents": 100,
            "currency": "USD",
            "mode": "prototype_demo",
            "real_charge": False,
        }

    @app.post("/payments/checkout", response_model=PaymentCheckout, status_code=status.HTTP_201_CREATED)
    def checkout(request: CheckoutRequest) -> PaymentCheckout:
        return payments.checkout(request.email)

    @app.post("/analyses", response_model=CreateAnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
    def create_analysis(request: CreateAnalysisRequest) -> CreateAnalysisResponse:
        if not payments.validate(request.payment_token):
            raise HTTPException(status_code=402, detail="valid prototype payment authorization is required")
        try:
            analysis_id = service.create_analysis(
                business_activity=request.business_activity,
                geography=request.geography,
                email=request.email,
                payment_token=request.payment_token,
                run_async=True,
            )
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc
        job = repository.get_job(analysis_id)
        return CreateAnalysisResponse(
            analysis_id=analysis_id,
            status=job.status.value,
            status_url=f"/analyses/{analysis_id}/status",
            report_url=f"/analyses/{analysis_id}",
        )

    @app.get("/analyses/{analysis_id}/status", response_model=AnalysisJob)
    def get_analysis_status(analysis_id: str) -> AnalysisJob:
        if analysis_id == "demo_packaging_ny_v1":
            return AnalysisJob(
                analysis_id=analysis_id,
                business_activity="Packaging manufacturing",
                geography="New York",
                email="demo@analytica.local",
                payment_token="demo_pay_static",
                status=AnalysisStatus.COMPLETED,
                progress_percent=100,
                stage_label="Analysis complete",
                created_at="2026-08-19T00:00:00+00:00",
                updated_at="2026-08-19T00:00:00+00:00",
            )
        job = repository.get_job(analysis_id)
        if job is None:
            raise HTTPException(status_code=404, detail="analysis not found")
        return job

    @app.get("/analyses/{analysis_id}", response_model=AnalysisReport)
    def get_analysis(analysis_id: str) -> AnalysisReport:
        if analysis_id == "demo_packaging_ny_v1":
            return build_demo_report()
        job = repository.get_job(analysis_id)
        if job is None:
            raise HTTPException(status_code=404, detail="analysis not found")
        report = repository.get_report(analysis_id)
        if report is None:
            raise HTTPException(status_code=409, detail={"status": job.status.value, "stage": job.stage_label, "progress_percent": job.progress_percent})
        return report

    web_dir = Path(__file__).resolve().parents[3] / "apps" / "web-preview"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web-preview")
    return app


app = create_app()
