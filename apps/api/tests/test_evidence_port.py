import unittest

from apps.api.app.evidence import (
    AssumptionOrigin,
    FinancialTruthFirewall,
    PredictaEvidencePort,
)


def predicta_response():
    return {
        "apiVersion": "predicta.search.v1",
        "query": {
            "queryId": "qry_001",
            "rawQuery": "packaging input cost New York 2022",
            "normalizedQuery": "packaging input cost new york 2022",
        },
        "candidates": [
            {
                "candidateId": "src_001",
                "providerId": "census",
                "url": "https://example.gov/series/packaging",
                "canonicalUrl": "https://example.gov/series/packaging",
                "title": "Packaging input-cost series",
                "snippet": "Packaging input costs rose materially during 2022.",
                "publisher": "Example Government Dataset",
                "publicationDate": "2023-01-15",
                "retrievalDate": "2026-09-04T18:00:00Z",
                "sourceType": "PRIMARY",
            },
            {
                "candidateId": "src_002",
                "providerId": "industry_web",
                "url": "https://example.org/industry-note",
                "canonicalUrl": "https://example.org/industry-note",
                "title": "Regional packaging note",
                "snippet": "Some regional converters reported stable contracted prices.",
                "publisher": "Industry Association",
                "publicationDate": "2023-02-01",
                "retrievalDate": "2026-09-04T18:00:01Z",
                "sourceType": "SECONDARY",
            },
        ],
        "claims": [
            {
                "claimId": "claim_001",
                "statement": "Input costs increased materially in 2022.",
                "status": "CONTESTED",
                "evidence": [
                    {"sourceId": "src_001", "passageId": "passage_src_001", "relation": "SUPPORTS"},
                    {"sourceId": "src_002", "passageId": "passage_src_002", "relation": "CONTRADICTS"},
                ],
                "independentSourceCount": 2,
                "limitations": ["Regional and national measures differ."],
            }
        ],
        "diagnostics": {
            "providersRequested": ["census", "industry_web"],
            "providersSucceeded": ["census", "industry_web"],
            "providersFailed": [],
            "latencyMs": 220,
            "estimatedCostUsd": 0,
            "degraded": False,
        },
    }


class PredictaEvidencePortTests(unittest.TestCase):
    def test_adapter_preserves_contradictions_and_builds_stable_lineage(self):
        port = PredictaEvidencePort(predicta_version="1.0.0-session01")
        first = port.adapt(
            predicta_response(), case_id="case_001", submitted_name="Northstar Packaging",
            geography="New York", industry="Packaging manufacturing",
        )
        second = port.adapt(
            predicta_response(), case_id="case_001", submitted_name="Northstar Packaging",
            geography="New York", industry="Packaging manufacturing",
        )

        self.assertEqual(first.schema_version, "analytica.evidence.v1")
        self.assertEqual(first.upstream_api_version, "predicta.search.v1")
        self.assertEqual(first.claims[0].status.value, "CONTESTED")
        self.assertEqual(len(first.contradictions), 1)
        self.assertEqual(first.lineage.content_hash, second.lineage.content_hash)
        self.assertEqual(len(first.lineage.content_hash), 64)
        self.assertTrue(all(len(source.snapshot.content_hash) == 64 for source in first.sources))

    def test_adapter_rejects_unknown_evidence_links(self):
        response = predicta_response()
        response["claims"][0]["evidence"][0]["passageId"] = "missing"
        with self.assertRaisesRegex(ValueError, "unknown passage"):
            PredictaEvidencePort("1.0.0-session01").adapt(
                response, case_id="case_001", submitted_name="Northstar Packaging",
                geography="New York", industry="Packaging manufacturing",
            )


class FinancialTruthFirewallTests(unittest.TestCase):
    def setUp(self):
        self.packet = PredictaEvidencePort("1.0.0-session01").adapt(
            predicta_response(), case_id="case_001", submitted_name="Northstar Packaging",
            geography="New York", industry="Packaging manufacturing",
        )
        self.firewall = FinancialTruthFirewall()

    def test_web_evidence_cannot_become_financial_truth_without_human_acceptance(self):
        proposal = self.firewall.propose(
            packet=self.packet, claim_id="claim_001", metric="input_cost_inflation",
            value=0.11, unit="ratio", period="2022", origin=AssumptionOrigin.SOURCE_ESTIMATE,
            transformation="Converted an 11% cited annual change to a decimal ratio.",
        )
        with self.assertRaisesRegex(PermissionError, "human-approved"):
            self.firewall.to_canonical_input(proposal)

        accepted = self.firewall.accept(proposal, reviewer_id="analyst_001")
        canonical = self.firewall.to_canonical_input(accepted)
        self.assertEqual(canonical.value, 0.11)
        self.assertEqual(canonical.source_claim_ids, ["claim_001"])
        self.assertEqual(canonical.origin, AssumptionOrigin.SOURCE_ESTIMATE)

    def test_unsupported_claim_cannot_be_accepted(self):
        response = predicta_response()
        response["claims"][0]["status"] = "UNSUPPORTED"
        response["claims"][0]["evidence"] = []
        packet = PredictaEvidencePort("1.0.0-session01").adapt(
            response, case_id="case_001", submitted_name="Northstar Packaging",
            geography="New York", industry="Packaging manufacturing",
        )
        proposal = self.firewall.propose(
            packet=packet, claim_id="claim_001", metric="gross_margin", value=0.3,
            unit="ratio", period="2025", origin=AssumptionOrigin.SOURCE_ESTIMATE,
            transformation="Converted percentage to decimal ratio.",
        )
        with self.assertRaisesRegex(ValueError, "unsupported claim"):
            self.firewall.accept(proposal, reviewer_id="analyst_001")


if __name__ == "__main__":
    unittest.main()
