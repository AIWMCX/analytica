from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_readme_documents_preview_and_health_endpoint(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn('python3 scripts/run_preview.py', readme)
        self.assertIn('GET http://127.0.0.1:8000/health', readme)
        self.assertIn('not yet a paid-production release', readme)

    def test_status_document_explicitly_separates_rd_from_paid_launch(self):
        status = (ROOT / 'docs/status/2026-08-19-rd-readiness.md').read_text(encoding='utf-8')
        self.assertIn('GO for continued R&D and MVP engineering', status)
        self.assertIn('NO-GO for paid public production today', status)
        self.assertIn('Real-company discovery | Not implemented', status)
        self.assertIn('Payments | Not implemented', status)

    def test_preview_runner_exists(self):
        runner = ROOT / 'scripts/run_preview.py'
        self.assertTrue(runner.exists())
        self.assertIn('uvicorn.run', runner.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
