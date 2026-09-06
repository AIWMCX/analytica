import unittest
import tempfile
from pathlib import Path

from apps.api.app.cost_ledger import CaseCostLedgerRepository, CostMetric, MeasurementStatus
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

    def test_live_research_records_search_attempts_and_provider_failures_in_the_case_ledger(self):
        with tempfile.TemporaryDirectory() as directory:
            costs = CaseCostLedgerRepository(Path(directory) / "costs.db")
            pipeline = ResearchPipeline([SuccessfulProvider(), FailingProvider()], cost_ledger=costs)

            pipeline.run("case_cost_research", "packaging inputs")

            measurements = {item.metric: item for item in costs.report("case_cost_research").measurements}
            self.assertEqual(measurements[CostMetric.SEARCH_COUNT].quantity, 2)
            self.assertEqual(measurements[CostMetric.SEARCH_COUNT].status, MeasurementStatus.MEASURED)
            self.assertEqual(measurements[CostMetric.PROVIDER_FAILURES].quantity, 1)
            self.assertEqual(measurements[CostMetric.PROVIDER_FAILURES].status, MeasurementStatus.MEASURED)


if __name__ == "__main__":
    unittest.main()
