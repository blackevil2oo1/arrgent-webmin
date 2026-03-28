from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from templates_config import templates
from auth import require_auth
from config import get_app_config
from controllers.jellyseerr_controller import JellyseerrController

router = APIRouter(prefix="/jellyseerr")

NOT_CONFIGURED = """<div class="bg-yellow-900/30 border border-yellow-700 rounded-lg p-6 text-center">
    <p class="text-yellow-300 mb-2">Jellyseerr is not configured.</p>
    <a href="/settings" class="text-blue-400 underline">Go to Settings</a>
</div>"""


def _get_controller():
    cfg = get_app_config("jellyseerr")
    if not cfg.enabled or not cfg.url or not cfg.api_key:
        return None
    return JellyseerrController(cfg.url, cfg.api_key)


@router.get("", response_class=HTMLResponse)
async def jellyseerr_page(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    configured = ctrl is not None

    counts = None
    pending = []
    recent = []

    if configured:
        try:
            counts = ctrl.get_request_counts()
        except Exception as e:
            counts = {"error": str(e)}
        try:
            pending = ctrl.get_pending_requests(take=20)
        except Exception:
            pending = []
        try:
            recent = ctrl.get_recent_requests(take=15)
        except Exception:
            recent = []

    return templates.TemplateResponse("jellyseerr.html", {
        "request": request,
        "title": "Jellyseerr",
        "configured": configured,
        "counts": counts,
        "pending": pending,
        "recent": recent,
    })


@router.post("/request/{request_id}/approve", response_class=HTMLResponse)
async def approve_request(request: Request, request_id: int, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        ctrl.approve_request(request_id)
        return HTMLResponse(f"""
        <div class="flex items-center gap-2 text-green-400 text-xs py-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"/></svg>
            Approved
        </div>""")
    except Exception as e:
        return HTMLResponse(f'<span class="text-red-400 text-xs">Error: {e}</span>')


@router.post("/request/{request_id}/decline", response_class=HTMLResponse)
async def decline_request(request: Request, request_id: int, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        ctrl.decline_request(request_id)
        return HTMLResponse(f"""
        <div class="flex items-center gap-2 text-red-400 text-xs py-1">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/></svg>
            Declined
        </div>""")
    except Exception as e:
        return HTMLResponse(f'<span class="text-red-400 text-xs">Error: {e}</span>')
