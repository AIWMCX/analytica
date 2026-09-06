"""Tenant-scoped access and test-mode Stripe payment boundary.

This module deliberately keeps customer access, payment state, entitlement and
report release separate.  It does not calculate finance, mutate evidence, or
interpret a browser redirect as proof of payment.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Iterator
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MembershipRole(str, Enum):
    CUSTOMER = "CUSTOMER"
    REVIEWER = "REVIEWER"


class OrderStatus(str, Enum):
    DRAFT = "DRAFT"
    AWAITING_PAYMENT = "AWAITING_PAYMENT"
    PAID = "PAID"
    PAYMENT_FAILED = "PAYMENT_FAILED"
    REFUNDED = "REFUNDED"
    DISPUTED = "DISPUTED"
    CANCELLED = "CANCELLED"


class EntitlementStatus(str, Enum):
    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    REVOKED = "REVOKED"
    SUSPENDED = "SUSPENDED"


class ReportReleaseStatus(str, Enum):
    DRAFT = "DRAFT"
    QA_PENDING = "QA_PENDING"
    RELEASED = "RELEASED"
    REVOKED = "REVOKED"


class Customer(BaseModel):
    customer_id: str
    primary_email: str
    created_at: str
    tenant_id: str


class Tenant(BaseModel):
    tenant_id: str
    display_name: str
    created_at: str


class Order(BaseModel):
    order_id: str
    tenant_id: str
    case_id: str
    product_code: str
    stripe_price_id: str
    status: OrderStatus
    created_at: str


class Payment(BaseModel):
    payment_id: str
    order_id: str
    stripe_checkout_session_id: str | None = None
    stripe_payment_intent_id: str | None = None
    amount_minor: int = Field(ge=0)
    currency: str
    status: str


class PaymentEvent(BaseModel):
    provider_event_id: str
    event_type: str
    received_at: str
    processed_at: str | None = None
    payload_hash: str
    processing_status: str


class Entitlement(BaseModel):
    entitlement_id: str
    tenant_id: str
    case_id: str
    order_id: str
    status: EntitlementStatus
    granted_at: str | None = None
    revoked_at: str | None = None


class ReportRelease(BaseModel):
    report_id: str
    case_id: str
    tenant_id: str
    review_status: str
    release_status: ReportReleaseStatus
    released_at: str | None = None
    token_version: int


class Principal(BaseModel):
    subject_id: str
    role: MembershipRole
    expires_at: int


class CreateOrderRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    case_id: str = Field(min_length=4, max_length=160)
    product_code: str = Field(min_length=3, max_length=80)


class CheckoutResponse(BaseModel):
    order_id: str
    checkout_session_id: str
    checkout_url: str
    stripe_price_id: str
    mode: str = "stripe_test"


class WebhookResponse(BaseModel):
    duplicate: bool
    processing_status: str


class AccessTokenService:
    """HMAC-signed beta tokens. Production must inject a managed signing key."""

    def __init__(self, secret: str):
        if len(secret) < 24:
            raise ValueError("access signing secret must be at least 24 characters")
        self._secret = secret.encode("utf-8")

    def _encode(self, payload: dict[str, Any]) -> str:
        raw = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        body = base64.urlsafe_b64encode(raw).rstrip(b"=")
        signature = hmac.new(self._secret, body, hashlib.sha256).digest()
        return f"{body.decode()}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"

    def _decode(self, token: str) -> dict[str, Any]:
        try:
            body_text, signature_text = token.split(".", 1)
            body = body_text.encode("ascii")
            expected = hmac.new(self._secret, body, hashlib.sha256).digest()
            actual = base64.urlsafe_b64decode(signature_text + "=" * (-len(signature_text) % 4))
            if not hmac.compare_digest(expected, actual):
                raise ValueError("invalid token signature")
            payload = json.loads(base64.urlsafe_b64decode(body_text + "=" * (-len(body_text) % 4)))
            if int(payload["exp"]) <= int(datetime.now(timezone.utc).timestamp()):
                raise ValueError("token expired")
            return payload
        except (ValueError, KeyError, json.JSONDecodeError, UnicodeDecodeError) as exc:
            raise ValueError("invalid access token") from exc

    def _issue(self, subject_id: str, role: MembershipRole, ttl_seconds: int = 3600) -> str:
        return self._encode({"sub": subject_id, "role": role.value, "exp": int((datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).timestamp())})

    def issue_customer(self, customer_id: str, ttl_seconds: int = 3600) -> str:
        return self._issue(customer_id, MembershipRole.CUSTOMER, ttl_seconds)

    def issue_reviewer(self, reviewer_id: str, ttl_seconds: int = 3600) -> str:
        return self._issue(reviewer_id, MembershipRole.REVIEWER, ttl_seconds)

    def authenticate(self, authorization: str | None) -> Principal:
        if not authorization or not authorization.startswith("Bearer "):
            raise PermissionError("authentication is required")
        payload = self._decode(authorization.removeprefix("Bearer "))
        return Principal(subject_id=str(payload["sub"]), role=MembershipRole(payload["role"]), expires_at=int(payload["exp"]))

    def issue_report_link(self, report_id: str, tenant_id: str, token_version: int, ttl_seconds: int) -> str:
        if ttl_seconds <= 0:
            raise ValueError("report token ttl must be positive")
        return self._encode({"kind": "report", "report_id": report_id, "tenant_id": tenant_id, "version": token_version, "nonce": secrets.token_urlsafe(12), "exp": int((datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).timestamp())})

    def verify_report_link(self, token: str, report_id: str, tenant_id: str, token_version: int) -> None:
        payload = self._decode(token)
        if payload.get("kind") != "report" or payload.get("report_id") != report_id or payload.get("tenant_id") != tenant_id or payload.get("version") != token_version:
            raise PermissionError("report token is not authorized")


class PaymentAccessRepository:
    DEFAULT_PRODUCT_PRICES = {"CONCIERGE_CASE": "price_test_concierge_case"}

    def __init__(self, db_path: str | Path, product_prices: dict[str, str] | None = None):
        self.db_path = Path(db_path)
        self.product_prices = product_prices or self.DEFAULT_PRODUCT_PRICES
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.db_path)
        db.row_factory = sqlite3.Row
        try:
            yield db; db.commit()
        except Exception:
            db.rollback(); raise
        finally:
            db.close()

    def _initialize(self) -> None:
        with self.connection() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS customers (customer_id TEXT PRIMARY KEY, primary_email TEXT UNIQUE NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tenants (tenant_id TEXT PRIMARY KEY, display_name TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS tenant_memberships (tenant_id TEXT NOT NULL, customer_id TEXT NOT NULL, role TEXT NOT NULL, PRIMARY KEY (tenant_id, customer_id));
            CREATE TABLE IF NOT EXISTS case_ownership (case_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, case_id TEXT NOT NULL, product_code TEXT NOT NULL, stripe_price_id TEXT NOT NULL, status TEXT NOT NULL, created_at TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS payments (payment_id TEXT PRIMARY KEY, order_id TEXT UNIQUE NOT NULL, stripe_checkout_session_id TEXT UNIQUE, stripe_payment_intent_id TEXT UNIQUE, amount_minor INTEGER NOT NULL, currency TEXT NOT NULL, status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS payment_events (provider_event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, received_at TEXT NOT NULL, processed_at TEXT, payload_hash TEXT NOT NULL, processing_status TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS entitlements (entitlement_id TEXT PRIMARY KEY, tenant_id TEXT NOT NULL, case_id TEXT NOT NULL, order_id TEXT UNIQUE NOT NULL, status TEXT NOT NULL, granted_at TEXT, revoked_at TEXT);
            CREATE TABLE IF NOT EXISTS report_releases (report_id TEXT PRIMARY KEY, case_id TEXT UNIQUE NOT NULL, tenant_id TEXT NOT NULL, review_status TEXT NOT NULL, release_status TEXT NOT NULL, released_at TEXT, token_version INTEGER NOT NULL);
            CREATE TABLE IF NOT EXISTS commerce_audit_events (event_id TEXT PRIMARY KEY, event_type TEXT NOT NULL, case_id TEXT, order_id TEXT, occurred_at TEXT NOT NULL, detail TEXT NOT NULL);
            """)

    def bootstrap_customer(self, email: str, tenant_name: str) -> Customer:
        email = email.strip().lower()
        with self.connection() as db:
            row = db.execute("SELECT customer_id FROM customers WHERE primary_email=?", (email,)).fetchone()
            if row:
                tenant = db.execute("SELECT tenant_id FROM tenant_memberships WHERE customer_id=?", (row["customer_id"],)).fetchone()
                customer = db.execute("SELECT * FROM customers WHERE customer_id=?", (row["customer_id"],)).fetchone()
                return Customer(customer_id=customer["customer_id"], primary_email=customer["primary_email"], created_at=customer["created_at"], tenant_id=tenant["tenant_id"])
            now, customer_id, tenant_id = _now(), f"cus_{uuid4().hex}", f"ten_{uuid4().hex}"
            db.execute("INSERT INTO customers VALUES (?,?,?)", (customer_id, email, now))
            db.execute("INSERT INTO tenants VALUES (?,?,?)", (tenant_id, tenant_name.strip(), now))
            db.execute("INSERT INTO tenant_memberships VALUES (?,?,?)", (tenant_id, customer_id, MembershipRole.CUSTOMER.value))
        return Customer(customer_id=customer_id, primary_email=email, created_at=now, tenant_id=tenant_id)

    def assign_case(self, case_id: str, tenant_id: str) -> None:
        with self.connection() as db:
            db.execute("INSERT INTO case_ownership VALUES (?,?)", (case_id, tenant_id))
            db.execute("INSERT INTO report_releases VALUES (?,?,?,?,?,?,?)", (f"rpt_{uuid4().hex}", case_id, tenant_id, "QA_PENDING", ReportReleaseStatus.QA_PENDING.value, None, 1))

    def tenant_for_case(self, case_id: str) -> str | None:
        with self.connection() as db:
            row = db.execute("SELECT tenant_id FROM case_ownership WHERE case_id=?", (case_id,)).fetchone()
        return row["tenant_id"] if row else None

    def customer_can_access_case(self, customer_id: str, case_id: str) -> bool:
        with self.connection() as db:
            row = db.execute("""SELECT 1 FROM case_ownership c JOIN tenant_memberships m ON m.tenant_id=c.tenant_id WHERE c.case_id=? AND m.customer_id=? AND m.role=?""", (case_id, customer_id, MembershipRole.CUSTOMER.value)).fetchone()
        return row is not None

    def create_order(self, tenant_id: str, case_id: str, product_code: str) -> Order:
        if product_code not in self.product_prices:
            raise ValueError("unsupported product code")
        if self.tenant_for_case(case_id) != tenant_id:
            raise PermissionError("case ownership mismatch")
        order = Order(order_id=f"ord_{uuid4().hex}", tenant_id=tenant_id, case_id=case_id, product_code=product_code, stripe_price_id=self.product_prices[product_code], status=OrderStatus.DRAFT, created_at=_now())
        with self.connection() as db:
            db.execute("INSERT INTO orders VALUES (?,?,?,?,?,?,?)", tuple(order.model_dump().values()))
            self._audit(db, "order_created", case_id, order.order_id, "server-selected product and Stripe test price")
        return order

    def get_order(self, order_id: str) -> Order | None:
        with self.connection() as db: row = db.execute("SELECT * FROM orders WHERE order_id=?", (order_id,)).fetchone()
        return Order(**dict(row)) if row else None

    def attach_checkout(self, order_id: str, checkout_session_id: str, amount_minor: int, currency: str) -> Payment:
        order = self.get_order(order_id)
        if order is None: raise KeyError(order_id)
        if order.status not in {OrderStatus.DRAFT, OrderStatus.AWAITING_PAYMENT}: raise PermissionError("order cannot enter checkout")
        payment = Payment(payment_id=f"pay_{uuid4().hex}", order_id=order_id, stripe_checkout_session_id=checkout_session_id, amount_minor=amount_minor, currency=currency.lower(), status="PENDING")
        with self.connection() as db:
            db.execute("UPDATE orders SET status=? WHERE order_id=?", (OrderStatus.AWAITING_PAYMENT.value, order_id))
            db.execute("INSERT OR IGNORE INTO payments VALUES (?,?,?,?,?,?,?)", tuple(payment.model_dump().values()))
            self._audit(db, "checkout_created", order.case_id, order_id, "Stripe test Checkout session created")
        return self.list_payments(order_id)[0]

    def list_payments(self, order_id: str) -> list[Payment]:
        with self.connection() as db: rows = db.execute("SELECT * FROM payments WHERE order_id=?", (order_id,)).fetchall()
        return [Payment(**dict(row)) for row in rows]

    def record_event_once(self, event_id: str, event_type: str, payload: bytes) -> bool:
        event = PaymentEvent(provider_event_id=event_id, event_type=event_type, received_at=_now(), payload_hash=hashlib.sha256(payload).hexdigest(), processing_status="RECEIVED")
        with self.connection() as db:
            try:
                db.execute("INSERT INTO payment_events VALUES (?,?,?,?,?,?)", tuple(event.model_dump().values()))
                return True
            except sqlite3.IntegrityError:
                return False

    def get_payment_event(self, event_id: str) -> PaymentEvent | None:
        with self.connection() as db: row = db.execute("SELECT * FROM payment_events WHERE provider_event_id=?", (event_id,)).fetchone()
        return PaymentEvent(**dict(row)) if row else None

    def mark_event(self, event_id: str, status: str) -> None:
        with self.connection() as db: db.execute("UPDATE payment_events SET processing_status=?, processed_at=? WHERE provider_event_id=?", (status, _now(), event_id))

    def mark_paid(self, order_id: str, payment_intent_id: str, amount_minor: int, currency: str) -> None:
        order = self.get_order(order_id)
        if order is None: raise KeyError(order_id)
        with self.connection() as db:
            db.execute("UPDATE orders SET status=? WHERE order_id=?", (OrderStatus.PAID.value, order_id))
            db.execute("UPDATE payments SET status='PAID', stripe_payment_intent_id=?, amount_minor=?, currency=? WHERE order_id=?", (payment_intent_id, amount_minor, currency.lower(), order_id))
            existing = db.execute("SELECT entitlement_id FROM entitlements WHERE order_id=?", (order_id,)).fetchone()
            if not existing:
                db.execute("INSERT INTO entitlements VALUES (?,?,?,?,?,?,?)", (f"ent_{uuid4().hex}", order.tenant_id, order.case_id, order_id, EntitlementStatus.ACTIVE.value, _now(), None))
            self._audit(db, "payment_verified", order.case_id, order_id, "verified Stripe webhook")
            self._audit(db, "entitlement_activated", order.case_id, order_id, "payment status PAID")

    def revoke_for_order(self, order_id: str, status: OrderStatus, event_type: str) -> None:
        order = self.get_order(order_id)
        if order is None: raise KeyError(order_id)
        with self.connection() as db:
            db.execute("UPDATE orders SET status=? WHERE order_id=?", (status.value, order_id))
            db.execute("UPDATE payments SET status=? WHERE order_id=?", (status.value, order_id))
            db.execute("UPDATE entitlements SET status=?, revoked_at=? WHERE order_id=?", (EntitlementStatus.REVOKED.value, _now(), order_id))
            db.execute("UPDATE report_releases SET release_status=?, token_version=token_version+1 WHERE case_id=?", (ReportReleaseStatus.REVOKED.value, order.case_id))
            self._audit(db, event_type, order.case_id, order_id, "verified Stripe webhook")
            self._audit(db, "entitlement_revoked", order.case_id, order_id, status.value)

    def get_report_release_for_case(self, case_id: str) -> ReportRelease | None:
        with self.connection() as db: row = db.execute("SELECT * FROM report_releases WHERE case_id=?", (case_id,)).fetchone()
        return ReportRelease(**dict(row)) if row else None

    def get_report_release(self, report_id: str) -> ReportRelease | None:
        with self.connection() as db: row = db.execute("SELECT * FROM report_releases WHERE report_id=?", (report_id,)).fetchone()
        return ReportRelease(**dict(row)) if row else None

    def mark_report_released(self, case_id: str, tenant_id: str, reviewer_id: str) -> ReportRelease:
        release = self.get_report_release_for_case(case_id)
        if release is None or release.tenant_id != tenant_id: raise PermissionError("case ownership mismatch")
        if not self.has_active_entitlement(tenant_id, case_id): raise PermissionError("active entitlement is required")
        with self.connection() as db:
            db.execute("UPDATE report_releases SET review_status=?, release_status=?, released_at=? WHERE case_id=?", (f"APPROVED:{reviewer_id}", ReportReleaseStatus.RELEASED.value, _now(), case_id))
            self._audit(db, "report_released", case_id, None, "reviewer-approved release")
        return self.get_report_release_for_case(case_id)  # type: ignore[return-value]

    def has_active_entitlement(self, tenant_id: str, case_id: str) -> bool:
        with self.connection() as db: row = db.execute("SELECT 1 FROM entitlements WHERE tenant_id=? AND case_id=? AND status=?", (tenant_id, case_id, EntitlementStatus.ACTIVE.value)).fetchone()
        return row is not None

    def can_access_released_report(self, tenant_id: str, case_id: str) -> bool:
        release = self.get_report_release_for_case(case_id)
        return bool(release and release.tenant_id == tenant_id and release.release_status == ReportReleaseStatus.RELEASED and self.has_active_entitlement(tenant_id, case_id))

    def can_release_report(self, tenant_id: str, case_id: str, *, qa_blockers: list[str]) -> dict[str, object]:
        """Return every material delivery blocker; callers never infer from one flag."""
        blockers = list(qa_blockers)
        if self.tenant_for_case(case_id) != tenant_id:
            blockers.append("CASE_OWNERSHIP_MISSING")
        with self.connection() as db:
            paid = db.execute("SELECT 1 FROM orders WHERE tenant_id=? AND case_id=? AND status=?", (tenant_id, case_id, OrderStatus.PAID.value)).fetchone()
        if paid is None:
            blockers.append("PAYMENT_NOT_VERIFIED")
        if not self.has_active_entitlement(tenant_id, case_id):
            blockers.append("ENTITLEMENT_NOT_ACTIVE")
        release = self.get_report_release_for_case(case_id)
        if release is None or release.release_status == ReportReleaseStatus.REVOKED:
            blockers.append("REPORT_RELEASE_NOT_ALLOWED")
        return {"ready": not blockers, "blockers": blockers}

    @staticmethod
    def _audit(db: sqlite3.Connection, event_type: str, case_id: str | None, order_id: str | None, detail: str) -> None:
        db.execute("INSERT INTO commerce_audit_events VALUES (?,?,?,?,?,?)", (f"cae_{uuid4().hex}", event_type, case_id, order_id, _now(), detail))


class FakeStripeEvent(BaseModel):
    event_id: str
    event_type: str
    payload: dict[str, Any]
    raw_body: bytes
    signature: str


class FakeStripeTestGateway:
    """Test-only gateway. It has no network access and cannot charge a card."""
    secret = b"stripe-test-webhook-secret"

    def create_checkout(self, order: Order) -> CheckoutResponse:
        return CheckoutResponse(order_id=order.order_id, checkout_session_id=f"cs_test_{uuid4().hex}", checkout_url="https://checkout.stripe.test/session", stripe_price_id=order.stripe_price_id)

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> FakeStripeEvent:
        expected = hmac.new(self.secret, raw_body, hashlib.sha256).hexdigest()
        if not signature or not hmac.compare_digest(expected, signature): raise ValueError("invalid Stripe signature")
        payload = json.loads(raw_body)
        return FakeStripeEvent(event_id=payload["id"], event_type=payload["type"], payload=payload["data"]["object"], raw_body=raw_body, signature=signature)

    def _event(self, event_id: str, event_type: str, payload: dict[str, Any]) -> FakeStripeEvent:
        raw = json.dumps({"id": event_id, "type": event_type, "data": {"object": payload}}, sort_keys=True, separators=(",", ":")).encode()
        return FakeStripeEvent(event_id=event_id, event_type=event_type, payload=payload, raw_body=raw, signature=hmac.new(self.secret, raw, hashlib.sha256).hexdigest())

    def payment_succeeded(self, event_id: str, order_id: str, checkout_session_id: str, payment_intent_id: str) -> FakeStripeEvent:
        return self._event(event_id, "payment_intent.succeeded", {"id": payment_intent_id, "metadata": {"order_id": order_id}, "checkout_session_id": checkout_session_id, "amount_received": 4999, "currency": "usd"})

    def refunded(self, event_id: str, order_id: str, payment_intent_id: str) -> FakeStripeEvent:
        return self._event(event_id, "charge.refunded", {"payment_intent": payment_intent_id, "metadata": {"order_id": order_id}})


class UnavailableStripeGateway:
    """Prevents an accidental fake checkout outside an explicitly injected test."""
    def create_checkout(self, order: Order) -> CheckoutResponse:
        raise RuntimeError("Stripe test credentials are not configured")

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> FakeStripeEvent:
        raise RuntimeError("Stripe test credentials are not configured")


class StripeTestGateway:
    """Official Stripe SDK boundary. Only `sk_test_` keys are accepted."""
    def __init__(self, secret_key: str, webhook_secret: str, success_url: str, cancel_url: str):
        if not secret_key.startswith("sk_test_"): raise ValueError("only Stripe test-mode keys are permitted")
        self.secret_key, self.webhook_secret, self.success_url, self.cancel_url = secret_key, webhook_secret, success_url, cancel_url

    def _stripe(self):
        try:
            import stripe
        except ImportError as exc:
            raise RuntimeError("Stripe SDK is not installed") from exc
        stripe.api_key = self.secret_key
        return stripe

    def create_checkout(self, order: Order) -> CheckoutResponse:
        session = self._stripe().checkout.Session.create(mode="payment", line_items=[{"price": order.stripe_price_id, "quantity": 1}], success_url=self.success_url, cancel_url=self.cancel_url, metadata={"order_id": order.order_id, "case_id": order.case_id})
        return CheckoutResponse(order_id=order.order_id, checkout_session_id=session.id, checkout_url=session.url, stripe_price_id=order.stripe_price_id)

    def verify_webhook(self, raw_body: bytes, signature: str | None) -> FakeStripeEvent:
        if not signature: raise ValueError("missing Stripe signature")
        event = self._stripe().Webhook.construct_event(raw_body, signature, self.webhook_secret)
        payload = event.data.object.to_dict_recursive() if hasattr(event.data.object, "to_dict_recursive") else dict(event.data.object)
        return FakeStripeEvent(event_id=event.id, event_type=event.type, payload=payload, raw_body=raw_body, signature=signature)
