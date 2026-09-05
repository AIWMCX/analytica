"""Append-only research audit storage. This store never creates financial inputs."""
import json
import sqlite3
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path

from .research_pipeline import ProviderRecord, ResearchRun, ResearchRunManifest


class ResearchStore:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript('''
                CREATE TABLE IF NOT EXISTS research_runs (
                    run_id TEXT PRIMARY KEY, case_id TEXT NOT NULL,
                    providers_json TEXT NOT NULL, failures_json TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS research_records (
                    run_id TEXT NOT NULL REFERENCES research_runs(run_id),
                    provider_id TEXT NOT NULL, record_id TEXT NOT NULL,
                    title TEXT NOT NULL, canonical_url TEXT NOT NULL, text TEXT NOT NULL,
                    authority TEXT NOT NULL, data_scope TEXT NOT NULL,
                    retrieved_at TEXT NOT NULL, content_hash TEXT NOT NULL,
                    PRIMARY KEY(run_id, provider_id, record_id));
            ''')

    @contextmanager
    def connection(self):
        db = sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        try:
            with db:
                yield db
        finally:
            db.close()

    def save(self, run_id: str, run: ResearchRun):
        if run.fixture_fallback_used:
            raise ValueError('fixture fallback is not permitted in research storage')
        with self.connection() as db:
            db.execute('INSERT INTO research_runs VALUES (?,?,?,?)', (
                run_id, run.manifest.case_id, json.dumps(run.manifest.providers),
                json.dumps(run.manifest.failures)))
            for record in run.records:
                validated = ProviderRecord(**asdict(record))
                db.execute('INSERT INTO research_records VALUES (?,?,?,?,?,?,?,?,?,?)', (
                    run_id, validated.provider_id, validated.record_id, validated.title,
                    validated.canonical_url, validated.text, validated.authority,
                    validated.data_scope, validated.retrieved_at, validated.content_hash))

    def get(self, run_id: str) -> ResearchRun | None:
        with self.connection() as db:
            row = db.execute('SELECT * FROM research_runs WHERE run_id=?', (run_id,)).fetchone()
            if row is None:
                return None
            records = []
            for record in db.execute('SELECT * FROM research_records WHERE run_id=? ORDER BY provider_id, record_id', (run_id,)):
                payload = dict(record)
                payload.pop('run_id')
                records.append(ProviderRecord(**payload))
            manifest = ResearchRunManifest(row['case_id'], json.loads(row['providers_json']), json.loads(row['failures_json']))
            return ResearchRun(manifest, records)
