from __future__ import annotations

import json
from typing import Any, Callable
from urllib.parse import urlencode
from urllib.request import Request, urlopen


Transport = Callable[[Request], dict[str, Any]]


def _live_transport(request: Request) -> dict[str, Any]:
    with urlopen(request, timeout=15) as response:  # noqa: S310 - URLs are fixed service endpoints
        return json.loads(response.read().decode("utf-8"))


class PredictaHttpClient:
    """HTTP boundary for the deployed Predicta Pages API."""

    def __init__(self, base_url: str, *, transport: Transport | None = None):
        self.base_url = base_url.rstrip("/")
        self.transport = transport or _live_transport

    def search(self, raw_query: str, *, session_id: str, country: str = "US", mode: str = "quick") -> dict[str, Any]:
        payload = {"rawQuery": raw_query, "queryVersion": 0, "language": "en", "country": country, "lens": "financial", "safeSearch": "moderate", "mode": mode, "sessionId": session_id}
        request = Request(f"{self.base_url}/api/search", data=json.dumps(payload, separators=(",", ":")).encode(), headers={"content-type": "application/json", "accept": "application/json"}, method="POST")
        response = self.transport(request)
        if not isinstance(response.get("query"), dict) or not isinstance(response.get("candidates"), list):
            raise ValueError("Predicta response does not satisfy the search envelope")
        return {"apiVersion": "predicta.search.v1", **response}


class SecCompanyFactsClient:
    """Official SEC EDGAR companyfacts connector; public-issuer data only."""

    BASE_URL = "https://data.sec.gov"

    def __init__(self, user_agent: str, *, transport: Transport | None = None):
        if "@" not in user_agent:
            raise ValueError("SEC requires a contactable User-Agent")
        self.user_agent = user_agent
        self.transport = transport or _live_transport

    def company_facts(self, cik: str) -> dict[str, Any]:
        normalized_cik = "".join(character for character in cik if character.isdigit()).zfill(10)
        request = Request(f"{self.BASE_URL}/api/xbrl/companyfacts/CIK{normalized_cik}.json", headers={"accept": "application/json", "User-Agent": self.user_agent})
        return {"provider_id": "sec_edgar", "authority": "OFFICIAL_FILING", "data": self.transport(request)}


class CensusDatasetClient:
    """Official Census API client for industry/geography benchmarks, never company facts."""

    BASE_URL = "https://api.census.gov/data"

    def __init__(self, *, transport: Transport | None = None):
        self.transport = transport or _live_transport

    def get(self, dataset_path: str, parameters: dict[str, str]) -> dict[str, Any]:
        path = dataset_path.strip("/")
        request = Request(f"{self.BASE_URL}/{path}?{urlencode(parameters)}", headers={"accept": "application/json", "User-Agent": "Analytica public-data adapter"})
        return {"provider_id": "census", "authority": "OFFICIAL_DATASET", "data_scope": "BENCHMARK", "data": self.transport(request)}
