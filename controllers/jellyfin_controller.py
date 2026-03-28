import httpx
from controllers.base import BaseController

TIMEOUT = 15.0


class JellyfinController(BaseController):
    def __init__(self, url: str, api_key: str):
        super().__init__(url, api_key)

    def _headers(self) -> dict:
        return {
            "Authorization": f'MediaBrowser Token="{self.api_key}"',
            "Content-Type": "application/json"
        }

    def _get_admin_user_id(self) -> str | None:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(f"{self.base_url}/Users", headers=self._headers())
            resp.raise_for_status()
            users = resp.json()
        if users:
            return users[0].get("Id")
        return None

    def get_recent_media(self, limit: int = 20) -> list[dict]:
        user_id = self._get_admin_user_id()
        if not user_id:
            return []

        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/Users/{user_id}/Items/Latest",
                headers=self._headers(),
                params={
                    "IncludeItemTypes": "Movie,Series",
                    "Fields": "ProductionYear",
                    "Limit": limit,
                    "EnableUserData": False,
                }
            )
            resp.raise_for_status()
            items = resp.json()

        result = []
        for item in items:
            result.append({
                "title": item.get("Name", ""),
                "type": item.get("Type", ""),
                "year": item.get("ProductionYear", 0),
            })
        return result

    def trigger_library_scan(self) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(
                f"{self.base_url}/Library/Refresh",
                headers=self._headers()
            )
            resp.raise_for_status()
        return {"success": True, "message": "Library scan triggered"}

    def get_library_stats(self) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/Items/Counts",
                headers=self._headers()
            )
            resp.raise_for_status()
            counts = resp.json()

        return {
            "total_movies": counts.get("MovieCount", 0),
            "total_series": counts.get("SeriesCount", 0),
            "total_episodes": counts.get("EpisodeCount", 0)
        }
