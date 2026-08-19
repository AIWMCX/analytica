# Analytica v1 MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the first browser-visible, fixture-backed Analytica vertical slice for a U.S.-first launch, using Packaging Manufacturing / New York as the canonical demonstrator and preserving the approved production architecture boundaries.

**Architecture:** A FastAPI analytical API owns deterministic analysis contracts, fixture-backed cohort data, scoring, findings, and evidence. A browser client renders the radial business trajectory, cohort summary, evidence drilldown, and top lessons. The first slice deliberately keeps provider adapters fixture-backed so product behavior, visual semantics, and analytical contracts can be verified independently from third-party data quality. The production target remains Next.js + FastAPI; a dependency-free browser preview is included in this increment so R&D progress can be reviewed immediately in this environment.

**Tech Stack:** Python 3.13, FastAPI, Pydantic v2, pytest/unittest-compatible tests, HTML5, CSS, modern browser JavaScript, SVG.

**Spec:** `docs/superpowers/specs/2026-08-18-analytica-v1-design.md`

## Global Constraints

- U.S.-first MVP; canonical launch fixture is Packaging Manufacturing / New York.
- Historical intelligence and prescriptive decision support first; forward prediction is not claimed in this slice.
- External data is fixture-backed in this slice; no unsupported real-company claims.
- Deterministic application code calculates scores, ranking, trajectory, and state.
- AI is not a source of numerical truth.
- Every material finding exposes evidence references and confidence class.
- Radial visualization has no conventional clock numerals and must not rely solely on color.
- Up to ten annual intervals per trajectory.
- Missing historical values remain missing rather than synthesized.
- No private IRS, bank, or confidential data access.
- Product state must visibly distinguish R&D/demo readiness from production launch readiness.

---

### Task 1: Deterministic analysis domain and fixture

**Files:**
- Create: `apps/api/app/domain.py`
- Create: `apps/api/app/fixtures.py`
- Test: `apps/api/tests/test_domain.py`

**Interfaces:**
- Consumes: none.
- Produces: `AnalysisStatus`, `ConfidenceClass`, `EvidenceItem`, `TrajectoryPoint`, `CompanyTrajectory`, `Finding`, `AnalysisReport`, `build_demo_report()`.

- [ ] **Step 1: Write failing tests for report identity, ten-year trajectory bounds, evidence traceability, confidence taxonomy, and ordered lessons.**
- [ ] **Step 2: Run `python3 -m unittest apps.api.tests.test_domain -v` and confirm RED due to missing domain implementation.**
- [ ] **Step 3: Implement typed Pydantic domain models and deterministic fixture generation.**
- [ ] **Step 4: Run the same test command and confirm GREEN.**
- [ ] **Step 5: Commit domain + fixture implementation.**

### Task 2: FastAPI analysis contract and state endpoints

**Files:**
- Create: `apps/api/app/main.py`
- Create: `apps/api/tests/test_api.py`

**Interfaces:**
- Consumes: `build_demo_report()` from Task 1.
- Produces: `GET /health`, `POST /analyses`, `GET /analyses/{analysis_id}`, `GET /analyses/{analysis_id}/status`.

- [ ] **Step 1: Write failing API tests for health, canonical analysis creation, report retrieval, and unknown analysis 404 behavior.**
- [ ] **Step 2: Run `python3 -m unittest apps.api.tests.test_api -v` and confirm RED.**
- [ ] **Step 3: Implement minimal FastAPI endpoints with an in-memory repository for the vertical slice.**
- [ ] **Step 4: Run API tests and full backend test suite; confirm GREEN.**
- [ ] **Step 5: Commit API contract implementation.**

### Task 3: Browser-visible radial demonstrator

**Files:**
- Create: `apps/web-preview/index.html`
- Create: `apps/web-preview/app.js`
- Create: `apps/web-preview/styles.css`
- Create: `apps/web-preview/tests/test_ui_contract.mjs`

**Interfaces:**
- Consumes: JSON shape exposed by Task 2.
- Produces: browser-visible landing/request section, readiness badge, cohort KPI cards, SVG radial trajectory map, selectable company rays, year/evidence drilldown, top lessons.

- [ ] **Step 1: Write failing Node contract tests for required semantic regions, accessibility labels, radial SVG host, evidence drawer hooks, and API endpoint constant.**
- [ ] **Step 2: Run `node --test apps/web-preview/tests/test_ui_contract.mjs` and confirm RED.**
- [ ] **Step 3: Implement the HTML/CSS/JS preview using accessible SVG and deterministic fallback fixture data when the API is unavailable.**
- [ ] **Step 4: Run UI contract tests and confirm GREEN.**
- [ ] **Step 5: Serve the preview locally, capture a visual screenshot, and inspect the result for clipping, readability, radial semantics, mobile behavior, and evidence drilldown.**
- [ ] **Step 6: Commit the browser demonstrator.**

### Task 4: Local integrated preview and launch-readiness instrumentation

**Files:**
- Create: `scripts/run_preview.py`
- Create: `README.md`
- Create: `docs/status/2026-08-19-rd-readiness.md`
- Test: `tests/test_repository_contract.py`

**Interfaces:**
- Consumes: backend and browser preview from Tasks 1-3.
- Produces: one-command local preview, repository onboarding, explicit readiness matrix, known gaps, commercial-launch gates.

- [ ] **Step 1: Write failing repository-contract tests that require the run command, health endpoint documentation, R&D status labels, and explicit non-production limitations.**
- [ ] **Step 2: Run `python3 -m unittest tests.test_repository_contract -v` and confirm RED.**
- [ ] **Step 3: Implement preview runner, README, and readiness document with exact current-state claims.**
- [ ] **Step 4: Run all Python and Node tests and confirm GREEN.**
- [ ] **Step 5: Launch the integrated preview and verify `/health`, `/analyses`, and the visual app manually.**
- [ ] **Step 6: Commit integrated-preview and readiness documentation.**

### Task 5: Review and pull request

**Files:**
- Review all files created above.

**Interfaces:**
- Consumes: complete vertical slice.
- Produces: review-ready feature branch and pull request into `main`.

- [ ] **Step 1: Run full verification suite from a clean process.**
- [ ] **Step 2: Inspect the browser screenshot and fix any obvious visual defects before proposing merge.**
- [ ] **Step 3: Review diff against the approved spec and document intentional MVP deferrals.**
- [ ] **Step 4: Open a pull request from `feat/analytica-v1-mvp` to `main` with verification evidence and readiness state.**
- [ ] **Step 5: Do not merge until the partner reviews the visual preview and technical state.**
