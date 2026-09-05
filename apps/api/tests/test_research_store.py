import sqlite3
import tempfile
import unittest
from pathlib import Path
from apps.api.app.research_pipeline import ResearchPipeline
from apps.api.app.research_store import ResearchStore
from apps.api.tests.test_research_pipeline import SuccessfulProvider, FailingProvider


class ResearchStoreTests(unittest.TestCase):
    def test_run_survives_reopen_with_failures_and_verified_records(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'research.db'
            run = ResearchPipeline([SuccessfulProvider(), FailingProvider()]).run('case', 'query')
            ResearchStore(path).save('run-1', run)
            loaded = ResearchStore(path).get('run-1')
            self.assertEqual(loaded.manifest.providers, {'sec_edgar': 'SUCCEEDED', 'fred': 'FAILED'})
            self.assertEqual(loaded.records[0].text, 'Official filing')
            with sqlite3.connect(path) as db:
                db.execute("UPDATE research_records SET text='corrupt'")
            db.close()
            with self.assertRaises(ValueError):
                ResearchStore(path).get('run-1')

    def test_existing_run_cannot_be_overwritten(self):
        with tempfile.TemporaryDirectory() as folder:
            store = ResearchStore(Path(folder) / 'research.db')
            run = ResearchPipeline([]).run('case', 'query')
            store.save('run-1', run)
            with self.assertRaises(sqlite3.IntegrityError):
                store.save('run-1', run)
