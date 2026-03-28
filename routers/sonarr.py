from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse

from templates_config import templates
from auth import require_auth
from config import get_app_config
from controllers.sonarr_controller import SonarrController

router = APIRouter(prefix="/sonarr")

NOT_CONFIGURED = """<div class="bg-yellow-900/30 border border-yellow-700 rounded-lg p-6 text-center">
    <p class="text-yellow-300 mb-2">Sonarr is not configured.</p>
    <a href="/settings" class="text-blue-400 underline">Go to Settings</a>
</div>"""


def _get_controller():
    cfg = get_app_config("sonarr")
    if not cfg.enabled or not cfg.url:
        return None
    return SonarrController(cfg.url, cfg.api_key)


@router.get("", response_class=HTMLResponse)
async def sonarr_page(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    configured = ctrl is not None

    stats = None
    recent = None
    profiles = []

    if configured:
        try:
            stats = ctrl.get_library_stats()
        except Exception as e:
            stats = {"error": str(e)}
        try:
            recent = ctrl.get_recent_series(limit=10)
        except Exception:
            recent = []
        try:
            profiles = ctrl.get_quality_profiles()
        except Exception:
            profiles = []

    return templates.TemplateResponse("sonarr.html", {
        "request": request,
        "title": "Sonarr",
        "configured": configured,
        "stats": stats,
        "recent": recent,
        "profiles": profiles
    })


@router.post("/search", response_class=HTMLResponse)
async def search_series(request: Request, query: str = Form(...), auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        results = ctrl.search_series(query)
        profiles = ctrl.get_quality_profiles()
        return templates.TemplateResponse("partials/series_search_results.html", {
            "request": request,
            "results": results,
            "profiles": profiles,
            "query": query
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-4">Search error: {e}</div>')


@router.get("/quality-profiles", response_class=HTMLResponse)
async def quality_profiles(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse("<option>Not configured</option>")
    try:
        profiles = ctrl.get_quality_profiles()
        options = "".join(f'<option value="{p["profile_id"]}">{p["name"]}</option>' for p in profiles)
        return HTMLResponse(options)
    except Exception as e:
        return HTMLResponse(f'<option>Error: {e}</option>')


@router.post("/add", response_class=HTMLResponse)
async def add_series(
    request: Request,
    tvdb_id: int = Form(...),
    title: str = Form(...),
    year: int = Form(...),
    quality_profile_id: int = Form(...),
    auth=Depends(require_auth)
):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        result = ctrl.add_series(tvdb_id, title, year, quality_profile_id)
        return HTMLResponse(f"""
        <div class="bg-green-900/30 border border-green-700 rounded-lg p-4">
            <p class="text-green-300">Added <strong>{result['title']}</strong> ({result['year']}) to Sonarr!</p>
        </div>""")
    except Exception as e:
        return HTMLResponse(f"""
        <div class="bg-red-900/30 border border-red-700 rounded-lg p-4">
            <p class="text-red-300">Failed to add series: {e}</p>
        </div>""")


@router.get("/updates", response_class=HTMLResponse)
async def series_updates(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        updates = ctrl.get_series_updates(days=7)
        return templates.TemplateResponse("partials/series_updates.html", {
            "request": request,
            "updates": updates
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-4">Error: {e}</div>')


@router.get("/missing", response_class=HTMLResponse)
async def missing_episodes(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        missing = ctrl.get_missing_episodes(limit=100)
        return templates.TemplateResponse("partials/missing_episodes.html", {
            "request": request,
            "missing": missing
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-4">Error: {e}</div>')


@router.post("/search-missing", response_class=HTMLResponse)
async def search_all_missing(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        result = ctrl.search_all_missing()
        return HTMLResponse(f"""
        <div class="bg-green-900/30 border border-green-700 rounded-lg p-3 text-sm text-green-300">
            ✓ {result['message']}
        </div>""")
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-3 text-sm">Error: {e}</div>')
