from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from .domain import AnalysisJob, AnalysisReport, AnalysisStatus
from .cost_ledger import CaseCostLedgerRepository, CaseCostReport, CostMeasurement
from .entities import ResolutionDecision, ResolutionStatus
from .evidence_repository import SQLiteEvidenceRepository
from .evidence_graph import EvidenceGraphCase, EvidenceGraphService, RecommendationLineage
from .fixtures import build_demo_report
from .intelligence import SQLiteRelationshipRepository
from .payments import DemoPaymentProvider, PaymentCheckout
from .payment_access import (
    AccessTokenService,
    CheckoutResponse,
    CreateOrderRequest,
    FakeStripeTestGateway,
    MembershipRole,
    OrderStatus,
    PaymentAccessRepository,
    ReportReleaseStatus,
    StripeTestGateway,
    UnavailableStripeGateway,
    WebhookResponse,
)
from .readiness import build_readiness
from .repository import SQLiteAnalysisRepository
from .reviewer_workflow import ReviewActionType, ReviewerInspection, ReviewerWorkflow, SQLiteReviewerRepository
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


class ReviewerActionRequest(BaseModel):
    action_type: ReviewActionType
    reviewer_id: str = Field(min_length=1, max_length=120)
    reason: str | None = Field(default=None, max_length=2000)
    assumption_id: str | None = Field(default=None, max_length=160)
    recommendation_text: str | None = Field(default=None, max_length=4000)


def create_app(
    db_path: str | Path | None = None,
    stage_delay: float | None = None,
    stripe_gateway=None,
    access_signing_secret: str | None = None,
) -> FastAPI:
    app = FastAPI(
        title="Analytica API",
        version="0.2.0",
        description="Evidence-driven historical business intelligence — workable MVP prototype",
    )

    resolved_db = Path(db_path or os.environ.get("ANALYTICA_DB_PATH", ".data/analytica.db"))
    delay = float(os.environ.get("ANALYTICA_STAGE_DELAY", "0.08")) if stage_delay is None else stage_delay
    repository = SQLiteAnalysisRepository(resolved_db)
    cost_ledger = CaseCostLedgerRepository(resolved_db)
    service = AnalysisService(repository, stage_delay=delay, cost_ledger=cost_ledger)
    payments = DemoPaymentProvider()
    app.state.repository = repository
    app.state.analysis_service = service
    app.state.payment_provider = payments
    app.state.cost_ledger = cost_ledger
    app.state.evidence_repository = SQLiteEvidenceRepository(resolved_db)
    app.state.reviewer_repository = SQLiteReviewerRepository(resolved_db)
    app.state.reviewer_workflow = ReviewerWorkflow(app.state.reviewer_repository, app.state.evidence_repository, cost_ledger=cost_ledger)
    app.state.relationship_repository = SQLiteRelationshipRepository(resolved_db)
    app.state.evidence_graph = EvidenceGraphService()
    app.state.payment_access = PaymentAccessRepository(resolved_db, {"CONCIERGE_CASE": os.environ.get("STRIPE_CONCIERGE_PRICE_ID", "price_test_concierge_case")})
    # The generated local secret is deliberately development-only. Deployments must
    # inject a managed value and an external identity issuer before customer launch.
    configured_signing_secret = access_signing_secret or os.environ.get("ANALYTICA_ACCESS_TOKEN_SECRET")
    if os.environ.get("ANALYTICA_ENVIRONMENT") == "production" and not configured_signing_secret:
        raise RuntimeError("ANALYTICA_ACCESS_TOKEN_SECRET must be configured in production")
    app.state.access_tokens = AccessTokenService(configured_signing_secret or "development-only-signing-secret-change-before-deployment")
    if stripe_gateway is not None:
        app.state.stripe_gateway = stripe_gateway
    elif os.environ.get("STRIPE_SECRET_KEY") and os.environ.get("STRIPE_WEBHOOK_SECRET"):
        app.state.stripe_gateway = StripeTestGateway(
            os.environ["STRIPE_SECRET_KEY"], os.environ["STRIPE_WEBHOOK_SECRET"],
            os.environ.get("ANALYTICA_STRIPE_SUCCESS_URL", "https://example.invalid/payment/success"),
            os.environ.get("ANALYTICA_STRIPE_CANCEL_URL", "https://example.invalid/payment/cancel"),
        )
    else:
        app.state.stripe_gateway = UnavailableStripeGateway()

    def principal_for(request: Request):
        try:
            return app.state.access_tokens.authenticate(request.headers.get("Authorization"))
        except (PermissionError, ValueError) as exc:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="authentication is required", headers={"WWW-Authenticate": "Bearer"}) from exc

    def owned_case(request: Request, case_id: str):
        principal = principal_for(request)
        if principal.role != MembershipRole.CUSTOMER or not app.state.payment_access.customer_can_access_case(principal.subject_id, case_id):
            # Deliberately conceal cross-tenant case existence.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="case not found")
        return principal

    def reviewer_principal(request: Request):
        principal = principal_for(request)
        if principal.role != MembershipRole.REVIEWER:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="reviewer role is required")
        return principal

    def report_for(analysis_id: str) -> AnalysisReport:
        if analysis_id == "demo_packaging_ny_v1":
            return build_demo_report()
        job = repository.get_job(analysis_id)
        if job is None:
            raise HTTPException(status_code=404, detail="analysis not found")
        report = repository.get_report(analysis_id)
        if report is None:
            raise HTTPException(status_code=409, detail={"status": job.status.value, "stage": job.stage_label, "progress_percent": job.progress_percent})
        return report

    def reviewer_case_for(analysis_id: str):
        existing = app.state.reviewer_repository.get_case(analysis_id)
        if existing is not None:
            return existing
        report = report_for(analysis_id)
        identity = report.entity_identity
        resolution = ResolutionDecision(
            status=ResolutionStatus.RESOLVED if identity.resolution_status == "RESOLVED" else ResolutionStatus.UNRESOLVED,
            entity_id=identity.entity_id if identity.resolution_status == "RESOLVED" else None,
            confidence=1 if identity.resolution_status == "RESOLVED" else 0,
            matching_signals=3 if identity.resolution_status == "RESOLVED" else 0,
        )
        return app.state.reviewer_workflow.open_case(
            case_id=analysis_id, entity=resolution, packet_ids=[], assumptions=[], financial_results=[],
            findings=[item.finding_id for item in report.findings], recommendation=report.decision_brief.recommendation,
        )

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

    @app.get("/internal/cases/{case_id}/cost-ledger", response_model=CaseCostReport)
    def internal_case_cost_ledger(case_id: str, request: Request) -> CaseCostReport:
        reviewer_principal(request)
        if case_id != "demo_packaging_ny_v1" and repository.get_job(case_id) is None:
            raise HTTPException(status_code=404, detail="analysis not found")
        cost_ledger.open_case(case_id)
        return cost_ledger.report(case_id)

    @app.post("/internal/cases/{case_id}/cost-ledger/measurements", response_model=CaseCostReport)
    def record_internal_case_cost(case_id: str, measurement: CostMeasurement, request: Request) -> CaseCostReport:
        reviewer_principal(request)
        if case_id != "demo_packaging_ny_v1" and repository.get_job(case_id) is None:
            raise HTTPException(status_code=404, detail="analysis not found")
        cost_ledger.record(case_id, measurement)
        return cost_ledger.report(case_id)

    @app.post("/payments/checkout", response_model=PaymentCheckout, status_code=status.HTTP_201_CREATED)
    def checkout(request: CheckoutRequest) -> PaymentCheckout:
        return payments.checkout(request.email)

    @app.post("/commerce/orders", status_code=status.HTTP_201_CREATED)
    def create_order(request: Request, body: CreateOrderRequest) -> dict:
        principal = owned_case(request, body.case_id)
        tenant_id = app.state.payment_access.tenant_for_case(body.case_id)
        try:
            order = app.state.payment_access.create_order(tenant_id, body.case_id, body.product_code)  # type: ignore[arg-type]
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        return order.model_dump(mode="json")

    @app.post("/commerce/orders/{order_id}/checkout", response_model=CheckoutResponse, status_code=status.HTTP_201_CREATED)
    def create_stripe_checkout(order_id: str, request: Request) -> CheckoutResponse:
        principal = principal_for(request)
        order = app.state.payment_access.get_order(order_id)
        if order is None or principal.role != MembershipRole.CUSTOMER or not app.state.payment_access.customer_can_access_case(principal.subject_id, order.case_id):
            raise HTTPException(status_code=404, detail="order not found")
        try:
            checkout = app.state.stripe_gateway.create_checkout(order)
            app.state.payment_access.attach_checkout(order_id, checkout.checkout_session_id, amount_minor=0, currency="usd")
            return checkout
        except (ValueError, RuntimeError, PermissionError) as exc:
            raise HTTPException(status_code=503, detail="Stripe test checkout is unavailable") from exc

    @app.post("/payments/stripe/webhook", response_model=WebhookResponse)
    async def stripe_webhook(request: Request) -> WebhookResponse:
        raw_body = await request.body()
        try:
            event = app.state.stripe_gateway.verify_webhook(raw_body, request.headers.get("Stripe-Signature"))
        except (ValueError, RuntimeError):
            raise HTTPException(status_code=400, detail="invalid Stripe webhook")
        if not app.state.payment_access.record_event_once(event.event_id, event.event_type, raw_body):
            return WebhookResponse(duplicate=True, processing_status="DUPLICATE")
        order_id = str(event.payload.get("metadata", {}).get("order_id", ""))
        if not order_id or app.state.payment_access.get_order(order_id) is None:
            app.state.payment_access.mark_event(event.event_id, "UNKNOWN_ORDER")
            return WebhookResponse(duplicate=False, processing_status="UNKNOWN_ORDER")
        try:
            if event.event_type == "payment_intent.succeeded":
                amount_minor = event.payload.get("amount_received")
                currency = event.payload.get("currency")
                if not isinstance(amount_minor, int) or amount_minor < 0 or not isinstance(currency, str) or len(currency) != 3:
                    app.state.payment_access.mark_event(event.event_id, "INVALID_PAYMENT_AMOUNT")
                    raise HTTPException(status_code=409, detail="Stripe payment amount is invalid")
                app.state.payment_access.mark_paid(order_id, str(event.payload.get("id", "")), amount_minor, currency)
                app.state.payment_access.mark_event(event.event_id, "PAID")
                return WebhookResponse(duplicate=False, processing_status="PAID")
            if event.event_type == "payment_intent.payment_failed":
                app.state.payment_access.revoke_for_order(order_id, status=OrderStatus.PAYMENT_FAILED, event_type="payment_failed")
                app.state.payment_access.mark_event(event.event_id, "PAYMENT_FAILED")
                return WebhookResponse(duplicate=False, processing_status="PAYMENT_FAILED")
            if event.event_type == "charge.refunded":
                app.state.payment_access.revoke_for_order(order_id, status=OrderStatus.REFUNDED, event_type="refund_received")
                app.state.payment_access.mark_event(event.event_id, "REFUNDED")
                return WebhookResponse(duplicate=False, processing_status="REFUNDED")
            if event.event_type == "charge.dispute.created":
                app.state.payment_access.revoke_for_order(order_id, status=OrderStatus.DISPUTED, event_type="dispute_received")
                app.state.payment_access.mark_event(event.event_id, "DISPUTED")
                return WebhookResponse(duplicate=False, processing_status="DISPUTED")
        except (KeyError, PermissionError, ValueError):
            app.state.payment_access.mark_event(event.event_id, "PROCESSING_ERROR")
            raise HTTPException(status_code=409, detail="Stripe event could not be applied")
        app.state.payment_access.mark_event(event.event_id, "IGNORED")
        return WebhookResponse(duplicate=False, processing_status="IGNORED")

    @app.get("/customer/cases/{case_id}")
    def customer_case(case_id: str, request: Request) -> dict:
        owned_case(request, case_id)
        release = app.state.payment_access.get_report_release_for_case(case_id)
        return {"case_id": case_id, "report_release_status": release.release_status if release else None}

    @app.get("/customer/cases/{case_id}/report", response_model=AnalysisReport)
    def customer_report(case_id: str, request: Request) -> AnalysisReport:
        principal = owned_case(request, case_id)
        tenant_id = app.state.payment_access.tenant_for_case(case_id)
        if not app.state.payment_access.can_access_released_report(tenant_id, case_id):  # type: ignore[arg-type]
            raise HTTPException(status_code=403, detail="report is not released for this customer")
        return report_for(case_id)

    @app.post("/customer/cases/{case_id}/analysis")
    def start_paid_case_analysis(case_id: str, request: Request) -> dict:
        """Do not substitute a paid case with the synthetic demonstrator."""
        owned_case(request, case_id)
        tenant_id = app.state.payment_access.tenant_for_case(case_id)
        if not app.state.payment_access.has_active_entitlement(tenant_id, case_id):  # type: ignore[arg-type]
            raise HTTPException(status_code=409, detail={"code": "ENTITLEMENT_NOT_ACTIVE"})
        raise HTTPException(status_code=409, detail={"code": "LIVE_RESEARCH_NOT_AVAILABLE", "message": "Live research is not connected to customer delivery in this build."})

    @app.get("/reports/{report_id}/access", response_model=AnalysisReport)
    def signed_report_access(report_id: str, token: str) -> AnalysisReport:
        release = app.state.payment_access.get_report_release(report_id)
        if release is None or release.release_status != ReportReleaseStatus.RELEASED or not app.state.payment_access.has_active_entitlement(release.tenant_id, release.case_id):
            raise HTTPException(status_code=403, detail="report is not available")
        try:
            app.state.access_tokens.verify_report_link(token, report_id, release.tenant_id, release.token_version)
        except (PermissionError, ValueError):
            raise HTTPException(status_code=403, detail="report link is invalid or expired")
        return report_for(release.case_id)

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
        owner = app.state.payment_access.bootstrap_customer(request.email, request.email.split("@", 1)[0])
        app.state.payment_access.assign_case(analysis_id, owner.tenant_id)
        return CreateAnalysisResponse(
            analysis_id=analysis_id,
            status=job.status.value,
            status_url=f"/analyses/{analysis_id}/status",
            report_url=f"/analyses/{analysis_id}",
        )

    @app.get("/analyses/{analysis_id}/status", response_model=AnalysisJob)
    def get_analysis_status(analysis_id: str, request: Request) -> AnalysisJob:
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
        owned_case(request, analysis_id)
        job = repository.get_job(analysis_id)
        if job is None:
            raise HTTPException(status_code=404, detail="analysis not found")
        return job

    @app.get("/analyses/{analysis_id}", response_model=AnalysisReport)
    def get_analysis(analysis_id: str, request: Request) -> AnalysisReport:
        if analysis_id != "demo_packaging_ny_v1":
            owned_case(request, analysis_id)
        return report_for(analysis_id)

    @app.get("/analyses/{analysis_id}/evidence-graph", response_model=EvidenceGraphCase)
    def get_evidence_graph(analysis_id: str, request: Request) -> EvidenceGraphCase:
        if analysis_id != "demo_packaging_ny_v1":
            owned_case(request, analysis_id)
        case = app.state.evidence_graph.build_case(report_for(analysis_id))
        app.state.evidence_graph.persist_case(case, app.state.relationship_repository)
        return case

    @app.get("/analyses/{analysis_id}/evidence-graph/recommendations/{recommendation_id}/lineage", response_model=RecommendationLineage)
    def get_recommendation_lineage(analysis_id: str, recommendation_id: str, request: Request) -> RecommendationLineage:
        if analysis_id != "demo_packaging_ny_v1":
            owned_case(request, analysis_id)
        case = app.state.evidence_graph.build_case(report_for(analysis_id))
        app.state.evidence_graph.persist_case(case, app.state.relationship_repository)
        try:
            return app.state.evidence_graph.explain_recommendation(case, recommendation_id)
        except KeyError as exc:
            raise HTTPException(status_code=404, detail="recommendation not found") from exc

    @app.get("/review/cases/{case_id}", response_model=ReviewerInspection)
    def inspect_reviewer_case(case_id: str, request: Request) -> ReviewerInspection:
        reviewer_principal(request)
        reviewer_case_for(case_id)
        return app.state.reviewer_workflow.inspect(case_id)

    @app.post("/review/cases/{case_id}/actions", response_model=ReviewerInspection)
    def apply_reviewer_action(case_id: str, request: ReviewerActionRequest, http_request: Request) -> ReviewerInspection:
        principal = reviewer_principal(http_request)
        if request.reviewer_id != principal.subject_id:
            raise HTTPException(status_code=403, detail="reviewer identity must match authenticated principal")
        reviewer_case_for(case_id)
        try:
            app.state.reviewer_workflow.apply(
                case_id, request.action_type, reviewer_id=request.reviewer_id, reason=request.reason,
                assumption_id=request.assumption_id, recommendation_text=request.recommendation_text,
            )
        except (KeyError, ValueError, PermissionError) as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return app.state.reviewer_workflow.inspect(case_id)

    @app.post("/review/cases/{case_id}/release")
    def release_customer_report(case_id: str, request: Request) -> dict:
        reviewer = reviewer_principal(request)
        reviewer_case_for(case_id)
        inspection = app.state.reviewer_workflow.inspect(case_id)
        tenant_id = app.state.payment_access.tenant_for_case(case_id)
        if tenant_id is None:
            raise HTTPException(status_code=409, detail={"ready": False, "blockers": ["CASE_OWNERSHIP_MISSING"]})
        gate = app.state.payment_access.can_release_report(tenant_id, case_id, qa_blockers=inspection.delivery_gate.blockers)
        if not gate["ready"]:
            raise HTTPException(status_code=409, detail=gate)
        release = app.state.payment_access.mark_report_released(case_id, tenant_id, reviewer.subject_id)
        return {"ready": True, "report_id": release.report_id, "release_status": release.release_status}

    web_dir = Path(__file__).resolve().parents[3] / "apps" / "web-preview"
    if web_dir.exists():
        app.mount("/", StaticFiles(directory=web_dir, html=True), name="web-preview")
    return app


app = create_app()
