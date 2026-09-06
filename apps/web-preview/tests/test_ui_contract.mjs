import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const js = fs.readFileSync(new URL('../app.js', import.meta.url), 'utf8');
const css = fs.readFileSync(new URL('../styles.css', import.meta.url), 'utf8');

function has(pattern, source = html) { return pattern.test(source); }

test('labels the build as a workable MVP prototype and launch-gated', () => {
  assert.ok(has(/data-testid="readiness-badge"/));
  assert.ok(has(/Workable MVP prototype/i));
  assert.ok(has(/Paid launch gated/i));
});

test('commercial prototype flow includes email and one-dollar demo checkout', () => {
  assert.ok(has(/type="email"[^>]+id="email"/s));
  assert.ok(has(/\$1\.00/));
  assert.ok(js.includes('/payments/checkout'));
  assert.ok(js.includes('payment_token'));
});

test('contains processing pipeline and technical readiness regions', () => {
  for (const id of ['analysis-pipeline', 'analysis-summary', 'decision-brief', 'evidence-quality', 'scenario-comparison', 'assumption-register', 'cohort-kpis', 'trajectory-map', 'evidence-panel', 'lessons', 'technical-readiness', 'technical-command-center', 'entity-provenance-state', 'verification-strip', 'real-demo-matrix']) {
    assert.ok(html.includes(`id="${id}"`), `missing ${id}`);
  }
  assert.ok(js.includes('/readiness'));
});

test('radial map is accessible and supports keyboard-selectable evidence points', () => {
  assert.ok(has(/<svg[^>]+id="radial-map"[^>]+role="img"/s));
  assert.ok(has(/aria-labelledby="radial-title radial-desc"/));
  assert.ok(js.includes("role: 'button'") || js.includes("role:'button'"));
  assert.ok(js.includes("tabindex: '0'") || js.includes("tabindex:'0'"));
});

test('evidence drilldown exposes provenance and confidence semantics', () => {
  assert.ok(has(/id="evidence-panel"[^>]+aria-live="polite"/s));
  assert.ok(js.includes('normalized_fact'));
  assert.ok(js.includes('confidence'));
  assert.ok(js.includes('source_title'));
});

test('responsive CSS includes desktop and mobile breakpoints', () => {
  assert.ok(css.includes('@media(max-width:980px)'));
  assert.ok(css.includes('@media(max-width:640px)'));
});

test('client renders report, radial trajectories, findings, lessons, and readiness', () => {
  for (const name of ['renderReport', 'renderDecisionBrief', 'renderEvidenceQuality', 'renderScenarios', 'renderAssumptions', 'renderRadialMap', 'showEvidence', 'renderFindings', 'renderLessons', 'renderReadiness', 'renderCommandCenter']) {
    assert.ok(js.includes(name), `missing ${name}`);
  }
});

test('decision brief has an explainable recommendation interaction rather than a decorative graph', () => {
  assert.ok(js.includes('id="why-recommendation"'));
  assert.ok(js.includes('id="decision-lineage"'));
  assert.ok(js.includes('renderDecisionLineage'));
  assert.ok(js.includes('/evidence-graph/recommendations/'));
  assert.match(js, /Why are you telling me this\?/);
});

test('decision workspace surfaces only contracted reliability, financial, and limitation data', () => {
  for (const id of ['entity-identity', 'turning-points', 'contradictions', 'recommendation-ledger', 'method-limitations']) {
    assert.ok(html.includes(`id="${id}"`), `missing ${id}`);
  }
  for (const name of ['renderEntityIdentity', 'renderTurningPoints', 'renderContradictions', 'renderRecommendationLedger', 'renderMethodLimitations']) {
    assert.ok(js.includes(name), `missing ${name}`);
  }
  assert.ok(js.includes('low_operating_profit'));
  assert.ok(js.includes('high_operating_profit'));
  assert.ok(!js.includes('fixture confidence'));
  assert.ok(!js.includes('DEPENDENCY BLOCKED'));
  assert.ok(js.includes('Entity delivery'));
});

test('internal reviewer screen exposes the concierge delivery gate and only audit-backed controls', () => {
  const reviewHtmlPath = new URL('../review.html', import.meta.url);
  const reviewJsPath = new URL('../review.js', import.meta.url);
  assert.ok(fs.existsSync(reviewHtmlPath), 'missing internal reviewer screen');
  assert.ok(fs.existsSync(reviewJsPath), 'missing internal reviewer client');
  const reviewHtml = fs.readFileSync(reviewHtmlPath, 'utf8');
  const reviewJs = fs.readFileSync(reviewJsPath, 'utf8');
  for (const id of ['review-gate', 'review-case', 'review-evidence', 'review-assumptions', 'review-financials', 'review-recommendation', 'review-audit']) {
    assert.ok(reviewHtml.includes(`id="${id}"`), `missing ${id}`);
  }
  assert.match(reviewHtml, /Internal concierge review/i);
  assert.ok(reviewJs.includes('/review/cases/'));
  for (const action of ['APPROVE_ENTITY', 'REJECT_ENTITY', 'REQUEST_ADDITIONAL_RESEARCH', 'ACCEPT_ASSUMPTION', 'REJECT_ASSUMPTION', 'EDIT_RECOMMENDATION', 'RETURN_FOR_REVISION', 'APPROVE_DELIVERY', 'REJECT_DELIVERY']) {
    assert.ok(reviewJs.includes(action), `missing reviewer action ${action}`);
  }
});
