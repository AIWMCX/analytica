import tempfile
import time
import unittest
from pathlib import Path

from apps.api.app.domain import AnalysisStatus
from apps.api.app.repository import SQLiteAnalysisRepository
from apps.api.app.service import AnalysisService


class AnalysisServiceTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.repo = SQLiteAnalysisRepository(Path(self.tempdir.name) / "service.db")
        self.service = AnalysisService(self.repo, stage_delay=0)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_supported_request_runs_through_explicit_stages_to_completion(self):
        analysis_id = self.service.create_analysis(
            business_activity="Packaging manufacturing",
            geography="New York",
            email="owner@example.com",
            payment_token="demo_pay_test",
            run_async=False,
        )
        job = self.repo.get_job(analysis_id)
        report = self.repo.get_report(analysis_id)

        self.assertEqual(job.status, AnalysisStatus.COMPLETED)
        self.assertEqual(job.progress_percent, 100)
        self.assertEqual(job.stage_label, "Analysis complete")
        self.assertIsNotNone(report)
        self.assertEqual(report.analysis_id, analysis_id)

    def test_unsupported_market_is_rejected_without_creating_job(self):
        with self.assertRaises(ValueError):
            self.service.create_analysis(
                business_activity="Coffee shop",
                geography="California",
                email="owner@example.com",
                payment_token="demo_pay_test",
                run_async=False,
            )

    def test_async_request_returns_queued_then_finishes(self):
        service = AnalysisService(self.repo, stage_delay=0.002)
        analysis_id = service.create_analysis(
            business_activity="Packaging manufacturing",
            geography="New York",
            email="owner@example.com",
            payment_token="demo_pay_test",
            run_async=True,
        )
        first = self.repo.get_job(analysis_id)
        self.assertIn(first.status, {AnalysisStatus.QUEUED, AnalysisStatus.DISCOVERING_COMPANIES})

        deadline = time.time() + 2
        while time.time() < deadline:
            job = self.repo.get_job(analysis_id)
            if job.status == AnalysisStatus.COMPLETED:
                break
            time.sleep(0.01)
        self.assertEqual(self.repo.get_job(analysis_id).status, AnalysisStatus.COMPLETED)


if __name__ == "__main__":
    unittest.main()

class AnalysisServiceLifecycleTests(unittest.TestCase):
    def test_wait_for_all_joins_background_workers(self):
        with tempfile.TemporaryDirectory() as tempdir:
            repo = SQLiteAnalysisRepository(Path(tempdir) / "lifecycle.db")
            service = AnalysisService(repo, stage_delay=0.002)
            service.create_analysis(
                business_activity="Packaging manufacturing",
                geography="New York",
                email="owner@example.com",
                payment_token="demo_pay_test",
                run_async=True,
            )
            service.wait_for_all(timeout=2)
            self.assertEqual(service.active_worker_count, 0)
