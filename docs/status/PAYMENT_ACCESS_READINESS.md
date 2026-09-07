# Payment and customer-access readiness

**Session:** Controlled-beta customer-access and Stripe test-mode boundary
**Date:** 2026-09-06
**Live Stripe charges:** Disabled by design

## VERIFIED_WORKING

- SQLite-backed domain records exist for customer, tenant, membership, case ownership, order, payment, payment event, entitlement, report release, and safe commerce audit events.
- Signed bearer principals are required for new tenant-scoped customer routes. Cross-tenant case reads and checkout attempts return `404`; reviewer and internal FinOps routes require a reviewer bearer principal.
- Customer report access requires matching tenant ownership, an active entitlement, and `RELEASED` status. An expiring HMAC-signed report link is bound to report ID, tenant, and a revocable token version.
- The server, not the browser, maps the sole `CONCIERGE_CASE` product code to the approved Stripe price ID. Additional client fields such as amount and price ID are rejected.
- A verified webhook is the only route that sets payment `PAID` and activates entitlement. The browser return path has no payment authority.
- Payment events are deduplicated by provider event ID. Duplicate success/refund events do not duplicate payment transition or revocation. Unknown orders are retained as `UNKNOWN_ORDER` without money attachment.
- Verified refund/dispute transitions revoke entitlement, revoke released report access, and increment the signed-link token version.
- Customer-paid cases return `LIVE_RESEARCH_NOT_AVAILABLE` rather than falling back to a synthetic analysis.
- The official Stripe Python SDK is declared in `requirements.txt` and installed locally (`stripe 15.6.1`). Test execution uses an injected no-network fake gateway; it cannot charge a card.

## IMPLEMENTED_UNVERIFIED

- `StripeTestGateway` uses the official SDK, accepts only `sk_test_` credentials, creates hosted Checkout sessions, and verifies raw-body `Stripe-Signature` webhooks.
- Production startup rejects a missing access-token secret when `ANALYTICA_ENVIRONMENT=production`.
- Stripe price is configured server-side through `STRIPE_CONCIERGE_PRICE_ID`; it is not supplied by the browser.

These paths have not been exercised against a real Stripe test account because no test-mode credentials, test Price ID, public HTTPS webhook address, or endpoint signing secret were provided.

## BLOCKED

- Real customer identity issuance/login (OIDC, passwordless email, or an approved identity provider) is not connected. The signed-principal service is an injected beta boundary for tests and development, not a customer authentication product.
- Stripe test-mode canary and deployed webhook signature verification require user-provided test credentials and a public HTTPS endpoint.
- Durable workers, production database, backups, restore rehearsal, and monitoring remain outside this session.
- Live Predicta customer research and canonical Quantis parity remain blocked; no paid case can receive synthetic evidence as a substitute.
- Human-QA delivery release still requires a real research-backed reviewer case that satisfies entity, evidence, financial-reconciliation, and reviewer gates.

## NOT_IMPLEMENTED

- Live Stripe mode, subscriptions, coupons, bundles, multiple public tiers, usage billing, card data handling, and browser-controlled price selection.
- Payout reconciliation, refund operations UI, dispute deadline operations, tax/invoice workflows, email identity flow, and external identity-provider integration.
- Production secrets manager, rate limiting, WAF/CSP, PostgreSQL/RLS, durable queue, backup automation, and restore runbook.

## Test evidence

- `apps.api.tests.test_payment_access`: 9 payment/access security tests passed.
- Full backend suite: 78 tests passed after this session (including evidence, financial firewall, provider, reviewer, service, persistence, and payment-access coverage).
- Repository contracts: 6 passed.
- Browser UI contracts: 10 passed.
- Python compile check passed.

## Stripe test-mode canary

**Not run.** No Stripe test secret, webhook signing secret, approved test Price ID, or externally reachable HTTPS webhook endpoint is present. This is correctly classified as `IMPLEMENTED_UNVERIFIED`, not working production integration.

## Remaining live-payment blockers

1. Managed secrets and externally authenticated customer/reviewer identity.
2. Public HTTPS deployment plus Stripe test webhook canary: successful payment, failure, refund, dispute, replay, and unknown-order evidence.
3. Durable production database/queue, backup/restore and operational alerting.
4. Live research and canonical Quantis parity before accepting any paid analytical case.
5. A repeated controlled-beta production gate with no unclosed BLOCKER/HIGH issue.
