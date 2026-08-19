# Analytica v1 Design Specification

## Status

Approved for implementation on 2026-08-18.

## Product Definition

Analytica is a comparative historical-business intelligence and predictive decision-support SaaS. A user describes a business activity and geography; the system discovers comparable companies, reconstructs up to approximately ten years of lawful public/licensed historical evidence, identifies success and failure patterns, produces evidence-backed lessons, and renders the result through an intuitive radial historical-performance interface.

The first production release is historical intelligence and prescriptive decision support first. Forward-looking predictive analytics is a later layer built on validated historical evidence.

## Product Promise

Before risking capital, inspect what happened to businesses like yours, why important changes occurred, which patterns repeatedly worked or failed, and what lessons can be applied to the user's own decisions.

## Primary Users

1. Pre-launch entrepreneurs evaluating a business direction.
2. Existing business operators benchmarking decisions against peers.

Future users may include consultants, accelerators, lenders, investors, and economic-development organizations.

## MVP User Flow

1. User enters business activity in natural language.
2. User selects target geography.
3. System normalizes industry and geography.
4. User authenticates or provides email identity.
5. Payment is authorized through an abstracted payment provider.
6. Analysis job is queued.
7. System discovers a relevant peer cohort.
8. System collects and normalizes evidence.
9. Deterministic scoring and pattern detection run.
10. Evidence-constrained AI produces explanations and recommendations.
11. User receives a completed report and notification.
12. User can inspect the radial trajectory, drill into periods, view evidence, and ask a paid follow-up question.

## Required Inputs

MVP requires:

- `business_activity`: free-text business description.
- `geography`: country/state/region/city input resolved to a normalized geographic object.
- `email` or authenticated identity for result delivery.
- payment authorization before commercial analysis execution.

Additional business details may be introduced progressively but are not required for the initial flow.

## Cohort Discovery

Target cohort size is up to approximately 100 comparable companies when sufficient high-quality evidence exists. Quality overrides quota: the system must prefer fewer genuinely comparable companies over padding the cohort with weak matches.

Each candidate receives a comparability score derived from:

- industry similarity;
- geography similarity;
- product/service similarity;
- company scale similarity when known;
- historical-data completeness.

The cohort engine records why a company was included.

### Geographic Expansion

Search expands progressively when local coverage is insufficient.

For the U.S. launch path:

`city -> county -> state -> adjacent states -> region -> nation`

Other countries use an equivalent administrative-area hierarchy.

## Historical Window

The system seeks up to approximately ten years of history. Missing years must remain missing; the platform must not synthesize factual business history that is not supported by evidence.

Each historical fact or metric carries source, date, confidence, and completeness metadata.

## Cohort Segmentation

Companies may be classified as:

- active;
- distressed/declining;
- closed/failed/bankrupt;
- high performing.

Original conversation percentages such as 10-20% failed companies or a top 40% high-performer segment are configurable heuristics, not universal truths. Production segmentation must be data-derived.

## Data Legality

Analytica may use only information that is public, licensed, user-authorized, or otherwise lawfully accessible. It must not imply access to private IRS records, private bank information, confidential systems, or protected data without authorization.

## Evidence Model

Every material analytical conclusion must be traceable to evidence. A normalized evidence record contains at least:

- `evidence_id`;
- `company_id`;
- `source_type`;
- `source_uri`;
- `source_title`;
- `publisher`;
- `publication_date`;
- `retrieved_at`;
- `fact`;
- `normalized_fact`;
- `period`;
- `confidence`;
- `verification_status`.

## Historical Event Model

Raw evidence is transformed into normalized company events and metrics. The event model is the bridge between heterogeneous source material and cross-company analysis.

Representative event categories include:

- company status changes;
- product/service changes;
- location expansion/contraction;
- funding/debt events;
- revenue or margin changes where lawfully available;
- litigation/regulatory events;
- major procurement/input-cost changes where observable;
- management changes where material;
- macroeconomic and competitive events relevant to the company.

## Analytical Layers

The analysis pipeline is separated into ten logical units:

1. Discovery
2. Entity Resolution
3. Evidence Acquisition
4. Normalization
5. Feature Engineering
6. Performance Scoring
7. Pattern Detection
8. Explanation
9. Recommendation
10. Visualization

Each unit must have a narrow interface so it can be tested independently and replaced later without breaking consumers.

## Deterministic Analytics vs AI

Deterministic application code calculates:

- growth rates;
- rankings and percentiles;
- normalized scores;
- cohort membership;
- historical distances and trajectories;
- time-series statistics;
- risk/performance scores;
- confidence aggregation.

AI may assist with:

- document interpretation;
- structured event extraction;
- evidence summarization;
- question generation;
- evidence-constrained explanations;
- recommendation wording.

AI must not invent financial numbers or unsupported business facts.

## Confidence Taxonomy

Material conclusions must be classified as one of:

1. Verified observation — directly supported by reliable evidence.
2. Correlation — variables/events co-occur without proven causality.
3. Evidence-supported explanation — a credible source explicitly connects the factors.
4. Analytical inference — the system estimates a likely relationship from multiple signals.

The UI must not present correlation as proven causation.

## Performance and Risk Scores

Performance and risk are normalized, explainable scores rather than opaque model outputs. The architecture must support industry-specific feature weighting.

Distance from the center of the radial map is derived from normalized historical performance/risk state, not arbitrary UI geometry.

## Radial Business Trajectory Map

The original "clock" concept is implemented as a radial historical-performance visualization, not a literal clock.

Requirements:

- no conventional clock numerals;
- top-down view;
- trajectories/rays representing companies, strategies, or normalized analytical dimensions as selected by the product view;
- up to ten annual intervals per historical trajectory;
- selectable periods;
- hover/focus details;
- filters for state/quality bands;
- accessible representation that does not rely solely on color.

Initial semantic colors:

- red: serious weakness/distress;
- yellow: caution/instability;
- blue: intermediate/neutral;
- green: strong condition.

The visual must remain understandable on mobile and desktop.

The word "sinusoid" from the source discussion is interpreted as historical performance trajectory unless later evidence justifies an actual periodic mathematical model.

## Drilldown Contract

Selecting a ray/period must answer:

- what happened;
- when it happened;
- which factors were associated with the change;
- what evidence supports the finding;
- confidence level;
- what lesson may be relevant to the user.

The primary differentiator is the chain:

`evidence -> event -> explanation -> lesson -> recommendation`

## Top Lessons

A completed report should prioritize approximately ten actionable lessons when evidence supports them.

Each recommendation includes:

- lesson text;
- business impact;
- supporting companies;
- supporting events;
- confidence;
- risk addressed;
- recommended action;
- evidence references.

Low-confidence recommendations are visibly labeled.

## Bring-Your-Own-AI

The source discussion proposes using AI resources already available to the user. This is classified as future R&D, not an MVP dependency.

The long-term architecture may expose a user-authorized `AIProvider` adapter for supported providers, but the core product must remain functional using platform-owned providers or deterministic fixture implementations.

## Production Architecture

Analytica v1 uses a modular monolith with clean internal boundaries.

### Frontend

Next.js + React + TypeScript.

Responsibilities:

- landing page;
- analysis request flow;
- authentication/email identity;
- payment handoff;
- processing/status experience;
- radial visualization;
- evidence drawer;
- top lessons;
- follow-up questions;
- responsive/accessibility behavior.

### Analytical API

Python + FastAPI.

Responsibilities:

- industry/geography normalization;
- analysis orchestration;
- cohort generation;
- evidence normalization;
- scoring;
- pattern detection;
- explanation/recommendation provider routing;
- report API.

### Database

PostgreSQL is the durable system of record.

Core entities:

- users;
- analyses;
- business queries;
- geographies;
- companies and aliases;
- evidence;
- events and metrics;
- cohort memberships;
- scores;
- findings;
- recommendations;
- follow-up questions;
- payments;
- notifications;
- audit events.

### Background Processing

Long-running analyses execute asynchronously through a Redis-backed worker queue or compatible adapter. HTTP requests must not remain open for the full analysis duration.

### Provider Interfaces

External integrations must be behind narrow interfaces:

- `SearchProvider`;
- `CompanyDataProvider`;
- `MacroDataProvider`;
- `LegalDataProvider`;
- `AIProvider`;
- `EmailProvider`;
- `PaymentProvider`;
- `StorageProvider`.

Provider count is not a product metric; evidence quality and coverage are.

## Analysis State Machine

Required states:

- `CREATED`;
- `PAYMENT_PENDING`;
- `QUEUED`;
- `DISCOVERING_COMPANIES`;
- `COLLECTING_EVIDENCE`;
- `NORMALIZING`;
- `SCORING`;
- `GENERATING_FINDINGS`;
- `RENDERING_RESULT`;
- `COMPLETED`;
- `FAILED_RETRYABLE`;
- `FAILED_PERMANENT`;
- `INSUFFICIENT_DATA`;
- `CANCELLED`.

State transitions must be explicit and testable.

## API Surface

Representative endpoints:

- `POST /analyses`
- `GET /analyses/{id}`
- `GET /analyses/{id}/status`
- `GET /analyses/{id}/companies`
- `GET /analyses/{id}/trajectory`
- `GET /analyses/{id}/findings`
- `GET /analyses/{id}/recommendations`
- `GET /analyses/{id}/evidence`
- `POST /analyses/{id}/questions`
- `POST /payments/checkout`
- `POST /webhooks/payment`

All externally visible payloads use typed schemas.

## Security and Privacy

Minimum production requirements:

- HTTPS/TLS;
- server-side secret storage;
- least-privilege credentials;
- secure session/auth handling;
- input validation;
- tenant ownership boundaries;
- rate limiting;
- CSRF protection where relevant;
- payment-webhook signature validation;
- audit logging;
- dependency scanning;
- no secrets committed to Git;
- environment-specific configuration;
- minimal personal-data collection.

## Multi-Tenancy

Every user-owned analysis, question, report, payment, and private result is explicitly scoped to its owner/tenant. One user's unpublished analyses must never be visible to another user.

## Pricing

The original commercial hypothesis is approximately $1 for an initial analysis and $1 for a follow-up analytical question. Pricing must be configuration-driven and validated against actual variable cost.

Each analysis should record resource usage and estimated cost so the business can measure gross margin per analysis.

## Observability

Production metrics include:

- analysis success rate;
- median and p95 analysis duration;
- company-discovery success;
- evidence coverage;
- provider failure rate;
- AI validation failure rate;
- cost per analysis;
- gross margin per analysis;
- conversion rate;
- follow-up question rate.

Logs, traces, worker events, and provider latency must be observable.

## Error Handling

The system must handle and surface:

- insufficient peer companies;
- provider outage/timeouts;
- malformed evidence;
- low-confidence entity resolution;
- AI-provider failure;
- payment failure;
- email failure;
- partial analysis;
- cancellation.

A transparent partial result is preferable to a fabricated complete result.

## MVP Scope

The first commercial vertical slice must include:

- business query;
- geography;
- identity/email;
- analysis creation;
- explicit state machine;
- asynchronous job abstraction;
- fixture-based peer cohort;
- fixture-based evidence timeline;
- deterministic scoring;
- active/failed/high-performer segmentation;
- evidence-supported findings;
- top lessons;
- radial visualization;
- evidence drilldown;
- result persistence abstraction;
- email/payment provider abstractions;
- follow-up-question architecture;
- logging/error handling;
- automated unit/integration/E2E tests.

Real external data providers are connected after the fixture-driven vertical slice proves the complete flow.

## Non-Goals for MVP

The MVP does not depend on:

- arbitrary AI installed on a user's phone;
- private IRS/tax access;
- perfect worldwide coverage;
- forty simultaneous data providers;
- guaranteed business forecasts;
- full causal inference;
- enterprise BI dashboards.

## Delivery Strategy

The approved architecture is implemented in independently testable increments:

1. Production foundation and fixture-driven vertical slice.
2. Radial report UX and evidence drilldown.
3. Evidence acquisition/entity-resolution/provider pipeline.
4. Commercial workflow: auth, payments, email, follow-up questions.
5. Production hardening, observability, deployment, security, and data-quality controls.
6. Predictive/scenario layer only after historical-engine validation.

## Definition of Done for v1 Foundation

The initial production foundation is complete when a user can submit a business and geography, receive an asynchronous fixture-backed analysis, inspect a radial ten-year report, open evidence-backed explanations, view approximately ten prioritized lessons, and traverse the entire flow through automated tests without external data providers.

## Key Product Constraint

Analytica must never reduce itself to "an AI that predicts whether your business will succeed." The credible product positioning is evidence-driven historical comparison, explanation, and decision support, with predictive scenarios layered on only after the underlying historical engine is validated.
