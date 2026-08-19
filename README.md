# Analytica

Analytica is an evidence-driven historical business-intelligence and decision-support product. The current branch implements the first U.S.-first R&D vertical slice using a fully synthetic `Packaging manufacturing / New York` fixture.

## Current state

This repository is **not yet a paid-production release**. The current vertical slice validates:

- typed analysis/evidence contracts;
- explicit analysis state;
- deterministic trajectories and scoring semantics;
- synthetic peer cohort segmentation;
- radial historical-performance visualization;
- selectable evidence drilldown;
- confidence taxonomy;
- prioritized Top 10 business lessons;
- a browser-visible integrated preview served by the FastAPI process.

The demonstrator does **not** make claims about real companies. All company names, events, scores, findings, and evidence in the fixture are synthetic.

## Run the preview

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 scripts/run_preview.py
```

Then open:

```text
http://127.0.0.1:8000/
```

Health endpoint:

```text
GET http://127.0.0.1:8000/health
```

Canonical analysis endpoint:

```text
GET http://127.0.0.1:8000/analyses/demo_packaging_ny_v1
```

Create canonical R&D analysis:

```bash
curl -X POST http://127.0.0.1:8000/analyses \
  -H 'content-type: application/json' \
  -d '{"business_activity":"Packaging manufacturing","geography":"New York"}'
```

## Tests

Backend/domain:

```bash
python3 -m unittest discover -s apps/api/tests -v
```

Browser contract:

```bash
node --test apps/web-preview/tests/test_ui_contract.mjs
```

Repository/readiness contract:

```bash
python3 -m unittest tests.test_repository_contract -v
```

## Architecture

The approved architecture is defined in:

- `docs/superpowers/specs/2026-08-18-analytica-v1-design.md`

The active implementation plan is:

- `docs/superpowers/plans/2026-08-19-analytica-v1-mvp.md`

The production target remains a modular architecture with a Next.js/TypeScript product frontend, FastAPI analytical service, PostgreSQL persistence, asynchronous workers, provider adapters, authentication, payments, email delivery, and observability. The dependency-free browser client in this branch exists so product R&D can be reviewed visually immediately while those production integrations are built.

## Paid-launch blockers

Before charging customers, the project still requires at minimum:

1. lawful real-company data providers and entity resolution;
2. PostgreSQL persistence and migrations;
3. asynchronous analysis jobs/queue;
4. authentication and tenant isolation;
5. payment checkout plus verified/idempotent webhooks;
6. email/result delivery;
7. cost telemetry and pricing validation;
8. production observability, rate limiting, security hardening, backups, and deployment;
9. evidence validation against real source material;
10. visual acceptance and user testing of the radial interface.

See `docs/status/2026-08-19-rd-readiness.md` for the exact readiness matrix.
