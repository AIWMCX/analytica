# Development intelligence controls

## Graphify

Graphify is installed as repository-local tooling in `.tools/graphify`, intentionally excluded from version control. Its output belongs in `graphify-out/`: `GRAPH_REPORT.md`, `graph.json`, and `graph.html` are reviewed architectural artefacts, not application data.

Run the graph against the repository before a cross-service change or release rehearsal. The graph must identify the path from provider policy through EvidencePacket, reviewer approval, Quantis-compatible calculation, and report delivery. Extracted relationships must remain distinct from inferred relationships.

## Everything Claude Code adaptation

Claude Code is available locally. We adopt only portable operating controls rather than copying a third-party repository:

- inspect the call path and current tests before edits;
- make behavioural changes test-first;
- require evidence/provenance and financial-firewall checks for data changes;
- keep secrets, provider credentials, and customer data out of commits and generated graph artefacts;
- use focused verification plus a release checklist before a demo or deployment.

These controls apply equally to Codex, Claude Code, and human contributors. They do not create a dependency on an external agent framework.

## Provider readiness

`apps/api/app/providers.py` is the authoritative internal catalogue of permitted data uses. A provider being public or connected never converts its content into canonical financial truth. The only promotion path is EvidencePacket -> proposed assumption -> named human acceptance -> canonical financial input.
