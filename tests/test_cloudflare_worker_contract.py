from __future__ import annotations

import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CloudflareWorkerContractTests(unittest.TestCase):
    def test_worker_deployment_serves_the_existing_labeled_static_preview(self) -> None:
        config_path = ROOT / "wrangler.toml"
        self.assertTrue(config_path.exists(), "Cloudflare needs a root wrangler.toml")

        config = tomllib.loads(config_path.read_text(encoding="utf-8"))
        self.assertEqual(config["main"], "cloudflare/worker.mjs")
        self.assertEqual(config["assets"]["directory"], "./apps/web-preview")
        self.assertEqual(config["assets"]["binding"], "ASSETS")
        self.assertTrue((ROOT / config["main"]).exists(), "asset Worker entry point is required")


if __name__ == "__main__":
    unittest.main()
