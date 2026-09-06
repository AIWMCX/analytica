import tempfile
import time
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

from apps.api.app.main import create_app


class ApiContractTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.app = create_app(db_path=Path(self.tempdir.name) / "api.db", stage_delay=0)
        self.client = TestClient(self.app)

    def tearDown(self):
        self.app.state.analysis_service.wait_for_all(timeout=2)
        self.client.close()
        self.tempdir.cleanup()

    def test_health_and_readiness_are_explicit(self):
        health = self.client.get('/health')
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.json()['status'], 'ok')
        readiness = self.client.get('/readiness')
        self.assertEqual(readiness.status_code, 200)
        body = readiness.json()
        self.assertEqual(body['product_stage'], 'workable_mvp_prototype')
        self.assertFalse(body['paid_public_launch_ready'])
        self.assertGreaterEqual(body['prototype_completion_percent'], 70)

    def test_demo_payment_checkout_returns_one_dollar_authorization(self):
        response = self.client.post('/payments/checkout', json={'email': 'owner@example.com'})
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body['amount_cents'], 100)
        self.assertEqual(body['currency'], 'USD')
        self.assertEqual(body['mode'], 'prototype_demo')
        self.assertTrue(body['payment_token'].startswith('demo_pay_'))
        self.assertFalse(body['real_charge'])

    def test_create_analysis_requires_demo_payment_and_email(self):
        payment = self.client.post('/payments/checkout', json={'email': 'owner@example.com'}).json()
        response = self.client.post('/analyses', json={
            'business_activity': 'Packaging manufacturing',
            'geography': 'New York',
            'email': 'owner@example.com',
            'payment_token': payment['payment_token'],
        })
        self.assertEqual(response.status_code, 202)
        body = response.json()
        self.assertTrue(body['analysis_id'].startswith('ana_'))
        self.assertIn(body['status'], {'QUEUED', 'DISCOVERING_COMPANIES', 'COMPLETED'})
        self.assertIn('/analyses/', body['report_url'])

    def test_status_progress_and_report_complete_end_to_end(self):
        payment = self.client.post('/payments/checkout', json={'email': 'owner@example.com'}).json()
        created = self.client.post('/analyses', json={
            'business_activity': 'Packaging manufacturing',
            'geography': 'New York',
            'email': 'owner@example.com',
            'payment_token': payment['payment_token'],
        }).json()
        analysis_id = created['analysis_id']
        deadline = time.time() + 2
        while time.time() < deadline:
            status_response = self.client.get(f'/analyses/{analysis_id}/status')
            self.assertEqual(status_response.status_code, 200)
            job = status_response.json()
            if job['status'] == 'COMPLETED':
                break
            time.sleep(0.01)
        self.assertEqual(job['progress_percent'], 100)
        report = self.client.get(f'/analyses/{analysis_id}')
        self.assertEqual(report.status_code, 200)
        body = report.json()
        self.assertEqual(body['analysis_id'], analysis_id)
        self.assertEqual(len(body['lessons']), 10)
        self.assertEqual(body['data_mode'], 'synthetic_fixture')

    def test_invalid_payment_token_is_rejected(self):
        response = self.client.post('/analyses', json={
            'business_activity': 'Packaging manufacturing',
            'geography': 'New York',
            'email': 'owner@example.com',
            'payment_token': 'not-valid',
        })
        self.assertEqual(response.status_code, 402)

    def test_unsupported_market_is_transparently_rejected(self):
        payment = self.client.post('/payments/checkout', json={'email': 'owner@example.com'}).json()
        response = self.client.post('/analyses', json={
            'business_activity': 'Coffee shop',
            'geography': 'California',
            'email': 'owner@example.com',
            'payment_token': payment['payment_token'],
        })
        self.assertEqual(response.status_code, 422)
        self.assertIn('Packaging manufacturing / New York', response.json()['detail'])

    def test_canonical_demo_report_remains_available_for_static_preview(self):
        response = self.client.get('/analyses/demo_packaging_ny_v1')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['analysis_id'], 'demo_packaging_ny_v1')

    def test_recommendation_lineage_api_returns_a_report_ready_decision_path(self):
        response = self.client.get(
            '/analyses/demo_packaging_ny_v1/evidence-graph/'
            'recommendations/rec_lease_validate_before_buying/lineage'
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertTrue(body['report_ready'])
        self.assertEqual(body['recommendation']['node_type'], 'RECOMMENDATION')
        self.assertTrue(body['findings'])
        self.assertTrue(body['calculations'])
        self.assertTrue(body['assumptions'])
        self.assertTrue(body['claims'])
        self.assertTrue(body['passages'])
        self.assertTrue(body['sources'])

    def test_internal_reviewer_case_exposes_delivery_gate_and_audits_recommendation_edits(self):
        initial = self.client.get('/review/cases/demo_packaging_ny_v1')
        self.assertEqual(initial.status_code, 200)
        self.assertFalse(initial.json()['delivery_gate']['eligible'])
        self.assertIn('entity is not resolved', initial.json()['delivery_gate']['blockers'])

        edited = self.client.post('/review/cases/demo_packaging_ny_v1/actions', json={
            'action_type': 'EDIT_RECOMMENDATION',
            'reviewer_id': 'founder_01',
            'recommendation_text': 'Keep the first capacity decision reversible.',
        })
        self.assertEqual(edited.status_code, 200)
        body = edited.json()
        self.assertEqual(body['case']['reviewer_recommendation'], 'Keep the first capacity decision reversible.')
        self.assertEqual(body['case']['source_recommendation'], 'LEASE / VALIDATE BEFORE BUYING')
        self.assertEqual(body['audit_actions'][-1]['action_type'], 'EDIT_RECOMMENDATION')
        self.assertTrue(body['audit_actions'][-1]['occurred_at'].endswith('+00:00'))

    def test_internal_case_cost_ledger_records_runtime_and_keeps_public_pricing_unchanged(self):
        payment = self.client.post('/payments/checkout', json={'email': 'owner@example.com'}).json()
        created = self.client.post('/analyses', json={
            'business_activity': 'Packaging manufacturing', 'geography': 'New York',
            'email': 'owner@example.com', 'payment_token': payment['payment_token'],
        }).json()
        self.app.state.analysis_service.wait_for_all(timeout=2)

        initial = self.client.get(f"/internal/cases/{created['analysis_id']}/cost-ledger")
        self.assertEqual(initial.status_code, 200)
        body = initial.json()
        self.assertEqual(body['case_id'], created['analysis_id'])
        metrics = {item['metric']: item for item in body['measurements']}
        self.assertEqual(metrics['SEARCH_COUNT']['quantity'], 0)
        self.assertEqual(metrics['TOKENS']['quantity'], 0)
        self.assertEqual(metrics['PROVIDER_FAILURES']['quantity'], 0)
        self.assertEqual(metrics['COMPUTE_TIME_SECONDS']['status'], 'MEASURED')
        self.assertEqual(metrics['WORKER_TIME_SECONDS']['status'], 'MEASURED')
        self.assertEqual([item['target_contribution_margin'] for item in body['break_even_prices']], [0.5, 0.7, 0.8])
        self.assertNotIn('break_even_prices', self.client.get('/pricing').json())

        updated = self.client.post(f"/internal/cases/{created['analysis_id']}/cost-ledger/measurements", json={
            'metric': 'HUMAN_QA_MINUTES', 'status': 'MEASURED', 'quantity': 30,
            'unit': 'minutes', 'unit_cost_usd': 0.60, 'source': 'reviewer time entry',
        })
        self.assertEqual(updated.status_code, 200)
        self.assertEqual(updated.json()['human_review_cost']['known_amount_usd'], 18.00)
        self.assertEqual(updated.json()['human_review_cost']['status'], 'MEASURED')


if __name__ == '__main__':
    unittest.main()
