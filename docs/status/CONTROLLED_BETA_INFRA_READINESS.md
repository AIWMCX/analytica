# Controlled-beta infrastructure readiness

**Audit date:** 2026-09-06
**Deployment URL:** None
**Database mode:** Local SQLite only
**Worker mode:** In-process daemon thread only
**Stripe mode:** Test-mode adapter implemented; no account canary
**Final verdict:** **NO_GO**

## VERIFIED_WORKING

- Local FastAPI prototype, fixture workspace, evidence integrity tests, financial-firewall tests, reviewer workflow tests, and payment-access tests.
- Tenant/case, order/payment/event, entitlement, and signed report-link local controls introduced in `2369862`.
- Payment and entitlement state remain separate from QA/release state; paid customer analysis fails explicitly with `LIVE_RESEARCH_NOT_AVAILABLE` instead of using synthetic research.
- CI executes backend, UI-contract, repository-contract, and compilation checks.

## IMPLEMENTED_UNVERIFIED

- Stripe official-SDK test gateway, hosted Checkout creation, and raw-body signature verification.
- Server-configured test Price ID and production missing-access-secret guard.
- Docker CLI is present on the local workstation, but no application image or deployment configuration exists.

## BLOCKERS

- No approved hosting target, deployment URL, managed PostgreSQL database, or migration path.
- No production identity provider or managed secrets integration.
- No durable job queue/worker model; active research can be lost on process restart.
- No backup/restore procedure or executed restore rehearsal.
- No public HTTPS webhook endpoint, Stripe test credentials, webhook signing secret, or Stripe test canary.
- No live verified Predicta EvidencePacket path, provider-rights evidence, or canonical Quantis parity.
- No observability/alerting/rate limiting/WAF/production security-header configuration.

## HIGH_RISK

- Current `/readiness` health model is stale and cannot establish database, worker, Stripe, Predicta, or Quantis availability.
- SQLite local filesystem data is unsuitable for ephemeral production hosting and has no production concurrency or recovery evidence.
- Existing public fixture preview is appropriate only when prominently labelled synthetic; it must not share a customer production path.
- CI lacks dependency vulnerability scan, secret scan, migration dry run, deployment smoke test, and restore test.

## MEDIUM_RISK

- No Stripe CLI or PostgreSQL client tooling is installed locally for canary/restore exercises.
- No email-delivery service or retry model exists.
- No RLS evidence exists; do not claim database-level tenant isolation.

## NOT_IMPLEMENTED

- PostgreSQL adapter/migrations, durable jobs, deployment manifests, managed secrets, external identity, HTTPS deployment, backup/restore, metrics/alerts, rate limits, test Stripe canary, email delivery, live research fulfillment, Quantis parity.

## TEST COUNTS

- Backend: 78 passing.
- Repository contracts: 6 passing.
- Browser UI contracts: 10 passing.
- Production database integration, worker recovery, deployment smoke, and Stripe live-test canaries: not runnable because the required infrastructure does not exist or was not supplied.

## BACKUP / RESTORE RESULT

**NOT RUN.** No production database or backup tooling is configured. A written backup plan without a restored isolated environment would not qualify as verification.

## PREDICTA STATUS

**IMPLEMENTED_UNVERIFIED.** Strict adapter and tests exist; no verified successful deployed Predicta response and durable customer packet exists.

## QUANTIS STATUS

**PARITY_UNVERIFIED.** Analytica contains a deterministic demonstrator, but canonical Quantis source and parity remain unresolved.

## Required next inputs

Hosting target, managed PostgreSQL, identity provider, secret manager, Stripe test credentials and test Price ID, public HTTPS webhook URL, and confirmed Predicta/Quantis integration contracts.
