from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from templates_config import templates
from auth import require_auth
from config import get_app_config
from controllers.sabnzbd_controller import SabnzbdController

router = APIRouter(prefix="/sabnzbd")

NOT_CONFIGURED = """<div class="bg-yellow-900/30 border border-yellow-700 rounded-lg p-6 text-center">
    <p class="text-yellow-300 mb-2">SABnzbd is not configured.</p>
    <a href="/settings" class="text-blue-400 underline">Go to Settings</a>
</div>"""


def _get_controller():
    cfg = get_app_config("sabnzbd")
    if not cfg.enabled or not cfg.url:
        return None
    return SabnzbdController(cfg.url, cfg.api_key)


@router.get("", response_class=HTMLResponse)
async def sabnzbd_page(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    configured = ctrl is not None

    queue = None
    history = None

    if configured:
        try:
            queue = ctrl.get_queue()
        except Exception as e:
            queue = {"error": str(e)}
        try:
            history = ctrl.get_history(limit=10)
        except Exception as e:
            history = []

    return templates.TemplateResponse("sabnzbd.html", {
        "request": request,
        "title": "SABnzbd",
        "configured": configured,
        "queue": queue,
        "history": history
    })


@router.get("/partial/queue", response_class=HTMLResponse)
async def partial_queue(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        queue = ctrl.get_queue()
        return templates.TemplateResponse("partials/sabnzbd_queue.html", {
            "request": request,
            "queue": queue
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-2 text-sm">Queue error: {e}</div>')


@router.post("/pause", response_class=HTMLResponse)
async def pause_queue(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        ctrl.pause_queue()
        queue = ctrl.get_queue()
        return templates.TemplateResponse("partials/sabnzbd_queue.html", {
            "request": request,
            "queue": queue
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-2">Error: {e}</div>')


@router.post("/resume", response_class=HTMLResponse)
async def resume_queue(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        ctrl.resume_queue()
        queue = ctrl.get_queue()
        return templates.TemplateResponse("partials/sabnzbd_queue.html", {
            "request": request,
            "queue": queue
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-2">Error: {e}</div>')
