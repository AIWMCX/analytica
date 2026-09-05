import unittest

from apps.api.app.evidence import FinancialTruthFirewall, ProposedAssumption
from apps.api.app.research_pipeline import ProviderRecord, ResearchPipeline


class IntegrityBoundaryTests(unittest.TestCase):
    def test_forged_record_hash_is_rejected(self):
        with self.assertRaises(ValueError):
            ProviderRecord('sec_edgar', 'one', 'Filing', 'https://www.sec.gov/one',
                           'actual text', 'OFFICIAL_FILING', 'COMPANY', content_hash='0' * 64)

    def test_exception_details_do_not_leak_into_manifest(self):
        class Provider:
            provider_id = 'fred'
            def collect(self, query):
                raise RuntimeError('https://host?api_key=secret-value')
        run = ResearchPipeline([Provider()]).run('case', 'query')
        self.assertEqual(run.manifest.providers['fred'], 'FAILED')
        self.assertNotIn('secret-value', str(run.manifest))

    def test_duplicate_provider_ids_rejected_before_collection(self):
        class Provider:
            provider_id = 'fred'
        with self.assertRaises(ValueError):
            ResearchPipeline([Provider(), Provider()])

    def test_accepted_flag_alone_cannot_bypass_review_validation(self):
        proposal = ProposedAssumption(
            assumption_id='a', packet_id='p', metric='margin', value=0.2,
            unit='ratio', period='2025', origin='SOURCE_ESTIMATE',
            transformation='percentage conversion', source_claim_ids=['c'],
            source_claim_statuses=['SUPPORTED'], review_status='ACCEPTED',
            reviewer_id='analyst', reviewed_at=None,
        )
        with self.assertRaises(PermissionError):
            FinancialTruthFirewall().to_canonical_input(proposal)
