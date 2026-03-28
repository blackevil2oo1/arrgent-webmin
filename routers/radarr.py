from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse

from templates_config import templates
from auth import require_auth
from config import get_app_config
from controllers.radarr_controller import RadarrController

router = APIRouter(prefix="/radarr")

NOT_CONFIGURED = """<div class="bg-yellow-900/30 border border-yellow-700 rounded-lg p-6 text-center">
    <p class="text-yellow-300 mb-2">Radarr is not configured.</p>
    <a href="/settings" class="text-blue-400 underline">Go to Settings</a>
</div>"""


def _get_controller():
    cfg = get_app_config("radarr")
    if not cfg.enabled or not cfg.url:
        return None
    return RadarrController(cfg.url, cfg.api_key)


@router.get("", response_class=HTMLResponse)
async def radarr_page(request: Request, auth=Depends(require_auth)):
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
            recent = ctrl.get_recent_movies(limit=10)
        except Exception as e:
            recent = []
        try:
            profiles = ctrl.get_quality_profiles()
        except Exception:
            profiles = []

    return templates.TemplateResponse("radarr.html", {
        "request": request,
        "title": "Radarr",
        "configured": configured,
        "stats": stats,
        "recent": recent,
        "profiles": profiles
    })


@router.post("/search", response_class=HTMLResponse)
async def search_movie(request: Request, query: str = Form(...), auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        results = ctrl.search_movie(query)
        profiles = ctrl.get_quality_profiles()
        return templates.TemplateResponse("partials/movie_search_results.html", {
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
async def add_movie(
    request: Request,
    tmdb_id: int = Form(...),
    title: str = Form(...),
    year: int = Form(...),
    quality_profile_id: int = Form(...),
    auth=Depends(require_auth)
):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        result = ctrl.add_movie(tmdb_id, title, year, quality_profile_id)
        return HTMLResponse(f"""
        <div class="bg-green-900/30 border border-green-700 rounded-lg p-4">
            <p class="text-green-300">Added <strong>{result['title']}</strong> ({result['year']}) to Radarr!</p>
        </div>""")
    except Exception as e:
        return HTMLResponse(f"""
        <div class="bg-red-900/30 border border-red-700 rounded-lg p-4">
            <p class="text-red-300">Failed to add movie: {e}</p>
        </div>""")


@router.get("/recent", response_class=HTMLResponse)
async def recent_movies(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        recent = ctrl.get_recent_movies(limit=10)
        return templates.TemplateResponse("partials/recent_movies.html", {
            "request": request,
            "recent": recent
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-4">Error: {e}</div>')


@router.get("/missing", response_class=HTMLResponse)
async def missing_movies(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        missing = ctrl.get_missing_movies()
        return templates.TemplateResponse("partials/missing_movies.html", {
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
