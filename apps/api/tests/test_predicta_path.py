import json
import tempfile
import unittest
from pathlib import Path
from urllib.error import HTTPError
from apps.api.tests.test_evidence_port import predicta_response
from apps.api.app.predicta_path import PredictaHttpPort, ResearchCase, run_case


class PredictaPathTests(unittest.TestCase):
    def port(self, transport):
        return PredictaHttpPort('https://aiwmc.org', timeout=2, attempts=2, transport=transport, sleep=lambda _: None)

    def test_correct_version(self):
        self.assertEqual(self.port(lambda request, timeout: predicta_response()).search('query', 'case')['apiVersion'], 'predicta.search.v1')

    def test_wrong_version(self):
        response = predicta_response(); response['apiVersion'] = 'v2'
        with self.assertRaises(ValueError):
            self.port(lambda r, t: response).search('q', 'case')

    def test_invalid_schema(self):
        with self.assertRaises(ValueError):
            self.port(lambda r, t: {'apiVersion': 'predicta.search.v1'}).search('q', 'case')

    def assert_retry(self, error):
        calls = []
        def transport(request, timeout):
            calls.append(timeout)
            raise error
        with self.assertRaises(type(error)):
            self.port(transport).search('q', 'case')
        self.assertEqual(calls, [2, 2])

    def test_timeout(self):
        self.assert_retry(TimeoutError('timeout'))

    def test_429(self):
        self.assert_retry(HTTPError('https://aiwmc.org', 429, 'limited', {'Retry-After': '0'}, None))

    def test_503(self):
        self.assert_retry(HTTPError('https://aiwmc.org', 503, 'unavailable', {}, None))

    def test_contradictions_diagnostics_and_hash_survive_persistence(self):
        response = predicta_response(); response['diagnostics']['degraded'] = True
        with tempfile.TemporaryDirectory() as folder:
            store, run_id = run_case(ResearchCase('case', 'q', 'Company', 'NY', 'Packaging'), self.port(lambda r, t: response), Path(folder)/'db')
            manifest = store.manifest(run_id)
            self.assertEqual(manifest['state'], 'DEGRADED')
            self.assertEqual(manifest['response']['diagnostics'], response['diagnostics'])
            packet = store.get_packet(manifest['packet_id'])
            self.assertEqual(len(packet.contradictions), 1)
            self.assertTrue(store.verify_packet_hash(packet.packet_id))
            with store.connection() as db:
                db.execute("UPDATE evidence_passages SET text='tampered'")
            self.assertFalse(store.verify_packet_hash(packet.packet_id))

    def test_no_fixture_fallback(self):
        def fail(r, t):
            raise TimeoutError('timeout')
        with tempfile.TemporaryDirectory() as folder:
            with self.assertRaises(TimeoutError):
                run_case(ResearchCase('case', 'q', 'Company', 'NY', 'Packaging'), self.port(fail), Path(folder)/'db')

    def test_source_passage_mismatch_rejected(self):
        response = predicta_response()
        response['claims'][0]['evidence'][0]['passageId'] = 'passage_src_002'
        with self.assertRaises(ValueError):
            self.port(lambda r,t: response).search('q', 'case')
