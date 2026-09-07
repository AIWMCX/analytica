from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class RepositoryContractTests(unittest.TestCase):
    def test_readme_documents_workable_preview_and_health_endpoint(self):
        readme = (ROOT / 'README.md').read_text(encoding='utf-8')
        self.assertIn('workable MVP prototype', readme)
        self.assertIn('python3 scripts/run_preview.py', readme)
        self.assertIn('GET http://127.0.0.1:8000/health', readme)
        self.assertIn('No real payment is charged', readme)

    def test_status_document_reports_new_prototype_capabilities_and_launch_gates(self):
        status = (ROOT / 'docs/status/2026-08-19-rd-readiness.md').read_text(encoding='utf-8')
        self.assertIn('GO for workable MVP prototype review', status)
        self.assertIn('NO-GO for paid public production today', status)
        self.assertIn('SQLite persistence | Prototype working', status)
        self.assertIn('Async analysis state machine | Prototype working', status)
        self.assertIn('$1 demo checkout | Prototype working', status)
        self.assertIn('Real-company discovery | Not implemented', status)
        self.assertIn('Real payment provider | Not implemented', status)

    def test_preview_and_demo_data_builders_exist(self):
        runner = ROOT / 'scripts/run_preview.py'
        builder = ROOT / 'scripts/build_demo_data.py'
        self.assertTrue(runner.exists())
        self.assertTrue(builder.exists())
        self.assertIn('uvicorn.run', runner.read_text(encoding='utf-8'))
        self.assertIn('build_demo_report', builder.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()

class VisualSnapshotContractTests(unittest.TestCase):
    def test_generated_visual_snapshot_is_committable_and_reports_current_state(self):
        snapshot = ROOT / 'docs/previews/analytica-mvp-dashboard.svg'
        self.assertTrue(snapshot.exists())
        content = snapshot.read_text(encoding='utf-8')
        for phrase in ['ANALYTICA', 'Packaging manufacturing', '78%', 'Top 10 lessons', 'Workable MVP prototype']:
            self.assertIn(phrase, content)
        self.assertIn('viewBox="0 0 1440 1800"', content)

class RepositoryHygieneTests(unittest.TestCase):
    def test_gitignore_excludes_runtime_artifacts(self):
        gitignore = (ROOT / '.gitignore').read_text(encoding='utf-8')
        for entry in ['.venv/', '.data/', '__pycache__/', '*.py[cod]']:
            self.assertIn(entry, gitignore)

    def test_ci_workflow_runs_complete_verification_suite(self):
        workflow = (ROOT / '.github/workflows/ci.yml').read_text(encoding='utf-8')
        self.assertIn('python3 scripts/build_demo_data.py', workflow)
        self.assertIn('python3 scripts/build_visual_snapshot.py', workflow)
        self.assertIn('python3 -m unittest discover -s apps/api/tests -v', workflow)
        self.assertIn('node --test apps/web-preview/tests/test_ui_contract.mjs', workflow)
        self.assertIn('python3 -m unittest tests.test_repository_contract -v', workflow)
