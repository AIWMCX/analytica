import tempfile
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.app.main import create_app
from apps.api.app.fixtures import build_demo_report
from apps.api.app.payment_access import (
    FakeStripeTestGateway,
    OrderStatus,
    PaymentAccessRepository,
    ReportReleaseStatus,
)


class PaymentAccessTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.gateway = FakeStripeTestGateway()
        self.app = create_app(
            db_path=Path(self.tempdir.name) / "access.db",
            stage_delay=0,
            stripe_gateway=self.gateway,
            access_signing_secret="test-signing-secret-with-adequate-length",
        )
        self.client = TestClient(self.app)
        self.repo: PaymentAccessRepository = self.app.state.payment_access
        self.alice = self.repo.bootstrap_customer("alice@example.com", "Alice Holdings")
        self.bob = self.repo.bootstrap_customer("bob@example.com", "Bob Holdings")
        self.alice_headers = {"Authorization": f"Bearer {self.app.state.access_tokens.issue_customer(self.alice.customer_id)}"}
        self.bob_headers = {"Authorization": f"Bearer {self.app.state.access_tokens.issue_customer(self.bob.customer_id)}"}
        self.reviewer_headers = {"Authorization": f"Bearer {self.app.state.access_tokens.issue_reviewer('reviewer_01')}"}
        self.case_id = "case_alice_001"
        self.repo.assign_case(self.case_id, self.alice.tenant_id)
        self.app.state.repository.create_job(self.case_id, "Packaging manufacturing", "New York", "alice@example.com", "test_only")
        self.app.state.repository.save_report(build_demo_report(analysis_id=self.case_id))

    def tearDown(self):
        self.client.close()
        self.tempdir.cleanup()

    def test_tenant_b_cannot_read_or_mutate_tenant_a_case(self):
        order = self.client.post("/commerce/orders", headers=self.alice_headers, json={"case_id": self.case_id, "product_code": "CONCIERGE_CASE"})
        self.assertEqual(order.status_code, 201)
        self.assertEqual(self.client.get(f"/customer/cases/{self.case_id}", headers=self.bob_headers).status_code, 404)
        self.assertEqual(self.client.post(f"/commerce/orders/{order.json()['order_id']}/checkout", headers=self.bob_headers).status_code, 404)

    def test_server_chooses_price_and_client_amount_is_rejected(self):
        response = self.client.post("/commerce/orders", headers=self.alice_headers, json={
            "case_id": self.case_id, "product_code": "CONCIERGE_CASE", "amount": 1, "stripe_price_id": "price_attacker",
        })
        self.assertEqual(response.status_code, 422)
        created = self.client.post("/commerce/orders", headers=self.alice_headers, json={"case_id": self.case_id, "product_code": "CONCIERGE_CASE"})
        checkout = self.client.post(f"/commerce/orders/{created.json()['order_id']}/checkout", headers=self.alice_headers)
        self.assertEqual(checkout.status_code, 201)
        self.assertEqual(checkout.json()["mode"], "stripe_test")
        self.assertEqual(checkout.json()["stripe_price_id"], "price_test_concierge_case")

    def test_verified_webhook_is_idempotent_and_payment_does_not_release_report(self):
        created = self.client.post("/commerce/orders", headers=self.alice_headers, json={"case_id": self.case_id, "product_code": "CONCIERGE_CASE"}).json()
        checkout = self.client.post(f"/commerce/orders/{created['order_id']}/checkout", headers=self.alice_headers).json()
        event = self.gateway.payment_succeeded("evt_paid_1", created["order_id"], checkout["checkout_session_id"], "pi_1")
        first = self.client.post("/payments/stripe/webhook", content=event.raw_body, headers={"Stripe-Signature": event.signature})
        second = self.client.post("/payments/stripe/webhook", content=event.raw_body, headers={"Stripe-Signature": event.signature})
        self.assertEqual(first.status_code, 200)
        self.assertFalse(first.json()["duplicate"])
        self.assertTrue(second.json()["duplicate"])
        self.assertEqual(self.repo.get_order(created["order_id"]).status, OrderStatus.PAID)
        payments = self.repo.list_payments(created["order_id"])
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0].amount_minor, 4999)
        self.assertEqual(payments[0].currency, "usd")
        self.assertEqual(self.repo.get_report_release_for_case(self.case_id).release_status, ReportReleaseStatus.QA_PENDING)
        self.assertEqual(self.client.get(f"/customer/cases/{self.case_id}/report", headers=self.alice_headers).status_code, 403)

    def test_invalid_signature_and_unknown_order_do_not_attach_money(self):
        invalid = self.client.post("/payments/stripe/webhook", content=b'{"id":"evt_bad"}', headers={"Stripe-Signature": "invalid"})
        self.assertEqual(invalid.status_code, 400)
        event = self.gateway.payment_succeeded("evt_unknown", "ord_unknown", "cs_unknown", "pi_unknown")
        unknown = self.client.post("/payments/stripe/webhook", content=event.raw_body, headers={"Stripe-Signature": event.signature})
        self.assertEqual(unknown.status_code, 200)
        self.assertEqual(self.repo.get_payment_event("evt_unknown").processing_status, "UNKNOWN_ORDER")

    def test_refund_replay_revokes_entitlement_once_and_signed_report_links_expire_or_revoke(self):
        created = self.client.post("/commerce/orders", headers=self.alice_headers, json={"case_id": self.case_id, "product_code": "CONCIERGE_CASE"}).json()
        checkout = self.client.post(f"/commerce/orders/{created['order_id']}/checkout", headers=self.alice_headers).json()
        paid = self.gateway.payment_succeeded("evt_paid_2", created["order_id"], checkout["checkout_session_id"], "pi_2")
        self.client.post("/payments/stripe/webhook", content=paid.raw_body, headers={"Stripe-Signature": paid.signature})
        self.repo.mark_report_released(self.case_id, self.alice.tenant_id, reviewer_id="reviewer_01")
        release = self.repo.get_report_release_for_case(self.case_id)
        token = self.app.state.access_tokens.issue_report_link(release.report_id, self.alice.tenant_id, release.token_version, ttl_seconds=60)
        self.assertEqual(self.client.get(f"/reports/{release.report_id}/access?token={token}").status_code, 200)
        refunded = self.gateway.refunded("evt_refund_1", created["order_id"], "pi_2")
        self.client.post("/payments/stripe/webhook", content=refunded.raw_body, headers={"Stripe-Signature": refunded.signature})
        replay = self.client.post("/payments/stripe/webhook", content=refunded.raw_body, headers={"Stripe-Signature": refunded.signature})
        self.assertTrue(replay.json()["duplicate"])
        self.assertEqual(self.client.get(f"/reports/{release.report_id}/access?token={token}").status_code, 403)

    def test_delivery_gate_returns_structured_payment_entitlement_and_qa_blockers(self):
        before_payment = self.repo.can_release_report(self.alice.tenant_id, self.case_id, qa_blockers=["QA_NOT_APPROVED"])
        self.assertFalse(before_payment["ready"])
        self.assertIn("PAYMENT_NOT_VERIFIED", before_payment["blockers"])
        self.assertIn("ENTITLEMENT_NOT_ACTIVE", before_payment["blockers"])
        created = self.client.post("/commerce/orders", headers=self.alice_headers, json={"case_id": self.case_id, "product_code": "CONCIERGE_CASE"}).json()
        checkout = self.client.post(f"/commerce/orders/{created['order_id']}/checkout", headers=self.alice_headers).json()
        paid = self.gateway.payment_succeeded("evt_paid_3", created["order_id"], checkout["checkout_session_id"], "pi_3")
        self.client.post("/payments/stripe/webhook", content=paid.raw_body, headers={"Stripe-Signature": paid.signature})
        qa_pending = self.repo.can_release_report(self.alice.tenant_id, self.case_id, qa_blockers=["QA_NOT_APPROVED"])
        self.assertFalse(qa_pending["ready"])
        self.assertEqual(qa_pending["blockers"], ["QA_NOT_APPROVED"])

    def test_expired_signed_report_token_is_rejected_before_report_read(self):
        created = self.client.post("/commerce/orders", headers=self.alice_headers, json={"case_id": self.case_id, "product_code": "CONCIERGE_CASE"}).json()
        checkout = self.client.post(f"/commerce/orders/{created['order_id']}/checkout", headers=self.alice_headers).json()
        paid = self.gateway.payment_succeeded("evt_paid_4", created["order_id"], checkout["checkout_session_id"], "pi_4")
        self.client.post("/payments/stripe/webhook", content=paid.raw_body, headers={"Stripe-Signature": paid.signature})
        release = self.repo.mark_report_released(self.case_id, self.alice.tenant_id, reviewer_id="reviewer_01")
        expired = self.app.state.access_tokens._encode({
            "kind": "report", "report_id": release.report_id, "tenant_id": self.alice.tenant_id,
            "version": release.token_version, "nonce": "expired-test", "exp": 1,
        })
        self.assertEqual(self.client.get(f"/reports/{release.report_id}/access?token={expired}").status_code, 403)

    def test_paid_customer_case_does_not_fall_back_to_fixture_analysis(self):
        created = self.client.post("/commerce/orders", headers=self.alice_headers, json={"case_id": self.case_id, "product_code": "CONCIERGE_CASE"}).json()
        checkout = self.client.post(f"/commerce/orders/{created['order_id']}/checkout", headers=self.alice_headers).json()
        paid = self.gateway.payment_succeeded("evt_paid_5", created["order_id"], checkout["checkout_session_id"], "pi_5")
        self.client.post("/payments/stripe/webhook", content=paid.raw_body, headers={"Stripe-Signature": paid.signature})
        response = self.client.post(f"/customer/cases/{self.case_id}/analysis", headers=self.alice_headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"]["code"], "LIVE_RESEARCH_NOT_AVAILABLE")

    def test_reviewer_and_internal_finops_routes_require_reviewer_bearer_identity(self):
        self.assertEqual(self.client.get(f"/review/cases/{self.case_id}").status_code, 401)
        self.assertEqual(self.client.get(f"/internal/cases/{self.case_id}/cost-ledger").status_code, 401)
        self.assertEqual(self.client.get(f"/review/cases/{self.case_id}", headers=self.alice_headers).status_code, 403)


if __name__ == "__main__":
    unittest.main()
