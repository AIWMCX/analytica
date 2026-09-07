import tempfile
import unittest
from pathlib import Path

from apps.api.app.evidence_graph import EvidenceGraphService
from apps.api.app.fixtures import build_demo_report
from apps.api.app.intelligence import SQLiteRelationshipRepository


class EvidenceGraphTraversalTests(unittest.TestCase):
    """Breaks if the recommendation cannot be traced through all material evidence layers."""

    def setUp(self):
        self.report = build_demo_report()
        self.graph_service = EvidenceGraphService()

    def test_recommendation_explanation_returns_complete_material_lineage_in_order(self):
        lineage = self.graph_service.explain_recommendation(
            self.graph_service.build_case(self.report),
            "rec_lease_validate_before_buying",
        )

        self.assertTrue(lineage.report_ready)
        self.assertEqual(lineage.recommendation.node_type, "RECOMMENDATION")
        self.assertEqual([node.node_type for node in lineage.findings], ["FINDING"])
        self.assertEqual([node.node_type for node in lineage.calculations], ["CALCULATION"])
        self.assertTrue(all(node.node_type == "ASSUMPTION" for node in lineage.assumptions))
        self.assertTrue(all(node.node_type == "CLAIM" for node in lineage.claims))
        self.assertTrue(all(node.node_type == "PASSAGE" for node in lineage.passages))
        self.assertTrue(all(node.node_type == "SOURCE" for node in lineage.sources))
        self.assertEqual(lineage.issues, [])

    def test_missing_material_passage_lineage_marks_recommendation_not_report_ready(self):
        case = self.graph_service.build_case(self.report)
        case.edges = [
            edge for edge in case.edges
            if not (edge.relationship_type == "DERIVED_FROM" and edge.from_type == "PASSAGE")
        ]

        lineage = self.graph_service.explain_recommendation(case, "rec_lease_validate_before_buying")

        self.assertFalse(lineage.report_ready)
        self.assertIn("BROKEN_MATERIAL_LINEAGE", {issue.code for issue in lineage.issues})

    def test_graph_case_persists_canonical_relationship_types_in_existing_relational_store(self):
        case = self.graph_service.build_case(self.report)
        with tempfile.TemporaryDirectory() as directory:
            relationships = SQLiteRelationshipRepository(Path(directory) / "graph.db")
            self.graph_service.persist_case(case, relationships)
            self.graph_service.persist_case(case, relationships)
            persisted = relationships.list_for_case(self.report.analysis_id)

        self.assertEqual(len(persisted), len(case.edges))
        relationship_types = {edge.relationship_type for edge in persisted}
        self.assertIn("JUSTIFIES_RECOMMENDATION", relationship_types)
        self.assertIn("CALCULATED_FROM", relationship_types)
        self.assertIn("SUPPORTS_FINDING", relationship_types)
        self.assertIn("SUPPORTS", relationship_types)
        self.assertTrue(all(edge.from_type.isupper() and edge.to_type.isupper() for edge in persisted))


if __name__ == "__main__":
    unittest.main()
