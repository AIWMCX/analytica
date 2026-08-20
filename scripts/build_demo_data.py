from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.app.fixtures import build_demo_report  # noqa: E402


def main() -> None:
    report = build_demo_report().model_dump(mode="json")
    target = ROOT / "apps" / "web-preview" / "demo-data.js"
    payload = json.dumps(report, ensure_ascii=False, separators=(",", ":"))
    target.write_text(f"window.__ANALYTICA_DEMO_REPORT__={payload};\n", encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
