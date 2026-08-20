import tempfile
import unittest
from pathlib import Path

from apps.api.app.domain import AnalysisStatus
from apps.api.app.repository import SQLiteAnalysisRepository


class SQLiteAnalysisRepositoryTests(unittest.TestCase):
    def setUp(self):
        self.tempdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.tempdir.name) / "analytica.db"
        self.repo = SQLiteAnalysisRepository(self.db_path)

    def tearDown(self):
        self.tempdir.cleanup()

    def test_job_survives_repository_reopen(self):
        self.repo.create_job(
            analysis_id="ana_test",
            business_activity="Packaging manufacturing",
            geography="New York",
            email="owner@example.com",
            payment_token="demo_pay_test",
        )
        self.repo.update_status("ana_test", AnalysisStatus.SCORING, 72, "Scoring peer trajectories")

        reopened = SQLiteAnalysisRepository(self.db_path)
        job = reopened.get_job("ana_test")

        self.assertIsNotNone(job)
        self.assertEqual(job.analysis_id, "ana_test")
        self.assertEqual(job.status, AnalysisStatus.SCORING)
        self.assertEqual(job.progress_percent, 72)
        self.assertEqual(job.email, "owner@example.com")

    def test_completed_report_is_persisted_and_reloaded(self):
        from apps.api.app.fixtures import build_demo_report

        self.repo.create_job(
            analysis_id="ana_persisted",
            business_activity="Packaging manufacturing",
            geography="New York",
            email="owner@example.com",
            payment_token="demo_pay_test",
        )
        report = build_demo_report(analysis_id="ana_persisted")
        self.repo.save_report(report)

        loaded = self.repo.get_report("ana_persisted")
        self.assertIsNotNone(loaded)
        self.assertEqual(loaded.analysis_id, "ana_persisted")
        self.assertEqual(loaded.status, AnalysisStatus.COMPLETED)
        self.assertEqual(len(loaded.lessons), 10)


if __name__ == "__main__":
    unittest.main()

class SQLiteConnectionLifecycleTests(unittest.TestCase):
    def test_repository_operations_do_not_leak_sqlite_connections(self):
        import gc
        import warnings

        with tempfile.TemporaryDirectory() as tempdir:
            repo = SQLiteAnalysisRepository(Path(tempdir) / "connections.db")
            repo.create_job(
                analysis_id="ana_connections",
                business_activity="Packaging manufacturing",
                geography="New York",
                email="owner@example.com",
                payment_token="demo_pay_test",
            )
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always", ResourceWarning)
                for _ in range(5):
                    self.assertIsNotNone(repo.get_job("ana_connections"))
                gc.collect()
            leaked = [warning for warning in caught if "unclosed database" in str(warning.message)]
            self.assertEqual(leaked, [], f"leaked sqlite connections: {leaked}")
