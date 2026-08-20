from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from .domain import AnalysisJob, AnalysisReport, AnalysisStatus, utc_now_iso


class SQLiteAnalysisRepository:
    """Durable local persistence for the MVP prototype.

    Each operation owns and closes its SQLite connection. This makes the repository
    safe for the prototype background worker threads and prevents descriptor leaks.
    PostgreSQL remains the paid-production target.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, timeout=10)
        connection.row_factory = sqlite3.Row
        return connection

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        connection = self._connect()
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS analysis_jobs (
                    analysis_id TEXT PRIMARY KEY,
                    business_activity TEXT NOT NULL,
                    geography TEXT NOT NULL,
                    email TEXT NOT NULL,
                    payment_token TEXT NOT NULL,
                    status TEXT NOT NULL,
                    progress_percent INTEGER NOT NULL,
                    stage_label TEXT NOT NULL,
                    report_json TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def create_job(self, analysis_id: str, business_activity: str, geography: str, email: str, payment_token: str) -> AnalysisJob:
        now = utc_now_iso()
        job = AnalysisJob(
            analysis_id=analysis_id,
            business_activity=business_activity,
            geography=geography,
            email=email,
            payment_token=payment_token,
            status=AnalysisStatus.QUEUED,
            progress_percent=2,
            stage_label="Queued",
            created_at=now,
            updated_at=now,
        )
        with self._connection() as connection:
            connection.execute(
                """INSERT INTO analysis_jobs
                (analysis_id,business_activity,geography,email,payment_token,status,progress_percent,stage_label,report_json,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,NULL,?,?)""",
                (
                    job.analysis_id,
                    job.business_activity,
                    job.geography,
                    job.email,
                    job.payment_token,
                    job.status.value,
                    job.progress_percent,
                    job.stage_label,
                    job.created_at,
                    job.updated_at,
                ),
            )
        return job

    def update_status(self, analysis_id: str, status: AnalysisStatus, progress_percent: int, stage_label: str) -> None:
        now = utc_now_iso()
        with self._connection() as connection:
            cursor = connection.execute(
                "UPDATE analysis_jobs SET status=?,progress_percent=?,stage_label=?,updated_at=? WHERE analysis_id=?",
                (status.value, progress_percent, stage_label, now, analysis_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(analysis_id)

    def save_report(self, report: AnalysisReport) -> None:
        now = utc_now_iso()
        with self._connection() as connection:
            cursor = connection.execute(
                """UPDATE analysis_jobs
                SET report_json=?,status=?,progress_percent=100,stage_label=?,updated_at=?
                WHERE analysis_id=?""",
                (report.model_dump_json(), AnalysisStatus.COMPLETED.value, "Analysis complete", now, report.analysis_id),
            )
            if cursor.rowcount == 0:
                raise KeyError(report.analysis_id)

    def get_job(self, analysis_id: str) -> AnalysisJob | None:
        with self._connection() as connection:
            row = connection.execute("SELECT * FROM analysis_jobs WHERE analysis_id=?", (analysis_id,)).fetchone()
        if row is None:
            return None
        return AnalysisJob(
            analysis_id=row["analysis_id"],
            business_activity=row["business_activity"],
            geography=row["geography"],
            email=row["email"],
            payment_token=row["payment_token"],
            status=AnalysisStatus(row["status"]),
            progress_percent=row["progress_percent"],
            stage_label=row["stage_label"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def get_report(self, analysis_id: str) -> AnalysisReport | None:
        with self._connection() as connection:
            row = connection.execute("SELECT report_json FROM analysis_jobs WHERE analysis_id=?", (analysis_id,)).fetchone()
        if row is None or row["report_json"] is None:
            return None
        return AnalysisReport.model_validate_json(row["report_json"])
