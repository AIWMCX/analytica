# First Paid Concierge Go / No-Go

**Audit date:** 2026-09-06
**Auditor:** Controlled Beta Release Engineer / independent release audit
**Audited commit:** `3a9215c`
**Scope:** First real, one-time concierge payment. No subscription, tier, coupon, usage-billing, or bundle release was evaluated or enabled.

## Verdict

**NO-GO**

**LIVE_PAYMENTS_ENABLED = NO**

No live transaction was attempted. There is no evidence of a deployed production environment, managed live Stripe secret, public HTTPS webhook, or owner authorization for a real charge. Attempting a payment under those conditions would be unsafe and would not test the required production trust boundary.

## Gate results

| # | Required gate | Finding | Classification | Evidence |
|---:|---|---|---|---|
| 1 | External customer identity works | No external identity provider, login, session lifecycle, or managed issuer is configured. The application uses locally signed development principals. | BLOCKER | `main.py` constructs `AccessTokenService`; runtime audit confirms no IdP. |
| 2 | Cross-tenant isolation passes | Local ownership checks exist, but no deployed identity + durable database test can prove production isolation. | BLOCKER | `owned_case()` conceals unowned cases; only TestClient evidence exists. |
| 3 | Customers access only owned cases | Local route checks are present; not production verified. | BLOCKER | `customer_can_access_case()` is exercised locally only. |
| 4 | Live Stripe credentials in managed secrets | No secret manager, live credential evidence, or deployment configuration was supplied. The code rejects non-test keys. | BLOCKER | `StripeTestGateway` accepts only `sk_test_`. |
| 5 | Browser cannot select amount or Price ID | The commerce route takes a product code and server-side map; browser amount/Price ID is not accepted by that route. | LOW | Local implementation and payment-access tests. |
| 6 | Server Checkout uses allowlisted live Price ID | Only a test-only gateway exists; the default price is a test placeholder and no live Price ID is configured. | BLOCKER | `STRIPE_CONCIERGE_PRICE_ID` defaults to `price_test_concierge_case`. |
| 7 | Public HTTPS webhook exists | No deployment target, domain, or webhook endpoint evidence exists. | BLOCKER | No deployment manifest or public URL supplied. |
| 8 | Stripe signature verification works | Raw-body signature verification is implemented with Stripe SDK but has not been run against Stripe. | HIGH | `StripeTestGateway.verify_webhook()`; no live-test canary. |
| 9 | Webhook replay is idempotent | Local repository deduplicates provider event IDs; no concurrent/durable production exercise. | HIGH | `record_event_once()` and local tests. |
| 10 | Payment activates entitlement exactly once | Local code creates one entitlement per order; no production database or live event proof. | HIGH | Unique order relation in SQLite implementation. |
| 11 | Refund/dispute revokes entitlement | Local handlers exist; no Stripe test event proof. | HIGH | `charge.refunded` and `charge.dispute.created` handlers. |
| 12 | Payment redirect grants nothing | The payment state is changed only in webhook handling, not in redirect handling. | LOW | No success redirect route grants entitlement. |
| 13 | Durable database verified | Application runtime repositories use SQLite. No PostgreSQL adapter, migration, or managed database evidence exists. | BLOCKER | `sqlite3` imports throughout persistence modules. |
| 14 | Durable workers verified | Research/analysis uses a daemon `threading.Thread`; restart can lose active work. | BLOCKER | `AnalysisService` starts daemon threads. |
| 15 | Backup and successful restore rehearsal | Neither system nor rehearsal evidence exists. | BLOCKER | No backup/restore configuration; Postgres tools unavailable. |
| 16 | Monitoring and alerts exist | No metrics, alert routing, structured production logging, or dashboard configuration found. | BLOCKER | No observability deployment/configuration artifacts. |
| 17 | Live Predicta research succeeds for product | Strict client exists, but no successful authenticated canary and durable customer EvidencePacket exist. | BLOCKER | Prior recorded canary is 401; paid path returns `LIVE_RESEARCH_NOT_AVAILABLE`. |
| 18 | Canonical Quantis parity or no promise | Canonical Quantis kernel has not been identified; the local port is explicitly a compatible demonstrator. | BLOCKER | `quantis-compatible.demo.v1`; canonicality blocker remains open. |
| 19 | Synthetic evidence cannot enter paid flow | Paid-case analysis fails closed instead of substituting the fixture; fixture storage rejects fallback. Legacy public demo remains synthetic by design. | LOW | `LIVE_RESEARCH_NOT_AVAILABLE`; `research_store.py` rejects fixture fallback. |
| 20 | Human QA mandatory | Reviewer delivery gate is implemented and locally tested. | HIGH | `ReviewerWorkflow` + payment release gate; not production verified. |
| 21 | No report before QA approval | Release checks QA blockers before report release locally. | HIGH | `can_release_report()` is invoked before `mark_report_released()`. |
| 22 | Post-release tenant-scoped authorization | Local customer and signed-link checks are tenant-scoped; external identity and durable database are absent. | HIGH | Customer route ownership + token-version revocation logic. |
| 23 | Production-like payment-to-report case | Not run and not runnable: no public deployment, live Stripe configuration, durable platform, live research, or canonical finance evidence. | BLOCKER | No sanitized order/event/payment/entitlement/case evidence exists. |

## Final security review

| Finding | Classification | Release impact / mitigation required |
|---|---|---|
| Development-signed principals are not external authentication | BLOCKER | Integrate a named production IdP, validate issuer/audience/expiry, and run cross-tenant negative tests in deployment. |
| SQLite and daemon jobs can lose payment/case/release state on restart | BLOCKER | Use managed PostgreSQL plus durable queue/workers, idempotent jobs, reclaim/retry, and restart proof. |
| Stripe boundary cannot use live keys and has no public webhook proof | BLOCKER | Implement a separate live-mode gateway with allowlisted live Price ID, managed secrets, HTTPS webhook, signature/replay/refund/dispute canaries. |
| Paid flow intentionally cannot run live research | BLOCKER | Complete Predicta live contract/canary and provider rights before accepting a research order. |
| Quantis parity is unresolved | BLOCKER | Select an approved canonical kernel and show direct-to-port parity, or remove any Quantis-backed promise from the paid product. |
| No backup/restore, monitoring, alerting, or rate limit evidence | BLOCKER | Establish operating controls and successful restore/recovery exercises. |
| Dependency advisory scan could not contact PyPI because local TLS validation failed | MEDIUM | Repair trusted CA/proxy configuration and require a passing scan in CI. `pip check` passed. |
| Legacy public demo and prototype checkout remain mounted | MEDIUM | Isolate them from production routing or remove them before exposing a paid customer domain. |
| Strict Predicta client does not yet establish an approved-host/DNS-rebinding policy | MEDIUM | Restrict service hostname and egress before live provider expansion. |

## Verification performed

- `python -m unittest discover -s apps/api/tests -q`: **78 passed**.
- `python -m unittest tests.test_repository_contract -q`: **6 passed**.
- `node --test apps/web-preview/tests/test_ui_contract.mjs`: **10 passed**.
- `python -m compileall -q apps scripts tests`: **passed**.
- `pip check`: **passed**.
- `pip-audit --format json --desc`: **not completed**; advisory lookup failed TLS certificate validation, including through the approved network path.
- Deployment, live Stripe, live webhook, backup restore, durable-worker restart, live Predicta, and Quantis-parity canaries: **not run** because the corresponding production systems/credentials/evidence are absent.

## Conditions to re-open this gate

1. Provide a production-like HTTPS deployment with named IdP, managed secret store, managed PostgreSQL, durable queue, monitoring, rate limiting, and tested backup restore.
2. Supply owner-authorized Stripe live configuration: allowlisted single Price ID, managed live key, webhook secret, public webhook, and minimal-value transaction authorization.
3. Run and retain sanitized evidence for Checkout, signed webhook, replay, refund/dispute, entitlement, mandatory human QA, release, cross-tenant denial, and post-release report access.
4. Prove the live Predicta packet path and canonical Quantis parity, or explicitly remove Quantis claims from the first paid product.

## Required release state

**NO-GO**

**LIVE_PAYMENTS_ENABLED = NO**
