import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';

const html = fs.readFileSync(new URL('../index.html', import.meta.url), 'utf8');
const js = fs.readFileSync(new URL('../app.js', import.meta.url), 'utf8');

function has(pattern, source = html) { return pattern.test(source); }

test('exposes explicit R&D readiness state', () => {
  assert.ok(has(/data-testid="readiness-badge"/));
  assert.ok(has(/R&D vertical slice/i));
});

test('contains the main semantic product regions', () => {
  for (const id of ['analysis-summary', 'cohort-kpis', 'trajectory-map', 'evidence-panel', 'lessons']) {
    assert.ok(html.includes(`id="${id}"`), `missing ${id}`);
  }
});

test('radial map is an accessible SVG application region', () => {
  assert.ok(has(/<svg[^>]+id="radial-map"[^>]+role="img"/s));
  assert.ok(has(/aria-labelledby="radial-title radial-desc"/));
});

test('evidence drilldown has live announcement semantics', () => {
  assert.ok(has(/id="evidence-panel"[^>]+aria-live="polite"/s));
});

test('client points at the approved analysis API contract', () => {
  assert.ok(js.includes('/analyses/demo_packaging_ny_v1'));
  assert.ok(js.includes('/analyses'));
});

test('client renders radial trajectories and evidence', () => {
  assert.ok(js.includes('renderRadialMap'));
  assert.ok(js.includes('showEvidence'));
  assert.ok(js.includes('renderLessons'));
});
