import unittest

from apps.api.app.live_adapters import CensusDatasetClient, PredictaHttpClient, SecCompanyFactsClient


class LiveAdapterTests(unittest.TestCase):
    def test_predicta_client_posts_real_service_shape_and_normalizes_version_boundary(self):
        seen = {}
        def handler(request):
            seen["path"] = request.full_url
            seen["body"] = request.data
            return {"query": {"queryId": "q1"}, "candidates": [], "claims": [], "diagnostics": {"providersSucceeded": []}}
        client = PredictaHttpClient("https://predicta.example", transport=handler)
        response = client.search("Northstar Packaging New York", session_id="case_01")
        self.assertTrue(seen["path"].endswith("/api/search"))
        self.assertIn('"lens":"financial"', seen["body"].decode())
        self.assertEqual(response["apiVersion"], "predicta.search.v1")

    def test_sec_client_uses_official_companyfacts_endpoint_and_identifies_source(self):
        seen = {}
        def handler(request):
            seen["path"] = request.full_url
            seen["user_agent"] = request.get_header("User-agent")
            return {"cik": 320193, "entityName": "Apple Inc."}
        client = SecCompanyFactsClient("Analytica contact@aiwmc.example", transport=handler)
        result = client.company_facts("0000320193")
        self.assertTrue(seen["path"].endswith("/api/xbrl/companyfacts/CIK0000320193.json"))
        self.assertIn("Analytica", seen["user_agent"])
        self.assertEqual(result["provider_id"], "sec_edgar")

    def test_census_client_labels_public_industry_data_as_benchmark_not_company_fact(self):
        seen = {}
        def handler(request):
            seen["url"] = request.full_url
            return [["NAME", "NAICS2017"], ["New York", "322"]]
        result = CensusDatasetClient(transport=handler).get("2022/acs/acs5", {"get": "NAME,NAICS2017", "for": "state:36"})
        self.assertIn("api.census.gov/data/2022/acs/acs5", seen["url"])
        self.assertEqual(result["data_scope"], "BENCHMARK")


if __name__ == "__main__":
    unittest.main()
