import unittest

from apps.api.app.domain import ConfidenceClass, AnalysisStatus
from apps.api.app.fixtures import build_demo_report


class DomainFixtureTests(unittest.TestCase):
    def setUp(self):
        self.report = build_demo_report()

    def test_canonical_report_identity(self):
        self.assertEqual(self.report.business_activity, "Packaging manufacturing")
        self.assertEqual(self.report.geography, "New York")
        self.assertEqual(self.report.status, AnalysisStatus.COMPLETED)
        self.assertTrue(self.report.analysis_id.startswith("demo_"))

    def test_trajectories_have_at_most_ten_annual_points(self):
        self.assertGreaterEqual(len(self.report.companies), 4)
        for company in self.report.companies:
            self.assertLessEqual(len(company.trajectory), 10)
            years = [point.year for point in company.trajectory]
            self.assertEqual(years, sorted(set(years)))

    def test_every_finding_has_traceable_evidence(self):
        evidence_ids = {item.evidence_id for item in self.report.evidence}
        self.assertGreater(len(evidence_ids), 0)
        for finding in self.report.findings:
            self.assertGreater(len(finding.evidence_ids), 0)
            self.assertTrue(set(finding.evidence_ids).issubset(evidence_ids))

    def test_findings_use_explicit_confidence_taxonomy(self):
        allowed = set(ConfidenceClass)
        for finding in self.report.findings:
            self.assertIn(finding.confidence, allowed)

    def test_lessons_are_ordered_and_actionable(self):
        self.assertGreaterEqual(len(self.report.lessons), 6)
        priorities = [lesson.priority for lesson in self.report.lessons]
        self.assertEqual(priorities, sorted(priorities))
        for lesson in self.report.lessons:
            self.assertTrue(lesson.action.strip())
            self.assertGreater(len(lesson.evidence_ids), 0)


if __name__ == "__main__":
    unittest.main()
