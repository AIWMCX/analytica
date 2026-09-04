from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class IntendedUse(str, Enum):
    DISCOVERY = "DISCOVERY"
    EVIDENCE = "EVIDENCE"
    FINANCIAL_ASSUMPTION_PROPOSAL = "FINANCIAL_ASSUMPTION_PROPOSAL"
    CANONICAL_FINANCIAL_TRUTH = "CANONICAL_FINANCIAL_TRUTH"


@dataclass(frozen=True)
class DataProvider:
    provider_id: str
    display_name: str
    authority: str
    data_scope: str
    connection_state: str
    permitted_uses: tuple[IntendedUse, ...]
    terms_required: bool
    notes: str


@dataclass(frozen=True)
class ProviderAssessment:
    provider: DataProvider
    intended_use: IntendedUse
    allowed: bool
    safeguard: str


class DataProviderCatalog:
    """Explicit data-use controls; provider availability is never evidence validity."""

    def __init__(self) -> None:
        proposal_uses = (IntendedUse.DISCOVERY, IntendedUse.EVIDENCE, IntendedUse.FINANCIAL_ASSUMPTION_PROPOSAL)
        evidence_uses = (IntendedUse.DISCOVERY, IntendedUse.EVIDENCE)
        self._providers = {
            "sec_edgar": DataProvider("sec_edgar", "SEC EDGAR / XBRL", "OFFICIAL_FILING", "COMPANY", "PLANNED", proposal_uses, False, "Public issuer filings; reviewer approval remains required."),
            "census": DataProvider("census", "U.S. Census Bureau", "OFFICIAL_DATASET", "BENCHMARK", "PLANNED", proposal_uses, False, "Industry and geography benchmarks; never treated as company facts."),
            "fred": DataProvider("fred", "Federal Reserve Economic Data", "OFFICIAL_DATASET", "MACRO", "PLANNED", proposal_uses, False, "Macroeconomic context; never treated as company facts."),
            "bls": DataProvider("bls", "U.S. Bureau of Labor Statistics", "OFFICIAL_DATASET", "MACRO", "PLANNED", proposal_uses, False, "Labor and price context; never treated as company facts."),
            "bea": DataProvider("bea", "U.S. Bureau of Economic Analysis", "OFFICIAL_DATASET", "MACRO", "PLANNED", proposal_uses, False, "Economic context; never treated as company facts."),
            "company_web": DataProvider("company_web", "Company web and releases", "PRIMARY_STATEMENT", "COMPANY", "PLANNED", evidence_uses, True, "Company-authored statements require provenance and corroboration."),
            "predicta_search": DataProvider("predicta_search", "Predicta web research", "DISCOVERY_LAYER", "DISCOVERY", "CONTRACT_READY", evidence_uses, True, "Retrieval and discovery only; it cannot silently create financial truth."),
            "social_media": DataProvider("social_media", "Social media signals", "DISCOVERY_SIGNAL", "DISCOVERY", "NOT_CONNECTED", (IntendedUse.DISCOVERY,), True, "Timing and discovery only. No profile harvesting or financial inference."),
            "licensed_financial": DataProvider("licensed_financial", "Licensed financial/profile data", "LICENSED_COMMERCIAL", "COMPANY", "NOT_CONNECTED", evidence_uses, True, "Connection requires a licensed provider, contractual rights, and audit trail."),
            "quantis": DataProvider("quantis", "Quantis financial engine", "CALCULATION_ENGINE", "FINANCIAL_MODEL", "CONTRACT_READY", (IntendedUse.FINANCIAL_ASSUMPTION_PROPOSAL,), False, "A calculation engine, not an evidence source; inputs still pass the firewall."),
        }

    def get(self, provider_id: str) -> DataProvider:
        try:
            return self._providers[provider_id]
        except KeyError as error:
            raise ValueError(f"unknown data provider: {provider_id}") from error

    def assess(self, provider_id: str, intended_use: IntendedUse) -> ProviderAssessment:
        provider = self.get(provider_id)
        if intended_use == IntendedUse.CANONICAL_FINANCIAL_TRUTH:
            return ProviderAssessment(provider, intended_use, False, "Only a human-approved EvidencePacket assumption may become canonical financial input.")
        allowed = intended_use in provider.permitted_uses
        safeguard = "Permitted by provider policy; preserve provenance, rights, and evidence limitations."
        if not allowed:
            safeguard = "Provider policy prohibits this use; retain it as a bounded discovery signal only."
        return ProviderAssessment(provider, intended_use, allowed, safeguard)

    def all(self) -> tuple[DataProvider, ...]:
        return tuple(self._providers.values())
