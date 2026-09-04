from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterator, Literal

from pydantic import BaseModel, Field


class IntelligenceRelationship(BaseModel):
    relationship_id: str
    case_id: str
    from_type: str
    from_id: str
    relationship_type: Literal["SUPPORTS", "CONTRADICTS", "CONCERNS", "DERIVED_FROM", "CONSTRAINS", "SUPERSEDES"]
    to_type: str
    to_id: str
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    metadata: dict = Field(default_factory=dict)


class SQLiteRelationshipRepository:
    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path); self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.execute("CREATE TABLE IF NOT EXISTS intelligence_relationships (relationship_id TEXT PRIMARY KEY, case_id TEXT NOT NULL, from_type TEXT NOT NULL, from_id TEXT NOT NULL, relationship_type TEXT NOT NULL, to_type TEXT NOT NULL, to_id TEXT NOT NULL, created_at TEXT NOT NULL, metadata_json TEXT NOT NULL)")

    @contextmanager
    def connection(self) -> Iterator[sqlite3.Connection]:
        db = sqlite3.connect(self.db_path); db.row_factory = sqlite3.Row
        try: yield db; db.commit()
        except Exception: db.rollback(); raise
        finally: db.close()

    def save(self, relationship: IntelligenceRelationship) -> None:
        with self.connection() as db:
            db.execute("INSERT INTO intelligence_relationships VALUES (?,?,?,?,?,?,?,?,?)", (relationship.relationship_id, relationship.case_id, relationship.from_type, relationship.from_id, relationship.relationship_type, relationship.to_type, relationship.to_id, relationship.created_at, json.dumps(relationship.metadata, sort_keys=True)))

    def list_for_case(self, case_id: str) -> list[IntelligenceRelationship]:
        with self.connection() as db: rows = db.execute("SELECT * FROM intelligence_relationships WHERE case_id=?", (case_id,)).fetchall()
        return [IntelligenceRelationship(**{**dict(row), "metadata": json.loads(row["metadata_json"])}) for row in rows]
