from __future__ import annotations

import math
import sys
import textwrap
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.app.fixtures import build_demo_report  # noqa: E402
from apps.api.app.readiness import build_readiness  # noqa: E402

W, H = 1440, 1800
BG = "#061011"
SURFACE = "#0b191a"
SURFACE2 = "#102224"
LINE = "#203234"
TEXT = "#f1f8f5"
MUTED = "#8aa5a1"
FAINT = "#58736f"
ACCENT = "#8df0c6"
GREEN = "#64e0a3"
BLUE = "#6ca7ff"
YELLOW = "#f1c85e"
RED = "#ff756f"
VIOLET = "#c79aff"


def t(x: float, y: float, text: str, size=18, fill=TEXT, weight=500, anchor="start", cls="") -> str:
    return f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" font-weight="{weight}" text-anchor="{anchor}" class="{cls}">{escape(str(text))}</text>'


def rounded(x, y, w, h, r=18, fill=SURFACE, stroke=LINE, sw=1) -> str:
    return f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>'


def lines(x, y, text, width=52, size=16, fill=MUTED, lh=23, weight=400, max_lines=None) -> str:
    chunks = textwrap.wrap(str(text), width=width)
    if max_lines:
        chunks = chunks[:max_lines]
    return "".join(t(x, y + i * lh, chunk, size=size, fill=fill, weight=weight) for i, chunk in enumerate(chunks))


def polar(cx, cy, radius, angle_deg):
    rad = math.radians(angle_deg - 90)
    return cx + radius * math.cos(rad), cy + radius * math.sin(rad)


def build_svg() -> str:
    report = build_demo_report()
    readiness = build_readiness()
    active = report.companies[0]
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}">',
        "<defs>",
        '<linearGradient id="heroGlow" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#102a27"/><stop offset="1" stop-color="#071415"/></linearGradient>',
        '<radialGradient id="bgGlow"><stop offset="0" stop-color="#17372f" stop-opacity=".55"/><stop offset="1" stop-color="#061011" stop-opacity="0"/></radialGradient>',
        '<style>text{font-family:Inter,Segoe UI,Arial,sans-serif}.caps{letter-spacing:2px}</style>',
        "</defs>", f'<rect width="{W}" height="{H}" fill="{BG}"/>', '<circle cx="1180" cy="80" r="420" fill="url(#bgGlow)"/>',
    ]
    parts += [
        '<rect x="0" y="0" width="1440" height="76" fill="#071213" stroke="#17282a"/>', rounded(64,20,36,36,10,"#0d211f","#315a50"), t(82,44,"A",18,ACCENT,800,"middle"), t(114,45,"ANALYTICA",15,TEXT,800,cls="caps"), rounded(950,21,188,34,17,"#0d211f","#315a50"), '<circle cx="970" cy="38" r="4" fill="#64e0a3"/>', t(985,43,"Workable MVP prototype",12,ACCENT,700), rounded(1150,21,138,34,17,"#1a1716","#3c2927"), t(1219,43,"Paid launch gated",11,"#d7aaa4",700,"middle"), t(1310,43,"U.S.-first",11,MUTED,600),
        t(68,130,"HISTORICAL INTELLIGENCE → DECISION SUPPORT",12,ACCENT,800,cls="caps"), t(68,194,"See how businesses like yours",52,TEXT,780), t(68,250,"won, struggled, and adapted.",52,"#89a29e",700), lines(68,295,"Analytica reconstructs peer-company trajectories, exposes evidence behind turning points, and converts patterns into practical actions before you commit capital.",76,18,MUTED,27),
    ]
    bx=68
    for label in ["10-year trajectories","Evidence trace","Failure cases","Top 10 lessons"]:
        bw=126+len(label)*2.6; parts += [rounded(bx,370,bw,34,17,"#0a1718",LINE),t(bx+bw/2,392,label,11,"#b7cbc7",600,"middle")]; bx+=bw+10
    parts += [rounded(945,112,420,316,24,"url(#heroGlow)","#213638"),t(970,144,"PROTOTYPE CHECKOUT",10,MUTED,700,cls="caps"),t(970,174,"Run an analysis",24,TEXT,750),t(1320,160,"$1.00",24,ACCENT,800,"end"),t(1320,178,"target price",9,FAINT,700,"end")]
    for fy,label,val in [(211,"Business activity","Packaging manufacturing"),(270,"Geography","New York"),(329,"Result email","owner@example.com")]:
        parts += [t(970,fy,label,10,MUTED,650),rounded(970,fy+10,350,38,10,"#071315","#253638"),t(984,fy+35,val,13,TEXT,500)]
    parts += [rounded(970,388,350,42,10,ACCENT,ACCENT),t(1145,414,"Authorize demo + run analysis  →",13,BG,800,"middle"),rounded(68,452,1297,128,20,"#0a1a1b",LINE),t(92,482,"ANALYSIS ENGINE",10,ACCENT,800,cls="caps"),t(92,514,"Prototype processing pipeline",22,TEXT,750),t(1325,490,"100%",22,ACCENT,800,"end"),t(1325,512,"Analysis complete",10,MUTED,500,"end"),'<rect x="92" y="532" width="1233" height="4" rx="2" fill="#142425"/>','<rect x="92" y="532" width="1233" height="4" rx="2" fill="#8df0c6"/>']
    for i,name in enumerate(["Queued","Discover","Evidence","Normalize","Score","Findings","Render","Complete"]):
        x=98+i*153; parts += [f'<circle cx="{x}" cy="555" r="8" fill="#102d27" stroke="#4f8d79"/>',t(x,559,"✓",8,GREEN,800,"middle"),t(x+15,559,name,10,"#78958f",600)]
    parts += [t(68,624,"DECISION REPORT",10,ACCENT,800,cls="caps"),t(68,660,"Packaging manufacturing — New York",28,TEXT,760),t(68,685,report.market_scope,12,MUTED,500),t(1365,657,"●  COMPLETED",11,ACCENT,750,"end"),t(1365,679,"Workable MVP — synthetic evidence only",10,MUTED,500,"end")]
    kpis=[(report.cohort.fixture_company_count,"Comparable peers","fixture sample"),(report.cohort.high_performer_count,"High performers","strong trajectories"),(report.cohort.active_count,"Active / stable","operating case"),(report.cohort.distressed_count,"Distressed","declining case"),(report.cohort.failed_count,"Failed cases","failure evidence")]
    for i,(value,label,note) in enumerate(kpis):
        x=68+i*258; parts += [rounded(x,708,244,100,16,SURFACE,LINE),t(x+18,744,value,30,TEXT,800),t(x+18,770,label,12,"#b3c8c3",650),t(x+18,790,note,9,FAINT,500)]
    map_x,map_y,map_w,map_h=68,835,820,570; ev_x,ev_y,ev_w,ev_h=905,835,460,570
    parts += [rounded(map_x,map_y,map_w,map_h,22,"#09191a",LINE),rounded(ev_x,ev_y,ev_w,ev_h,22,"#09191a",LINE),t(map_x+24,map_y+32,"RADIAL BUSINESS TRAJECTORY MAP",10,ACCENT,800,cls="caps"),t(map_x+24,map_y+62,"Ten-year historical signal",24,TEXT,750),t(map_x+24,map_y+86,f"{active.display_name.replace(' (synthetic)','')} · High performer · {round(active.comparability_score*100)}% comparable",11,MUTED,500)]
    cx,cy=465,1132; inner,outer=62,225
    for ratio,label in [(0.25,"25"),(0.5,"50"),(0.75,"75"),(1,"100")]:
        r=inner+ratio*(outer-inner); parts.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="#1b2c2e"/>'); parts.append(t(cx+7,cy-r+13,label,9,FAINT,500))
    years=[p.year for p in active.trajectory]
    for idx,year in enumerate(years):
        angle=idx*36; ax,ay=polar(cx,cy,outer,angle); lx,ly=polar(cx,cy,outer+28,angle); parts += [f'<line x1="{cx}" y1="{cy}" x2="{ax:.1f}" y2="{ay:.1f}" stroke="#182a2b"/>',t(lx,ly+4,year,9,"#68847f",600,"middle")]
    chart_colors=[ACCENT,BLUE,YELLOW,RED,VIOLET]
    for ci,company in enumerate(report.companies):
        pts=[]
        for idx,p in enumerate(company.trajectory):
            r=inner+(p.performance_score/100)*(outer-inner); x,y=polar(cx,cy,r,idx*36); pts.append((x,y,p))
        parts.append(f'<polyline points="{" ".join(f"{x:.1f},{y:.1f}" for x,y,_ in pts)}" fill="none" stroke="{chart_colors[ci]}" stroke-width="{5 if ci==0 else 2.5}" opacity="{1 if ci==0 else .35}" stroke-linejoin="round"/>')
        for x,y,p in pts:
            color={"green":GREEN,"blue":BLUE,"yellow":YELLOW,"red":RED}[p.state]; parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{5 if ci==0 else 3.2}" fill="{color}" stroke="{BG}" stroke-width="2" opacity="{1 if ci==0 else .55}"/>')
    parts += [f'<circle cx="{cx}" cy="{cy}" r="48" fill="{BG}" stroke="#315a50"/>',t(cx,cy-2,"ANALYTICA",11,TEXT,800,"middle"),t(cx,cy+15,"10Y PEER SIGNAL",7,MUTED,600,"middle")]
    tab_y=1370
    for ci,company in enumerate(report.companies):
        x=map_x+20+(ci%3)*258; y=tab_y+(ci//3)*40; w=246; fill="#102523" if ci==0 else "#0b191a"; stroke="#315a50" if ci==0 else LINE
        parts += [rounded(x,y,w,32,9,fill,stroke),f'<circle cx="{x+12}" cy="{y+16}" r="3.5" fill="{chart_colors[ci]}"/>',t(x+22,y+20,company.display_name.replace(" (synthetic)",""),9,TEXT if ci==0 else MUTED,600),t(x+w-10,y+20,f"{round(company.comparability_score*100)}%",8,FAINT,600,"end")]
    evidence=report.evidence[1]; point=next(p for p in active.trajectory if p.year==evidence.period)
    parts += [t(ev_x+24,ev_y+32,"EVIDENCE DRILLDOWN",10,ACCENT,800,cls="caps"),t(ev_x+ev_w-24,ev_y+32,"TRACEABLE",9,ACCENT,700,"end"),t(ev_x+24,ev_y+66,f"Northstar Packaging — {evidence.period}",22,TEXT,750),t(ev_x+24,ev_y+91,"High performer · 94% comparability · GREEN state",11,MUTED,500),rounded(ev_x+24,ev_y+118,188,78,13,SURFACE2,LINE),t(ev_x+40,ev_y+151,round(point.performance_score),27,TEXT,800),t(ev_x+40,ev_y+174,"Performance / 100",9,MUTED,500),rounded(ev_x+224,ev_y+118,188,78,13,SURFACE2,LINE),t(ev_x+240,ev_y+151,f"{round(point.risk_score*100)}%",27,TEXT,800),t(ev_x+240,ev_y+174,"Modeled risk",9,MUTED,500),t(ev_x+24,ev_y+234,"SOURCE TRACE",9,FAINT,700,cls="caps"),t(ev_x+ev_w-24,ev_y+234,f"{round(evidence.confidence*100)}% confidence",9,ACCENT,700,"end"),t(ev_x+24,ev_y+270,evidence.source_title,15,TEXT,700),t(ev_x+24,ev_y+293,f"{evidence.publisher} · {evidence.period} · {evidence.verification_status}",9,FAINT,500),lines(ev_x+24,ev_y+328,evidence.fact,50,13,"#b9cbc7",20),rounded(ev_x+24,ev_y+390,412,96,10,"#0b1a20","#1e3440"),t(ev_x+38,ev_y+413,"NORMALIZED SIGNAL",8,"#688b9a",700,cls="caps"),lines(ev_x+38,ev_y+438,evidence.normalized_fact,48,12,"#9fb9b4",18)]
    y=1442; parts += [t(68,y,"CROSS-COMPANY PATTERNS",10,ACCENT,800,cls="caps"),t(68,y+34,"What changed outcomes in the fixture",24,TEXT,750)]
    for i,finding in enumerate(report.findings):
        x=68+i*318; cy2=y+58; parts += [rounded(x,cy2,302,165,16,SURFACE,LINE),t(x+16,cy2+24,f"0{i+1}",9,FAINT,800),t(x+286,cy2+24,finding.confidence.value.replace('_',' ').title(),7,ACCENT,700,"end"),lines(x+16,cy2+55,finding.title,34,14,TEXT,18,700,2),lines(x+16,cy2+103,finding.summary,42,10,MUTED,15,400,4)]
    y2=1690; parts += [t(68,y2,"Top 10 lessons",20,TEXT,760),t(245,y2,"· evidence-referenced decision output",11,MUTED,500),rounded(1035,y2-29,330,50,14,"#0e1c1c",LINE),t(1055,y2+1,"R&D technical state",10,MUTED,600),t(1338,y2+2,f"{readiness['prototype_completion_percent']}%",22,ACCENT,800,"end"),t(68,1760,"Workable MVP prototype",12,ACCENT,800),t(1365,1760,"Historical intelligence first · paid launch gated",10,FAINT,600,"end"),"</svg>"]
    return "".join(parts)


def main() -> None:
    target = ROOT / "docs" / "previews" / "analytica-mvp-dashboard.svg"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(build_svg(), encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
