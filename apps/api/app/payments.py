from __future__ import annotations

from uuid import uuid4

from pydantic import BaseModel


class PaymentCheckout(BaseModel):
    payment_token: str
    amount_cents: int = 100
    currency: str = "USD"
    mode: str = "prototype_demo"
    status: str = "authorized"
    real_charge: bool = False
    notice: str = "Prototype checkout only — no money is charged in this build."


class DemoPaymentProvider:
    amount_cents = 100

    def checkout(self, email: str) -> PaymentCheckout:
        if "@" not in email:
            raise ValueError("valid email is required")
        return PaymentCheckout(payment_token=f"demo_pay_{uuid4().hex[:16]}")

    def validate(self, payment_token: str) -> bool:
        return payment_token.startswith("demo_pay_") and len(payment_token) > len("demo_pay_")
