import httpx
from controllers.base import BaseController

TIMEOUT = 15.0


class SabnzbdController(BaseController):
    def __init__(self, url: str, api_key: str):
        super().__init__(url, api_key)

    def _api_params(self, mode: str, **extra) -> dict:
        params = {
            "apikey": self.api_key,
            "output": "json",
            "mode": mode
        }
        params.update(extra)
        return params

    def get_queue(self) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api",
                params=self._api_params("queue")
            )
            resp.raise_for_status()
            data = resp.json()

        queue = data.get("queue", {})
        slots = queue.get("slots", [])
        items = []
        for slot in slots:
            mb = float(slot.get("mb", 0))
            mbleft = float(slot.get("mbleft", 0))
            percentage = 0
            if mb > 0:
                percentage = round((mb - mbleft) / mb * 100)
            items.append({
                "filename": slot.get("filename", ""),
                "percentage": percentage,
                "size": slot.get("size", ""),
                "status": slot.get("status", "")
            })

        return {
            "status": queue.get("status", "Unknown"),
            "speed": queue.get("speed", "0"),
            "size_left": queue.get("sizeleft", "0"),
            "time_left": queue.get("timeleft", "0:00:00"),
            "items": items
        }

    def pause_queue(self) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api",
                params=self._api_params("pause")
            )
            resp.raise_for_status()
            data = resp.json()
        return {"success": data.get("status", False), "message": "Queue paused"}

    def resume_queue(self) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api",
                params=self._api_params("resume")
            )
            resp.raise_for_status()
            data = resp.json()
        return {"success": data.get("status", False), "message": "Queue resumed"}

    def get_history(self, limit: int = 10) -> list[dict]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api",
                params=self._api_params("history", limit=limit)
            )
            resp.raise_for_status()
            data = resp.json()

        history = data.get("history", {})
        slots = history.get("slots", [])
        result = []
        for slot in slots:
            completed = slot.get("completed", 0)
            # completed is a unix timestamp
            import datetime
            try:
                completed_str = datetime.datetime.utcfromtimestamp(completed).strftime("%Y-%m-%d %H:%M")
            except Exception:
                completed_str = ""
            result.append({
                "name": slot.get("name", ""),
                "status": slot.get("status", ""),
                "size": slot.get("size", ""),
                "completed": completed_str
            })
        return result
