from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class ProviderRecord:
    provider_id: str
    record_id: str
    title: str
    canonical_url: str
    text: str
    authority: str
    data_scope: str
    retrieved_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content_hash: str = ""

    def __post_init__(self):
        calculated = hashlib.sha256(self.text.encode()).hexdigest()
        if self.content_hash and self.content_hash != calculated:
            raise ValueError('provider record content hash mismatch')
        object.__setattr__(self, 'content_hash', calculated)


class ResearchProvider(Protocol):
    provider_id: str
    def collect(self, query: str) -> list[ProviderRecord]: ...


@dataclass(frozen=True)
class ResearchRunManifest:
    case_id: str
    providers: dict[str, str]
    failures: list[str]


@dataclass(frozen=True)
class ResearchRun:
    manifest: ResearchRunManifest
    records: list[ProviderRecord]
    fixture_fallback_used: bool = False


class ResearchPipeline:
    def __init__(self, providers: list[ResearchProvider]):
        identifiers = [provider.provider_id for provider in providers]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError('duplicate provider identifiers')
        self.providers = providers

    def run(self, case_id: str, query: str) -> ResearchRun:
        states, failures, records = {}, [], []
        for provider in self.providers:
            try:
                result = provider.collect(query)
                records.extend(result)
                states[provider.provider_id] = "SUCCEEDED" if result else "DEGRADED"
            except Exception as error:
                states[provider.provider_id] = "FAILED"
                # Exceptions can contain credential-bearing upstream URLs.
                failures.append(f"{provider.provider_id}: {type(error).__name__}")
        return ResearchRun(ResearchRunManifest(case_id, states, failures), records)
