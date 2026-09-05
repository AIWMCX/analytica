"""Internal live research command. Never imports fixture or financial services."""
import json
import os
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from uuid import uuid4

from .evidence import PredictaEvidencePort, _sha256
from .evidence_repository import SQLiteEvidenceRepository


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def transport(request, timeout):
    with build_opener(NoRedirect()).open(request, timeout=timeout) as response:
        data = response.read(4_000_001)
        if len(data) > 4_000_000:
            raise ValueError('Predicta response exceeds size limit')
        return json.loads(data)


def validate(response):
    if not isinstance(response, dict) or response.get('apiVersion') != 'predicta.search.v1':
        raise ValueError('Predicta version mismatch')
    if not isinstance(response.get('query'), dict) or not response['query'].get('queryId'):
        raise ValueError('missing query identity')
    for key in ('candidates', 'claims'):
        if not isinstance(response.get(key), list):
            raise ValueError('invalid search schema')
    diagnostics = response.get('diagnostics')
    if not isinstance(diagnostics, dict) or type(diagnostics.get('degraded')) is not bool:
        raise ValueError('missing diagnostics')
    for key in ('providersSucceeded', 'providersFailed', 'providersRequested'):
        if not isinstance(diagnostics.get(key), list):
            raise ValueError('invalid diagnostics')
    ids = set()
    for source in response['candidates']:
        for field in ('candidateId', 'providerId', 'canonicalUrl', 'title', 'snippet', 'retrievalDate'):
            if not isinstance(source.get(field), str):
                raise ValueError('invalid source provenance')
        if source['candidateId'] in ids:
            raise ValueError('duplicate source')
        ids.add(source['candidateId'])
        if urlsplit(source['canonicalUrl']).scheme not in ('https', 'http'):
            raise ValueError('invalid source URL')
    claims = set()
    for claim in response['claims']:
        if claim['claimId'] in claims:
            raise ValueError('duplicate claim')
        claims.add(claim['claimId'])
        for link in claim['evidence']:
            if link['sourceId'] not in ids or link['passageId'] != 'passage_' + link['sourceId']:
                raise ValueError('source/passage mismatch')
    # Validate typed claim states and remaining references before persisting anything.
    PredictaEvidencePort('predicta.search.v1').adapt(response, case_id='validation', submitted_name='', geography='', industry='')
    return response


class PredictaHttpPort:
    def __init__(self, base_url=None, *, timeout=None, attempts=None, transport=transport, sleep=time.sleep):
        self.base_url = base_url or os.environ.get('PREDICTA_BASE_URL', '')
        url = urlsplit(self.base_url)
        if url.scheme != 'https' or not url.hostname or url.username or url.password or url.query or url.fragment:
            raise ValueError('PREDICTA_BASE_URL must be an HTTPS service URL')
        self.timeout = float(timeout if timeout is not None else os.environ.get('PREDICTA_TIMEOUT_SECONDS', '15'))
        self.attempts = int(attempts if attempts is not None else os.environ.get('PREDICTA_MAX_ATTEMPTS', '3'))
        if not 0 < self.timeout <= 60 or not 1 <= self.attempts <= 4:
            raise ValueError('invalid timeout or retry bound')
        self.transport, self.sleep = transport, sleep

    def search(self, query, case_id):
        headers = {'Content-Type': 'application/json', 'Accept': 'application/json', 'User-Agent': 'Analytica research adapter/1.0'}
        token = os.environ.get('PREDICTA_API_KEY')
        if token:
            headers['Authorization'] = 'Bearer ' + token
        payload = dict(rawQuery=query, sessionId=case_id, queryVersion=0, language='en', country='US', lens='financial', safeSearch='moderate', mode='quick')
        request = Request(self.base_url.rstrip('/')+'/api/search', data=json.dumps(payload).encode(), headers=headers, method='POST')
        for attempt in range(self.attempts):
            delay = min(2 ** attempt, 8)
            try:
                return validate(self.transport(request, self.timeout))
            except HTTPError as error:
                if error.code != 429 and not 500 <= error.code < 600:
                    raise
                retry_after = (error.headers or {}).get('Retry-After', '')
                if retry_after.isdigit():
                    delay = min(int(retry_after), 30)
                if attempt + 1 == self.attempts:
                    raise
            except (TimeoutError, URLError):
                if attempt + 1 == self.attempts:
                    raise
            self.sleep(delay)


@dataclass(frozen=True)
class ResearchCase:
    case_id: str
    query: str
    submitted_name: str
    geography: str
    industry: str


class CaseStore(SQLiteEvidenceRepository):
    def __init__(self, path):
        super().__init__(path)
        with self.connection() as db:
            db.execute('CREATE TABLE IF NOT EXISTS predicta_runs (run_id TEXT PRIMARY KEY, manifest TEXT NOT NULL)')

    def manifest(self, run_id):
        with self.connection() as db:
            return json.loads(db.execute('SELECT manifest FROM predicta_runs WHERE run_id=?', (run_id,)).fetchone()[0])


def run_case(case, port, path):
    store, run_id = CaseStore(path), uuid4().hex
    manifest = dict(run_id=run_id, case_id=case.case_id, state='RUNNING', started_at=datetime.now(timezone.utc).isoformat(), packet_id=None)
    with store.connection() as db:
        db.execute('INSERT INTO predicta_runs VALUES (?,?)', (run_id, json.dumps(manifest)))
    try:
        response = port.search(case.query, case.case_id)
        manifest.update(response=response, response_hash=_sha256(response))
        normalized = dict(response)
        normalized['query'] = {**response['query'], 'analytica_run_id': run_id, 'predicta_diagnostics': response['diagnostics']}
        packet = PredictaEvidencePort('predicta.search.v1').adapt(normalized, case_id=case.case_id, submitted_name=case.submitted_name, geography=case.geography, industry=case.industry)
        store.save_packet(packet)
        if not store.verify_packet_hash(packet.packet_id):
            raise ValueError('persisted packet integrity failed')
        manifest['packet_id'] = packet.packet_id
        manifest['state'] = 'DEGRADED' if response['diagnostics']['degraded'] or response['diagnostics']['providersFailed'] or not packet.sources else 'SUCCEEDED'
    except Exception as error:
        manifest.update(state='FAILED', error_type=type(error).__name__, http_status=getattr(error, 'code', None))
        raise
    finally:
        manifest['finished_at'] = datetime.now(timezone.utc).isoformat()
        with store.connection() as db:
            db.execute('UPDATE predicta_runs SET manifest=? WHERE run_id=?', (json.dumps(manifest), run_id))
    return store, run_id
