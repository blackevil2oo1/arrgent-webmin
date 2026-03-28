import json
from typing import Any

from config import get_app_config
from controllers.radarr_controller import RadarrController
from controllers.sonarr_controller import SonarrController
from controllers.sabnzbd_controller import SabnzbdController
from controllers.jellyfin_controller import JellyfinController
from controllers.docker_controller import DockerController
from controllers.system_controller import SystemController

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_movie",
            "description": "Search for a movie in Radarr lookup. Returns results with title, year, overview.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Movie title to search for"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_radarr_quality_profiles",
            "description": "Get available quality profiles in Radarr.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_movie",
            "description": "Add a movie to Radarr for download.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tmdb_id": {"type": "integer", "description": "TMDB ID of the movie"},
                    "title": {"type": "string", "description": "Movie title"},
                    "year": {"type": "integer", "description": "Release year"},
                    "quality_profile_id": {"type": "integer", "description": "Quality profile ID from get_radarr_quality_profiles"}
                },
                "required": ["tmdb_id", "title", "year", "quality_profile_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_series",
            "description": "Search for a TV series in Sonarr lookup.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Series title to search for"}
                },
                "required": ["title"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_sonarr_quality_profiles",
            "description": "Get available quality profiles in Sonarr.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "add_series",
            "description": "Add a TV series to Sonarr for download.",
            "parameters": {
                "type": "object",
                "properties": {
                    "tvdb_id": {"type": "integer", "description": "TVDB ID of the series"},
                    "title": {"type": "string", "description": "Series title"},
                    "year": {"type": "integer", "description": "Start year"},
                    "quality_profile_id": {"type": "integer", "description": "Quality profile ID"}
                },
                "required": ["tvdb_id", "title", "year", "quality_profile_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_series_updates",
            "description": "Get TV series that had new episodes downloaded recently.",
            "parameters": {
                "type": "object",
                "properties": {
                    "days": {"type": "integer", "description": "Number of days to look back", "default": 7}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_download_queue",
            "description": "Get the current SABnzbd download queue status.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "pause_downloads",
            "description": "Pause the SABnzbd download queue.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "resume_downloads",
            "description": "Resume the SABnzbd download queue.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_media",
            "description": "Get recently added media from Jellyfin.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of items to return", "default": 20}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_container_status",
            "description": "Get status of all Docker containers.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "start_container",
            "description": "Start a Docker container by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Container name"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "stop_container",
            "description": "Stop a Docker container by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Container name"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "restart_container",
            "description": "Restart a Docker container by name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Container name"}
                },
                "required": ["name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_system_status",
            "description": "Get system status including CPU, RAM, and array information.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_disk_health",
            "description": "Get disk health information including temperatures and SMART status.",
            "parameters": {"type": "object", "properties": {}, "required": []}
        }
    }
]


def dispatch(function_name: str, arguments: dict, settings: dict) -> Any:
    """Dispatch a tool call to the appropriate controller."""
    from config import get_app_config

    try:
        def _radarr():
            cfg = get_app_config("radarr")
            return RadarrController(cfg.url, cfg.api_key)

        def _sonarr():
            cfg = get_app_config("sonarr")
            return SonarrController(cfg.url, cfg.api_key)

        def _sabnzbd():
            cfg = get_app_config("sabnzbd")
            return SabnzbdController(cfg.url, cfg.api_key)

        def _jellyfin():
            cfg = get_app_config("jellyfin")
            return JellyfinController(cfg.url, cfg.api_key)

        def _docker():
            return DockerController()

        def _system():
            cfg = get_app_config("system")
            return SystemController(cfg.url, cfg.api_key)

        match function_name:
            case "search_movie":
                return _radarr().search_movie(arguments["title"])
            case "get_radarr_quality_profiles":
                return _radarr().get_quality_profiles()
            case "add_movie":
                return _radarr().add_movie(
                    arguments["tmdb_id"], arguments["title"],
                    arguments["year"], arguments["quality_profile_id"]
                )
            case "search_series":
                return _sonarr().search_series(arguments["title"])
            case "get_sonarr_quality_profiles":
                return _sonarr().get_quality_profiles()
            case "add_series":
                return _sonarr().add_series(
                    arguments["tvdb_id"], arguments["title"],
                    arguments["year"], arguments["quality_profile_id"]
                )
            case "get_series_updates":
                return _sonarr().get_series_updates(arguments.get("days", 7))
            case "get_download_queue":
                return _sabnzbd().get_queue()
            case "pause_downloads":
                return _sabnzbd().pause_queue()
            case "resume_downloads":
                return _sabnzbd().resume_queue()
            case "get_recent_media":
                return _jellyfin().get_recent_media(arguments.get("limit", 20))
            case "get_container_status":
                return _docker().get_containers()
            case "start_container":
                return _docker().start_container(arguments["name"])
            case "stop_container":
                return _docker().stop_container(arguments["name"])
            case "restart_container":
                return _docker().restart_container(arguments["name"])
            case "get_system_status":
                return _system().get_system_status()
            case "get_disk_health":
                return _system().get_disk_health()
            case _:
                return {"error": f"Unknown function: {function_name}"}

    except Exception as e:
        return {
            "error_type": type(e).__name__,
            "message": str(e)
        }
