# Analytica R&D Readiness — 2026-08-19

## Executive state

Analytica has moved from architecture-only into a working vertical-slice implementation. The current branch is suitable for product/R&D review and technical validation, but it is **not yet ready to accept paid production traffic**.

## Readiness matrix

| Area | State | Evidence / comment |
|---|---|---|
| Product definition | Ready | Approved architecture/spec committed |
| Historical-analysis domain | Working | Typed Pydantic contracts and deterministic fixture |
| Confidence taxonomy | Working | Verified observation / correlation / evidence-supported explanation / analytical inference |
| API contract | Working | Health, analysis creation, report retrieval, status endpoints |
| Radial visualization | Implemented | Browser client renders synthetic trajectories and selectable points |
| Evidence drilldown | Implemented | Selected year exposes supporting synthetic evidence or explicitly says evidence is absent |
| Top lessons | Implemented | Ten prioritized synthetic lessons with confidence/evidence references |
| Visual preview | Code-ready; runtime acceptance pending | Browser UI is committed; local Chromium screenshot capture was blocked by the execution container during this session and must be re-run before visual sign-off |
| Real-company discovery | Not implemented | Fixture-backed by design for first vertical slice |
| Entity resolution | Not implemented | Required before real cohort analysis |
| Real evidence acquisition | Not implemented | Must use lawful public/licensed/authorized providers |
| PostgreSQL persistence | Not implemented | Current R&D API uses in-memory report repository |
| Async queue/workers | Not implemented | Required for multi-minute real analyses |
| Authentication / tenancy | Not implemented | Required before user-private reports |
| Payments | Not implemented | $1 pricing is a business hypothesis, not a launch-ready checkout |
| Email delivery | Not implemented | Required for asynchronous completion flow |
| Cost telemetry | Not implemented | Mandatory before validating $1 unit economics |
| Observability / security hardening | Not implemented | Required before public paid traffic |
| Predictive forecasting | Deferred | Historical intelligence must be validated first |

## Verified engineering progress

During the initial implementation pass:

- five domain/fixture tests passed;
- five API contract tests passed;
- six browser semantic/UI contract tests passed before the local screenshot runtime failure;
- the implementation remains explicitly labeled as synthetic R&D data;
- the public API and UI do not claim real-company accuracy or future certainty.

## Canonical demonstrator

**Business:** Packaging manufacturing  
**Geography:** New York  
**Market scope:** United States-first  
**Fixture:** five synthetic peer companies  
**Historical depth:** up to ten annual points  
**Primary UI:** Radial Business Trajectory Map

The production cohort target remains up to approximately 100 genuinely comparable companies where evidence quality permits.

## What the current R&D slice proves

The current code proves that Analytica can represent the intended product contract end-to-end:

`business + geography -> cohort -> trajectory -> event evidence -> finding -> actionable lesson -> radial visualization`

It also proves that the visualization can distinguish strong, stable, caution, and distress periods without presenting a literal clock or a mathematically unsupported sine wave.

## What it does not prove yet

It does not yet prove:

- real-world data coverage;
- real-company entity matching accuracy;
- causal accuracy on real events;
- payment economics;
- completion time for a 100-company real analysis;
- security/tenant isolation under production load;
- worldwide coverage;
- predictive forecasting accuracy.

## Fastest credible path to paid launch

1. Complete visual acceptance of this vertical slice on desktop/mobile.
2. Connect one high-quality U.S. company-discovery/evidence path for one initial industry family.
3. Add PostgreSQL persistence and asynchronous jobs.
4. Add authenticated accounts/tenant ownership.
5. Add payment abstraction and verified checkout/webhook flow.
6. Add email completion delivery.
7. Add evidence provenance and source-quality telemetry for real sources.
8. Run closed beta analyses and measure cost per analysis.
9. Set commercial pricing from measured unit economics instead of assuming $1 is profitable.
10. Launch paid U.S. beta only after the security, data-quality, and observability gates are green.

## Go / no-go statement

**GO for continued R&D and MVP engineering.**  
**NO-GO for paid public production today.**

The codebase now has a concrete product surface and analytical contract. The remaining work is primarily real-data integration, persistence/jobs, commercial workflow, hardening, and visual/user acceptance—not redefining the product from scratch.
