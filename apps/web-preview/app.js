const API_BASE = window.ANALYTICA_API_BASE || 'http://127.0.0.1:8000';
const API_ENDPOINT = `${API_BASE}/analyses/demo_packaging_ny_v1`;
const CREATE_ENDPOINT = `${API_BASE}/analyses`;
const state = { report: null, activeCompanyId: null };
const colors = { green: '#63db9d', blue: '#67a7ff', yellow: '#edc965', red: '#ff786f' };
const lineColors = ['#8df0c6', '#7da9ff', '#f2ca69', '#ff817a', '#b58cff'];

async function loadReport() {
  try {
    const response = await fetch(API_ENDPOINT, { cache: 'no-store' });
    if (!response.ok) throw new Error(`API returned ${response.status}`);
    return await response.json();
  } catch (error) {
    if (window.__ANALYTICA_DEMO_REPORT__) return window.__ANALYTICA_DEMO_REPORT__;
    throw error;
  }
}

async function createAnalysis() {
  const business_activity = document.querySelector('#business').value.trim();
  const geography = document.querySelector('#geography').value.trim();
  try {
    await fetch(CREATE_ENDPOINT, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ business_activity, geography }),
    });
  } catch (_) {
    // The self-contained R&D preview remains usable through its deterministic fixture.
  }
  renderReport(await loadReport());
  document.querySelector('#analysis-summary').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function renderReport(report) {
  state.report = report;
  state.activeCompanyId = state.activeCompanyId || report.companies[0]?.company_id;
  document.querySelector('#summary-title').textContent = `${report.business_activity} — ${report.geography}`;
  document.querySelector('#readiness-label').textContent = report.readiness_label;
  document.querySelector('#report-disclaimer').textContent = report.disclaimer;
  renderKpis(report); renderCompanyTabs(report); renderRadialMap(report); renderFindings(report); renderLessons(report);
}

function renderKpis(report) {
  const items = [[report.cohort.fixture_company_count,'Synthetic peers'],[report.cohort.high_performer_count,'High performers'],[report.cohort.active_count,'Active / stable'],[report.cohort.distressed_count,'Distressed'],[report.cohort.failed_count,'Failed cases']];
  document.querySelector('#cohort-kpis').innerHTML = items.map(([value,label]) => `<article class="kpi"><strong>${value}</strong><span>${label}</span></article>`).join('');
}

function renderCompanyTabs(report) {
  const host = document.querySelector('#company-tabs'); host.innerHTML = '';
  report.companies.forEach((company) => {
    const button = document.createElement('button');
    button.className='company-tab'; button.type='button';
    button.setAttribute('aria-pressed', String(company.company_id === state.activeCompanyId));
    button.textContent=company.display_name.replace(' (synthetic)','');
    button.addEventListener('click', () => {
      state.activeCompanyId=company.company_id; renderCompanyTabs(report); renderRadialMap(report);
      showEvidence(company, company.trajectory[company.trajectory.length-1]);
    });
    host.appendChild(button);
  });
}

function svgEl(tag, attrs={}) { const element=document.createElementNS('http://www.w3.org/2000/svg',tag); Object.entries(attrs).forEach(([k,v])=>element.setAttribute(k,v)); return element; }
function polar(cx,cy,radius,angle){const rad=(angle-90)*Math.PI/180;return{x:cx+radius*Math.cos(rad),y:cy+radius*Math.sin(rad)}}

function renderRadialMap(report) {
  const grid=document.querySelector('#radial-grid'); const content=document.querySelector('#radial-content'); grid.innerHTML=''; content.innerHTML='';
  const cx=360,cy=360,inner=80,outer=292;
  [100,148,196,244,292].forEach((r,index)=>{grid.appendChild(svgEl('circle',{cx,cy,r,class:'grid-ring'})); const label=svgEl('text',{x:cx+7,y:cy-r+15,class:'grid-label'}); label.textContent=['20','40','60','80','100'][index]; grid.appendChild(label);});
  for(let angle=0;angle<360;angle+=45){const p=polar(cx,cy,outer,angle);grid.appendChild(svgEl('line',{x1:cx,y1:cy,x2:p.x,y2:p.y,class:'grid-axis'}));}
  report.companies.forEach((company,companyIndex)=>{
    const active=company.company_id===state.activeCompanyId;
    const points=company.trajectory.map((point,index)=>{const angle=index*(360/10);const radius=inner+(point.performance_score/100)*(outer-inner);return{point,...polar(cx,cy,radius,angle)}});
    content.appendChild(svgEl('polyline',{points:points.map(p=>`${p.x},${p.y}`).join(' '),class:`trajectory-line${active?' active':''}`,stroke:lineColors[companyIndex%lineColors.length],'aria-hidden':'true'}));
    points.forEach(({point,x,y})=>{
      const dot=svgEl('circle',{cx:x,cy:y,r:active?7:5,fill:colors[point.state],class:'trajectory-point',tabindex:'0',role:'button','aria-label':`${company.display_name}, ${point.year}, performance ${point.performance_score}, ${point.state}`,opacity:active?'1':'.45'});
      const activate=()=>{state.activeCompanyId=company.company_id;renderCompanyTabs(report);renderRadialMap(report);showEvidence(company,point)};
      dot.addEventListener('click',activate); dot.addEventListener('keydown',(event)=>{if(event.key==='Enter'||event.key===' '){event.preventDefault();activate();}}); content.appendChild(dot);
    });
  });
  content.appendChild(svgEl('circle',{cx,cy,r:67,class:'center-core'}));
  const t1=svgEl('text',{x:cx,y:cy-4,class:'center-title'});t1.textContent='ANALYTICA';content.appendChild(t1);
  const t2=svgEl('text',{x:cx,y:cy+17,class:'center-subtitle'});t2.textContent='10Y SIGNAL';content.appendChild(t2);
}

function confidenceLabel(value){return value.replaceAll('_',' ').replace(/\b\w/g,c=>c.toUpperCase())}

function showEvidence(company,point){
  const evidence=state.report.evidence.filter(item=>point.evidence_ids.includes(item.evidence_id));
  document.querySelector('#evidence-title').textContent=`${company.display_name.replace(' (synthetic)','')} — ${point.year}`;
  document.querySelector('#evidence-intro').textContent=`${company.status.replace('_',' ')} · comparability ${Math.round(company.comparability_score*100)}%`;
  document.querySelector('#evidence-body').innerHTML=`<div class="evidence-score"><div class="metric-tile"><strong>${Math.round(point.performance_score)}</strong><span>Performance / 100</span></div><div class="metric-tile"><strong>${Math.round(point.risk_score*100)}%</strong><span>Modeled risk</span></div></div>${evidence.length?evidence.map(item=>`<article class="evidence-item"><h4>${item.source_title}</h4><div class="evidence-meta"><span>${item.publisher}</span><span>${item.period}</span><span>${Math.round(item.confidence*100)}% source confidence</span></div><p>${item.fact}</p></article>`).join(''):'<article class="evidence-item"><h4>No event evidence attached to this fixture year</h4><p>The trajectory value is present for visual continuity, but this R&D fixture intentionally does not invent a causal event for every year.</p></article>'}`;
}

function renderFindings(report){document.querySelector('#findings-grid').innerHTML=report.findings.map(f=>`<article class="finding"><span class="confidence">${confidenceLabel(f.confidence)}</span><h3>${f.title}</h3><p>${f.summary}</p></article>`).join('')}
function renderLessons(report){document.querySelector('#lesson-list').innerHTML=report.lessons.map(lesson=>`<li class="lesson"><div><h3>${lesson.title}</h3><p>${lesson.action}</p><small>${confidenceLabel(lesson.confidence)} · ${lesson.evidence_ids.length} evidence reference${lesson.evidence_ids.length===1?'':'s'}</small></div></li>`).join('')}

document.querySelector('#analysis-form').addEventListener('submit',(event)=>{event.preventDefault();createAnalysis();});
loadReport().then(report=>{renderReport(report);const company=report.companies[0];if(company)showEvidence(company,company.trajectory[company.trajectory.length-1]);}).catch(error=>{document.querySelector('#readiness-label').textContent=`Preview data failed to load: ${error.message}`;});
