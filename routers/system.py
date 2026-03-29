from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from templates_config import templates
from auth import require_auth
from config import get_app_config
from controllers.system_controller import SystemController

router = APIRouter(prefix="/system")

NOT_CONFIGURED = """<div class="bg-yellow-900/30 border border-yellow-700 rounded-lg p-6 text-center">
    <p class="text-yellow-300 mb-2">System monitor is not configured.</p>
    <a href="/settings" class="text-blue-400 underline">Go to Settings</a>
</div>"""


def _get_controller():
    cfg = get_app_config("system")
    if not cfg.enabled or not cfg.url:
        return None
    return SystemController(cfg.url, cfg.api_key)


@router.get("", response_class=HTMLResponse)
async def system_page(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    # No data fetched on initial load — all sections lazy-load via HTMX
    return templates.TemplateResponse("system.html", {
        "request": request,
        "title": "System",
        "configured": ctrl is not None,
    })


@router.get("/partial/metrics", response_class=HTMLResponse)
async def partial_metrics(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)
    try:
        metrics = await ctrl.get_live_metrics()
        return templates.TemplateResponse("partials/live_metrics.html", {
            "request": request,
            "metrics": metrics
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-2 text-sm">Metrics error: {e}</div>')


@router.get("/partial/status", response_class=HTMLResponse)
async def partial_status(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)
    try:
        status = await ctrl.get_system_status()
        return templates.TemplateResponse("partials/system_status.html", {
            "request": request,
            "status": status
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-2 text-sm">System error: {e}</div>')


@router.get("/partial/disks", response_class=HTMLResponse)
async def partial_disks(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)
    try:
        disks = await ctrl.get_disk_health()
        return templates.TemplateResponse("partials/disk_health.html", {
            "request": request,
            "disks": disks
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-2 text-sm">Disk query error: {e}</div>')


@router.get("/partial/shares", response_class=HTMLResponse)
async def partial_shares(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)
    try:
        shares = await ctrl.get_shares()
        return templates.TemplateResponse("partials/shares.html", {
            "request": request,
            "shares": shares
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-2 text-sm">Shares error: {e}</div>')


@router.get("/partial/notifications", response_class=HTMLResponse)
async def partial_notifications(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse("")
    try:
        notifications = await ctrl.get_notifications()
        if not notifications:
            return HTMLResponse("")
        return templates.TemplateResponse("partials/notifications_banner.html", {
            "request": request,
            "notifications": notifications
        })
    except Exception:
        return HTMLResponse("")


@router.post("/reboot", response_class=HTMLResponse)
async def system_reboot(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)
    try:
        await ctrl.reboot()
        return HTMLResponse("""
        <div class="bg-yellow-900/30 border border-yellow-700 rounded-lg p-3 text-yellow-300 text-sm">
            Reboot wird durchgeführt... Server ist gleich nicht mehr erreichbar.
        </div>""")
    except Exception as e:
        return HTMLResponse(f'<div class="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm">Fehler: {e}</div>')


@router.post("/shutdown", response_class=HTMLResponse)
async def system_shutdown(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)
    try:
        await ctrl.shutdown()
        return HTMLResponse("""
        <div class="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm">
            Shutdown wird durchgeführt... Server fährt herunter.
        </div>""")
    except Exception as e:
        return HTMLResponse(f'<div class="bg-red-900/30 border border-red-700 rounded-lg p-3 text-red-300 text-sm">Fehler: {e}</div>')


@router.get("/partial/parity", response_class=HTMLResponse)
async def partial_parity(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse("")
    try:
        parity_history = await ctrl.get_parity_history()
        if not parity_history:
            return HTMLResponse('<p class="text-gray-500 text-sm">Keine Parity-Historie.</p>')
        return templates.TemplateResponse("partials/parity_history.html", {
            "request": request,
            "parity_history": parity_history
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-2 text-sm">Parity error: {e}</div>')
