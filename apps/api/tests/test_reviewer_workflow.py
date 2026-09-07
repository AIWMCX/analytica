import tempfile
import unittest
from pathlib import Path

from apps.api.app.entities import ResolutionDecision, ResolutionStatus
from apps.api.app.cost_ledger import CaseCostLedgerRepository, CostMetric, MeasurementStatus
from apps.api.app.evidence import AssumptionOrigin, FinancialTruthFirewall, PredictaEvidencePort
from apps.api.app.evidence_repository import SQLiteEvidenceRepository
from apps.api.app.financial import FinancialModelInput, QuantisFinancialPort
from apps.api.app.reviewer_workflow import ReviewActionType, ReviewerWorkflow, SQLiteReviewerRepository
from apps.api.tests.test_evidence_port import predicta_response


class ReviewerWorkflowE2ETests(unittest.TestCase):
    """A missing gate or audit event must prevent concierge delivery."""

    def test_research_assumption_quantis_and_reviewer_approval_make_case_deliverable(self):
        packet = PredictaEvidencePort("review-e2e").adapt(
            predicta_response(), case_id="case_concierge_001", submitted_name="Northstar Packaging",
            geography="New York", industry="Packaging",
        )
        proposal = FinancialTruthFirewall().propose(
            packet=packet, claim_id="claim_001", metric="input_cost_inflation", value=0.11,
            unit="ratio", period="2022", origin=AssumptionOrigin.SOURCE_ESTIMATE,
            transformation="Converted annual percentage to decimal ratio.",
        )
        result = QuantisFinancialPort("quantis-compatible.demo.v1").calculate_baseline(FinancialModelInput(
            capex=350000, monthly_capacity_revenue=420000, utilization=0.71, gross_margin=0.31,
            monthly_fixed_cost=69000, available_cash=510000,
        ))
        resolved_entity = ResolutionDecision(
            status=ResolutionStatus.RESOLVED, entity_id="ent_northstar", confidence=1,
            matching_signals=3, candidate_ids=["ent_northstar"],
        )

        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "review.db"
            evidence = SQLiteEvidenceRepository(db_path)
            evidence.save_packet(packet)
            costs = CaseCostLedgerRepository(db_path)
            costs.open_case("case_concierge_001")
            workflow = ReviewerWorkflow(SQLiteReviewerRepository(db_path), evidence, cost_ledger=costs)
            workflow.open_case(
                case_id="case_concierge_001", entity=resolved_entity, packet_ids=[packet.packet_id],
                assumptions=[proposal], financial_results=[result], findings=["finding_asset_timing"],
                recommendation="Lease before buying until demand is validated.",
            )

            workflow.apply("case_concierge_001", ReviewActionType.APPROVE_ENTITY, reviewer_id="founder_01")
            workflow.apply(
                "case_concierge_001", ReviewActionType.ACCEPT_ASSUMPTION,
                reviewer_id="founder_01", assumption_id=proposal.assumption_id,
            )
            deliverable = workflow.apply(
                "case_concierge_001", ReviewActionType.APPROVE_DELIVERY, reviewer_id="founder_01",
            )

            self.assertEqual(deliverable.delivery_status, "DELIVERABLE")
            self.assertEqual(deliverable.qa_approved_by, "founder_01")
            self.assertTrue(workflow.inspect("case_concierge_001").delivery_gate.eligible)
            inspection = workflow.inspect("case_concierge_001")
            self.assertEqual(inspection.evidence_packets[0].claims[0].claim_id, "claim_001")
            self.assertEqual(inspection.evidence_packets[0].contradictions[0].claim_id, "claim_001")
            actions = workflow.audit_log("case_concierge_001")
            self.assertEqual([action.action_type for action in actions], [
                ReviewActionType.APPROVE_ENTITY, ReviewActionType.ACCEPT_ASSUMPTION,
                ReviewActionType.APPROVE_DELIVERY,
            ])
            self.assertTrue(all(action.occurred_at.endswith("+00:00") for action in actions))
            delivery_duration = next(item for item in costs.report("case_concierge_001").measurements if item.metric == CostMetric.DELIVERY_DURATION_SECONDS)
            self.assertEqual(delivery_duration.status, MeasurementStatus.MEASURED)

    def test_return_for_revision_increments_the_case_revision_counter(self):
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "review.db"
            evidence = SQLiteEvidenceRepository(db_path)
            costs = CaseCostLedgerRepository(db_path)
            costs.open_case("case_concierge_revisions")
            workflow = ReviewerWorkflow(SQLiteReviewerRepository(db_path), evidence, cost_ledger=costs)
            workflow.open_case(
                case_id="case_concierge_revisions",
                entity=ResolutionDecision(status=ResolutionStatus.UNRESOLVED, entity_id=None, confidence=0, matching_signals=0),
                packet_ids=[], assumptions=[], financial_results=[], findings=[], recommendation="Hold.",
            )

            workflow.apply("case_concierge_revisions", ReviewActionType.RETURN_FOR_REVISION, reviewer_id="founder_01", reason="Need a second source.")

            revisions = next(item for item in costs.report("case_concierge_revisions").measurements if item.metric == CostMetric.REVISIONS)
            self.assertEqual(revisions.quantity, 1)
            self.assertEqual(revisions.status, MeasurementStatus.MEASURED)

    def test_delivery_rejects_missing_entity_approval_and_preserves_audit_record(self):
        packet = PredictaEvidencePort("review-e2e").adapt(
            predicta_response(), case_id="case_concierge_002", submitted_name="Northstar Packaging",
            geography="New York", industry="Packaging",
        )
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "review.db"
            evidence = SQLiteEvidenceRepository(db_path)
            evidence.save_packet(packet)
            workflow = ReviewerWorkflow(SQLiteReviewerRepository(db_path), evidence)
            workflow.open_case(
                case_id="case_concierge_002",
                entity=ResolutionDecision(status=ResolutionStatus.RESOLVED, entity_id="ent_northstar", confidence=1, matching_signals=3),
                packet_ids=[packet.packet_id], assumptions=[], financial_results=[], findings=[], recommendation="Hold.",
            )

            with self.assertRaisesRegex(PermissionError, "entity approval"):
                workflow.apply("case_concierge_002", ReviewActionType.APPROVE_DELIVERY, reviewer_id="founder_01")
            self.assertEqual(workflow.audit_log("case_concierge_002"), [])

    def test_delivery_rejects_a_tampered_packet_after_other_gates_pass(self):
        packet = PredictaEvidencePort("review-e2e").adapt(
            predicta_response(), case_id="case_concierge_003", submitted_name="Northstar Packaging",
            geography="New York", industry="Packaging",
        )
        result = QuantisFinancialPort("quantis-compatible.demo.v1").calculate_baseline(FinancialModelInput(
            capex=350000, monthly_capacity_revenue=420000, utilization=0.71, gross_margin=0.31,
            monthly_fixed_cost=69000, available_cash=510000,
        ))
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "review.db"
            evidence = SQLiteEvidenceRepository(db_path)
            evidence.save_packet(packet)
            workflow = ReviewerWorkflow(SQLiteReviewerRepository(db_path), evidence)
            workflow.open_case(
                case_id="case_concierge_003",
                entity=ResolutionDecision(status=ResolutionStatus.RESOLVED, entity_id="ent_northstar", confidence=1, matching_signals=3),
                packet_ids=[packet.packet_id], assumptions=[], financial_results=[result], findings=[], recommendation="Hold.",
            )
            workflow.apply("case_concierge_003", ReviewActionType.APPROVE_ENTITY, reviewer_id="founder_01")
            with evidence.connection() as db:
                db.execute("UPDATE source_snapshots SET text='tampered' WHERE packet_id=?", (packet.packet_id,))

            with self.assertRaisesRegex(PermissionError, "hash is invalid"):
                workflow.apply("case_concierge_003", ReviewActionType.APPROVE_DELIVERY, reviewer_id="founder_01")
            self.assertFalse(workflow.inspect("case_concierge_003").delivery_gate.eligible)


if __name__ == "__main__":
    unittest.main()
