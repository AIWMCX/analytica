# Controlled Beta Launch Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn Analytica from a clearly labelled synthetic demonstration into a trustworthy waitlist and controlled-beta service, without accepting payment until a real, recoverable, evidence-backed delivery path is verified.

**Architecture:** Keep the public demonstration and waitlist at the CDN edge, but run the current FastAPI application on a container-capable service behind it. Replace SQLite and daemon threads with managed PostgreSQL and durable jobs; bind live Predicta evidence to the existing provenance pipeline, then require external identity, reviewer QA, and verified Stripe webhooks before delivery.

**Tech Stack:** Cloudflare edge/CDN for public assets; FastAPI; managed PostgreSQL; durable job backend selected with the host; OIDC/passwordless identity provider; Stripe Checkout; Predicta versioned HTTPS contract; existing EvidencePacket, reviewer, and payment-access modules.

**Spec:** `docs/superpowers/specs/2026-08-18-analytica-v1-design.md`, `docs/status/FIRST_PAID_CONCIERGE_GO_NO_GO.md`, and `docs/status/CONTROLLED_BETA_INFRA_READINESS.md`

## Global Constraints

- Preserve the cream/forest editorial design, radial identity, and explicit synthetic-data labels until live evidence is truly present.
- Never route paid analysis through `build_demo_report`, `demo-data.js`, or any fixture fallback.
- Predicta is evidence-only; it must never invoke Quantis or set canonical financial inputs.
- Only a reviewer-approved, tenant-scoped case with verified evidence and financial reconciliation may be released.
- Begin with one concierge product only; do not add subscriptions, tiers, coupons, usage billing, or bundles.
- Do not enable Stripe live payments until every controlled-beta gate is evidenced in deployment.
- Every state-changing change has focused tests, a clean commit, and an updated readiness record.

---

## Truth audit: what is complete, stale, and blocked

### Verified in the current checkout

- `feat/analytica-v1-mvp` is synchronized with `origin/feat/analytica-v1-mvp` at `a3f043d`; GitHub `main` is not yet merged.
- 78 backend tests, 6 repository contract tests, and 10 UI contract tests passed in the 2026-09-06 release audit.
- Evidence packet persistence/hash controls, reviewer workflow, local tenant/report gate, cost ledger, and Stripe **test-only** boundary exist.
- The paid-case endpoint fails closed with `LIVE_RESEARCH_NOT_AVAILABLE`; this is safer than fixture substitution, but it is not a sellable workflow.

### Active-session reconciliation

- The current Analytica task is the only active implementation context for the current branch.
- The pinned Predicta task is **not loaded** and its last recorded work inspected an older `.remote-pr1` checkout. It does not establish a live Predicta API or current Analytica integration.
- Treat the following untracked root-level documents as historical audit drafts until explicitly reconciled: `CONTROLLED_BETA_GO_NO_GO.md`, `CURRENT_READINESS_MATRIX.md`, `CURRENT_SYSTEM_MAP.md`, `DEPENDENCY_AND_DUPLICATION_RISKS.md`, `NEXT_IMPLEMENTATION_SLICE.md`, and `TOP_15_TECHNICAL_GAPS.md`.

### Highest-value blockers

1. The public Cloudflare experience has not been proven to load the current interactive JavaScript bundle; a static/non-clickable deployment cannot validate demand.
2. There is no selected operational host, deployment configuration, managed PostgreSQL, durable worker, identity provider, secret manager, monitoring, backup/restore, or rate limit.
3. No successful authenticated live Predicta packet has been persisted; current evidence is synthetic in the public preview.
4. Canonical Quantis source/parity is unresolved.
5. Stripe integration is test-only and has no deployed Checkout or webhook canary.

### Deliberately deferred

- More decorative dashboard widgets, extra providers, Neo4j, Graphify runtime use, multiple pricing tiers, and live Stripe charges.
- They do not create trustworthy customer value before the five blockers above are removed.

## Tomorrow’s decision agenda

Before code changes that create external commitments, the owner must select or supply:

1. A container-capable hosting project for FastAPI, PostgreSQL, and the durable worker.
2. A named identity provider and reviewer-role model.
3. The exact public domain split: `demo.analytica.aiwmc.org` for synthetic demo/waitlist; `analytica.aiwmc.org` for the operational app after release gates pass.
4. Predicta’s protected endpoint, authentication scheme, and service token distribution method.
5. Quantis’s single canonical kernel/service contract, or approval to remove Quantis-backed commercial claims from beta.

No DNS record is changed until the selected host supplies its exact target record.

## File map for the next implementation cycle

| File | Responsibility |
|---|---|
| `apps/web-preview/app.js` | Public demo interaction, synthetic disclosure, waitlist handoff; no payment authority. |
| `apps/web-preview/index.html` and CSS files | Preserve the editorial public/demo experience and add clear waitlist/accessibility states. |
| `apps/api/app/settings.py` (create) | Typed production configuration, mandatory secret/URL validation, environment mode. |
| `apps/api/app/main.py` | Compose runtime ports only; remove production reliance on demo payment and static root fallback. |
| `apps/api/app/persistence/` (create) | PostgreSQL transaction/repository adapters and migrations, preserving existing repository contracts. |
| `apps/api/app/jobs/` (create) | Durable analysis/research jobs, idempotency, retry/reclaim, and operator-visible status. |
| `apps/api/app/predicta_path.py` | Strict versioned live Predicta port; no fixture fallback. |
| `apps/api/app/payment_access.py` | Server-side Stripe price map, entitlement transitions, webhook idempotency, report revocation. |
| `apps/api/app/identity.py` (create) | External OIDC/passwordless principal verification and tenant/reviewer role mapping. |
| `apps/api/tests/` | Contract, negative-authorization, failure-recovery, and integration tests. |
| `.github/workflows/ci.yml` | Full regression, secret/dependency scan, migration dry run, deployment smoke, and no-fixture gate. |
| `docs/operations/` | Deployment runbook, restore record, incident/release checklist. |

## 30-day sequence

### Task 1: Diagnose and repair the public demo before adding features

**Files:**
- Modify: `apps/web-preview/index.html`
- Modify: `apps/web-preview/app.js`
- Modify: `apps/web-preview/tests/test_ui_contract.mjs`
- Create: `docs/operations/PUBLIC_DEMO_SMOKE_CHECK.md`

**Consumes:** Current synthetic `demo-data.js` and public Cloudflare deployment URL.

**Produces:** A browser-verifiable interactive synthetic demonstration and a waitlist path with no misleading payment or live-data implication.

- [ ] **Step 1: Record the deployed Worker/Page URL, commit SHA, HTTP response headers, and browser console output.**

  Expected evidence: the deployed `index.html`, `app.js`, CSS, and `demo-data.js` load with no JavaScript error; if they do not, capture the failed asset URL and status.

- [ ] **Step 2: Write a failing UI contract for the public call-to-action and synthetic boundary.**

  ```javascript
  test('public demonstrator exposes a waitlist CTA and never labels fixture evidence as live', () => {
    assert.match(html, /Join the concierge beta waitlist/);
    assert.match(js, /synthetic_fixture/);
    assert.doesNotMatch(js, /live provider-backed market report/);
  });
  ```

- [ ] **Step 3: Add the smallest public interaction repair.**

  The page must load assets with relative URLs, defer `app.js` until the DOM exists, show a visible error state if demo data is missing, and retain keyboard-operable evidence/lineage controls.

- [ ] **Step 4: Add a waitlist form with only company-safe intake fields.**

  Collect: business email, company URL/name, decision type, industry, geography, and consent. Do not collect card details, financial account data, or unbounded free-text evidence.

- [ ] **Step 5: Run the browser contract suite and a real browser smoke on the deployed demo.**

  Run: `node --test apps/web-preview/tests/test_ui_contract.mjs`

  Expected: existing 10 tests plus the new public-demo checks pass; browser evidence confirms the radial selection and “Why are you telling me this?” interaction work.

- [ ] **Step 6: Commit.**

  ```bash
  git add apps/web-preview docs/operations/PUBLIC_DEMO_SMOKE_CHECK.md
  git commit -m "feat: make public demo interactive and waitlist-ready"
  ```

### Task 2: Select and codify the operational deployment boundary

**Files:**
- Create: `apps/api/app/settings.py`
- Create: `.env.example`
- Create: `Dockerfile`
- Create: `docs/operations/DEPLOYMENT_DECISION_RECORD.md`
- Modify: `apps/api/app/main.py`
- Test: `apps/api/tests/test_settings.py`

**Consumes:** Owner-approved host, Postgres endpoint policy, identity provider, secret manager, and public callback base URL.

**Produces:** A fail-closed service image and one typed runtime configuration object. This task does not deploy until the external inputs exist.

- [ ] **Step 1: Write failing configuration tests.**

  ```python
  def test_production_requires_database_url_and_managed_secrets():
      with patch.dict(os.environ, {"ANALYTICA_ENVIRONMENT": "production"}, clear=True):
          with pytest.raises(RuntimeConfigurationError):
              RuntimeSettings.from_environment()

  def test_production_rejects_sqlite_database_url():
      with patch.dict(os.environ, production_environment_with(DATABASE_URL="sqlite:///tmp.db")):
          with pytest.raises(RuntimeConfigurationError, match="PostgreSQL"):
              RuntimeSettings.from_environment()
  ```

- [ ] **Step 2: Implement `RuntimeSettings`.**

  ```python
  @dataclass(frozen=True)
  class RuntimeSettings:
      environment: Literal["development", "staging", "production"]
      database_url: str
      public_base_url: str
      predicta_base_url: str | None
      stripe_mode: Literal["disabled", "test", "live"]
  ```

  In production, reject SQLite, `example.invalid`, missing secret references, and `stripe_mode="live"` unless the release gate is independently satisfied.

- [ ] **Step 3: Build the FastAPI container and run `/health` locally with development configuration.**

  Run: `docker build -t analytica-api:local .`

  Expected: image builds without copying `.data`, `.env`, or credentials.

- [ ] **Step 4: Write the deployment decision record.**

  Include owner, chosen host, region, managed services, DNS target supplied by host, rollback procedure, and the exact secret names—not values.

- [ ] **Step 5: Commit.**

  ```bash
  git add Dockerfile .env.example apps/api/app/settings.py apps/api/app/main.py apps/api/tests/test_settings.py docs/operations/DEPLOYMENT_DECISION_RECORD.md
  git commit -m "feat: add fail-closed production runtime configuration"
  ```

### Task 3: Replace local persistence and daemon execution with recoverable services

**Files:**
- Create: `apps/api/app/persistence/postgres.py`
- Create: `apps/api/app/jobs/contracts.py`
- Create: `apps/api/app/jobs/worker.py`
- Modify: `apps/api/app/service.py`
- Modify: `apps/api/app/repository.py`
- Modify: `apps/api/app/research_store.py`
- Test: `apps/api/tests/test_job_recovery.py`
- Test: `apps/api/tests/test_postgres_contract.py`

**Consumes:** `RuntimeSettings.database_url` and selected queue backend.

**Produces:** Persisted job states with idempotency, retry/reclaim, and a PostgreSQL-backed repository boundary. Existing SQLite may remain only as a test adapter.

- [ ] **Step 1: Write a failing restart-recovery test.**

  ```python
  def test_expired_running_job_is_reclaimed_once(worker, repository, clock):
      job = repository.enqueue(case_id="case_1", idempotency_key="analysis:case_1")
      repository.claim(job.id, worker_id="dead-worker", lease_until=clock.now() - timedelta(seconds=1))
      reclaimed = worker.reclaim_expired_jobs()
      assert [item.id for item in reclaimed] == [job.id]
      assert repository.get(job.id).attempt_count == 2
  ```

- [ ] **Step 2: Define job invariants.**

  ```python
  class JobStatus(StrEnum):
      QUEUED = "QUEUED"
      RUNNING = "RUNNING"
      SUCCEEDED = "SUCCEEDED"
      RETRYABLE_FAILURE = "RETRYABLE_FAILURE"
      FAILED = "FAILED"
  ```

  A job is claimed with a lease; only one active claim is valid; all completion writes are idempotent by job ID and case ID.

- [ ] **Step 3: Implement PostgreSQL migrations and repository adapters.**

  Migrate customer/tenant/case/order/payment/event/entitlement/report release, research runs, EvidencePackets, reviewer actions, and jobs in one transaction boundary where required. Enforce tenant/case keys and foreign keys rather than reproducing disconnected SQLite schemas.

- [ ] **Step 4: Implement the worker loop and dead-letter state.**

  Retry only documented transient provider errors; terminal validation/integrity failures become `FAILED` with sanitized operator diagnostics.

- [ ] **Step 5: Run Postgres integration, restart/reclaim, and full regression tests.**

  Expected: process restart loses no claimed work; no duplicate report, payment transition, or research packet is created.

- [ ] **Step 6: Commit.**

  ```bash
  git add apps/api/app/persistence apps/api/app/jobs apps/api/app/service.py apps/api/app/repository.py apps/api/app/research_store.py apps/api/tests
  git commit -m "feat: add durable postgres-backed analysis jobs"
  ```

### Task 4: Connect real Predicta evidence to a paid-case-safe workflow

**Files:**
- Modify: `apps/api/app/predicta_path.py`
- Modify: `apps/api/app/research_pipeline.py`
- Modify: `apps/api/app/research_store.py`
- Modify: `apps/api/app/evidence_repository.py`
- Create: `apps/api/app/research_orchestrator.py`
- Test: `apps/api/tests/test_predicta_paid_case.py`
- Create: `scripts/run_predicta_canary.py`

**Consumes:** Versioned Predicta endpoint, server-only credential, approved hostname, and the durable job system from Task 3.

**Produces:** A persisted live ResearchRun → EvidencePacket path with manifest, diagnostics, provenance hashes, and no finance promotion.

- [ ] **Step 1: Write failing tests for the live-only path.**

  ```python
  def test_paid_case_never_uses_fixture_when_predicta_is_unavailable(orchestrator):
      result = orchestrator.run(case_id="case_1", query="example company")
      assert result.status == "DEGRADED"
      assert result.fixture_fallback_used is False
      assert result.packet_ids == []

  def test_predicta_packet_preserves_version_diagnostics_and_hash(orchestrator):
      run = orchestrator.run(case_id="case_1", query="example company")
      assert run.provider_outcomes[0].contract_version == "predicta.search.v1"
      assert repository.verify_packet_hash(run.packet_ids[0]) is True
  ```

- [ ] **Step 2: Restrict Predicta egress.**

  Require HTTPS, a configured allowlisted hostname, no redirects, bounded response bytes, timeout, bounded retry, and explicit 429/5xx outcomes. Do not log bearer tokens, URLs with credentials, or full provider payloads.

- [ ] **Step 3: Normalize and persist the packet before any finding or finance operation.**

  ```python
  def run_live_research(case_id: str, query: str) -> ResearchRun:
      response = predicta.search(query)
      packet = normalize_predicta_response(response)
      evidence_repository.persist(packet)
      return research_store.complete(case_id, packet=packet, diagnostics=response.diagnostics)
  ```

- [ ] **Step 4: Run one permitted live canary and reopen the persisted evidence.**

  Record only sanitized run ID, provider status, packet hash, retrieval time, and contract version in a dated status report. A 401/403/timeout is a failed canary, not a successful integration.

- [ ] **Step 5: Commit.**

  ```bash
  git add apps/api/app/predicta_path.py apps/api/app/research_orchestrator.py apps/api/app/research_pipeline.py apps/api/app/research_store.py apps/api/app/evidence_repository.py apps/api/tests/test_predicta_paid_case.py scripts/run_predicta_canary.py
  git commit -m "feat: run live Predicta research through durable evidence pipeline"
  ```

### Task 5: Establish authentic finance boundaries before any Quantis claim

**Files:**
- Modify: `apps/api/app/financial.py`
- Create: `apps/api/app/financial_port.py`
- Create: `apps/api/tests/test_quantis_parity.py`
- Modify: `apps/web-preview/app.js`
- Modify: `docs/status/2026-09-05-quantis-canonicality-blocker.md`

**Consumes:** An owner-approved canonical Quantis package/service and golden input/output fixtures.

**Produces:** Direct Quantis-to-Analytica parity evidence, or a UI/product copy change that removes all Quantis-backed claims.

- [ ] **Step 1: Stop if the canonical Quantis kernel is not identified.**

  Do not select among duplicate formulas. Update the blocker report with repository, commit/version, entry point, owner approval, and missing inputs.

- [ ] **Step 2: Write parity fixtures before implementation.**

  ```python
  @pytest.mark.parametrize("fixture", load_canonical_fixtures())
  def test_analytica_financial_port_matches_quantis(fixture):
      assert AnalyticaFinancialPort().evaluate(fixture.input) == fixture.expected_output
  ```

  Cover revenue, margin, contribution, fixed cost, operating profit, break-even, payback, runway, downside/base/upside, and sensitivity.

- [ ] **Step 3: Enforce accepted-assumption input.**

  The FinancialPort accepts only an approved `AssumptionSet` with reviewer identity and lineage; Predicta records cannot call it.

- [ ] **Step 4: If parity cannot be proven, remove “Quantis-compatible” and “Quantis-backed” from the public/pilot product.**

- [ ] **Step 5: Commit.**

  ```bash
  git add apps/api/app/financial.py apps/api/app/financial_port.py apps/api/tests/test_quantis_parity.py apps/web-preview/app.js docs/status
  git commit -m "feat: verify canonical Quantis finance boundary"
  ```

### Task 6: Add external identity and production authorization tests

**Files:**
- Create: `apps/api/app/identity.py`
- Modify: `apps/api/app/main.py`
- Modify: `apps/api/app/payment_access.py`
- Test: `apps/api/tests/test_identity_authorization.py`

**Consumes:** Named identity provider issuer, audience/client ID, role claim mapping, and managed verification keys.

**Produces:** Customers and reviewers are authenticated by an external issuer; every case/report/reviewer route uses a verified principal.

- [ ] **Step 1: Write cross-tenant negative tests.**

  ```python
  def test_customer_cannot_read_another_tenants_case(client, alice_token, bob_case):
      response = client.get(f"/customer/cases/{bob_case.id}", headers={"Authorization": f"Bearer {alice_token}"})
      assert response.status_code == 404

  def test_untrusted_dev_token_is_rejected_in_production(client):
      response = client.get("/customer/cases/case_1", headers={"Authorization": "Bearer development-token"})
      assert response.status_code == 401
  ```

- [ ] **Step 2: Verify issuer, audience, expiry, subject, and role claim.**

  ```python
  class IdentityPort(Protocol):
      def verify(self, bearer_token: str) -> Principal: ...
  ```

- [ ] **Step 3: Require a reviewer principal for every QA action and store immutable actor/time/action records.**

- [ ] **Step 4: Run production-mode authentication integration tests with test-issuer tokens.**

- [ ] **Step 5: Commit.**

  ```bash
  git add apps/api/app/identity.py apps/api/app/main.py apps/api/app/payment_access.py apps/api/tests/test_identity_authorization.py
  git commit -m "feat: verify external identity and tenant authorization"
  ```

### Task 7: Complete Stripe test-mode delivery rehearsal, then gate live payment

**Files:**
- Modify: `apps/api/app/payment_access.py`
- Modify: `apps/api/app/main.py`
- Create: `apps/api/tests/test_stripe_test_canary.py`
- Create: `docs/operations/STRIPE_TEST_REHEARSAL.md`
- Modify: `docs/status/FIRST_PAID_CONCIERGE_GO_NO_GO.md`

**Consumes:** Public HTTPS staging domain, Stripe test key, webhook secret, server-allowlisted test Price ID, and owner approval for test transactions.

**Produces:** Sanitized proof of hosted Checkout, signed webhook, replay, refund/dispute revocation, entitlement, reviewer release, and tenant-scoped access.

- [ ] **Step 1: Write tests that prove browser redirects grant nothing.**

  ```python
  def test_checkout_success_redirect_does_not_activate_entitlement(client, order):
      response = client.get("/payment/success", params={"session_id": "untrusted"})
      assert response.status_code in {404, 204}
      assert repository.has_active_entitlement(order.tenant_id, order.case_id) is False
  ```

- [ ] **Step 2: Configure one test-only product code.**

  `CONCIERGE_CASE` maps server-side to one approved Price ID. Reject browser-supplied amount, currency, price ID, or metadata that changes entitlement scope.

- [ ] **Step 3: Run the staged Stripe test canary.**

  Exercise successful payment, duplicate event, unknown order, refund, dispute, and payment failure. Retain only sanitized order/event/payment/entitlement/case identifiers.

- [ ] **Step 4: Release one internal case only after entity resolution, hashes, accepted assumptions, reconciliation, and named QA approval.**

- [ ] **Step 5: Update go/no-go evidence; do not set live mode.**

- [ ] **Step 6: Commit.**

  ```bash
  git add apps/api/app/payment_access.py apps/api/app/main.py apps/api/tests/test_stripe_test_canary.py docs/operations/STRIPE_TEST_REHEARSAL.md docs/status/FIRST_PAID_CONCIERGE_GO_NO_GO.md
  git commit -m "test: rehearse Stripe controlled-beta delivery path"
  ```

### Task 8: Automate the release evidence, not autonomous product changes

**Files:**
- Modify: `.github/workflows/ci.yml`
- Create: `scripts/verify_release.py`
- Create: `docs/operations/RESTORE_REHEARSAL.md`
- Create: `docs/operations/RELEASE_CHECKLIST.md`
- Test: `tests/test_release_verification.py`

**Consumes:** Deployment staging environment and managed database backup tooling.

**Produces:** Repeatable evidence for tests, dependency/secret scans, migration, deployment smoke, restore rehearsal, and provider/payment readiness.

- [ ] **Step 1: Write a failing release-verification test.**

  ```python
  def test_release_manifest_fails_when_fixture_mode_is_enabled_for_paid_routes():
      report = verify_release(RuntimeManifest(paid_data_mode="synthetic_fixture"))
      assert "PAID_FIXTURE_MODE" in report.blockers
  ```

- [ ] **Step 2: Implement a machine-readable release report.**

  Include exact suite status, commit SHA, migration status, deployed URL, worker status, backup restore ID, provider canary state, Stripe state, and remaining blockers. Never hard-code PASS percentages into UI or docs.

- [ ] **Step 3: Add CI checks.**

  Run Python tests, UI contracts, compile, dependency audit, secret scan, migration dry-run, and fixture-leakage tests. Fail CI on any high-severity secret exposure or paid-fixture route.

- [ ] **Step 4: Execute and document a restore rehearsal.**

  Restore a timestamped backup to an isolated database, run integrity/tenant-count checks, then destroy only the explicitly named temporary rehearsal resource according to the host runbook.

- [ ] **Step 5: Commit.**

  ```bash
  git add .github/workflows/ci.yml scripts/verify_release.py tests/test_release_verification.py docs/operations
  git commit -m "ci: automate controlled-beta release evidence"
  ```

## Calendar and acceptance gates

| Window | Outcome required before proceeding |
|---|---|
| Day 1–3 | Interactive, truthful demo and waitlist; source branch reviewed; host/IdP/Predicta/Quantis decisions recorded. |
| Day 4–7 | Staging environment has Postgres, durable jobs, identity, secrets, logs, rate limiting, and backup restore evidence. |
| Day 8–10 | One real Predicta case persists provenance intact; Quantis parity is proven or commercial claim removed. |
| Day 11–15 | Stripe test-mode payment-to-QA-to-report rehearsal succeeds and security review has no payment/authorization/recoverability blocker. |
| Day 16–30 | Invite 10–50 waitlist users; enable one live concierge product only after the go/no-go report is `GO`. |

## Commercial experiment rules

- Promise one deliverable: a reviewer-approved historical company/peer decision brief, with evidence coverage and limitations.
- Treat $1–$5 as a willingness-to-pay experiment, not as evidence of sustainable pricing.
- Record provider/model/payment/worker/storage/QA costs per case and calculate contribution margin from measured values.
- Interview every customer after delivery: decision changed, evidence trusted, missing evidence, refund intent, repurchase intent, and referral intent.
- Stop accepting new paid orders automatically if any required provider, reviewer queue, financial reconciliation, or release gate is degraded.

## Plan self-review

- **Spec coverage:** covers public demo integrity, deployment, persistence, jobs, Predicta, Quantis, identity, Stripe, QA/release, recovery, CI, and waitlist learning.
- **Intentionally not covered:** multi-provider expansion beyond Predicta, Neo4j, Graphify, multi-tier billing, and visual redesign; none are prerequisites for the first credible customer outcome.
- **Placeholder scan:** no task treats missing external credentials, hosting, or kernel selection as implementation success; each is an explicit decision gate.
- **Type consistency:** `RuntimeSettings`, `IdentityPort`, `Principal`, durable `JobStatus`, `ResearchRun`, `EvidencePacket`, and `AssumptionSet` are introduced before later tasks depend on them.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-09-07-controlled-beta-launch-foundation.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — dispatch a fresh subagent per task, review between tasks, fast iteration.
2. **Inline Execution** — execute tasks in this session using `superpowers:executing-plans`, with checkpoints for review.
