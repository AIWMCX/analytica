import unittest
from apps.api.app.domain import ConfidenceClass, AnalysisStatus
from apps.api.app.fixtures import build_demo_report

class DomainFixtureTests(unittest.TestCase):
    def setUp(self): self.report = build_demo_report()
    def test_canonical_report_identity(self):
        self.assertEqual(self.report.business_activity,"Packaging manufacturing"); self.assertEqual(self.report.geography,"New York"); self.assertEqual(self.report.status,AnalysisStatus.COMPLETED); self.assertTrue(self.report.analysis_id.startswith("demo_"))
    def test_trajectories_have_at_most_ten_annual_points(self):
        self.assertGreaterEqual(len(self.report.companies),4)
        for c in self.report.companies:
            self.assertLessEqual(len(c.trajectory),10); years=[p.year for p in c.trajectory]; self.assertEqual(years,sorted(set(years)))
    def test_every_finding_has_traceable_evidence(self):
        ids={i.evidence_id for i in self.report.evidence}; self.assertGreater(len(ids),0)
        for f in self.report.findings: self.assertGreater(len(f.evidence_ids),0); self.assertTrue(set(f.evidence_ids).issubset(ids))
    def test_findings_use_explicit_confidence_taxonomy(self):
        allowed=set(ConfidenceClass)
        for f in self.report.findings: self.assertIn(f.confidence,allowed)
    def test_lessons_are_ordered_and_actionable(self):
        self.assertGreaterEqual(len(self.report.lessons),6); priorities=[l.priority for l in self.report.lessons]; self.assertEqual(priorities,sorted(priorities))
        for l in self.report.lessons: self.assertTrue(l.action.strip()); self.assertGreater(len(l.evidence_ids),0)
