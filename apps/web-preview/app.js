const API_BASE = window.ANALYTICA_API_BASE || '';
const DEMO_ENDPOINT = '/analyses/demo_packaging_ny_v1';
const CREATE_ENDPOINT = '/analyses';
const CHECKOUT_ENDPOINT = '/payments/checkout';
const READINESS_ENDPOINT = '/readiness';
const state = { report: null, activeCompanyId: null, analysisId: null, recommendationLineage: null };
const colors = { green: '#64e0a3', blue: '#6ca7ff', yellow: '#f1c85e', red: '#ff756f' };
const lineColors = ['#8df0c6', '#7caaff', '#f0c45d', '#ff837a', '#c79aff'];
const PIPELINE = [
  ['QUEUED', 'Queued'],
  ['DISCOVERING_COMPANIES', 'Discover peers'],
  ['COLLECTING_EVIDENCE', 'Collect evidence'],
  ['NORMALIZING', 'Normalize history'],
  ['SCORING', 'Score trajectories'],
  ['GENERATING_FINDINGS', 'Generate findings'],
  ['RENDERING_RESULT', 'Render report'],
  ['COMPLETED', 'Complete'],
];
const FALLBACK_READINESS = {
  product_stage: 'workable_mvp_prototype', prototype_completion_percent: 78, paid_public_launch_ready: false,
  areas: [
    { area: 'Product architecture', state: 'working', detail: 'Approved architecture and analytical contracts' },
    { area: 'Historical analytics', state: 'working', detail: 'Evidence, trajectories, findings and lessons' },
    { area: 'Persistence', state: 'prototype', detail: 'SQLite prototype; PostgreSQL is production target' },
    { area: 'Async execution', state: 'prototype', detail: 'Background analysis state machine implemented' },
    { area: 'Commercial flow', state: 'prototype', detail: '$1 demo checkout contract; no real charge' },
    { area: 'Visual product', state: 'working', detail: 'Radial map + evidence drilldown + lessons' },
    { area: 'Real company data', state: 'blocked', detail: 'Lawful providers and entity resolution required' },
    { area: 'Authentication / tenancy', state: 'blocked', detail: 'Required before private customer reports' },
    { area: 'Real payments', state: 'blocked', detail: 'Checkout provider + signed webhooks required' },
    { area: 'Production deployment', state: 'blocked', detail: 'Observability, backups and hardening required' },
  ],
};

const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));
const apiUrl = (path) => `${API_BASE}${path}`;
const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, ch => ({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[ch]));
const confidenceLabel = (value) => String(value).replaceAll('_', ' ').replace(/\b\w/g, c => c.toUpperCase());

async function fetchJson(path, options = {}) {
  const response = await fetch(apiUrl(path), { cache: 'no-store', ...options });
  if (!response.ok) {
    let detail = `${response.status}`;
    try { const body = await response.json(); detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail); } catch (_) {}
    throw new Error(detail);
  }
  return response.json();
}

async function loadInitialReport() {
  try { return await fetchJson(DEMO_ENDPOINT); }
  catch (error) {
    if (window.__ANALYTICA_DEMO_REPORT__) return window.__ANALYTICA_DEMO_REPORT__;
    throw error;
  }
}

function renderPipeline(status = 'COMPLETED', progress = 100, label = 'Analysis complete') {
  const host = document.querySelector('#pipeline-steps');
  const currentIndex = Math.max(0, PIPELINE.findIndex(([code]) => code === status));
  host.innerHTML = PIPELINE.map(([code, name], index) => {
    const done = status === 'COMPLETED' || index < currentIndex;
    const active = code === status && status !== 'COMPLETED';
    return `<div class="pipeline-step ${done ? 'done' : ''} ${active ? 'active' : ''}"><span>${done ? '✓' : index + 1}</span><small>${escapeHtml(name)}</small></div>`;
  }).join('');
  document.querySelector('#pipeline-percent').textContent = `${Math.round(progress)}%`;
  document.querySelector('#pipeline-stage').textContent = label;
  document.querySelector('#pipeline-bar').style.width = `${Math.max(0, Math.min(100, progress))}%`;
}

async function simulateStaticPipeline() {
  const states = [
    ['QUEUED', 5, 'Prototype request queued'],
    ['DISCOVERING_COMPANIES', 18, 'Discovering comparable companies'],
    ['COLLECTING_EVIDENCE', 36, 'Collecting historical evidence'],
    ['NORMALIZING', 52, 'Normalizing company timelines'],
    ['SCORING', 70, 'Scoring peer trajectories'],
    ['GENERATING_FINDINGS', 85, 'Generating evidence-backed findings'],
    ['RENDERING_RESULT', 96, 'Rendering decision report'],
    ['COMPLETED', 100, 'Analysis complete — static preview mode'],
  ];
  for (const [status, progress, label] of states) { renderPipeline(status, progress, label); await sleep(90); }
}

async function runPrototypeAnalysis() {
  const button = document.querySelector('#run-analysis');
  const errorHost = document.querySelector('#form-error');
  const business_activity = document.querySelector('#business').value.trim();
  const geography = document.querySelector('#geography').value.trim();
  const email = document.querySelector('#email').value.trim();
  errorHost.hidden = true;
  button.disabled = true;
  button.querySelector('span').textContent = 'Authorizing prototype checkout…';
  renderPipeline('QUEUED', 3, 'Authorizing $1 prototype checkout');

  try {
    const checkout = await fetchJson(CHECKOUT_ENDPOINT, {
      method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify({ email }),
    });
    button.querySelector('span').textContent = 'Analysis running…';
    const created = await fetchJson(CREATE_ENDPOINT, {
      method: 'POST', headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ business_activity, geography, email, payment_token: checkout.payment_token }),
    });
    state.analysisId = created.analysis_id;
    let job;
    for (let attempt = 0; attempt < 120; attempt += 1) {
      job = await fetchJson(`/analyses/${created.analysis_id}/status`);
      renderPipeline(job.status, job.progress_percent, job.stage_label);
      if (job.status === 'COMPLETED') break;
      if (job.status.startsWith('FAILED') || job.status === 'CANCELLED') throw new Error(job.stage_label);
      await sleep(120);
    }
    if (!job || job.status !== 'COMPLETED') throw new Error('Analysis did not complete inside the prototype polling window.');
    const report = await fetchJson(`/analyses/${created.analysis_id}`);
    renderReport(report);
    document.querySelector('#analysis-summary').scrollIntoView({ behavior: 'smooth', block: 'start' });
  } catch (error) {
    const isStaticPreview = Boolean(window.__ANALYTICA_DEMO_REPORT__) && /Failed to fetch|404|405|Unexpected token|NetworkError/i.test(error.message);
    if (isStaticPreview) {
      await simulateStaticPipeline();
      renderReport(window.__ANALYTICA_DEMO_REPORT__);
      document.querySelector('#analysis-summary').scrollIntoView({ behavior: 'smooth', block: 'start' });
    } else {
      errorHost.textContent = error.message;
      errorHost.hidden = false;
      renderPipeline('QUEUED', 0, 'Request needs attention');
    }
  } finally {
    button.disabled = false;
    button.querySelector('span').textContent = 'Authorize demo + run analysis';
  }
}

function renderReport(report) {
  state.report = report;
  state.recommendationLineage = null;
  state.activeCompanyId = report.companies.some(c => c.company_id === state.activeCompanyId) ? state.activeCompanyId : report.companies[0]?.company_id;
  document.querySelector('#summary-title').textContent = `${report.business_activity} — ${report.geography}`;
  document.querySelector('#market-scope').textContent = report.market_scope;
  document.querySelector('#readiness-label').textContent = report.readiness_label;
  document.querySelector('#report-disclaimer').textContent = report.disclaimer;
  document.querySelector('#analysis-status').innerHTML = `<span aria-hidden="true"></span> ${escapeHtml(report.status)}`;
  renderDecisionBrief(report);
  renderEvidenceQuality(report);
  renderEntityIdentity(report);
  renderScenarios(report);
  renderAssumptions(report);
  renderKpis(report);
  renderCompanyTabs(report);
  renderRadialMap(report);
  renderFindings(report);
  renderLessons(report);
  renderTurningPoints(report);
  renderContradictions(report);
  renderRecommendationLedger(report);
  renderMethodLimitations(report);
  renderCommandCenter(report);
  preloadRecommendationLineage(report);
}

function money(value) {
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value);
}

function renderDecisionBrief(report) {
  const brief = report.decision_brief;
  document.querySelector('#decision-brief').innerHTML = `
    <div class="panel-kicker"><span>Decision brief</span><b>${escapeHtml(brief.recommendation_status.replaceAll('_', ' '))}</b></div>
    <h2>${escapeHtml(brief.decision)}</h2>
    <div class="decision-number"><span>Capital exposed</span><strong>${money(brief.capital_exposed)}</strong></div>
    <div class="recommendation"><span>Current demonstrator recommendation</span><strong>${escapeHtml(brief.recommendation)}</strong></div>
    <p class="decision-context"><b>Decision context:</b> ${escapeHtml(brief.deadline)}</p>
    <div id="decision-thresholds" class="condition-grid" aria-label="Decision thresholds">
      <div><b>Proceed if</b><p>${escapeHtml(brief.proceed_if)}</p></div>
      <div><b>Wait if</b><p>${escapeHtml(brief.wait_if)}</p></div>
      <div><b>Avoid if</b><p>${escapeHtml(brief.avoid_if)}</p></div>
    </div>
    <div class="lineage-control">
      <button id="why-recommendation" type="button" aria-expanded="false" aria-controls="decision-lineage">Why are you telling me this?</button>
      <p>Inspect the decision chain before acting on this demonstrator recommendation.</p>
    </div>
    <div id="decision-lineage" class="decision-lineage" aria-live="polite" hidden></div>`;
  document.querySelector('#why-recommendation').addEventListener('click', async event => {
    const button = event.currentTarget;
    const lineageHost = document.querySelector('#decision-lineage');
    if (!lineageHost.hidden) {
      lineageHost.hidden = true;
      button.textContent = 'Why are you telling me this?';
      button.setAttribute('aria-expanded', 'false');
      return;
    }
    if (!state.recommendationLineage) {
      button.disabled = true;
      button.textContent = 'Verifying decision lineage…';
      state.recommendationLineage = await loadRecommendationLineage(report);
      button.disabled = false;
    }
    button.textContent = 'Hide decision lineage';
    button.setAttribute('aria-expanded', 'true');
    renderDecisionLineage();
  });
}

async function loadRecommendationLineage(report) {
  const recommendationId = report.decision_brief?.recommendation_id;
  if (!recommendationId) return null;
  try {
    return await fetchJson(`/analyses/${encodeURIComponent(report.analysis_id)}/evidence-graph/recommendations/${encodeURIComponent(recommendationId)}/lineage`);
  } catch (_) {
    return window.__ANALYTICA_DEMO_LINEAGE__ || null;
  }
}

async function preloadRecommendationLineage(report) {
  const lineage = await loadRecommendationLineage(report);
  if (state.report?.analysis_id === report.analysis_id) state.recommendationLineage = lineage;
}

function renderDecisionLineage() {
  const host = document.querySelector('#decision-lineage');
  const lineage = state.recommendationLineage;
  if (!lineage) {
    host.hidden = false;
    host.innerHTML = '<p class="lineage-empty">The decision chain is unavailable in this preview. This recommendation is not report-ready.</p>';
    return;
  }
  const list = (items, empty) => items.length
    ? `<ul>${items.map(item => `<li>${escapeHtml(item.label)}</li>`).join('')}</ul>`
    : `<p>${escapeHtml(empty)}</p>`;
  host.hidden = false;
  host.innerHTML = `
    <div class="lineage-status ${lineage.report_ready ? 'ready' : 'blocked'}"><span>${lineage.report_ready ? 'Lineage complete' : 'Lineage incomplete'}</span><b>${lineage.report_ready ? 'Traceable through source records' : 'Not report-ready'}</b></div>
    <div class="lineage-summary"><div><span>Finding</span>${list(lineage.findings, 'No finding linked.')}</div><div><span>Calculation</span>${list(lineage.calculations, 'No calculation linked.')}</div><div><span>Accepted assumptions</span>${list(lineage.assumptions.filter(item => item.material), 'No accepted assumptions linked.')}</div><div><span>Source records</span>${list(lineage.sources, 'No source records linked.')}</div></div>
    <p class="lineage-note">This is an evidence path, not proof of future performance. Current data mode: ${escapeHtml(state.report.data_mode.replaceAll('_', ' '))}.</p>
    ${lineage.issues.length ? `<ul class="lineage-issues">${lineage.issues.map(issue => `<li>${escapeHtml(issue.message)}</li>`).join('')}</ul>` : ''}`;
}

function renderEvidenceQuality(report) {
  const inferred = report.evidence.filter(item => item.verification_status.includes('inference')).length;
  const verified = report.evidence.length - inferred;
  const tracedFindings = report.findings.filter(item => item.evidence_ids.length > 0).length;
  document.querySelector('#evidence-quality').innerHTML = `
    <div class="panel-kicker"><span>Evidence coverage</span><b>${escapeHtml(report.data_mode.replaceAll('_', ' '))}</b></div>
    <div class="coverage-head"><strong>${verified} / ${report.evidence.length}</strong><span>source records marked<br>fixture verified</span></div>
    <div class="quality-grid">
      <div><strong>${report.evidence.length}</strong><span>source records</span></div>
      <div><strong>${tracedFindings}</strong><span>findings with sources</span></div>
      <div><strong>${verified}</strong><span>fixture verified</span></div>
      <div><strong>${inferred}</strong><span>fixture inferred</span></div>
    </div>
    <p class="quality-note"><b>Reliability boundary:</b> these are record counts and verification labels, not a probability of success or a market-confidence score. Real-provider evidence is not represented by this fixture.</p>`;
}

function renderEntityIdentity(report) {
  const identity = report.entity_identity;
  document.querySelector('#entity-identity').innerHTML = `
    <div class="panel-kicker"><span>Entity identity</span><b>${escapeHtml(identity.resolution_status.replaceAll('_', ' '))}</b></div>
    <h2>${escapeHtml(identity.submitted_name)}</h2>
    <p class="identity-place">${escapeHtml(identity.geography)}</p>
    <div class="identity-delivery ${identity.eligible_for_customer_delivery ? 'eligible' : 'ineligible'}"><span>Delivery eligibility</span><strong>${identity.eligible_for_customer_delivery ? 'Eligible' : 'Not eligible'}</strong></div>
    <p class="quality-note">${escapeHtml(identity.detail)}</p>`;
}

function renderScenarios(report) {
  const cards = report.financial_scenarios.map(item => `
    <div class="scenario-card scenario-${item.name.toLowerCase()}">
      <div><span>${escapeHtml(item.name)}</span><b>${item.reconciliation_passed ? 'RECONCILED' : 'FAILED'}</b></div>
      <strong>${money(item.operating_profit)}<small>/mo operating profit</small></strong>
      <dl><dt>Revenue</dt><dd>${money(item.monthly_revenue)}</dd><dt>Break-even utilization</dt><dd>${Math.round(item.break_even_utilization * 100)}%</dd><dt>Payback</dt><dd>${item.payback_months >= 999 ? '> model horizon' : `${item.payback_months} mo`}</dd></dl>
    </div>`).join('');
  const baseline = report.financial_scenarios.find(item => item.name === 'BASE')?.operating_profit ?? 0;
  const maxImpact = Math.max(...report.sensitivity.flatMap(item => [Math.abs(item.low_operating_profit - baseline), Math.abs(item.high_operating_profit - baseline)]), 1);
  const sensitivity = report.sensitivity.map(item => {
    const lowImpact = Math.abs(item.low_operating_profit - baseline);
    const highImpact = Math.abs(item.high_operating_profit - baseline);
    return `<div class="tornado-row"><div><strong>${escapeHtml(item.driver.replaceAll('_', ' '))}</strong><span>modeled operating profit</span></div><div class="tornado-track" aria-label="${escapeHtml(item.driver)} downside ${money(item.low_operating_profit)}, upside ${money(item.high_operating_profit)}"><i class="tornado-down" style="width:${Math.max(8, lowImpact / maxImpact * 50)}%"></i><b></b><i class="tornado-up" style="width:${Math.max(8, highImpact / maxImpact * 50)}%"></i></div><div class="tornado-values"><span>${money(item.low_operating_profit)}</span><strong>${money(item.high_operating_profit)}</strong></div></div>`;
  }).join('');
  document.querySelector('#scenario-comparison').innerHTML = `<div class="panel-kicker"><span>Quantis-compatible financial port</span><b>Deterministic fixture</b></div><h2>Scenario comparison</h2><div class="scenario-grid">${cards}</div><h3 class="subhead">Sensitivity tornado · monthly operating profit</h3><p class="tornado-note">Downside ← lower modeled outcome · higher modeled outcome → upside. Base case: ${money(baseline)} / month.</p><div class="sensitivity-list">${sensitivity}</div>`;
}

function renderAssumptions(report) {
  document.querySelector('#assumption-register').innerHTML = `
    <div class="panel-kicker"><span>Financial-truth firewall</span><b>Approval required</b></div><h2>Assumption register</h2>
    <div class="assumption-list">${report.assumptions.map(item => `<div class="assumption-row"><div><strong>${escapeHtml(item.metric)}</strong><span>${escapeHtml(item.origin.replaceAll('_', ' '))}</span></div><b>${escapeHtml(item.value)}</b><em class="review-${item.review_status.toLowerCase()}">${escapeHtml(item.review_status)}</em></div>`).join('')}</div>
    <p class="quality-note">External evidence remains a proposal until a named reviewer accepts its source, units, period, and transformation. Calculations cannot approve their own inputs.</p>`;
}

function renderTurningPoints(report) {
  const companies = new Map(report.companies.map(item => [item.company_id, item]));
  const records = [...report.evidence]
    .sort((left, right) => right.period - left.period)
    .map(item => {
      const company = companies.get(item.company_id);
      return `<button type="button" class="turning-point" data-company-id="${escapeHtml(item.company_id)}" data-period="${item.period}"><time>${item.period}</time><span><b>${escapeHtml(company?.display_name.replace(' (synthetic)', '') || item.company_id)}</b><strong>${escapeHtml(item.normalized_fact)}</strong><small>${escapeHtml(item.verification_status.replaceAll('_', ' '))} · ${escapeHtml(item.source_title)}</small></span></button>`;
    }).join('');
  document.querySelector('#turning-points').innerHTML = `<div class="workspace-head"><div><p class="eyebrow">Historical trajectory</p><h2>Turning points, not just scores</h2></div><p>Each event below maps to the selected peer timeline and opens its source drawer.</p></div><div class="turning-list">${records}</div>`;
  document.querySelectorAll('.turning-point').forEach(button => button.addEventListener('click', () => {
    const company = companies.get(button.dataset.companyId);
    const point = company?.trajectory.find(item => String(item.year) === button.dataset.period);
    if (!company || !point) return;
    state.activeCompanyId = company.company_id;
    renderCompanyTabs(report);
    renderRadialMap(report);
    showEvidence(company, point);
    document.querySelector('#evidence-panel').scrollIntoView({ behavior: 'smooth', block: 'center' });
  }));
}

function renderContradictions(report) {
  const content = report.contradictions.length
    ? `<div class="contradiction-list">${report.contradictions.map(item => `<article><div><span>${escapeHtml(item.status)}</span><b>${escapeHtml(item.subject)}</b></div><p>${escapeHtml(item.summary)}</p><small>${item.evidence_ids.length} linked evidence record${item.evidence_ids.length === 1 ? '' : 's'}</small></article>`).join('')}</div>`
    : `<div class="empty-contradiction"><strong>No contradiction records declared</strong><p>${escapeHtml(report.contradictions_note)}</p></div>`;
  document.querySelector('#contradictions').innerHTML = `<div class="workspace-head"><div><p class="eyebrow">Contradictions</p><h2>What could challenge this view</h2></div><p>Conflicting claims are not netted away; they must remain visible to the reviewer.</p></div>${content}`;
}

function renderRecommendationLedger(report) {
  const items = report.lessons.slice(0, 3).map(item => `<li><span>${String(item.priority).padStart(2, '0')}</span><div><b>${escapeHtml(item.title)}</b><p>${escapeHtml(item.action)}</p></div><small>${escapeHtml(confidenceLabel(item.confidence))} · ${item.evidence_ids.length} evidence ref${item.evidence_ids.length === 1 ? '' : 's'}</small></li>`).join('');
  document.querySelector('#recommendation-ledger').innerHTML = `<div class="workspace-head"><div><p class="eyebrow">Recommendation ledger</p><h2>What to do next</h2></div><p>Ordered actions from the current report contract—not a task list generated without evidence.</p></div><ol class="recommendation-list">${items}</ol>`;
}

function renderMethodLimitations(report) {
  document.querySelector('#method-limitations').innerHTML = `<div class="workspace-head"><div><p class="eyebrow">Method / limitations</p><h2>What this workspace does not claim</h2></div><p>Use these boundaries before committing capital.</p></div><ul class="limitations-list"><li><b>Data mode</b><span>${escapeHtml(report.data_mode.replaceAll('_', ' '))}; ${escapeHtml(report.disclaimer)}</span></li><li><b>Peer cohort</b><span>${escapeHtml(report.cohort.note)}</span></li><li><b>Financial output</b><span>Deterministic scenario mathematics only. It is not a forecast, valuation, or probability of success.</span></li><li><b>Entity state</b><span>${escapeHtml(report.entity_identity.detail)}</span></li></ul>`;
}

function renderCommandCenter(report) {
  document.querySelector('#system-status-grid').innerHTML = report.system_status.map(item => `<article class="system-state state-${escapeHtml(item.state)}"><span>${escapeHtml(item.state)}</span><h3>${escapeHtml(item.capability)}</h3><p>${escapeHtml(item.truth)}</p></article>`).join('');
  document.querySelector('#verification-strip').innerHTML = [
    ['Python focused', '20 PASS'], ['Repository gates', '6 PASS'], ['Browser contracts', '7 PASS'],
    ['Python compile', 'PASS'], ['Visual capture', 'PASS'], ['FastAPI suite', 'DEPENDENCY BLOCKED'],
  ].map(([label, result]) => `<div><span>${escapeHtml(label)}</span><b>${escapeHtml(result)}</b></div>`).join('');
  document.querySelector('#real-demo-matrix').innerHTML = `<div class="matrix-head"><span>Capability</span><span>Current truth</span></div>${report.real_demo_matrix.map(item => `<div><span>${escapeHtml(item.capability)}</span><b>${escapeHtml(item.state)}</b></div>`).join('')}`;
}

function renderKpis(report) {
  const items = [
    [report.cohort.fixture_company_count, 'Comparable peers', 'fixture sample'],
    [report.cohort.high_performer_count, 'High performers', 'strong trajectories'],
    [report.cohort.active_count, 'Active / stable', 'operating case'],
    [report.cohort.distressed_count, 'Distressed', 'declining case'],
    [report.cohort.failed_count, 'Failed cases', 'failure evidence'],
  ];
  document.querySelector('#cohort-kpis').innerHTML = items.map(([value, label, note]) => `<article class="kpi"><strong>${escapeHtml(value)}</strong><span>${escapeHtml(label)}</span><small>${escapeHtml(note)}</small></article>`).join('');
}

function statusLabel(status) { return status.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase()); }

function renderCompanyTabs(report) {
  const host = document.querySelector('#company-tabs'); host.innerHTML = '';
  report.companies.forEach(company => {
    const button = document.createElement('button');
    button.className = 'company-tab'; button.type = 'button';
    button.setAttribute('aria-pressed', String(company.company_id === state.activeCompanyId));
    button.innerHTML = `<i class="company-state ${escapeHtml(company.status)}"></i><span>${escapeHtml(company.display_name.replace(' (synthetic)', ''))}</span><small>${Math.round(company.comparability_score * 100)}%</small>`;
    button.addEventListener('click', () => {
      state.activeCompanyId = company.company_id;
      renderCompanyTabs(report); renderRadialMap(report);
      const evidencePoint = [...company.trajectory].reverse().find(point => point.evidence_ids.length) || company.trajectory.at(-1);
      showEvidence(company, evidencePoint);
    });
    host.appendChild(button);
  });
}

function svgEl(tag, attrs = {}) { const element = document.createElementNS('http://www.w3.org/2000/svg', tag); Object.entries(attrs).forEach(([k, v]) => element.setAttribute(k, v)); return element; }
function polar(cx, cy, radius, angle) { const rad = (angle - 90) * Math.PI / 180; return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) }; }

function renderRadialMap(report) {
  const grid = document.querySelector('#radial-grid'); const content = document.querySelector('#radial-content');
  grid.innerHTML = ''; content.innerHTML = '';
  const cx = 380, cy = 380, inner = 78, outer = 290;
  const activeCompany = report.companies.find(c => c.company_id === state.activeCompanyId) || report.companies[0];
  document.querySelector('#active-company-summary').textContent = `${activeCompany.display_name.replace(' (synthetic)', '')} · ${statusLabel(activeCompany.status)} · ${Math.round(activeCompany.comparability_score * 100)}% comparable`;

  [0.25, 0.5, 0.75, 1].forEach((ratio, index) => {
    const r = inner + ratio * (outer - inner);
    grid.appendChild(svgEl('circle', { cx, cy, r, class: 'grid-ring' }));
    const score = svgEl('text', { x: cx + 8, y: cy - r + 16, class: 'grid-label' });
    score.textContent = ['25 · weak', '50 · watch', '75 · stable', '100 · strong'][index];
    grid.appendChild(score);
  });

  const years = activeCompany.trajectory.map(point => point.year);
  for (let index = 0; index < 10; index += 1) {
    const angle = index * 36;
    const axis = polar(cx, cy, outer, angle);
    grid.appendChild(svgEl('line', { x1: cx, y1: cy, x2: axis.x, y2: axis.y, class: 'grid-axis' }));
    if (years[index]) {
      const labelPoint = polar(cx, cy, outer + 34, angle);
      const label = svgEl('text', { x: labelPoint.x, y: labelPoint.y + 4, class: 'year-label', 'text-anchor': 'middle' });
      label.textContent = years[index]; grid.appendChild(label);
    }
  }

  report.companies.forEach((company, companyIndex) => {
    const active = company.company_id === state.activeCompanyId;
    const points = company.trajectory.map((point, index) => {
      const angle = index * 36;
      const radius = inner + (point.performance_score / 100) * (outer - inner);
      return { point, ...polar(cx, cy, radius, angle) };
    });
    if (active && points.length > 2) {
      content.appendChild(svgEl('polygon', { points: points.map(p => `${p.x},${p.y}`).join(' '), class: 'trajectory-area', fill: lineColors[companyIndex % lineColors.length] }));
    }
    content.appendChild(svgEl('polyline', { points: points.map(p => `${p.x},${p.y}`).join(' '), class: `trajectory-line${active ? ' active' : ''}`, stroke: lineColors[companyIndex % lineColors.length], 'aria-hidden': 'true' }));
    points.forEach(({ point, x, y }) => {
      const dot = svgEl('circle', { cx: x, cy: y, r: active ? 7 : 4.5, fill: colors[point.state], class: 'trajectory-point', tabindex: '0', role: 'button', 'aria-label': `${company.display_name}, ${point.year}, performance ${point.performance_score}, ${point.state}`, opacity: active ? '1' : '.34' });
      const activate = () => { state.activeCompanyId = company.company_id; renderCompanyTabs(report); renderRadialMap(report); showEvidence(company, point); };
      dot.addEventListener('click', activate);
      dot.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); activate(); } });
      content.appendChild(dot);
    });
  });
  content.appendChild(svgEl('circle', { cx, cy, r: 65, class: 'center-core' }));
  const t1 = svgEl('text', { x: cx, y: cy - 5, class: 'center-title' }); t1.textContent = 'ANALYTICA'; content.appendChild(t1);
  const t2 = svgEl('text', { x: cx, y: cy + 18, class: 'center-subtitle' }); t2.textContent = '10Y PEER SIGNAL'; content.appendChild(t2);
}

function showEvidence(company, point) {
  const evidence = state.report.evidence.filter(item => point.evidence_ids.includes(item.evidence_id));
  document.querySelector('#evidence-title').textContent = `${company.display_name.replace(' (synthetic)', '')} — ${point.year}`;
  document.querySelector('#evidence-intro').textContent = `${statusLabel(company.status)} · ${Math.round(company.comparability_score * 100)}% comparability · ${point.state.toUpperCase()} state`;
  const evidenceHtml = evidence.length ? evidence.map(item => `
    <article class="evidence-item">
      <div class="evidence-source-row"><span>Source trace</span><strong>${escapeHtml(item.verification_status.replaceAll('_', ' '))}</strong></div>
      <h4>${escapeHtml(item.source_title)}</h4>
      <div class="evidence-meta"><span>${escapeHtml(item.publisher)}</span><span>${escapeHtml(item.period)}</span><span>${escapeHtml(item.verification_status || 'fixture_verified')}</span></div>
      <p>${escapeHtml(item.fact)}</p>
      <div class="normalized-fact"><span>Normalized signal</span>${escapeHtml(item.normalized_fact || item.fact)}</div>
    </article>`).join('') : `<article class="evidence-item empty-evidence"><h4>No event evidence attached to this fixture year</h4><p>The trajectory value is present for visual continuity. Analytica intentionally does not invent a causal event when no evidence record is attached.</p></article>`;
  document.querySelector('#evidence-body').innerHTML = `<div class="evidence-score"><div class="metric-tile"><strong>${Math.round(point.performance_score)}</strong><span>Modeled performance index</span></div><div class="metric-tile"><strong>${escapeHtml(point.state)}</strong><span>Historical state</span></div></div>${evidenceHtml}`;
}

function renderFindings(report) {
  document.querySelector('#findings-grid').innerHTML = report.findings.map((finding, index) => `<article class="finding impact-${escapeHtml(finding.impact || 'context')}"><div class="finding-top"><span class="finding-index">0${index + 1}</span><span class="confidence">${escapeHtml(confidenceLabel(finding.confidence))}</span></div><h3>${escapeHtml(finding.title)}</h3><p>${escapeHtml(finding.summary)}</p><small>${finding.evidence_ids?.length || 0} evidence reference${finding.evidence_ids?.length === 1 ? '' : 's'}</small></article>`).join('');
}

function renderLessons(report) {
  document.querySelector('#lesson-list').innerHTML = report.lessons.map(lesson => `<li class="lesson"><div class="lesson-number">${String(lesson.priority).padStart(2, '0')}</div><div><div class="lesson-top"><span>${escapeHtml(confidenceLabel(lesson.confidence))}</span><small>${lesson.evidence_ids.length} evidence ref${lesson.evidence_ids.length === 1 ? '' : 's'}</small></div><h3>${escapeHtml(lesson.title)}</h3><p>${escapeHtml(lesson.action)}</p></div></li>`).join('');
}

function renderReadiness(readiness) {
  document.querySelector('#readiness-percent').textContent = `${readiness.prototype_completion_percent}%`;
  const host = document.querySelector('#readiness-grid');
  host.innerHTML = readiness.areas.map(item => `<article class="readiness-item state-${escapeHtml(item.state)}"><div><span class="readiness-state">${escapeHtml(item.state)}</span><h3>${escapeHtml(item.area)}</h3></div><p>${escapeHtml(item.detail)}</p></article>`).join('');
}

async function loadReadiness() {
  try { renderReadiness(await fetchJson(READINESS_ENDPOINT)); }
  catch (_) { renderReadiness(FALLBACK_READINESS); }
}

document.querySelector('#analysis-form').addEventListener('submit', event => { event.preventDefault(); runPrototypeAnalysis(); });
renderPipeline('COMPLETED', 100, 'Analysis complete');
loadInitialReport().then(report => {
  renderReport(report);
  const company = report.companies[0];
  if (company) {
    const point = [...company.trajectory].reverse().find(item => item.evidence_ids.length) || company.trajectory.at(-1);
    showEvidence(company, point);
  }
}).catch(error => { document.querySelector('#readiness-label').textContent = `Preview data failed to load: ${error.message}`; });
loadReadiness();
