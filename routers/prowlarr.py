from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from templates_config import templates
from auth import require_auth
from config import get_app_config
from controllers.prowlarr_controller import ProwlarrController

router = APIRouter(prefix="/prowlarr")

NOT_CONFIGURED = """<div class="bg-yellow-900/30 border border-yellow-700 rounded-lg p-6 text-center">
    <p class="text-yellow-300 mb-2">Prowlarr is not configured.</p>
    <a href="/settings" class="text-blue-400 underline">Go to Settings</a>
</div>"""


def _get_controller():
    cfg = get_app_config("prowlarr")
    if not cfg.enabled or not cfg.url or not cfg.api_key:
        return None
    return ProwlarrController(cfg.url, cfg.api_key)


@router.get("", response_class=HTMLResponse)
async def prowlarr_page(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    configured = ctrl is not None

    status = None
    indexers = []
    history = []

    if configured:
        try:
            status = ctrl.get_system_status()
        except Exception as e:
            status = {"error": str(e)}
        try:
            indexers = ctrl.get_indexers()
        except Exception:
            indexers = []
        try:
            history = ctrl.get_history(take=15)
        except Exception:
            history = []

    return templates.TemplateResponse("prowlarr.html", {
        "request": request,
        "title": "Prowlarr",
        "configured": configured,
        "status": status,
        "indexers": indexers,
        "history": history,
    })
