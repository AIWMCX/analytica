from __future__ import annotations

import threading
import time
from uuid import uuid4

from .domain import AnalysisStatus
from .fixtures import build_demo_report
from .repository import SQLiteAnalysisRepository


class AnalysisService:
    SUPPORTED_BUSINESS = "packaging manufacturing"
    SUPPORTED_GEOS = {"new york", "ny"}
    STAGES = (
        (AnalysisStatus.DISCOVERING_COMPANIES, 15, "Discovering comparable companies"),
        (AnalysisStatus.COLLECTING_EVIDENCE, 34, "Collecting historical evidence"),
        (AnalysisStatus.NORMALIZING, 50, "Normalizing company timelines"),
        (AnalysisStatus.SCORING, 68, "Scoring peer trajectories"),
        (AnalysisStatus.GENERATING_FINDINGS, 84, "Generating evidence-backed findings"),
        (AnalysisStatus.RENDERING_RESULT, 96, "Rendering decision report"),
    )

    def __init__(self, repository: SQLiteAnalysisRepository, stage_delay: float = 0.08):
        self.repository = repository
        self.stage_delay = max(0.0, stage_delay)
        self._workers: set[threading.Thread] = set()
        self._worker_lock = threading.Lock()

    @property
    def active_worker_count(self) -> int:
        with self._worker_lock:
            self._workers = {worker for worker in self._workers if worker.is_alive()}
            return len(self._workers)

    def wait_for_all(self, timeout: float | None = None) -> None:
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            with self._worker_lock:
                workers = list(self._workers)
            if not workers:
                return
            for worker in workers:
                remaining = None if deadline is None else max(0.0, deadline - time.monotonic())
                worker.join(remaining)
            with self._worker_lock:
                self._workers = {worker for worker in self._workers if worker.is_alive()}
                if not self._workers:
                    return
            if deadline is not None and time.monotonic() >= deadline:
                return

    def _validate_scope(self, business_activity: str, geography: str) -> None:
        if business_activity.strip().lower() != self.SUPPORTED_BUSINESS or geography.strip().lower() not in self.SUPPORTED_GEOS:
            raise ValueError("This MVP prototype currently supports Packaging manufacturing / New York only.")

    def create_analysis(self, business_activity: str, geography: str, email: str, payment_token: str, run_async: bool = True) -> str:
        self._validate_scope(business_activity, geography)
        if not payment_token.startswith("demo_pay_"):
            raise PermissionError("valid prototype payment authorization is required")
        analysis_id = f"ana_{uuid4().hex[:12]}"
        self.repository.create_job(analysis_id, business_activity.strip(), "New York", email, payment_token)
        if run_async:
            worker = threading.Thread(target=self._run_worker, args=(analysis_id,), daemon=True, name=f"analytica-{analysis_id}")
            with self._worker_lock:
                self._workers.add(worker)
            worker.start()
        else:
            self.run_analysis(analysis_id)
        return analysis_id

    def _run_worker(self, analysis_id: str) -> None:
        try:
            self.run_analysis(analysis_id)
        finally:
            current = threading.current_thread()
            with self._worker_lock:
                self._workers.discard(current)

    def run_analysis(self, analysis_id: str) -> None:
        job = self.repository.get_job(analysis_id)
        if job is None:
            raise KeyError(analysis_id)
        try:
            for status, progress, label in self.STAGES:
                self.repository.update_status(analysis_id, status, progress, label)
                if self.stage_delay:
                    time.sleep(self.stage_delay)
            report = build_demo_report(analysis_id=analysis_id, business_activity=job.business_activity, geography=job.geography)
            self.repository.save_report(report)
        except Exception:
            self.repository.update_status(analysis_id, AnalysisStatus.FAILED_RETRYABLE, 0, "Prototype analysis failed")
            raise
