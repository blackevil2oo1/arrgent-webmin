import httpx
from controllers.base import BaseController

TIMEOUT = 15.0


class ProwlarrController(BaseController):
    def __init__(self, url: str, api_key: str):
        super().__init__(url, api_key)

    def get_system_status(self) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v1/system/status",
                headers=self._headers()
            )
            resp.raise_for_status()
            data = resp.json()
        return {
            "version": data.get("version", ""),
            "app_name": data.get("appName", "Prowlarr"),
        }

    def get_indexers(self) -> list[dict]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v1/indexer",
                headers=self._headers()
            )
            resp.raise_for_status()
            indexers = resp.json()
        result = []
        for idx in indexers:
            result.append({
                "id": idx.get("id"),
                "name": idx.get("name", ""),
                "enabled": idx.get("enable", False),
                "protocol": idx.get("protocol", ""),
                "privacy": idx.get("privacy", ""),
                "priority": idx.get("priority", 25),
            })
        return sorted(result, key=lambda x: x["name"].lower())

    def get_history(self, take: int = 20) -> list[dict]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v1/history",
                headers=self._headers(),
                params={"pageSize": take, "page": 1, "sortKey": "date", "sortDirection": "descending"}
            )
            resp.raise_for_status()
            data = resp.json()
        records = data.get("records", []) if isinstance(data, dict) else []
        result = []
        for r in records:
            result.append({
                "query": r.get("query", ""),
                "indexer": r.get("indexer", ""),
                "successful": r.get("successful", False),
                "date": r.get("date", "")[:16].replace("T", " ") if r.get("date") else "",
            })
        return result
