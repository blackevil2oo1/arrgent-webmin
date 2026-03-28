from datetime import datetime, timedelta
import httpx
from controllers.base import BaseController

TIMEOUT = 15.0


class SonarrController(BaseController):
    def __init__(self, url: str, api_key: str):
        super().__init__(url, api_key)

    def search_series(self, title: str) -> list[dict]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v3/series/lookup",
                headers=self._headers(),
                params={"term": title}
            )
            resp.raise_for_status()
            results = resp.json()

        # Get existing library tvdb IDs
        with httpx.Client(timeout=TIMEOUT) as client:
            lib_resp = client.get(
                f"{self.base_url}/api/v3/series",
                headers=self._headers()
            )
            lib_resp.raise_for_status()
            library = lib_resp.json()

        existing_ids = {s.get("tvdbId") for s in library}

        series = []
        for item in results[:10]:
            series.append({
                "title": item.get("title", ""),
                "year": item.get("year", 0),
                "tvdb_id": item.get("tvdbId"),
                "overview": item.get("overview", "")[:200],
                "already_in_sonarr": item.get("tvdbId") in existing_ids
            })
        return series

    def get_quality_profiles(self) -> list[dict]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v3/qualityprofile",
                headers=self._headers()
            )
            resp.raise_for_status()
            profiles = resp.json()
        return [{"profile_id": p["id"], "name": p["name"]} for p in profiles]

    def add_series(self, tvdb_id: int, title: str, year: int, quality_profile_id: int) -> dict:
        # Lookup full series data
        with httpx.Client(timeout=TIMEOUT) as client:
            lookup_resp = client.get(
                f"{self.base_url}/api/v3/series/lookup",
                headers=self._headers(),
                params={"term": f"tvdb:{tvdb_id}"}
            )
            lookup_resp.raise_for_status()
            results = lookup_resp.json()

        if not results:
            raise ValueError(f"Series with tvdbId {tvdb_id} not found")

        series_data = results[0]

        # Get root folder
        with httpx.Client(timeout=TIMEOUT) as client:
            rf_resp = client.get(
                f"{self.base_url}/api/v3/rootfolder",
                headers=self._headers()
            )
            rf_resp.raise_for_status()
            root_folders = rf_resp.json()

        if not root_folders:
            raise ValueError("No root folders configured in Sonarr")

        root_folder_path = root_folders[0]["path"]

        # Get language profiles if needed
        language_profile_id = 1
        try:
            with httpx.Client(timeout=TIMEOUT) as client:
                lp_resp = client.get(
                    f"{self.base_url}/api/v3/languageprofile",
                    headers=self._headers()
                )
                if lp_resp.status_code == 200:
                    lps = lp_resp.json()
                    if lps:
                        language_profile_id = lps[0]["id"]
        except Exception:
            pass

        payload = {
            **series_data,
            "qualityProfileId": quality_profile_id,
            "languageProfileId": language_profile_id,
            "rootFolderPath": root_folder_path,
            "monitored": True,
            "addOptions": {
                "searchForMissingEpisodes": True
            }
        }

        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(
                f"{self.base_url}/api/v3/series",
                headers=self._headers(),
                json=payload
            )
            resp.raise_for_status()
            added = resp.json()

        return {
            "success": True,
            "title": added.get("title", title),
            "year": added.get("year", year)
        }

    def get_recent_series(self, limit: int = 10) -> list[dict]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v3/series",
                headers=self._headers()
            )
            resp.raise_for_status()
            series = resp.json()

        # Sort by added date descending
        def get_added(s):
            added = s.get("added", "")
            if added and added != "0001-01-01T00:00:00Z":
                return added
            return ""

        sorted_series = sorted(series, key=get_added, reverse=True)

        result = []
        for s in sorted_series[:limit]:
            result.append({
                "title": s.get("title", ""),
                "year": s.get("year", 0),
                "added": s.get("added", ""),
                "status": s.get("status", "")
            })
        return result

    def get_series_updates(self, days: int = 7) -> list[dict]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v3/history",
                headers=self._headers(),
                params={
                    "pageSize": 100,
                    "page": 1,
                    "eventType": 3,  # downloadFolderImported
                    "includeSeries": True,
                    "includeEpisode": True,
                    "sortKey": "date",
                    "sortDir": "desc"
                }
            )
            resp.raise_for_status()
            data = resp.json()

        cutoff = datetime.utcnow() - timedelta(days=days)
        records = data.get("records", [])

        seen_series = {}
        for rec in records:
            # Parse date
            date_str = rec.get("date", "")
            try:
                rec_date = datetime.fromisoformat(date_str.replace("Z", "+00:00")).replace(tzinfo=None)
            except Exception:
                continue
            if rec_date < cutoff:
                break

            series = rec.get("series", {})
            episode = rec.get("episode", {})
            series_title = series.get("title", rec.get("sourceTitle", "Unknown"))
            series_id = series.get("id", series_title)

            if series_id not in seen_series:
                seen_series[series_id] = {
                    "title": series_title,
                    "year": series.get("year", 0),
                    "episodes_added": 0
                }
            seen_series[series_id]["episodes_added"] += 1

        return list(seen_series.values())

    def get_library_stats(self) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v3/series",
                headers=self._headers()
            )
            resp.raise_for_status()
            series = resp.json()

        total = len(series)
        monitored = sum(1 for s in series if s.get("monitored"))
        # episodeCount/episodeFileCount are under series.statistics
        missing_episodes = 0
        for s in series:
            if s.get("monitored"):
                stats = s.get("statistics", {})
                ep_count = stats.get("episodeCount", 0) or 0
                ep_files = stats.get("episodeFileCount", 0) or 0
                missing_episodes += max(0, ep_count - ep_files)
        return {
            "total_series": total,
            "monitored": monitored,
            "missing_episodes": missing_episodes
        }

    def get_missing_episodes(self, limit: int = 50) -> list[dict]:
        """Gibt überwachte Serien zurück die fehlende Episoden haben."""
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v3/wanted/missing",
                headers=self._headers(),
                params={"pageSize": limit, "sortKey": "airDateUtc", "sortDirection": "descending"}
            )
            resp.raise_for_status()
            data = resp.json()

        result = []
        for rec in data.get("records", []):
            series = rec.get("series", {})
            result.append({
                "series_id": series.get("id"),
                "series_title": series.get("title", ""),
                "season": rec.get("seasonNumber", 0),
                "episode": rec.get("episodeNumber", 0),
                "title": rec.get("title", ""),
                "air_date": rec.get("airDateUtc", "")[:10] if rec.get("airDateUtc") else "",
            })
        return result

    def search_all_missing(self) -> dict:
        """Startet eine Suche für alle fehlenden überwachten Episoden."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.base_url}/api/v3/command",
                headers=self._headers(),
                json={"name": "MissingEpisodeSearch"}
            )
            resp.raise_for_status()
        return {"success": True, "message": "Suche nach fehlenden Episoden gestartet."}
