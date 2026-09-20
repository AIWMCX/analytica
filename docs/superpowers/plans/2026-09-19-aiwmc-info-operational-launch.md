# AIWMC.info Operational Launch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Launch Analytica at `https://aiwmc.info` as a truthful public waitlist/demo first, then promote it to a controlled operational beta only after the API, research, financial, identity, and payment gates are verified.

**Architecture:** Keep Cloudflare as the authoritative DNS, TLS, and edge layer for `aiwmc.info`. Host the existing FastAPI application as a containerized web service, move durable state from SQLite to managed PostgreSQL, and run research/report work in a durable queue-backed worker. The current Cloudflare Worker is a default `Hello world` response and must not receive the custom domain.

**Tech Stack:** Cloudflare DNS and edge protection; FastAPI/Uvicorn; managed PostgreSQL; Redis-compatible queue; container web service and background worker; GitHub Actions; Stripe test mode first.

**Spec:** `docs/superpowers/specs/2026-08-18-analytica-v1-design.md`, `docs/operations/PRODUCTION_RUNTIME_AUDIT.md`, and `docs/status/FIRST_PAID_CONCIERGE_GO_NO_GO.md`.

## Global Constraints

- `aiwmc.info` is Analytica's canonical production domain; Cloudflare is its authoritative DNS zone.
- Do not attach `aiwmc.info` to the Worker named `analyticajeltovbogdanworkersdev`: it currently returns only `Hello world`.
- Do not retry the failed Cloudflare Git build until a Worker configuration actually exists; the repository has no `wrangler.toml` or Worker entry point.
- Do not label synthetic fixture output, demo checkout, or the local Quantis demonstrator as live customer intelligence.
- Do not enable live Stripe payments until the controlled-beta go/no-go document is updated with production canary evidence.
- Never allow provider output to bypass EvidencePacket provenance, human assumption acceptance, or the FinancialPort boundary.
- Use `main` only as the release branch after the current feature pull request is reviewed and merged.

## Review Focus

- Root-domain DNS must not route visitors to the default Worker; a browser visit must show Analytica or a deliberate maintenance response.
- A web-service health check must fail when the application cannot reach its managed database, rather than returning a misleading green status.
- A restart during an analysis must leave the job reclaimable and must not silently substitute the synthetic fixture.
- Every public route must reject unauthorized customer cases and reviewer routes must require reviewer identity.
- A Stripe success redirect must not grant a report; only one verified webhook event may activate one entitlement.

---

## Owner Runbook: What to Do in Cloudflare Today

### Task 1: Preserve the domain and stop the incorrect Worker deployment

**Files:**
- Inspect: Cloudflare zone `aiwmc.info` and Worker `analyticajeltovbogdanworkersdev`

**Produces:** An active Cloudflare zone with no route to the default `Hello world` Worker.

- [ ] **Step 1: Open Cloudflare Dashboard → Websites → `aiwmc.info`**

Confirm the zone status is **Active**. This is already shown in the dashboard screenshot. Do not edit nameservers in IONOS while the Cloudflare zone remains Active.

- [ ] **Step 2: Open Workers & Pages → `analyticajeltovbogdanworkersdev` → Domains**

Confirm the **Custom Domains and Routes** table is empty. Leave it empty. Do not click **Add Domain** for `aiwmc.info`.

- [ ] **Step 3: Stop retrying the failed Git deployment**

The failed build executes:

```text
root directory: /
deploy command: npx wrangler deploy
```

This command cannot deploy the current repository because no `wrangler.toml`, Worker module, or Worker asset configuration exists. Retrying it only recreates the same failure.

- [ ] **Step 4: Keep the production address reserved**

Reserve these public addresses for the production topology:

```text
https://aiwmc.info            public waitlist / public product entry
https://app.aiwmc.info        authenticated Analytica customer app
https://api.aiwmc.info        FastAPI service
```

Do not manually create origin A records yet. The selected production host must provide the exact CNAME or IP target, and Cloudflare will proxy the record after the origin is healthy.

### Task 2: Review and merge the current release source

**Files:**
- Inspect: GitHub PR #1 and branch `feat/analytica-v1-mvp`
- Modify: GitHub branch protection for `main`

**Produces:** A traceable release branch from which hosting can automatically deploy.

- [ ] **Step 1: Open GitHub PR #1**

Verify the pull request compares `feat/analytica-v1-mvp` into `main`, has green CI, and contains the current FastAPI application and `apps/web-preview` assets.

- [ ] **Step 2: Merge only after the green checks are visible**

Use **Squash and merge** or **Create a merge commit** according to the repository's preferred history policy. Record the resulting `main` commit SHA in the release checklist.

- [ ] **Step 3: Protect `main`**

In GitHub → Settings → Branches, require the Analytica CI workflow before merge and disable force pushes. This prevents a domain deployment from tracking an unreviewed branch.

## Engineering Delivery: Make the Application Deployable

### Task 3: Add container and host configuration before creating any service

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`
- Create: `render.yaml`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/readiness.py`
- Create: `apps/api/tests/test_production_runtime.py`

**Interfaces:**
- Consumes: `PORT`, `ANALYTICA_ENVIRONMENT`, `DATABASE_URL`, `QUEUE_URL`, `ANALYTICA_ACCESS_TOKEN_SECRET`.
- Produces: `GET /health` and `GET /readiness` that distinguish process, database, queue, provider, and payment readiness.

- [ ] **Step 1: Write failing production-readiness tests**

```python
def test_production_startup_rejects_sqlite_and_missing_database_url():
    with patch.dict(os.environ, {"ANALYTICA_ENVIRONMENT": "production"}, clear=True):
        with pytest.raises(RuntimeError, match="DATABASE_URL"):
            create_app()

def test_health_returns_unhealthy_when_database_probe_fails(client):
    response = client.get("/health")
    assert response.status_code == 503
```

- [ ] **Step 2: Run the focused tests and confirm failure**

```text
python -m unittest apps.api.tests.test_production_runtime -v
```

Expected: failure because production still accepts the local SQLite default and `/health` does not probe dependencies.

- [ ] **Step 3: Implement fail-closed production settings**

Require a PostgreSQL `DATABASE_URL`, non-development signing secret, queue URL, allowed public origins, and explicit deployment environment whenever `ANALYTICA_ENVIRONMENT=production`. Preserve the present local SQLite path only when `ANALYTICA_ENVIRONMENT=development`.

- [ ] **Step 4: Add the container contract**

Use a Python image that installs `requirements.txt`, copies `apps`, `scripts`, and the static preview assets, and starts:

```text
uvicorn apps.api.app.main:app --host 0.0.0.0 --port $PORT
```

The container must expose `/health`, serve the packaged `apps/web-preview` directory, and contain no secret values.

- [ ] **Step 5: Add a host blueprint**

Define three resources in `render.yaml`: one FastAPI web service, one durable analysis worker, and one managed PostgreSQL database. Set the web-service `healthCheckPath` to `/health`; do not use a filesystem disk as the source of truth for customer cases.

- [ ] **Step 6: Run full local verification**

```text
python -m unittest discover -s apps/api/tests -v
node --test apps/web-preview/tests/test_ui_contract.mjs
python -m unittest tests.test_repository_contract -v
python -m compileall -q apps scripts tests
```

Expected: all tests pass, including the new production runtime tests.

- [ ] **Step 7: Commit**

```text
git add Dockerfile .dockerignore render.yaml apps/api/app/main.py apps/api/app/readiness.py apps/api/tests/test_production_runtime.py
git commit -m "feat: add production runtime deployment contract"
```

### Task 4: Replace local-only durability with PostgreSQL and a durable worker

**Files:**
- Create: `apps/api/app/database.py`
- Create: `apps/api/app/jobs.py`
- Create: `apps/api/migrations/001_initial.sql`
- Modify: `apps/api/app/repository.py`
- Modify: `apps/api/app/service.py`
- Create: `apps/api/tests/test_postgres_recovery.py`

**Interfaces:**
- Consumes: PostgreSQL `DATABASE_URL` and queue `QUEUE_URL`.
- Produces: `enqueue_analysis(case_id: str) -> str` and a worker that claims/retries jobs without fixture substitution.

- [ ] **Step 1: Write restart and no-fixture fallback tests**

```python
def test_claimed_job_is_reclaimed_after_worker_lease_expiry():
    job_id = queue.enqueue_analysis(case_id="case_123")
    queue.claim(job_id, worker_id="worker-a")
    clock.advance(seconds=301)
    assert queue.claim(job_id, worker_id="worker-b").worker_id == "worker-b"

def test_paid_case_failure_never_returns_demo_report():
    assert run_paid_case_with_provider_outage().code == "LIVE_RESEARCH_UNAVAILABLE"
```

- [ ] **Step 2: Run the focused tests and confirm failure**

```text
python -m unittest apps.api.tests.test_postgres_recovery -v
```

Expected: failure because the existing in-process daemon thread and SQLite repositories cannot reclaim work across a restart.

- [ ] **Step 3: Implement migrations and repository parity**

Migrate cases, orders, entitlements, evidence packets, reviewer actions, manifests, cost ledgers, and relationships into PostgreSQL tables with tenant-scoped foreign keys and unique event IDs.

- [ ] **Step 4: Implement worker lease/retry behavior**

Persist queued, claimed, retryable, terminal-failure, and completed states. A failed external provider must produce a persisted degraded manifest, never a synthetic customer report.

- [ ] **Step 5: Verify a restart canary against staging PostgreSQL**

Create a test case, queue it, restart the worker while it is claimed, then confirm it is reclaimed once and retains its audit history.

- [ ] **Step 6: Commit**

```text
git add apps/api/app apps/api/migrations apps/api/tests/test_postgres_recovery.py
git commit -m "feat: add durable postgres research jobs"
```

### Task 5: Deploy staging before connecting the public domain

**Files:**
- Modify: `render.yaml`
- Modify: `docs/operations/PRODUCTION_RUNTIME_AUDIT.md`
- Create: `docs/operations/STAGING_CANARY.md`

**Interfaces:**
- Consumes: merged `main`, managed secrets, staging database, staging queue.
- Produces: a staging API URL whose `/health` and `/readiness` can be independently probed.

- [ ] **Step 1: Create the staging services from the blueprint**

In the selected hosting provider, link the GitHub repository, select `main`, add the web service, worker, PostgreSQL, and queue resources defined in `render.yaml`.

- [ ] **Step 2: Configure staging secrets in the host secret store**

Set values only in the provider dashboard or secret manager:

```text
ANALYTICA_ENVIRONMENT=staging
DATABASE_URL=<managed PostgreSQL connection string>
QUEUE_URL=<managed queue connection string>
ANALYTICA_ACCESS_TOKEN_SECRET=<generated secret>
PREDICTA_BASE_URL=<approved versioned Predicta endpoint>
PREDICTA_API_KEY=<approved credential>
```

Leave `STRIPE_SECRET_KEY`, `STRIPE_WEBHOOK_SECRET`, and live payment flags absent during this task.

- [ ] **Step 3: Verify deployment health externally**

```text
GET https://<staging-api-host>/health
GET https://<staging-api-host>/readiness
```

Expected: `/health` reports database and queue connectivity; `/readiness` explicitly reports payments disabled and no claim of live financial parity.

- [ ] **Step 4: Run a live Predicta staging canary**

Create one approved internal case, save the provider manifest and EvidencePacket, confirm its hash verifies after persistence, and confirm no provider record becomes a canonical financial input without human acceptance.

- [ ] **Step 5: Commit the sanitized canary record**

```text
git add docs/operations/PRODUCTION_RUNTIME_AUDIT.md docs/operations/STAGING_CANARY.md render.yaml
git commit -m "docs: record staging deployment canary"
```

## Public Domain Release

### Task 6: Connect Cloudflare to the verified production service

**Files:**
- Modify: `docs/operations/STAGING_CANARY.md`
- Create: `docs/operations/AIWMC_INFO_CUTOVER.md`

**Interfaces:**
- Consumes: healthy staging/production web-service URL and origin DNS target supplied by the selected host.
- Produces: HTTPS service at `https://aiwmc.info`, `https://www.aiwmc.info`, and `https://api.aiwmc.info` with no traffic routed to the default Worker.

- [ ] **Step 1: Add custom domains at the application host first**

Add `api.aiwmc.info` to the FastAPI web service and obtain the host's exact DNS verification target. Add `aiwmc.info` and `www.aiwmc.info` to the public frontend service only after the frontend is a real build, not the current Hello World Worker.

- [ ] **Step 2: Update DNS in Cloudflare, not IONOS**

Cloudflare is already the active DNS authority. In Cloudflare DNS, create only the records prescribed by the selected host. Remove conflicting legacy A and AAAA records after recording their values. Do not add a CNAME at the apex unless the hosting provider explicitly supports apex CNAME flattening for that target.

- [ ] **Step 3: Use safe TLS mode**

Set Cloudflare SSL/TLS encryption mode to **Full (strict)** only after the origin certificate is valid. Do not use Flexible mode.

- [ ] **Step 4: Probe the cutover**

```text
GET https://aiwmc.info/
GET https://api.aiwmc.info/health
GET https://api.aiwmc.info/readiness
```

Expected: the root page identifies whether it is waitlist/demo or authenticated app; API health is 200 only when its database and queue dependencies are healthy; readiness remains truthful about disabled capabilities.

- [ ] **Step 5: Set a reversible rollback path**

Document the previous DNS record values and host deployment version. If health, login, or report retrieval fails after cutover, enable maintenance mode or restore the prior healthy host deployment before changing application code.

## Controlled Beta Gate

### Task 7: Add identity, research, financial, and payment gates in order

**Files:**
- Modify: `docs/status/FIRST_PAID_CONCIERGE_GO_NO_GO.md`
- Modify: `docs/status/CONTROLLED_BETA_INFRA_READINESS.md`
- Create: `docs/operations/CONTROLLED_BETA_CANARY.md`

**Interfaces:**
- Consumes: production identity issuer, successful Predicta EvidencePacket canary, canonical Quantis parity evidence, Stripe test secrets, and mandatory reviewer workflow.
- Produces: one evidence-backed `GO`, `CONDITIONAL_GO`, or `NO-GO` release decision.

- [ ] **Step 1: Enable external customer identity**

Replace development-issued principals with an identity provider. Prove a user from tenant A cannot read or mutate a tenant B case.

- [ ] **Step 2: Verify Predicta before Quantis**

Run a real company/industry research case through the versioned Predicta adapter. Persist the research manifest, provider diagnostics, sources, passages, claims, contradictions, and packet hashes.

- [ ] **Step 3: Establish canonical Quantis parity**

Identify the canonical Quantis kernel. Run parity fixtures for revenue, margin, contribution, fixed costs, operating profit, break-even, payback, runway, downside/base/upside, and sensitivity. Do not expose Quantis-backed claims until these fixtures pass.

- [ ] **Step 4: Run Stripe test mode end to end**

Use an allowlisted test Price ID. Verify signed webhook handling, duplicate-event idempotency, refund/dispute revocation, and that payment redirect alone grants no entitlement.

- [ ] **Step 5: Run the full concierge canary**

Execute:

```text
customer identity → owned case → live research → EvidencePacket verification
→ human-reviewed assumption → Quantis reconciliation → reviewer approval
→ Stripe test webhook → report release → tenant-scoped report access
```

Expected: one case completes without synthetic fixture substitution, and the audit log identifies every reviewer and payment event.

- [ ] **Step 6: Decide payments separately from domain launch**

Only when every prerequisite above is documented as verified may the release auditor enable one live, one-time concierge product. Do not add subscriptions, coupons, multiple tiers, or usage billing in the first paid release.

## Self-Review

- **Spec coverage:** The plan covers domain ownership, source release, deployment, durability, health checks, live research, Quantis, identity, payments, reviewer QA, and rollback. It intentionally excludes subscriptions and scale features.
- **Placeholder scan:** No task depends on an unspecified code path; the only external values are provider-issued credentials and DNS targets, which cannot be safely invented.
- **Type consistency:** Production settings, durable jobs, and health/readiness contracts are named explicitly for implementation tasks.
- **Review focus:** Every listed release-risk condition has an owning task and an explicit verification step.

