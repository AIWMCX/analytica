from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .evidence import (CanonicalFinancialInput, ClaimEvidenceLink, EvidenceClaim, EvidenceContradiction,
                       EvidenceLineage, EvidencePacket, EvidencePassage, EvidenceQuality, EvidenceSnapshot,
                       EvidenceSource, EvidenceSubject, FinancialTruthFirewall, ProposedAssumption, _sha256)


class SQLiteEvidenceRepository:
    """Normalized, append-only provenance persistence for evidence packets."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection; connection.commit()
        except Exception:
            connection.rollback(); raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self.connection() as db:
            db.executescript("""
            CREATE TABLE IF NOT EXISTS evidence_packets (packet_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, research_run_id TEXT NOT NULL, upstream_api_version TEXT NOT NULL, subject_json TEXT NOT NULL, query_json TEXT NOT NULL, quality_json TEXT NOT NULL, lineage_json TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS evidence_sources (packet_id TEXT NOT NULL, source_id TEXT NOT NULL, provider_id TEXT NOT NULL, canonical_url TEXT NOT NULL, title TEXT NOT NULL, publisher TEXT NOT NULL, publication_date TEXT, source_type TEXT NOT NULL, PRIMARY KEY(packet_id, source_id));
            CREATE TABLE IF NOT EXISTS source_snapshots (packet_id TEXT NOT NULL, source_id TEXT NOT NULL, retrieved_at TEXT NOT NULL, content_hash TEXT NOT NULL, text TEXT NOT NULL, PRIMARY KEY(packet_id, source_id));
            CREATE TABLE IF NOT EXISTS evidence_passages (packet_id TEXT NOT NULL, passage_id TEXT NOT NULL, source_id TEXT NOT NULL, text TEXT NOT NULL, content_hash TEXT NOT NULL, PRIMARY KEY(packet_id, passage_id));
            CREATE TABLE IF NOT EXISTS evidence_claims (packet_id TEXT NOT NULL, claim_id TEXT NOT NULL, statement TEXT NOT NULL, status TEXT NOT NULL, independent_source_count INTEGER NOT NULL, limitations_json TEXT NOT NULL, evidence_json TEXT NOT NULL, PRIMARY KEY(packet_id, claim_id));
            CREATE TABLE IF NOT EXISTS evidence_contradictions (packet_id TEXT NOT NULL, contradiction_id TEXT NOT NULL, claim_id TEXT NOT NULL, supporting_json TEXT NOT NULL, contradicting_json TEXT NOT NULL, explanation TEXT NOT NULL, PRIMARY KEY(packet_id, contradiction_id));
            CREATE TABLE IF NOT EXISTS financial_assumptions (assumption_id TEXT PRIMARY KEY, packet_id TEXT NOT NULL, proposal_json TEXT NOT NULL);
            """)

    def save_packet(self, packet: EvidencePacket) -> None:
        with self.connection() as db:
            db.execute("INSERT INTO evidence_packets VALUES (?,?,?,?,?,?,?,?)", (packet.packet_id, packet.case_id, packet.research_run_id, packet.upstream_api_version, packet.subject.model_dump_json(), json.dumps(packet.query, sort_keys=True), packet.quality.model_dump_json(), packet.lineage.model_dump_json()))
            for source in packet.sources:
                db.execute("INSERT INTO evidence_sources VALUES (?,?,?,?,?,?,?,?)", (packet.packet_id, source.source_id, source.provider_id, source.canonical_url, source.title, source.publisher, source.publication_date, source.source_type))
                db.execute("INSERT INTO source_snapshots VALUES (?,?,?,?,?)", (packet.packet_id, source.source_id, source.snapshot.retrieved_at, source.snapshot.content_hash, source.snapshot.text))
            for passage in packet.passages:
                db.execute("INSERT INTO evidence_passages VALUES (?,?,?,?,?)", (packet.packet_id, passage.passage_id, passage.source_id, passage.text, passage.content_hash))
            for claim in packet.claims:
                db.execute("INSERT INTO evidence_claims VALUES (?,?,?,?,?,?,?)", (packet.packet_id, claim.claim_id, claim.statement, claim.status.value, claim.independent_source_count, json.dumps(claim.limitations), json.dumps([item.model_dump(mode='json') for item in claim.evidence])))
            for item in packet.contradictions:
                db.execute("INSERT INTO evidence_contradictions VALUES (?,?,?,?,?,?)", (packet.packet_id, item.contradiction_id, item.claim_id, json.dumps(item.supporting_passage_ids), json.dumps(item.contradicting_passage_ids), item.explanation))

    def get_packet(self, packet_id: str) -> EvidencePacket | None:
        with self.connection() as db:
            packet = db.execute("SELECT * FROM evidence_packets WHERE packet_id=?", (packet_id,)).fetchone()
            if packet is None: return None
            snapshots = {row["source_id"]: row for row in db.execute("SELECT * FROM source_snapshots WHERE packet_id=?", (packet_id,))}
            sources = [EvidenceSource(source_id=row["source_id"], provider_id=row["provider_id"], canonical_url=row["canonical_url"], title=row["title"], publisher=row["publisher"], publication_date=row["publication_date"], source_type=row["source_type"], snapshot=EvidenceSnapshot(**dict(snapshots[row["source_id"]]))) for row in db.execute("SELECT * FROM evidence_sources WHERE packet_id=?", (packet_id,))]
            passages = [EvidencePassage(passage_id=row["passage_id"], source_id=row["source_id"], text=row["text"], content_hash=row["content_hash"]) for row in db.execute("SELECT * FROM evidence_passages WHERE packet_id=?", (packet_id,))]
            claims = [EvidenceClaim(claim_id=row["claim_id"], statement=row["statement"], status=row["status"], independent_source_count=row["independent_source_count"], limitations=json.loads(row["limitations_json"]), evidence=[ClaimEvidenceLink(**item) for item in json.loads(row["evidence_json"])]) for row in db.execute("SELECT * FROM evidence_claims WHERE packet_id=?", (packet_id,))]
            contradictions = [EvidenceContradiction(contradiction_id=row["contradiction_id"], claim_id=row["claim_id"], supporting_passage_ids=json.loads(row["supporting_json"]), contradicting_passage_ids=json.loads(row["contradicting_json"]), explanation=row["explanation"]) for row in db.execute("SELECT * FROM evidence_contradictions WHERE packet_id=?", (packet_id,))]
        return EvidencePacket(packet_id=packet["packet_id"], case_id=packet["case_id"], research_run_id=packet["research_run_id"], upstream_api_version=packet["upstream_api_version"], subject=EvidenceSubject.model_validate_json(packet["subject_json"]), query=json.loads(packet["query_json"]), sources=sources, passages=passages, claims=claims, contradictions=contradictions, quality=EvidenceQuality.model_validate_json(packet["quality_json"]), lineage=EvidenceLineage.model_validate_json(packet["lineage_json"]))

    def list_packets_for_case(self, case_id: str) -> list[EvidencePacket]:
        with self.connection() as db:
            ids = [row[0] for row in db.execute("SELECT packet_id FROM evidence_packets WHERE case_id=?", (case_id,))]
        return [packet for packet_id in ids if (packet := self.get_packet(packet_id))]

    def verify_packet_hash(self, packet_id: str) -> bool:
        packet = self.get_packet(packet_id)
        if packet is None: return False
        payload = {"case_id": packet.case_id, "research_run_id": packet.research_run_id, "subject": {"submitted_name": packet.subject.submitted_name, "geography": packet.subject.geography, "industry": packet.subject.industry}, "query": packet.query, "sources": [item.model_dump(mode="json") for item in packet.sources], "passages": [item.model_dump(mode="json") for item in packet.passages], "claims": [item.model_dump(mode="json") for item in packet.claims], "contradictions": [item.model_dump(mode="json") for item in packet.contradictions], "quality": packet.quality.model_dump(mode="json")}
        return _sha256(payload) == packet.lineage.content_hash

    def save_assumption(self, proposal: ProposedAssumption) -> None:
        if self.get_packet(proposal.packet_id) is None:
            raise ValueError("assumption references missing evidence packet")
        with self.connection() as db:
            db.execute("INSERT INTO financial_assumptions VALUES (?,?,?)", (proposal.assumption_id, proposal.packet_id, proposal.model_dump_json()))

    def canonical_input(self, assumption_id: str) -> CanonicalFinancialInput:
        with self.connection() as db:
            row = db.execute("SELECT proposal_json, packet_id FROM financial_assumptions WHERE assumption_id=?", (assumption_id,)).fetchone()
        if row is None:
            raise KeyError(assumption_id)
        if not self.verify_packet_hash(row["packet_id"]):
            raise PermissionError("evidence packet integrity is invalid")
        packet = self.get_packet(row["packet_id"])
        proposal = ProposedAssumption.model_validate_json(row["proposal_json"])
        if not set(proposal.source_claim_ids).issubset({claim.claim_id for claim in packet.claims}):
            raise PermissionError("assumption claim lineage is incomplete")
        return FinancialTruthFirewall().to_canonical_input(proposal)
