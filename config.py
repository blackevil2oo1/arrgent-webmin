import json
import os
import secrets
from dataclasses import dataclass
from passlib.context import CryptContext

SETTINGS_PATH = "/data/settings.json"
AUTH_PATH = "/data/auth.json"

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Mapping: app name → environment variable names
_ENV_APP_CONFIG = {
    "radarr":     {"url": "RADARR_URL",     "api_key": "RADARR_API_KEY"},
    "sonarr":     {"url": "SONARR_URL",     "api_key": "SONARR_API_KEY"},
    "sabnzbd":    {"url": "SABNZBD_URL",    "api_key": "SABNZBD_API_KEY"},
    "jellyfin":   {"url": "JELLYFIN_URL",   "api_key": "JELLYFIN_API_KEY"},
    "system":     {"url": "UNRAID_URL",     "api_key": "UNRAID_API_KEY"},
    "jellyseerr": {"url": "JELLYSEERR_URL", "api_key": "JELLYSEERR_API_KEY"},
    "fileflows":  {"url": "FILEFLOWS_URL",  "container_name": "FILEFLOWS_CONTAINER_NAME"},
    "prowlarr":   {"url": "PROWLARR_URL",   "api_key": "PROWLARR_API_KEY"},
    "huntarr":    {"url": "HUNTARR_URL"},
}

FILES_ROOT = os.environ.get("FILES_ROOT", "/mnt")

DEFAULT_SETTINGS = {
    "apps": {
        "radarr":     {"enabled": True},
        "sonarr":     {"enabled": True},
        "sabnzbd":    {"enabled": True},
        "jellyfin":   {"enabled": True},
        "docker":     {"enabled": True},
        "system":     {"enabled": True},
        "fileflows":  {"enabled": False},
        "jellyseerr": {"enabled": False},
        "prowlarr":   {"enabled": False},
        "huntarr":    {"enabled": False},
        "chat":       {"enabled": True},
    }
}


@dataclass
class AppConfig:
    enabled: bool = False
    url: str = ""
    api_key: str = ""
    container_name: str = "fileflows"


def _load_auth() -> dict:
    if os.path.exists(AUTH_PATH):
        with open(AUTH_PATH) as f:
            return json.load(f)
    return {}


def _save_auth(data: dict):
    os.makedirs(os.path.dirname(AUTH_PATH), exist_ok=True)
    with open(AUTH_PATH, "w") as f:
        json.dump(data, f, indent=2)


def ensure_settings_exist():
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    if not os.path.exists(SETTINGS_PATH):
        with open(SETTINGS_PATH, "w") as f:
            json.dump(DEFAULT_SETTINGS, f, indent=2)

    # Initialize or update auth.json
    auth = _load_auth()
    changed = False

    if "session_secret" not in auth:
        env_secret = os.environ.get("SESSION_SECRET", "")
        auth["session_secret"] = env_secret if env_secret else secrets.token_hex(32)
        changed = True

    env_pw = os.environ.get("ADMIN_PASSWORD", "")
    if env_pw:
        # Re-hash if env var changed or hash missing
        if not auth.get("password_hash") or not pwd_context.verify(env_pw, auth["password_hash"]):
            auth["password_hash"] = pwd_context.hash(env_pw)
            changed = True
    elif "password_hash" not in auth:
        auth["password_hash"] = pwd_context.hash("admin")
        changed = True

    if changed:
        _save_auth(auth)


def get_settings() -> dict:
    ensure_settings_exist()
    with open(SETTINGS_PATH, "r") as f:
        data = json.load(f)
    merged = json.loads(json.dumps(DEFAULT_SETTINGS))
    _deep_merge(merged, data)
    return merged


def save_settings(settings: dict):
    os.makedirs(os.path.dirname(SETTINGS_PATH), exist_ok=True)
    # Only persist enabled flags — URLs/keys live in env vars
    clean = {"apps": {}}
    for app_name, app_data in settings.get("apps", {}).items():
        clean["apps"][app_name] = {"enabled": bool(app_data.get("enabled", False))}
    with open(SETTINGS_PATH, "w") as f:
        json.dump(clean, f, indent=2)


def _deep_merge(base: dict, override: dict):
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value


def get_app_config(app_name: str) -> AppConfig:
    settings = get_settings()
    app = settings.get("apps", {}).get(app_name, {})
    env_keys = _ENV_APP_CONFIG.get(app_name, {})

    return AppConfig(
        enabled=app.get("enabled", False),
        url=os.environ.get(env_keys.get("url", ""), ""),
        api_key=os.environ.get(env_keys.get("api_key", ""), ""),
        container_name=os.environ.get(env_keys.get("container_name", ""), "fileflows"),
    )


def get_session_secret() -> str:
    env_secret = os.environ.get("SESSION_SECRET", "")
    if env_secret:
        return env_secret
    return _load_auth().get("session_secret", secrets.token_hex(32))


def get_password_hash() -> str:
    return _load_auth().get("password_hash", pwd_context.hash("admin"))


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def is_configured() -> bool:
    """Returns True if at least one app has a URL configured via env vars."""
    for env_keys in _ENV_APP_CONFIG.values():
        url_var = env_keys.get("url", "")
        if url_var and os.environ.get(url_var, ""):
            return True
    return False
