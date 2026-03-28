from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse
import httpx

from templates_config import templates
from auth import require_auth
from config import get_settings, save_settings, hash_password, verify_password, get_password_hash, get_app_config, _load_auth, _save_auth

router = APIRouter(prefix="/settings")


@router.get("", response_class=HTMLResponse)
async def settings_page(request: Request, auth=Depends(require_auth)):
    settings = get_settings()
    return templates.TemplateResponse("settings.html", {
        "request": request,
        "title": "Settings",
        "settings": settings,
        "saved": request.query_params.get("saved") == "1"
    })


@router.post("", response_class=RedirectResponse)
async def save_settings_route(request: Request, auth=Depends(require_auth)):
    form = await request.form()
    settings = get_settings()
    apps = settings.get("apps", {})

    for app_name in ["radarr", "sonarr", "sabnzbd", "jellyfin", "system", "jellyseerr", "fileflows", "docker", "prowlarr", "huntarr", "chat"]:
        if app_name not in apps:
            apps[app_name] = {}
        apps[app_name]["enabled"] = form.get(f"{app_name}_enabled") == "on"

    settings["apps"] = apps
    save_settings(settings)
    return RedirectResponse(url="/settings?saved=1", status_code=303)


@router.post("/password", response_class=HTMLResponse)
async def change_password(
    request: Request,
    current_password: str = Form(...),
    new_password: str = Form(...),
    confirm_password: str = Form(...),
    auth=Depends(require_auth)
):
    if not verify_password(current_password, get_password_hash()):
        return HTMLResponse("""
        <div class="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm">
            Current password is incorrect.
        </div>""")

    if new_password != confirm_password:
        return HTMLResponse("""
        <div class="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm">
            New passwords do not match.
        </div>""")

    if len(new_password) < 4:
        return HTMLResponse("""
        <div class="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm">
            Password must be at least 4 characters.
        </div>""")

    auth_data = _load_auth()
    auth_data["password_hash"] = hash_password(new_password)
    _save_auth(auth_data)

    return HTMLResponse("""
    <div class="bg-green-900/30 border border-green-700 rounded-lg p-3 text-green-300 text-sm">
        Password changed successfully.
    </div>""")


@router.post("/test/{app}", response_class=HTMLResponse)
async def test_connection(
    request: Request,
    app: str,
    auth=Depends(require_auth)
):
    cfg = get_app_config(app)
    url = cfg.url
    api_key = cfg.api_key

    if not url and app not in ("docker",):
        return HTMLResponse('<span class="text-yellow-400 text-sm">No URL configured</span>')

    try:
        if app in ("radarr", "sonarr"):
            endpoint = f"{url.rstrip('/')}/api/v3/system/status"
            headers = {"X-Api-Key": api_key}
            with httpx.Client(timeout=10) as client:
                resp = client.get(endpoint, headers=headers)
                resp.raise_for_status()
            return HTMLResponse('<span class="text-green-400 text-sm">Connected</span>')

        elif app == "sabnzbd":
            endpoint = f"{url.rstrip('/')}/api"
            with httpx.Client(timeout=10) as client:
                resp = client.get(endpoint, params={
                    "apikey": api_key, "output": "json", "mode": "version"
                })
                resp.raise_for_status()
                data = resp.json()
            version = data.get("version", "unknown")
            return HTMLResponse(f'<span class="text-green-400 text-sm">Connected (v{version})</span>')

        elif app == "jellyfin":
            endpoint = f"{url.rstrip('/')}/System/Info"
            headers = {"X-Emby-Token": api_key}
            with httpx.Client(timeout=10) as client:
                resp = client.get(endpoint, headers=headers)
                resp.raise_for_status()
            return HTMLResponse('<span class="text-green-400 text-sm">Connected</span>')

        elif app == "system":
            endpoint = f"{url.rstrip('/')}/graphql"
            headers = {"x-api-key": api_key, "Content-Type": "application/json"}
            with httpx.Client(timeout=10) as client:
                resp = client.post(endpoint, headers=headers, json={"query": "{ info { os { hostname } } }"})
                resp.raise_for_status()
                data = resp.json()
            hostname = data.get("data", {}).get("info", {}).get("os", {}).get("hostname", "unknown")
            return HTMLResponse(f'<span class="text-green-400 text-sm">Connected ({hostname})</span>')

        elif app == "docker":
            import docker
            client = docker.from_env()
            client.ping()
            return HTMLResponse('<span class="text-green-400 text-sm">Connected</span>')

        elif app == "jellyseerr":
            endpoint = f"{url.rstrip('/')}/api/v1/settings/public"
            headers = {"X-Api-Key": api_key}
            with httpx.Client(timeout=10) as client:
                resp = client.get(endpoint, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            app_name = data.get("applicationTitle", "Jellyseerr")
            return HTMLResponse(f'<span class="text-green-400 text-sm">Connected ({app_name})</span>')

        elif app == "fileflows":
            endpoint = f"{url.rstrip('/')}/api/status"
            with httpx.Client(timeout=10) as client:
                resp = client.get(endpoint)
                resp.raise_for_status()
                data = resp.json()
            processed = data.get("processed", 0)
            return HTMLResponse(f'<span class="text-green-400 text-sm">Connected ({processed} processed)</span>')

        elif app == "prowlarr":
            endpoint = f"{url.rstrip('/')}/api/v1/system/status"
            headers = {"X-Api-Key": api_key}
            with httpx.Client(timeout=10) as client:
                resp = client.get(endpoint, headers=headers)
                resp.raise_for_status()
                data = resp.json()
            version = data.get("version", "unknown")
            return HTMLResponse(f'<span class="text-green-400 text-sm">Connected (v{version})</span>')

        elif app == "huntarr":
            endpoint = f"{url.rstrip('/')}/api/v1/status"
            with httpx.Client(timeout=10) as client:
                resp = client.get(endpoint)
                resp.raise_for_status()
            return HTMLResponse('<span class="text-green-400 text-sm">Connected</span>')

        else:
            return HTMLResponse('<span class="text-yellow-400 text-sm">Unknown app</span>')

    except Exception as e:
        short_err = str(e)[:80]
        return HTMLResponse(f'<span class="text-red-400 text-sm">Error: {short_err}</span>')
