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

    def test_owner_demo_exposes_controlled_decision_intelligence(self):
        self.assertEqual(self.report.decision_brief.capital_exposed, 350000)
        self.assertEqual([item.name for item in self.report.financial_scenarios], ["DOWNSIDE", "BASE", "UPSIDE"])
        self.assertTrue(all(item.reconciliation_passed for item in self.report.financial_scenarios))
        self.assertGreaterEqual(len(self.report.assumptions), 4)
        self.assertTrue(any(item.origin == "SOURCE_ESTIMATE" and item.review_status == "PROPOSED" for item in self.report.assumptions))
        self.assertTrue(any(item.state == "blocked" for item in self.report.system_status))

    def test_decision_workspace_contract_exposes_identity_limits_and_signed_sensitivity(self):
        self.assertEqual(self.report.entity_identity.resolution_status, "SYNTHETIC_FIXTURE")
        self.assertFalse(self.report.entity_identity.eligible_for_customer_delivery)
        self.assertEqual(self.report.contradictions, [])
        self.assertIn("No contradiction records", self.report.contradictions_note)
        for driver in self.report.sensitivity:
            self.assertLess(driver.low_operating_profit, driver.high_operating_profit)
