from __future__ import annotations


def build_readiness() -> dict:
    areas = [
        {"area": "Product architecture", "state": "working", "detail": "Approved specification and modular service boundaries"},
        {"area": "Historical analytics domain", "state": "working", "detail": "Typed evidence, trajectories, findings and recommendations"},
        {"area": "Persistence", "state": "prototype", "detail": "Durable SQLite MVP store; PostgreSQL remains production target"},
        {"area": "Async execution", "state": "prototype", "detail": "Background worker thread and explicit progress state machine"},
        {"area": "Commercial flow", "state": "prototype", "detail": "$1 demo checkout contract; no real charge in this build"},
        {"area": "Visual product", "state": "working", "detail": "Interactive radial map, drilldown, findings and top lessons"},
        {"area": "Real company data", "state": "blocked", "detail": "Lawful provider adapters and entity resolution not connected yet"},
        {"area": "Authentication / tenancy", "state": "blocked", "detail": "Required before private customer reports"},
        {"area": "Real payments", "state": "blocked", "detail": "Provider credentials, checkout and verified webhooks required"},
        {"area": "Email delivery", "state": "blocked", "detail": "Provider integration required for asynchronous completion delivery"},
        {"area": "Production deployment", "state": "blocked", "detail": "Staging, observability, backups and security hardening required"},
    ]
    return {
        "product_stage": "workable_mvp_prototype",
        "prototype_completion_percent": 78,
        "paid_public_launch_ready": False,
        "launch_scope": "United States-first; canonical fixture Packaging manufacturing / New York",
        "data_mode": "synthetic_fixture",
        "areas": areas,
    }
