const API_BASE = window.ANALYTICA_API_BASE || '';
const ACTIONS = {
  APPROVE_ENTITY: 'APPROVE_ENTITY', REJECT_ENTITY: 'REJECT_ENTITY',
  REQUEST_ADDITIONAL_RESEARCH: 'REQUEST_ADDITIONAL_RESEARCH',
  ACCEPT_ASSUMPTION: 'ACCEPT_ASSUMPTION', REJECT_ASSUMPTION: 'REJECT_ASSUMPTION',
  EDIT_RECOMMENDATION: 'EDIT_RECOMMENDATION', RETURN_FOR_REVISION: 'RETURN_FOR_REVISION',
  APPROVE_DELIVERY: 'APPROVE_DELIVERY', REJECT_DELIVERY: 'REJECT_DELIVERY',
};
const state = { inspection: null };
const $ = (selector) => document.querySelector(selector);
const escapeHtml = (value) => String(value ?? '').replace(/[&<>'"]/g, (ch) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' }[ch]));
const label = (value) => String(value ?? '').replaceAll('_', ' ').replace(/\b\w/g, (letter) => letter.toUpperCase());
const money = (value) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 }).format(value || 0);
const apiUrl = (path) => `${API_BASE}${path}`;

async function request(path, options = {}) {
  const response = await fetch(apiUrl(path), { cache: 'no-store', ...options });
  if (!response.ok) {
    let detail = `${response.status}`;
    try { const body = await response.json(); detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail); } catch (_) { /* Preserve HTTP status. */ }
    throw new Error(detail);
  }
  return response.json();
}

function reviewerId() { return $('#reviewer-id').value.trim(); }
function caseId() { return $('#case-id').value.trim(); }
function message(text = '', error = false) { const host = $('#review-message'); host.textContent = text; host.style.color = error ? '#8b423a' : '#186447'; }
function actionControls(actions) { return `<div class="action-row">${actions.map(([action, text, danger = false, extra = '']) => `<button type="button" class="${danger ? 'danger' : ''}" data-action="${action}" ${extra}>${text}</button>`).join('')}</div>`; }

function renderGate(inspection) {
  const gate = inspection.delivery_gate;
  $('#review-gate').className = `review-gate ${gate.eligible ? 'eligible' : ''}`;
  $('#review-gate').innerHTML = `<div><p class="eyebrow">Delivery status · human QA gate</p><h2 id="review-gate-title">${escapeHtml(label(inspection.case.delivery_status))}</h2><p>${gate.eligible ? 'All mechanical controls pass. A named reviewer may now explicitly approve delivery.' : 'This case is blocked. Correct the listed evidence, approval, or financial condition before delivery.'}</p>${gate.blockers.length ? `<ul class="gate-list">${gate.blockers.map((blocker) => `<li>${escapeHtml(blocker)}</li>`).join('')}</ul>` : ''}</div><span class="gate-state">${gate.eligible ? 'READY FOR HUMAN QA' : `${gate.blockers.length} BLOCKER${gate.blockers.length === 1 ? '' : 'S'}`}</span>`;
}

function renderCase(inspection) {
  const c = inspection.case; const entity = c.entity;
  $('#review-case').innerHTML = `<div class="panel-kicker"><span>Case / entity</span><b>${escapeHtml(label(c.entity_review_status))}</b></div><h2>${escapeHtml(c.case_id)}</h2><ul class="case-list"><li><small>Entity decision</small><b>${escapeHtml(label(entity.status))}</b></li><li><small>Canonical entity</small><b>${escapeHtml(entity.entity_id || 'Not resolved')}</b></li><li><small>Entity reviewer</small><b>${escapeHtml(c.entity_reviewer_id || 'Not approved')}</b></li><li><small>Delivery status</small><b>${escapeHtml(label(c.delivery_status))}</b></li></ul>${actionControls([[ACTIONS.APPROVE_ENTITY, 'Approve entity'], [ACTIONS.REJECT_ENTITY, 'Reject entity', true], [ACTIONS.REQUEST_ADDITIONAL_RESEARCH, 'Request research'], [ACTIONS.RETURN_FOR_REVISION, 'Return for revision']])}`;
}

function renderEvidence(inspection) {
  const packets = inspection.packets; const fullPackets = inspection.evidence_packets || [];
  const packetHtml = packets.length ? packets.map((packet) => {
    const full = fullPackets.find((item) => item.packet_id === packet.packet_id);
    const sources = full?.sources || []; const claims = full?.claims || []; const contradictions = full?.contradictions || [];
    return `<div class="packet"><div class="packet-head"><span>${escapeHtml(packet.packet_id)}</span><b class="${packet.hash_valid ? 'valid' : 'invalid'}">${packet.hash_valid ? 'HASH VALID' : 'HASH INVALID'}</b></div><small>${packet.source_count} sources · ${packet.passage_count} passages · ${packet.claim_count} claims · ${packet.contradiction_count} contradictions</small>${sources.length ? `<div class="source-list">${sources.map((source) => `<article class="source-card"><a href="${escapeHtml(source.canonical_url)}" target="_blank" rel="noreferrer">${escapeHtml(source.title)} ↗</a><small>${escapeHtml(source.provider_id)} · ${escapeHtml(source.publisher)} · retrieved ${escapeHtml(source.snapshot.retrieved_at)}</small></article>`).join('')}</div>` : '<p class="empty">No source records are attached to this case.</p>'}${claims.map((claim) => `<article class="claim-card"><strong>${escapeHtml(claim.claim_id)} · ${escapeHtml(label(claim.status))}</strong><p>${escapeHtml(claim.statement)}</p><small>${claim.evidence.length} evidence link${claim.evidence.length === 1 ? '' : 's'} · ${claim.independent_source_count} independent source${claim.independent_source_count === 1 ? '' : 's'}</small></article>`).join('')}${contradictions.map((item) => `<article class="contradiction-card"><strong>Contradiction · ${escapeHtml(item.claim_id)}</strong><p>${escapeHtml(item.explanation)}</p><small>${item.supporting_passage_ids.length} supporting / ${item.contradicting_passage_ids.length} conflicting passages</small></article>`).join('')}</div>`;
  }).join('') : '<p class="empty">No EvidencePacket is attached. This case cannot be delivered.</p>';
  $('#review-evidence').innerHTML = `<div class="panel-kicker"><span>Providers / evidence / contradictions</span><b>${inspection.providers.length} PROVIDER${inspection.providers.length === 1 ? '' : 'S'}</b></div><h2>Evidence packet inspection</h2><div class="provider-strip">${inspection.providers.length ? inspection.providers.map((provider) => `<span>${escapeHtml(provider)}</span>`).join('') : '<span>None attached</span>'}</div>${packetHtml}`;
}

function renderAssumptions(inspection) {
  const assumptions = inspection.case.assumptions || [];
  $('#review-assumptions').innerHTML = `<div class="panel-kicker"><span>Assumptions</span><b>FIREWALL CONTROLLED</b></div><h2>Input review</h2>${assumptions.length ? assumptions.map((item) => `<div class="assumption-row"><div><h3>${escapeHtml(item.metric)} · ${escapeHtml(item.value)} ${escapeHtml(item.unit)}</h3><p>${escapeHtml(label(item.origin))} · ${escapeHtml(item.period)}<br>${escapeHtml(item.transformation)}</p><small>Source claims: ${item.source_claim_ids.map(escapeHtml).join(', ') || 'none'}</small></div><div><span class="assumption-status">${escapeHtml(label(item.review_status))}</span>${item.review_status === 'PROPOSED' ? actionControls([[ACTIONS.ACCEPT_ASSUMPTION, 'Accept', false, `data-assumption-id="${escapeHtml(item.assumption_id)}"`], [ACTIONS.REJECT_ASSUMPTION, 'Reject', true, `data-assumption-id="${escapeHtml(item.assumption_id)}"`]]) : `<small>${escapeHtml(item.reviewer_id || 'No reviewer')}<br>${escapeHtml(item.reviewed_at || '')}</small>`}</div></div>`).join('') : '<p class="empty">No proposed financial assumptions are attached.</p>'}`;
}

function renderFinancials(inspection) {
  const results = inspection.case.financial_results || [];
  $('#review-financials').innerHTML = `<div class="panel-kicker"><span>Quantis financial results</span><b>${results.length} RESULT${results.length === 1 ? '' : 'S'}</b></div><h2>Reconciliation</h2>${results.length ? results.map((item) => `<article class="result-card"><div><strong>${escapeHtml(item.name)} · ${escapeHtml(item.model_version)}</strong><p class="${item.reconciliation.passed ? 'pass' : 'fail'}">${item.reconciliation.passed ? 'RECONCILIATION PASSED' : 'RECONCILIATION FAILED'} · variance ${escapeHtml(item.reconciliation.variance)}</p></div><b>${money(item.operating_profit)} / mo</b><dl><div><dt>Revenue</dt><dd>${money(item.monthly_revenue)}</dd></div><div><dt>Break-even</dt><dd>${Math.round(item.break_even_utilization * 100)}%</dd></div><div><dt>Payback</dt><dd>${item.payback_months >= 999 ? 'Beyond horizon' : `${item.payback_months} mo`}</dd></div></dl></article>`).join('') : '<p class="empty">No Quantis result is attached. Delivery is blocked.</p>'}`;
}

function renderFindings(inspection) {
  const findings = inspection.case.findings || [];
  $('#review-findings').innerHTML = `<div class="panel-kicker"><span>Findings</span><b>${findings.length} LINKED</b></div><h2>Decision basis</h2>${findings.length ? `<ul class="inspection-list">${findings.map((item) => `<li><small>Finding</small><b>${escapeHtml(item)}</b></li>`).join('')}</ul>` : '<p class="empty">No finding IDs are attached. Validate lineage before adding a recommendation.</p>'}`;
}

function renderRecommendation(inspection) {
  const c = inspection.case;
  $('#review-recommendation').innerHTML = `<div class="panel-kicker"><span>Recommendation ledger</span><b>${c.reviewer_recommendation ? 'REVIEWER EDITED' : 'SOURCE TEXT'}</b></div><h2>Delivery recommendation</h2><div class="recommendation-copy"><strong>Source fact / original recommendation</strong><p>${escapeHtml(c.source_recommendation)}</p></div>${c.reviewer_recommendation ? `<div class="recommendation-copy"><strong>Reviewer wording</strong><p>${escapeHtml(c.reviewer_recommendation)}</p></div>` : ''}<div class="action-notes"><label class="field-label" for="recommendation-text">Reviewer wording — does not alter source facts</label><textarea id="recommendation-text" placeholder="Clarify the recommendation for the customer; source evidence stays unchanged."></textarea><button type="button" data-action="${ACTIONS.EDIT_RECOMMENDATION}">Save reviewer wording</button></div>`;
}

function renderDelivery(inspection) {
  const c = inspection.case;
  $('#review-delivery').innerHTML = `<div class="panel-kicker"><span>Delivery status</span><b>${escapeHtml(label(c.delivery_status))}</b></div><h2>Final QA</h2><p class="empty">A delivery approval is itself the mandatory human-QA action. It is refused until the gate above passes.</p><div class="action-notes"><label class="field-label" for="action-reason">Reason / reviewer note (required for rejection, research, and revision)</label><input id="action-reason" placeholder="State the reason for this audit action" /></div><div class="delivery-actions">${actionControls([[ACTIONS.APPROVE_DELIVERY, 'Approve delivery'], [ACTIONS.REJECT_DELIVERY, 'Reject delivery', true]])}</div><small>QA approver: ${escapeHtml(c.qa_approved_by || 'not approved')}</small>`;
}

function renderAudit(inspection) {
  const actions = inspection.audit_actions || [];
  $('#review-audit').innerHTML = `<div class="panel-kicker"><span>Audit history</span><b>APPEND-ONLY</b></div><h2>Reviewer actions</h2>${actions.length ? `<ol class="audit-list">${actions.map((item) => `<li><b>${escapeHtml(label(item.action_type))} · ${escapeHtml(item.reviewer_id)}</b><span>${escapeHtml(item.occurred_at)}${item.reason ? ` · ${escapeHtml(item.reason)}` : ''}${item.assumption_id ? ` · ${escapeHtml(item.assumption_id)}` : ''}</span></li>`).join('')}</ol>` : '<p class="empty">No QA actions have been recorded.</p>'}`;
}

function render(inspection) { state.inspection = inspection; renderGate(inspection); renderCase(inspection); renderEvidence(inspection); renderAssumptions(inspection); renderFinancials(inspection); renderFindings(inspection); renderRecommendation(inspection); renderDelivery(inspection); renderAudit(inspection); }

async function loadCase() { const id = caseId(); if (!id) return; message('Loading case…'); try { render(await request(`/review/cases/${encodeURIComponent(id)}`)); message('Case loaded.'); } catch (error) { message(`Could not load case: ${error.message}`, true); } }
function actionData(button) { const action = button.dataset.action; return { action_type: action, reviewer_id: reviewerId(), reason: $('#action-reason')?.value.trim() || undefined, assumption_id: button.dataset.assumptionId || undefined, recommendation_text: $('#recommendation-text')?.value.trim() || undefined }; }
async function applyAction(button) { if (!caseId() || !reviewerId()) { message('Case ID and reviewer are required.', true); return; } const data = actionData(button); button.disabled = true; message(`Recording ${label(data.action_type)}…`); try { render(await request(`/review/cases/${encodeURIComponent(caseId())}/actions`, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(data) })); message(`${label(data.action_type)} recorded in the audit history.`); } catch (error) { message(`Action not recorded: ${error.message}`, true); } finally { button.disabled = false; } }

$('#review-loader').addEventListener('submit', (event) => { event.preventDefault(); loadCase(); });
document.addEventListener('click', (event) => { const button = event.target.closest('[data-action]'); if (button) applyAction(button); });
loadCase();
