# Production runtime audit

**Audit date:** 2026-09-06
**Scope:** Local repository, runtime dependencies, CI configuration, and deployment artifacts. No cloud environment was changed.

## Runtime classification

| Dependency / concern | Classification | Evidence |
|---|---|---|
| FastAPI application and `/health` | PRODUCTION_CONDITIONAL | Application starts locally, but health represents process availability only. |
| `/readiness` | LOCAL_ONLY | It reports the old prototype state and does not independently check database, worker, Stripe, Predicta, or Quantis availability. |
| Static browser preview | LOCAL_ONLY | Root mount serves the fixture preview and browser has a static fixture fallback. |
| SQLite persistence | LOCAL_ONLY | All analysis, evidence, review, cost, research, and payment repositories use `sqlite3`; default path is `.data/analytica.db`. |
| Tenant/order/entitlement records | PRODUCTION_CONDITIONAL | Server-side controls and local tests exist, but no production identity issuer, PostgreSQL constraints/RLS, migration, or deployment configuration exists. |
| Stripe SDK boundary | PRODUCTION_CONDITIONAL | Only `sk_test_` keys are accepted; no test-account canary or public HTTPS webhook has been run. |
| In-process analysis thread | BLOCKER | Daemon thread is lost on restart; no durable queue, lease/reclaim, retry scheduler, or dead-letter handling exists. |
| Production database | BLOCKER | No PostgreSQL driver, adapter, migration tool, connection configuration, or managed database target exists. |
| Backup and restore | BLOCKER | `pg_dump`/`pg_restore` are not available and no backup/restore automation or rehearsal exists. |
| Identity provider | BLOCKER | Signed development principals exist, but no OIDC/passwordless identity issuer, session lifecycle, or managed key source exists. |
| Managed secrets | BLOCKER | Environment-variable reads exist; no managed secret-store integration, rotation procedure, or production startup inventory is present. |
| Observability | BLOCKER | There is no structured logging/metrics/tracing implementation, alerting target, or operational dashboard. |
| Rate limiting / WAF | BLOCKER | No server-side rate limiter, gateway configuration, request budget, or WAF configuration is committed. |
| Deployment configuration | BLOCKER | No Dockerfile, Compose file, Helm chart, Terraform, deployment manifest, or hosting configuration is committed. |
| CI verification | PRODUCTION_CONDITIONAL | GitHub Actions runs tests and compilation, but does not run dependency audit, secret scan, migration dry run, deployment test, or backup restore. |
| Predicta live research | BLOCKER | Strict client exists, but prior canary was unauthenticated and no successful live packet is recorded. |
| Quantis | BLOCKER | Deterministic demonstrator exists; canonical parity is explicitly unresolved. |

## Local-machine capability audit

| Tool | State |
|---|---|
| Docker CLI | Available locally; no repository image/Compose configuration uses it. |
| PostgreSQL client / backup tools | Not installed (`psql`, `pg_dump`, `pg_restore` unavailable). |
| Redis / durable queue runtime | Not installed or configured. |
| Alembic migrations | Not installed or configured. |
| Stripe CLI | Not installed; no Stripe test-account credentials supplied. |

## Startup and filesystem assumptions

- `ANALYTICA_DB_PATH` defaults to a local relative `.data/analytica.db` file. This cannot be the paid-beta persistence strategy in ephemeral hosting.
- The application mounts a local `apps/web-preview` directory at `/`; deployment must package this asset tree intentionally.
- The production environment currently fails closed only for missing `ANALYTICA_ACCESS_TOKEN_SECRET`. Stripe and Predicta configuration remain unavailable rather than fully production-validated.
- Existing developer demo APIs and fixture browser fallback remain present. Customer-paid analysis correctly returns `LIVE_RESEARCH_NOT_AVAILABLE`, but this is not an operable paid research path.

## Stale documentation identified

- `apps/api/app/readiness.py` still says authentication/tenancy and real payments are blocked, even though a local tenant/payment access boundary was added in commit `2369862`. It is correct that paid launch remains blocked, but the capability description is stale.
- `docs/security/CUSTOMER_ACCESS_AUDIT.md` describes the pre-boundary state by design; it is historical evidence, not the current route inventory.
- `CONTROLLED_BETA_GO_NO_GO.md` is an earlier audit. Its authenticated-access/payment findings require re-evaluation after commit `2369862`, while its live research, canonical Quantis, durable worker, backup, observability, deployment, and provider-rights blockers remain open.

## Required external inputs before a production-like test deployment

1. Approved hosting platform/project and target subdomain.
2. Managed PostgreSQL endpoint and credentials, plus selected migration policy.
3. Identity provider choice and tenant/reviewer role model.
4. Managed secret-store access for access-token, Stripe, Predicta, database, and email secrets.
5. Stripe test secret key, webhook signing secret, test Price ID, and approved test account.
6. Public HTTPS endpoint/domain authority for the Stripe webhook.
7. Predicta API credential/contract confirmation and canonical Quantis service/package decision.

## Audit conclusion

The repository is **not deployable as a controlled-beta service today**. A demo can be hosted after a deployment target is selected, but a production-like payment/research environment cannot be honestly created or canaried without the external inputs above.
