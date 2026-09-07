# Predicta research path

Classification: IMPLEMENTED_UNVERIFIED for deployed integration.

Entry point: apps.api.app.predicta_path.run_case(ResearchCase(...), PredictaHttpPort(), database_path).
This is an internal callable research path; the existing demo API/UI is unchanged.

Configuration: PREDICTA_BASE_URL (required HTTPS), PREDICTA_TIMEOUT_SECONDS (default 15, maximum 60), PREDICTA_MAX_ATTEMPTS (default 3, maximum 4), optional PREDICTA_API_KEY (Bearer). No credentials are embedded. Redirects are refused. Response body is limited to 4 MB. Timeout/network errors, 429 and 5xx are retried within the bound; numeric Retry-After is capped at 30 seconds. Date-form Retry-After uses exponential delay instead. Authentication and validation errors propagate without retry.

The new port requires an explicit predicta.search.v1 version, candidates, claims, query identity and diagnostics. It does not invent a version. Candidate snippets become passages per the existing v1 EvidencePort; explicit upstream extra fields are preserved in the raw response manifest, not automatically interpreted as new normalized schema fields. Source/passage pairing and duplicate source/claim IDs are checked. The entire response and diagnostics are persisted, with a response hash; normalized packet diagnostics are included in query metadata covered by the existing packet hash.

Run states: RUNNING, SUCCEEDED, DEGRADED, FAILED. Empty sources or provider failures prevent a full-success classification. Exceptions persist a sanitized error class and optional HTTP status, then propagate. Separate manifest/packet transactions mean a crash can leave RUNNING or an orphan packet; recovery/checkpoint reconciliation is still required. Existing packet repository integrity limitations from the truth audit remain. No authenticated identity resolution or financial acceptance is claimed.

Canary: POST https://aiwmc.org/api/search, case canary-2026-09-05, query New York packaging manufacturing industry. Observed HTTP 401 Unauthorized. Failure persisted in .data/predicta-canary.db. No successful deployed schema response observed. No packet or canonical financial input produced. No fixture fallback.

Tests before implementation: new module import failed (module absent). Tests after implementation: all nine new tests pass, covering correct/wrong version, schema, timeout, 429, 503, contradiction/diagnostics persistence and packet tamper detection, no fallback, source/passage mismatch.
Regression: 47 backend tests pass; test_api cannot import FastAPI (one import error). Six repository tests and seven static UI checks pass. Full suite is not green. No browser runtime verification claimed.

Next handoff: verify deployed endpoint/auth contract, configure authorized local credential, repeat canary, confirm durable packet roundtrip. Keep classification IMPLEMENTED_UNVERIFIED until successful. Add authenticated case ownership and restart recovery before public API exposure. Existing legacy live_adapters.PredictaHttpClient remains for compatibility and must not be mistaken for this strict port.
