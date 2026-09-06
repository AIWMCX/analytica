from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.app.fixtures import build_demo_report  # noqa: E402
from apps.api.app.evidence_graph import EvidenceGraphService  # noqa: E402


def main() -> None:
    source_report = build_demo_report()
    report = source_report.model_dump(mode="json")
    lineage = EvidenceGraphService().explain_recommendation(
        EvidenceGraphService().build_case(source_report), source_report.decision_brief.recommendation_id,
    ).model_dump(mode="json")
    target = ROOT / "apps" / "web-preview" / "demo-data.js"
    payload = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
    lineage_payload = json.dumps(lineage, ensure_ascii=False, separators=(",", ":"))
    target.write_text(f"window.__ANALYTICA_DEMO_REPORT__={payload};\nwindow.__ANALYTICA_DEMO_LINEAGE__={lineage_payload};\n", encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
