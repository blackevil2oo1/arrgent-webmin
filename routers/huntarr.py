from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from templates_config import templates
from auth import require_auth
from config import get_app_config
from controllers.huntarr_controller import HuntarrController

router = APIRouter(prefix="/huntarr")

NOT_CONFIGURED = """<div class="bg-yellow-900/30 border border-yellow-700 rounded-lg p-6 text-center">
    <p class="text-yellow-300 mb-2">Huntarr is not configured.</p>
    <a href="/settings" class="text-blue-400 underline">Go to Settings</a>
</div>"""


def _get_controller():
    cfg = get_app_config("huntarr")
    if not cfg.enabled or not cfg.url:
        return None
    return HuntarrController(cfg.url)


@router.get("", response_class=HTMLResponse)
async def huntarr_page(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    configured = ctrl is not None

    status = None
    logs = []

    if configured:
        try:
            status = ctrl.get_status()
        except Exception as e:
            status = {"error": str(e)}
        try:
            logs = ctrl.get_logs(limit=30)
        except Exception:
            logs = []

    return templates.TemplateResponse("huntarr.html", {
        "request": request,
        "title": "Huntarr",
        "configured": configured,
        "status": status,
        "logs": logs,
    })


@router.post("/trigger/{app}", response_class=HTMLResponse)
async def trigger_hunt(request: Request, app: str, auth=Depends(require_auth)):
    if app not in ("movies", "shows", "music", "books"):
        return HTMLResponse('<span class="text-red-400 text-sm">Unknown app type</span>')

    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        ctrl.trigger(app)
        return HTMLResponse(f"""
        <div class="bg-green-900/30 border border-green-700 rounded-lg p-3 text-green-300 text-sm">
            Hunt für <strong>{app}</strong> gestartet.
        </div>""")
    except Exception as e:
        return HTMLResponse(f'<div class="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm">Fehler: {e}</div>')
