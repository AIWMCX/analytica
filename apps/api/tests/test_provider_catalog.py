import unittest

from apps.api.app.providers import DataProviderCatalog, IntendedUse


class DataProviderCatalogTests(unittest.TestCase):
    def setUp(self):
        self.catalog = DataProviderCatalog()

    def test_official_company_filing_can_be_proposed_but_not_promoted_to_financial_truth(self):
        assessment = self.catalog.assess("sec_edgar", IntendedUse.FINANCIAL_ASSUMPTION_PROPOSAL)

        self.assertTrue(assessment.allowed)
        self.assertEqual(assessment.provider.authority, "OFFICIAL_FILING")
        self.assertFalse(self.catalog.assess("sec_edgar", IntendedUse.CANONICAL_FINANCIAL_TRUTH).allowed)

    def test_social_profile_data_is_discovery_only_and_cannot_seed_a_financial_assumption(self):
        assessment = self.catalog.assess("social_media", IntendedUse.FINANCIAL_ASSUMPTION_PROPOSAL)

        self.assertFalse(assessment.allowed)
        self.assertEqual(assessment.provider.permitted_uses, (IntendedUse.DISCOVERY,))

    def test_public_dataset_catalog_separates_company_benchmarks_and_macro_evidence(self):
        company = self.catalog.get("sec_edgar")
        benchmark = self.catalog.get("census")
        macro = self.catalog.get("fred")

        self.assertEqual(company.data_scope, "COMPANY")
        self.assertEqual(benchmark.data_scope, "BENCHMARK")
        self.assertEqual(macro.data_scope, "MACRO")


if __name__ == "__main__":
    unittest.main()
