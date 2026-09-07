# Analytica MVP / R&D Readiness — 2026-08-19

## Executive state

Analytica is now a **workable MVP prototype**, not merely an architecture document or static mockup. The branch executes the core commercial/product workflow with deterministic synthetic evidence, durable local persistence, asynchronous analysis progress, a safe $1 demo-checkout contract, and an interactive visual report.

**GO for workable MVP prototype review and continued engineering.**  
**NO-GO for paid public production today.**

The distinction is intentional: the software flow is demonstrably operational, while real-company evidence, production tenancy/security, real payment processing, delivery infrastructure and production operations remain controlled launch gates.

## Current prototype completion signal

**Internal MVP prototype completion: 78%** relative to the defined vertical-slice target.

This number is an engineering/readiness indicator, not a claim that 78% of the final commercial platform is complete. It measures the prototype path only.

## Readiness matrix

| Area | State | Evidence / current condition |
|---|---|---|
| Product definition | Ready | Approved architecture and technical specification committed |
| Historical-analysis domain | Working | Typed report, cohort, evidence, trajectory, finding and lesson contracts |
| Evidence traceability | Working | Findings/lessons are validated against known evidence IDs |
| Confidence taxonomy | Working | Observation / correlation / evidence-supported explanation / inference |
| Deterministic scoring fixture | Working | Performance, modeled risk and state are deterministic |
| API contract | Working | Health, readiness, pricing, checkout, analysis, status and report routes |
| SQLite persistence | Prototype working | Analysis jobs and completed reports survive repository re-open |
| Async analysis state machine | Prototype working | Background execution with explicit stage/progress polling |
| $1 demo checkout | Prototype working | `$1.00`, `prototype_demo`, `real_charge=false`; no money processed |
| Radial visualization | Working | Ten-year radial peer trajectories with selectable evidence points |
| Evidence drilldown | Working | Score, risk, source title, publisher, confidence, fact and normalized signal |
| Top lessons | Working | Ten prioritized recommendations with confidence/evidence references |
| Technical readiness UI | Working | Product visibly separates working/prototype/blocked capabilities |
| Static visual fallback | Working | Generated fixture JS allows browser review without backend access |
| Real-company discovery | Not implemented | Lawful company/search provider adapters required |
| Entity resolution | Not implemented | Required before real peer cohort accuracy can be claimed |
| Real evidence acquisition | Not implemented | Public/licensed/authorized sources must replace synthetic fixture |
| PostgreSQL | Not implemented | SQLite is prototype-only; PostgreSQL remains production target |
| Durable queue/workers | Not implemented | In-process thread is prototype-only; production requires durable jobs |
| Authentication / tenancy | Not implemented | Required before private user reports |
| Real payment provider | Not implemented | Real checkout, credentials, signed and idempotent webhooks required |
| Email completion delivery | Not implemented | Required for multi-minute paid analyses |
| Cost telemetry | Not implemented | Required to validate whether $1 pricing is commercially viable |
| Production observability | Not implemented | Logs/metrics/traces/provider telemetry required |
| Security hardening | Not implemented | Rate limits, secrets, abuse controls, backups and review required |
| Production deployment | Not implemented | Staging + reproducible production release path required |
| Predictive forecasting | Deferred | Historical intelligence must be validated on real data first |

## What the current build proves

The executable prototype proves the intended application contract:

```text
business + geography + email
        ↓
$1 prototype checkout boundary
        ↓
queued analysis
        ↓
discover → evidence → normalize → score → findings → render
        ↓
persisted analysis report
        ↓
radial trajectory + evidence drilldown + Top 10 lessons
```

It proves that the visual “clock/rays” concept can be translated into a technically coherent **Radial Business Trajectory Map** without pretending the data follows a mathematical sine wave.

It also demonstrates the key epistemic rule: the UI can show a performance state without inventing an explanatory event for every year. When evidence is absent, the drilldown says so.

## Canonical demonstrator

**Business:** Packaging manufacturing  
**Geography:** New York  
**Launch scope:** United States-first  
**Data mode:** Synthetic fixture  
**Peer entities:** 5 synthetic companies  
**Historical depth:** up to 10 annual points  
**Commercial UX:** $1.00 demo authorization, no real charge  
**Primary visualization:** Radial Business Trajectory Map

Production cohort intent remains up to approximately 100 genuinely comparable companies when evidence quality supports that number.

## Engineering improvements in this prototype

Compared with the earlier static vertical slice, this build adds:

1. **Durability:** analysis jobs/reports are stored in SQLite instead of only process memory.
2. **Asynchronous execution:** a background analysis worker advances through explicit states.
3. **Progress observability:** each analysis exposes a percentage and human-readable stage.
4. **Commercial API boundary:** a safe $1 demo checkout produces an authorization token.
5. **User identity input:** email is captured as part of the prototype flow.
6. **Readiness endpoint:** technical state is machine-readable at `/readiness`.
7. **Pricing endpoint:** current prototype pricing assumptions are machine-readable at `/pricing`.
8. **Improved UI:** processing pipeline, polished radial map, evidence provenance and technical-readiness matrix.
9. **Single-source fallback:** static browser fixture data is generated from the backend report model.
10. **Lifecycle correctness:** SQLite connections close explicitly and background workers can be joined for clean verification.

## What this build still does not prove

It does not yet prove:

- real-world company-data coverage;
- entity-resolution accuracy;
- real evidence freshness or licensing completeness;
- causal accuracy on real company outcomes;
- real payment processing or chargeback handling;
- private multi-tenant security;
- multi-minute durable queue reliability;
- email deliverability;
- production cost per analysis;
- global market coverage;
- predictive forecasting accuracy.

## Fastest credible route from prototype to paid beta

### Gate 1 — Real evidence vertical slice

Connect one lawful U.S. discovery/evidence path for the initial packaging/manufacturing family. Preserve source provenance and entity-resolution confidence. Do not expand industries until one real analysis is defensible end-to-end.

### Gate 2 — Production persistence and jobs

Move SQLite → PostgreSQL and in-process thread → durable worker queue. Preserve the current repository/service interfaces so the UI/API contract does not need to be rewritten.

### Gate 3 — Identity and commercial workflow

Add authentication/tenant ownership, real payment provider, signed/idempotent webhooks, and email completion delivery.

### Gate 4 — Economics and operational controls

Measure provider requests, model usage, worker time, storage, payment fees and gross margin per analysis. Confirm or revise the `$1` hypothesis from actual cost data.

### Gate 5 — Closed paid beta

Run a limited U.S. beta in supported sectors/regions with source coverage, customer feedback, security review and observable support processes.

## Go / no-go statement

**GO for workable MVP prototype review.**  
**GO for real-data vertical-slice engineering.**  
**NO-GO for paid public production today.**

The product concept is now represented by executable software. The critical next question is no longer “can we visualize the idea?” It is “can we produce defensible, economically viable real-company evidence at production quality?”
