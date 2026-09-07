# Quantis Canonicality Gate — BLOCKED

**Date:** 2026-09-05
**Scope:** FinancialPort parity assessment for Analytica.
**Decision:** Do not connect Analytica's financial calculations to Quantis yet.

## Why this is blocked

The Quantis repository identifies the active production calculator as:

`supabase/functions/analyze-business/financial-calculator.ts` →
`calculateStrictFinancials(...)`

The production entry point imports that function from
`supabase/functions/analyze-business/index.ts`. Repository tests also import
that function directly, so it is the strongest available evidence for the
current production calculation path.

It is **not**, however, a complete, versioned, standalone calculation kernel
that Analytica can safely treat as the sole financial authority. The repository
contains several independently callable, materially different financial paths:

| Capability | Production-path implementation | Other callable implementation | Why parity is unsafe now |
| --- | --- | --- | --- |
| Baseline P&L | `financial-calculator.ts::calculateStrictFinancials` | `src/lib/financial-engine.ts::generate3YearPL` | Inputs and outputs are different: the former starts from MRR and industry benchmarks; the latter projects customer growth, churn, capacity assumptions, and 36 monthly statements. |
| Break-even | `financial-calculator.ts` with `calculateCvp` plus its own revenue calculation | `src/lib/financial-engine.ts::findBreakEvenMonth`; `src/financial/contribution-margin.ts` | These mean different things: period break-even revenue, cash-flow break-even month, and CVP break-even. |
| Payback | `analyze-business/payback-contract.ts` used by `financial-calculator.ts` | `src/financial/payback.ts`; `financial-engine.ts::calculatePaybackPeriod` | The two contract files are distinct (207 vs. 73 lines; different SHA-256) and the projection engine uses another implementation. |
| Runway | No runway value in `StrictFinancialResult` | `financial-engine.ts::calculateCashRunway` | The apparent financial authority does not expose the required metric. |
| Scenarios / sensitivity | `run-scenario` reuses `calculateStrictFinancials` and `_shared/scenario-sensitivity.ts` | `src/services/scenario-engine.ts`; `scenario-sets-api.ts`; `sensitivity-analyzer.ts` | Multiple scenario layers have different input contracts and scopes. |
| Reconciliation | narrow calculator-level checks | `src/financial/reconcile.ts`; `src/lib/reconciliation-engine.ts` | The formula manifest explicitly classifies `src/financial/reconcile.ts` as spec-only, and Quantis's own accuracy ledger records the reconciliation engines as unreachable from the live path. |
| Assumption lineage | `_shared/assumption-origin.ts` in the edge-function workflow | no equivalent typed public kernel contract | Analytica cannot map its ACCEPTED assumptions to a stable Quantis request schema without inventing lineage semantics. |

The duplicate source modules are not byte-identical. For example, the
repository has different SHA-256 values for the edge-function and `src/financial`
versions of payback, CVP, and profitability-margin modules. The current formula
registry also states that its local registry is distinct from an older runtime
registry and that some paths are not called by the live analysis pipeline.

This meets the explicit stop condition for ambiguous duplicate implementations.
Choosing one silently would create the exact “two financial truths” failure
that a FinancialPort is meant to prevent.

## Verification evidence

Focused Quantis tests were run against the repository's installed Vitest:

```text
src/__tests__/golden-cases.test.ts
src/__tests__/scenario-engine-reuse.test.ts
src/__tests__/financial-payback-contract.test.ts
src/__tests__/financial-reconciliation.test.ts

4 test files passed; 13 tests passed.
```

Those tests verify behavior around `calculateStrictFinancials` and selected
contracts. They do **not** establish a parity contract between all of the
duplicate engines, nor do they make a versioned external Financial API
available to Analytica.

## Architecture decision

No integration option is presently safe to implement.

| Option | Decision | Evidence |
| --- | --- | --- |
| A. Local package/import boundary | Rejected now | Analytica is Python/FastAPI; Quantis is TypeScript with browser and Deno/Supabase modules. There is no published, runtime-neutral package export, and importing a source file by cross-repository path would couple deployments and toolchains. |
| B. Versioned HTTP service | Rejected now | No versioned FinancialPort endpoint or stable request/response schema was found for the calculation kernel. `analyze-business` is an application workflow, not a documented financial-kernel service contract. |
| C. Extracted shared deterministic library | Recommended, but blocked pending canonicalization | A small runtime-neutral kernel contract plus immutable golden vectors is the only option that can serve both Quantis and Analytica without code copying. It must be extracted from a founder-approved canonical source and versioned before either application consumes it. |

The next safe implementation choice is therefore **C**, after Quantis has one
approved canonical contract. It is not authorized to be implemented in this
Analytica change because it would require selecting or altering Quantis source
code outside this repository.

## Analytica impact

`apps/api/app/financial.py::QuantisFinancialPort` is currently a local
demonstrator, not a Quantis integration. Its input model and formulas do not
match `calculateStrictFinancials`, and it has no canonical accepted-assumption
mapping. It must remain classified as **PROTOTYPE** and must not be represented
as Quantis-parity evidence.

The existing Analytica evidence firewall remains a required precondition:

```text
Predicta / provider evidence
  -> proposed assumption
  -> reviewer ACCEPTED
  -> CanonicalFinancialInput
  -> future FinancialPort
```

Predicta must not call Quantis. The financial boundary must accept only
persisted, reviewer-accepted CanonicalFinancialInput records; raw provider
records and unaccepted proposals stay outside it.

## Exact unblock slice

1. In Quantis, approve one canonical calculation surface and state the
   supported business model, input schema, output schema, rounding policy,
   unavailable-metric semantics, and version identifier.
2. Extract it into a versioned deterministic library with no React, browser,
   Deno request, Supabase, logger, or provider dependencies.
3. Publish at least five immutable, hand-reviewed golden vectors covering
   revenue, contribution, fixed costs, operating profit, break-even, payback,
   runway, downside/base/upside, and sensitivity.
4. Add an explicit reconciliation endpoint/function that compares a request,
   output, vector version, formula version, and assumption lineage.
5. Only then build the Analytica adapter: map *only ACCEPTED* assumptions to
   the canonical request, invoke the versioned contract, persist the response
   and formula/vector versions, and assert direct-Quantis-to-Analytica parity.

Until steps 1–4 are complete, no claim of Quantis mathematical parity or
production financial readiness is warranted.
