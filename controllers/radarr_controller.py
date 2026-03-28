from typing import Any
import httpx
from controllers.base import BaseController

TIMEOUT = 15.0


class RadarrController(BaseController):
    def __init__(self, url: str, api_key: str):
        super().__init__(url, api_key)

    def search_movie(self, title: str) -> list[dict]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v3/movie/lookup",
                headers=self._headers(),
                params={"term": title}
            )
            resp.raise_for_status()
            results = resp.json()

        # Get existing library tmdb IDs
        with httpx.Client(timeout=TIMEOUT) as client:
            lib_resp = client.get(
                f"{self.base_url}/api/v3/movie",
                headers=self._headers()
            )
            lib_resp.raise_for_status()
            library = lib_resp.json()

        existing_ids = {m.get("tmdbId") for m in library}

        movies = []
        for item in results[:10]:
            movies.append({
                "title": item.get("title", ""),
                "year": item.get("year", 0),
                "tmdb_id": item.get("tmdbId"),
                "overview": item.get("overview", "")[:200],
                "already_in_radarr": item.get("tmdbId") in existing_ids
            })
        return movies

    def get_quality_profiles(self) -> list[dict]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v3/qualityprofile",
                headers=self._headers()
            )
            resp.raise_for_status()
            profiles = resp.json()
        return [{"profile_id": p["id"], "name": p["name"]} for p in profiles]

    def add_movie(self, tmdb_id: int, title: str, year: int, quality_profile_id: int) -> dict:
        # First lookup to get full movie data including root folder
        with httpx.Client(timeout=TIMEOUT) as client:
            lookup_resp = client.get(
                f"{self.base_url}/api/v3/movie/lookup/tmdb",
                headers=self._headers(),
                params={"tmdbId": tmdb_id}
            )
            lookup_resp.raise_for_status()
            movie_data = lookup_resp.json()

        # Get root folder
        with httpx.Client(timeout=TIMEOUT) as client:
            rf_resp = client.get(
                f"{self.base_url}/api/v3/rootfolder",
                headers=self._headers()
            )
            rf_resp.raise_for_status()
            root_folders = rf_resp.json()

        if not root_folders:
            raise ValueError("No root folders configured in Radarr")

        root_folder_path = root_folders[0]["path"]

        payload = {
            **movie_data,
            "qualityProfileId": quality_profile_id,
            "rootFolderPath": root_folder_path,
            "monitored": True,
            "addOptions": {
                "searchForMovie": True
            }
        }

        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.post(
                f"{self.base_url}/api/v3/movie",
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

    def get_recent_movies(self, limit: int = 10) -> list[dict]:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v3/history",
                headers=self._headers(),
                params={
                    "pageSize": 50,
                    "page": 1,
                    "eventType": 3,  # downloadFolderImported
                    "sortKey": "date",
                    "sortDir": "desc"
                }
            )
            resp.raise_for_status()
            data = resp.json()

        records = data.get("records", [])
        seen = set()
        movies = []
        for rec in records:
            movie = rec.get("movie", {})
            title = movie.get("title", rec.get("sourceTitle", "Unknown"))
            year = movie.get("year", 0)
            key = (title, year)
            if key not in seen:
                seen.add(key)
                movies.append({"title": title, "year": year})
            if len(movies) >= limit:
                break
        return movies

    def get_library_stats(self) -> dict:
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v3/movie",
                headers=self._headers()
            )
            resp.raise_for_status()
            movies = resp.json()

        total = len(movies)
        monitored = sum(1 for m in movies if m.get("monitored"))
        missing = sum(1 for m in movies if m.get("monitored") and not m.get("hasFile"))
        return {
            "total_movies": total,
            "monitored": monitored,
            "missing": missing
        }

    def get_missing_movies(self) -> list[dict]:
        """Gibt überwachte Filme zurück die noch keine Datei haben."""
        with httpx.Client(timeout=TIMEOUT) as client:
            resp = client.get(
                f"{self.base_url}/api/v3/movie",
                headers=self._headers()
            )
            resp.raise_for_status()
            movies = resp.json()

        missing = [
            {
                "id": m.get("id"),
                "tmdb_id": m.get("tmdbId"),
                "title": m.get("title", ""),
                "year": m.get("year", 0),
                "status": m.get("status", ""),
            }
            for m in movies
            if m.get("monitored") and not m.get("hasFile")
        ]
        return sorted(missing, key=lambda x: x["title"])

    def search_all_missing(self) -> dict:
        """Startet eine Suche für alle fehlenden überwachten Filme."""
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                f"{self.base_url}/api/v3/command",
                headers=self._headers(),
                json={"name": "MissingMoviesSearch", "filterKey": "status", "filterValue": "released"}
            )
            resp.raise_for_status()
        return {"success": True, "message": "Suche nach fehlenden Filmen gestartet."}
