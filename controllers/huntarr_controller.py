import httpx

TIMEOUT = 15.0


class HuntarrController:
    def __init__(self, url: str):
        self.base_url = url.rstrip("/")

    def get_status(self) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(f"{self.base_url}/api/v1/status")
            resp.raise_for_status()
            data = resp.json()
        return {
            "state": data.get("state", data.get("status", "unknown")),
            "current_app": data.get("current_app", data.get("app", "")),
            "version": data.get("version", ""),
        }

    def get_logs(self, limit: int = 30) -> list[str]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(f"{self.base_url}/api/v1/logs", params={"limit": limit})
            resp.raise_for_status()
            data = resp.json()
        if isinstance(data, list):
            return data[-limit:]
        return data.get("logs", [])

    def trigger(self, app: str) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(f"{self.base_url}/api/v1/trigger/{app}")
            resp.raise_for_status()
            return resp.json() if resp.content else {"ok": True}
