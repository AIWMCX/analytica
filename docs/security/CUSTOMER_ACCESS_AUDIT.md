# Customer access audit

**Date:** 2026-09-05
**Scope:** Current `feat/analytica-v1-mvp` before the payment-access boundary implementation.

## Current model

There is no customer identity, tenant, membership, case-ownership, order, entitlement, report-release, or authenticated session model. `analysis_id` is the only effective report locator.

`analysis_jobs` persists `email` and `payment_token` alongside the case. The existing `DemoPaymentProvider` accepts an email and issues a `demo_pay_*` token. That token is a prototype UX mechanism only; it is neither a Stripe authorization nor a durable payment record.

## Exposed routes and access result

| Route | Current access control | Risk |
|---|---|---|
| `GET /analyses/{analysis_id}/status` | None | Anyone knowing an ID can view case progress and persisted email metadata. |
| `GET /analyses/{analysis_id}` | None | Anyone knowing an ID can retrieve a report. |
| `GET /analyses/{analysis_id}/evidence-graph` | None | Anyone knowing an ID can retrieve relationship/evidence-derived intelligence. |
| `GET /analyses/{analysis_id}/evidence-graph/recommendations/{id}/lineage` | None | Anyone knowing an ID can retrieve decision lineage. |
| `GET /review/cases/{case_id}` | None | Reviewer case, evidence packet identifiers, assumptions, financial results and audit trail are exposed. |
| `POST /review/cases/{case_id}/actions` | Caller supplies `reviewer_id` in body | Any caller can impersonate a reviewer and mutate QA state. |
| `GET/POST /internal/cases/{case_id}/cost-ledger...` | None | Operating-cost and human-QA data is exposed and mutable. |
| `POST /payments/checkout` | Email only | Creates a demo token; no customer identity or payment trust boundary. |
| `POST /analyses` | Email plus demo token | Creates a case without ownership/tenant record; response reveals direct report URL. |

`demo_packaging_ny_v1` is a synthetic public demonstrator. It must remain explicitly fixture-only and must never be a model for customer-case authorization.

## Security conclusion

This is a **BLOCKER** for paid beta. The required control is a server-enforced customer/tenant/case ownership boundary, a reviewer role boundary, internally recorded payment state, and report release authorization. Browser state, email request fields, demo tokens, and guessed IDs are not authorization.

## Implementation guardrails

- Preserve the existing evidence and FinancialPort firewalls. Payment and customer access must not mutate canonical financial inputs.
- Preserve public fixture access only for the explicitly labelled static demonstrator.
- Use hosted Stripe Checkout in test mode only; do not receive card data.
- Treat Stripe redirect success as untrusted. Only a verified, deduplicated webhook can set an internal payment to `PAID` and activate an entitlement.
- No customer report becomes accessible until internal payment, entitlement, QA, and release gates all pass.
