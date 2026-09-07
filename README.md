# Analytica

Analytica is an evidence-driven historical business-intelligence and decision-support product. This branch contains the first **workable MVP prototype** for the approved U.S.-first launch architecture.

The current canonical demonstrator is:

- **Business:** Packaging manufacturing
- **Geography:** New York
- **Historical model:** up to ten annual trajectory points
- **Peer cohort:** five synthetic companies for deterministic R&D validation
- **Commercial UX:** $1 analysis contract in safe demo mode
- **Data boundary:** synthetic fixture only — no real-company conclusions are asserted

## What works now

The prototype is executable end-to-end and demonstrates the product flow:

`business + geography + email -> demo checkout -> async analysis -> persisted result -> radial trajectory -> evidence drilldown -> findings -> Top 10 lessons`

Implemented components:

- typed Pydantic analysis/evidence contracts;
- evidence traceability and explicit confidence taxonomy;
- deterministic historical performance/risk trajectories;
- synthetic success, active, distress and failure peer cases;
- SQLite-backed durable MVP analysis-job persistence;
- explicit asynchronous analysis state machine with progress percentages;
- FastAPI health, readiness, pricing, checkout, analysis, status and report endpoints;
- $1 prototype checkout API boundary;
- responsive browser UI;
- radial ten-year trajectory visualization;
- keyboard-selectable trajectory points;
- evidence provenance drilldown;
- cross-company findings;
- Top 10 evidence-referenced lessons;
- explicit technical-readiness dashboard in the product UI;
- dependency-free static fallback data for visual review when the API is unavailable;
- deterministic SVG executive preview and CI verification workflow.

## Important commercial boundary

**No real payment is charged in this prototype.** The `$1.00` checkout flow is a deliberately safe `prototype_demo` provider that validates the commercial API and user experience without processing money.

The build is also **not yet using real-company data**. All displayed company names, events, evidence, scores, findings and lessons are synthetic R&D fixtures.

## Run the workable prototype

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/build_demo_data.py
python3 scripts/run_preview.py
```

Open:

```text
http://127.0.0.1:8000/
```

Health:

```text
GET http://127.0.0.1:8000/health
```

Technical readiness:

```text
GET http://127.0.0.1:8000/readiness
```

Pricing contract:

```text
GET http://127.0.0.1:8000/pricing
```

Canonical static demo report:

```text
GET http://127.0.0.1:8000/analyses/demo_packaging_ny_v1
```

## Visual review

The repository includes two review paths:

- interactive browser prototype: `apps/web-preview/index.html` (served by the FastAPI preview runner);
- deterministic executive snapshot: `docs/previews/analytica-mvp-dashboard.svg`, generated from the same backend fixture and readiness model.

Rebuild the snapshot with:

```bash
python3 scripts/build_visual_snapshot.py
```

The snapshot is a deterministic product-state artifact, not a substitute for browser acceptance testing.

## Continuous verification

`.github/workflows/ci.yml` rebuilds generated fixtures/snapshots and runs the Python domain/API/service/repository tests, Node browser-contract tests, repository/readiness contracts, and Python compilation on every push and pull request.

## Prototype API workflow

### 1. Authorize the safe demo checkout

```bash
curl -X POST http://127.0.0.1:8000/payments/checkout \
  -H 'content-type: application/json' \
  -d '{"email":"owner@example.com"}'
```

The response returns a `demo_pay_...` token, `$1.00` amount, `prototype_demo` mode, and `real_charge: false`.

### 2. Start the analysis

```bash
curl -X POST http://127.0.0.1:8000/analyses \
  -H 'content-type: application/json' \
  -d '{
    "business_activity":"Packaging manufacturing",
    "geography":"New York",
    "email":"owner@example.com",
    "payment_token":"demo_pay_REPLACE_WITH_TOKEN"
  }'
```

The API returns `202 Accepted` with an analysis ID and URLs for status/report retrieval.

### 3. Poll status

```text
GET /analyses/{analysis_id}/status
```

Prototype stages are explicit:

1. `QUEUED`
2. `DISCOVERING_COMPANIES`
3. `COLLECTING_EVIDENCE`
4. `NORMALIZING`
5. `SCORING`
6. `GENERATING_FINDINGS`
7. `RENDERING_RESULT`
8. `COMPLETED`

### 4. Retrieve report

```text
GET /analyses/{analysis_id}
```

## Tests

Run all backend/service/persistence/API tests:

```bash
PYTHONWARNINGS='error::ResourceWarning' python3 -m unittest discover -s apps/api/tests -v
```

Run browser contract tests:

```bash
node --test apps/web-preview/tests/test_ui_contract.mjs
```

Run repository/readiness contract tests:

```bash
python3 -m unittest tests.test_repository_contract -v
```

Run compilation check:

```bash
python3 -m compileall -q apps scripts tests
```

## Architecture source of truth

Approved design:

- `docs/superpowers/specs/2026-08-18-analytica-v1-design.md`

Implementation plan:

- `docs/superpowers/plans/2026-08-19-analytica-v1-mvp.md`

Current technical state:

- `docs/status/2026-08-19-rd-readiness.md`

## Production target

The prototype intentionally uses SQLite and a lightweight in-process worker because the goal is a reviewable, executable vertical slice. The approved paid-production target remains:

- Next.js / TypeScript product frontend;
- FastAPI analytical service;
- PostgreSQL persistence;
- durable asynchronous queue/workers;
- lawful public/licensed company-data providers;
- entity resolution;
- authenticated tenants;
- real payment provider + signed/idempotent webhooks;
- email completion delivery;
- provider/cost telemetry;
- observability, backups, security hardening and staged deployment.

## Paid-launch rule

Do not represent this branch as a paid-production release. It is a **workable MVP prototype** that proves the product surface and engineering boundaries. Paid launch becomes credible after the real-data, security, payment, delivery and production-operations gates are verified.
<!-- trigger Cloudflare staging deployment -->
