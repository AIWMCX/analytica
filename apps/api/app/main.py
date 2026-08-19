from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException, status
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from .domain import AnalysisReport
from .fixtures import build_demo_report


app = FastAPI(title="Analytica API", version="0.1.0")


class CreateAnalysisRequest(BaseModel):
    business_activity: str = Field(min_length=2, max_length=160)
    geography: str = Field(min_length=2, max_length=120)


class CreateAnalysisResponse(BaseModel):
    analysis_id: str
    status: str
    report_url: str


_ANALYSES: dict[str, AnalysisReport] = {}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "analytica-api", "version": app.version}


@app.post("/analyses", response_model=CreateAnalysisResponse, status_code=status.HTTP_201_CREATED)
def create_analysis(request: CreateAnalysisRequest) -> CreateAnalysisResponse:
    normalized_business = request.business_activity.strip().lower()
    normalized_geo = request.geography.strip().lower()
    if normalized_business != "packaging manufacturing" or normalized_geo not in {"new york", "ny"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="This R&D vertical slice currently supports Packaging manufacturing / New York only.",
        )

    report = build_demo_report()
    _ANALYSES[report.analysis_id] = report
    return CreateAnalysisResponse(
        analysis_id=report.analysis_id,
        status=report.status.value,
        report_url=f"/analyses/{report.analysis_id}",
    )


def _get_report(analysis_id: str) -> AnalysisReport:
    report = _ANALYSES.get(analysis_id)
    if report is None:
        canonical = build_demo_report()
        if analysis_id == canonical.analysis_id:
            _ANALYSES[analysis_id] = canonical
            return canonical
        raise HTTPException(status_code=404, detail="analysis not found")
    return report


@app.get("/analyses/{analysis_id}", response_model=AnalysisReport)
def get_analysis(analysis_id: str) -> AnalysisReport:
    return _get_report(analysis_id)


@app.get("/analyses/{analysis_id}/status")
def get_analysis_status(analysis_id: str) -> dict[str, str]:
    report = _get_report(analysis_id)
    return {"analysis_id": report.analysis_id, "status": report.status.value}


# Mount the dependency-free R&D browser client after API routes so a single
# uvicorn process exposes both the typed API and visual demonstrator.
_WEB_DIR = Path(__file__).resolve().parents[3] / "apps" / "web-preview"
if _WEB_DIR.exists():
    app.mount("/", StaticFiles(directory=_WEB_DIR, html=True), name="web-preview")
