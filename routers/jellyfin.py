from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from templates_config import templates
from auth import require_auth
from config import get_app_config
from controllers.jellyfin_controller import JellyfinController

router = APIRouter(prefix="/jellyfin")

NOT_CONFIGURED = """<div class="bg-yellow-900/30 border border-yellow-700 rounded-lg p-6 text-center">
    <p class="text-yellow-300 mb-2">Jellyfin is not configured.</p>
    <a href="/settings" class="text-blue-400 underline">Go to Settings</a>
</div>"""


def _get_controller():
    cfg = get_app_config("jellyfin")
    if not cfg.enabled or not cfg.url:
        return None
    return JellyfinController(cfg.url, cfg.api_key)


@router.get("", response_class=HTMLResponse)
async def jellyfin_page(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    configured = ctrl is not None

    stats = None
    recent = None

    if configured:
        try:
            stats = ctrl.get_library_stats()
        except Exception as e:
            stats = {"error": str(e)}
        try:
            recent = ctrl.get_recent_media(limit=20)
        except Exception as e:
            recent = []

    return templates.TemplateResponse("jellyfin.html", {
        "request": request,
        "title": "Jellyfin",
        "configured": configured,
        "stats": stats,
        "recent": recent
    })


@router.get("/partial/recent", response_class=HTMLResponse)
async def partial_recent(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        recent = ctrl.get_recent_media(limit=20)
        return templates.TemplateResponse("partials/jellyfin_recent.html", {
            "request": request,
            "recent": recent
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-2">Error: {e}</div>')


@router.post("/scan", response_class=HTMLResponse)
async def trigger_scan(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        result = ctrl.trigger_library_scan()
        return HTMLResponse(f"""
        <div class="bg-green-900/30 border border-green-700 rounded-lg p-3 text-green-300 text-sm">
            {result['message']}
        </div>""")
    except Exception as e:
        return HTMLResponse(f"""
        <div class="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm">
            Scan error: {e}
        </div>""")
