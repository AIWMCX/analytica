import unittest

from apps.api.app.research_pipeline import ProviderRecord, ResearchPipeline


class SuccessfulProvider:
    provider_id = "sec_edgar"
    def collect(self, query):
        return [ProviderRecord(provider_id=self.provider_id, record_id="sec_1", title="10-K", canonical_url="https://sec.example/10-k", text="Official filing", authority="OFFICIAL_FILING", data_scope="COMPANY")]


class FailingProvider:
    provider_id = "fred"
    def collect(self, query):
        raise RuntimeError("upstream unavailable")


class ResearchPipelineTests(unittest.TestCase):
    def test_partial_provider_failure_is_manifested_without_fixture_fallback(self):
        run = ResearchPipeline([SuccessfulProvider(), FailingProvider()]).run("case_04", "packaging inputs")
        self.assertEqual(len(run.records), 1)
        self.assertEqual(run.manifest.providers["sec_edgar"], "SUCCEEDED")
        self.assertEqual(run.manifest.providers["fred"], "FAILED")
        self.assertFalse(run.fixture_fallback_used)
        self.assertEqual(len(run.manifest.failures), 1)


if __name__ == "__main__":
    unittest.main()
