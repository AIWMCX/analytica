# Secrets inventory

This document contains secret *names and ownership only*. Never place secret values in the repository, issue tracker, screenshots, or logs.

| Secret / credential | Current code use | Required production source | Current state |
|---|---|---|---|
| `ANALYTICA_ACCESS_TOKEN_SECRET` | Signs development customer/reviewer/report tokens | Managed secret store | Required only when `ANALYTICA_ENVIRONMENT=production`; no secret manager integration |
| Stripe test secret key | Creates hosted Checkout through official SDK | Managed secret store | Not supplied |
| Stripe webhook signing secret | Verifies raw webhook signature | Managed secret store | Not supplied |
| `STRIPE_CONCIERGE_PRICE_ID` | Server-side product-to-Price mapping; not secret | Versioned deployment configuration | Test placeholder only |
| `PREDICTA_API_KEY` | Optional bearer token for Predicta adapter | Managed secret store | Not supplied / live contract unverified |
| `PREDICTA_BASE_URL` | HTTPS Predicta service URL | Versioned deployment configuration | Not configured for a verified canary |
| PostgreSQL URL / password / TLS material | Not implemented | Managed secret store | No production database adapter |
| Email provider API key | Not implemented | Managed secret store | No email delivery integration |
| External identity-provider credentials | Not implemented | Managed secret store | No identity provider selected |

## Production startup policy

Production must fail closed if any mandatory secret for enabled capabilities is absent. A production process must never use the repository's development fallback signing secret, a placeholder Stripe price, or a fake Stripe gateway.

## Logging policy

Never log authorization headers, access/report tokens, webhook signatures, Stripe API keys, database URLs, raw payment payloads, or full Predicta credential-bearing URLs. Log only safe identifiers, event hashes, status codes, and correlation IDs.
