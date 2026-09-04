# Analytica owner-demo cut — 2026-09-04

## Demonstrated end-to-end architecture

`Predicta search.v1 → Analytica EvidencePort → EvidencePacket v1 → financial-truth firewall → Quantis-compatible deterministic port → Decision Workspace → readiness command center`

## Real and tested in this branch

- `analytica.evidence.v1` immutable Pydantic contract.
- Predicta anti-corruption adapter with deterministic SHA-256 source, passage, and packet lineage.
- Preservation of `SUPPORTED`, `PARTIALLY_SUPPORTED`, `CONTESTED`, `SINGLE_SOURCE`, `STALE`, `INFERRED`, and `UNSUPPORTED` claim states.
- Explicit contradiction records and graph-link validation.
- Proposed-assumption boundary requiring named human acceptance before canonical financial input creation.
- Deterministic Quantis-compatible baseline, downside/base/upside, break-even, payback, sensitivity, and reconciliation calculations.
- Browser-visible Decision Brief, Evidence Quality, Scenario Comparison, Sensitivity, Assumption Register, and Owner Technical Command Center.
- Cream/forest editorial-finance visual system restored over the MVP layout.

## Still fixture or blocked

- Current company histories and report evidence are synthetic.
- The financial port is a compatible demonstrator, not a deployed connection to the separate Quantis repository.
- Predicta production service is not deployed or authenticated from Analytica.
- Entity resolution, durable EvidencePacket persistence, human QA console, authentication/tenancy, real payment webhooks, and production deployment remain incomplete.
- FastAPI endpoint tests were not executed locally because FastAPI is absent from the bundled Python runtime; the domain, service, repository, evidence, financial, UI, and compile gates passed.

## Fresh verification

- Python focused tests: 20 passed.
- Repository contract tests: 6 passed.
- Browser contract tests: 7 passed.
- Python compilation: passed.
- Headless Edge visual capture: passed.

## Next production gate

Session 03 should add entity resolution and persist EvidencePacket/assumption lineage. Session 04 should implement graph-semantic repositories. The real Quantis adapter must be validated against the canonical Quantis kernel before any customer-facing financial result is labeled integrated.

