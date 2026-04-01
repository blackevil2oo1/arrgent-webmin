import httpx

TIMEOUT = 15.0


class JellyseerrController:
    def __init__(self, url: str, api_key: str):
        self.base_url = url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict:
        return {"X-Api-Key": self.api_key, "Accept": "application/json"}

    def _get(self, path: str, params: dict = None) -> dict | list:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}{path}",
                headers=self._headers(),
                params=params or {}
            )
            resp.raise_for_status()
            return resp.json()

    def _get_media_title(self, media_type: str, tmdb_id: int | None, tvdb_id: int | None) -> str:
        try:
            if media_type == "movie" and tmdb_id:
                data = self._get(f"/api/v1/movie/{tmdb_id}")
                return data.get("title") or data.get("originalTitle") or ""
            elif media_type == "tv":
                search_id = tvdb_id or tmdb_id
                if search_id:
                    data = self._get(f"/api/v1/tv/{search_id}")
                    return data.get("name") or data.get("originalName") or ""
        except Exception:
            pass
        return ""

    def _post(self, path: str, json: dict = None) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(
                f"{self.base_url}{path}",
                headers=self._headers(),
                json=json or {}
            )
            resp.raise_for_status()
            return resp.json()

    def get_request_counts(self) -> dict:
        data = self._get("/api/v1/request/count")
        return {
            "total": data.get("total", 0),
            "movie": data.get("movie", 0),
            "tv": data.get("tv", 0),
            "pending": data.get("pending", 0),
            "approved": data.get("approved", 0),
            "available": data.get("available", 0),
        }

    def get_pending_requests(self, take: int = 20) -> list[dict]:
        data = self._get("/api/v1/request", params={"take": take, "skip": 0, "filter": "pending", "sort": "added"})
        results = data.get("results", []) if isinstance(data, dict) else []
        requests = []
        for r in results:
            media = r.get("media", {})
            req_by = r.get("requestedBy", {})
            title = (media.get("title") or media.get("originalTitle") or
                     media.get("name") or media.get("originalName") or "")
            if not title:
                title = self._get_media_title(
                    media.get("mediaType", ""),
                    media.get("tmdbId"),
                    media.get("tvdbId"),
                )
            requests.append({
                "id": r.get("id"),
                "type": media.get("mediaType", ""),
                "title": title,
                "tmdb_id": media.get("tmdbId"),
                "poster": media.get("posterPath", ""),
                "requested_by": req_by.get("displayName") or req_by.get("username") or "",
                "created_at": r.get("createdAt", "")[:10] if r.get("createdAt") else "",
                "status": r.get("status", 1),
            })
        return requests

    def get_recent_requests(self, take: int = 20) -> list[dict]:
        data = self._get("/api/v1/request", params={"take": take, "skip": 0, "sort": "added"})
        results = data.get("results", []) if isinstance(data, dict) else []
        requests = []
        status_map = {1: "Pending", 2: "Approved", 3: "Declined", 4: "Available", 5: "Processing"}
        for r in results:
            media = r.get("media", {})
            req_by = r.get("requestedBy", {})
            title = (media.get("title") or media.get("originalTitle") or
                     media.get("name") or media.get("originalName") or "")
            if not title:
                title = self._get_media_title(
                    media.get("mediaType", ""),
                    media.get("tmdbId"),
                    media.get("tvdbId"),
                )
            requests.append({
                "id": r.get("id"),
                "type": media.get("mediaType", ""),
                "title": title,
                "requested_by": req_by.get("displayName") or req_by.get("username") or "",
                "created_at": r.get("createdAt", "")[:10] if r.get("createdAt") else "",
                "status": status_map.get(r.get("status", 1), "Unknown"),
                "status_code": r.get("status", 1),
            })
        return requests

    def approve_request(self, request_id: int) -> dict:
        return self._post(f"/api/v1/request/{request_id}/approve")

    def decline_request(self, request_id: int) -> dict:
        return self._post(f"/api/v1/request/{request_id}/decline")
