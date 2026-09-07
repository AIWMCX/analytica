import tempfile
import unittest
from pathlib import Path

from apps.api.app.entities import BusinessEntity, EntityResolver, ResolutionStatus
from apps.api.app.evidence import AssumptionOrigin, FinancialTruthFirewall, PredictaEvidencePort
from apps.api.app.evidence_repository import SQLiteEvidenceRepository
from apps.api.app.intelligence import IntelligenceRelationship, SQLiteRelationshipRepository
from apps.api.tests.test_evidence_port import predicta_response


class EntityResolutionTests(unittest.TestCase):
    def test_matching_legal_name_domain_and_state_resolves_a_single_business(self):
        candidate = BusinessEntity(
            entity_id="ent_northstar", canonical_name="Northstar Packaging", legal_name="Northstar Packaging LLC",
            domains=["northstar.example"], states=["NY"], industry="Packaging", naics="322220",
        )
        decision = EntityResolver().resolve(
            submitted_name="Northstar Packaging LLC", domain="northstar.example", state="NY", candidates=[candidate]
        )

        self.assertEqual(decision.status, ResolutionStatus.RESOLVED)
        self.assertEqual(decision.entity_id, "ent_northstar")
        self.assertGreaterEqual(decision.confidence, 0.85)

    def test_same_name_with_two_close_candidates_is_ambiguous_not_silently_merged(self):
        candidates = [
            BusinessEntity(entity_id="ent_a", canonical_name="MetroSeal", legal_name="MetroSeal Industries LLC", domains=["metros.example"], states=["NY"], industry="Packaging"),
            BusinessEntity(entity_id="ent_b", canonical_name="MetroSeal", legal_name="MetroSeal Industries LLC", domains=["metros.example"], states=["NY"], industry="Packaging"),
        ]
        decision = EntityResolver().resolve(submitted_name="MetroSeal Industries LLC", domain="metros.example", state="NY", candidates=candidates)

        self.assertEqual(decision.status, ResolutionStatus.AMBIGUOUS)
        self.assertIsNone(decision.entity_id)


class EvidencePersistenceTests(unittest.TestCase):
    def test_packet_round_trip_retains_integrity_and_detects_passage_tampering(self):
        packet = PredictaEvidencePort("session03").adapt(
            predicta_response(), case_id="case_003", submitted_name="Northstar Packaging",
            geography="New York", industry="Packaging",
        )
        with tempfile.TemporaryDirectory() as directory:
            db_path = Path(directory) / "intelligence.db"
            repository = SQLiteEvidenceRepository(db_path)
            repository.save_packet(packet)

            loaded = repository.get_packet(packet.packet_id)
            self.assertEqual(loaded.lineage.content_hash, packet.lineage.content_hash)
            self.assertTrue(repository.verify_packet_hash(packet.packet_id))

            with repository.connection() as connection:
                connection.execute("UPDATE evidence_passages SET text='tampered' WHERE packet_id=?", (packet.packet_id,))
            self.assertFalse(repository.verify_packet_hash(packet.packet_id))

    def test_only_reviewed_assumption_with_intact_packet_can_become_canonical_input(self):
        packet = PredictaEvidencePort("session03").adapt(predicta_response(), case_id="case_004", submitted_name="Northstar Packaging", geography="New York", industry="Packaging")
        firewall = FinancialTruthFirewall()
        accepted = firewall.accept(firewall.propose(packet=packet, claim_id="claim_001", metric="input_cost_inflation", value=0.11, unit="ratio", period="2022", origin=AssumptionOrigin.SOURCE_ESTIMATE, transformation="Percent to decimal."), reviewer_id="analyst_01")
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteEvidenceRepository(Path(directory) / "intelligence.db")
            repository.save_packet(packet)
            repository.save_assumption(accepted)
            self.assertEqual(repository.canonical_input(accepted.assumption_id).value, 0.11)

            with repository.connection() as connection:
                connection.execute("UPDATE evidence_passages SET text='tampered' WHERE packet_id=?", (packet.packet_id,))
            with self.assertRaisesRegex(PermissionError, "integrity"):
                repository.canonical_input(accepted.assumption_id)


class IntelligenceRelationshipTests(unittest.TestCase):
    def test_persists_an_evidence_relationship_for_the_next_graph_layer(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = SQLiteRelationshipRepository(Path(directory) / "intelligence.db")
            relationship = IntelligenceRelationship(relationship_id="rel_001", case_id="case_003", from_type="passage", from_id="passage_src_001", relationship_type="SUPPORTS", to_type="claim", to_id="claim_001")
            repository.save(relationship)
            loaded = repository.list_for_case("case_003")
        self.assertEqual(loaded[0].relationship_type, "SUPPORTS")


if __name__ == "__main__":
    unittest.main()
