# Intelligence implementation audit — 2026-09-05

Session 04 remains incomplete. Earlier completion messages overstated the production controls and treated selected tests as full regression verification.

## Verified working in this increment

- Provider text hashes are recomputed and supplied mismatches are rejected.
- Duplicate provider identifiers cannot silently overwrite manifest outcomes.
- Provider exception messages cannot expose upstream credential-bearing URLs in the manifest; only exception class names are retained.
- Canonical finance conversion requires an accepted state, nonblank reviewer, timezone-aware review timestamp, transformation, claim references, matching status count, and no unsupported status.
- ResearchStore persists run outcomes and separate provider records in SQLite transactions. Reopening reconstructs and verifies text hashes. Existing run IDs cannot be overwritten.
- Six new regression tests reproduced the missing protections before implementation and pass afterward.

## Implemented but not live verified

- Existing Predicta, SEC and Census HTTP client wrappers.
- ResearchStore is callable infrastructure; providers and application routes are not wired to it yet.

## Prototype

- Entity resolver uses name/domain/state matching with an uncalibrated bonus. It is not a verified legal-identity service.
- Financial mathematics remains the existing compatible demonstrator.
- Existing EvidencePacket store checks a payload hash, but lacks complete provenance validation and database constraints.
- Accepted assumptions remain object-based approvals, not authenticated reviewer actions. The added checks do not establish reviewer identity or prevent authorized database modification.
- Owner browser UI remains the synthetic demonstration and was not changed by this increment.

## Blocked or unverified

- Full API regression discovery: FastAPI is absent from the bundled Python runtime. Discovery ran 38 passing tests and one module import error. Seven static browser-contract checks pass; these are not browser interaction tests.
- Prior HTTP 401 responses do not establish that the deployed Predicta search handler exists or identify its authentication scheme.
- No new live provider canary succeeded in this increment.

## Not implemented

- FRED/BLS/BEA adapters, complete provider retries/rate limits/cache and legal-use metadata.
- End-to-end live research to resolved entity to EvidencePacket to authenticated approval to real Quantis.
- Production readiness gate, tenant isolation, authenticated delivery and operational launch controls.

Next acceptance gate remains a real Predicta response plus official provider data with durable evidence and explicit provider outcomes. Do not interpret this audit or its tests as paid-launch approval.
