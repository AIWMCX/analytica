import unittest

from fastapi.testclient import TestClient

from apps.api.app.main import app


class ApiContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client = TestClient(app)

    def test_health_reports_service_ready(self):
        response = self.client.get('/health')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'ok')
        self.assertEqual(response.json()['service'], 'analytica-api')

    def test_create_canonical_demo_analysis(self):
        response = self.client.post('/analyses', json={
            'business_activity': 'Packaging manufacturing',
            'geography': 'New York',
        })
        self.assertEqual(response.status_code, 201)
        body = response.json()
        self.assertEqual(body['analysis_id'], 'demo_packaging_ny_v1')
        self.assertEqual(body['status'], 'COMPLETED')
        self.assertIn('/analyses/demo_packaging_ny_v1', body['report_url'])

    def test_get_report_returns_evidence_backed_fixture(self):
        self.client.post('/analyses', json={
            'business_activity': 'Packaging manufacturing',
            'geography': 'New York',
        })
        response = self.client.get('/analyses/demo_packaging_ny_v1')
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body['readiness_label'], 'R&D vertical slice — synthetic evidence only')
        self.assertGreaterEqual(len(body['evidence']), 1)
        self.assertGreaterEqual(len(body['lessons']), 6)

    def test_status_endpoint_returns_explicit_state(self):
        self.client.post('/analyses', json={
            'business_activity': 'Packaging manufacturing',
            'geography': 'New York',
        })
        response = self.client.get('/analyses/demo_packaging_ny_v1/status')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'COMPLETED')

    def test_unknown_analysis_returns_404(self):
        response = self.client.get('/analyses/not-real')
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()['detail'], 'analysis not found')


if __name__ == '__main__':
    unittest.main()
