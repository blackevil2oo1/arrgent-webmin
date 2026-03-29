from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
import httpx

from templates_config import templates
from auth import require_auth
from config import get_app_config
from controllers.fileflows_controller import FileFlowsController

router = APIRouter(prefix="/fileflows")

NOT_CONFIGURED = """<div class="bg-yellow-900/30 border border-yellow-700 rounded-lg p-6 text-center">
    <p class="text-yellow-300 mb-2">FileFlows is not configured.</p>
    <a href="/settings" class="text-blue-400 underline">Go to Settings</a>
</div>"""


def _get_controller():
    cfg = get_app_config("fileflows")
    if not cfg.enabled or not cfg.url:
        return None
    return FileFlowsController(cfg.url)


def _error_html(e: Exception, context: str = "") -> str:
    prefix = f"{context}: " if context else ""
    if isinstance(e, (httpx.ConnectError, httpx.ConnectTimeout)):
        msg = f"{prefix}FileFlows nicht erreichbar"
    elif isinstance(e, httpx.TimeoutException):
        msg = f"{prefix}Timeout — FileFlows antwortet nicht"
    elif isinstance(e, httpx.HTTPStatusError):
        msg = f"{prefix}API-Fehler (HTTP {e.response.status_code})"
    else:
        msg = f"{prefix}Fehler: {type(e).__name__}"
    return f'<div class="text-red-400 p-2 text-sm">{msg}</div>'


@router.get("", response_class=HTMLResponse)
async def fileflows_page(request: Request, auth=Depends(require_auth)):
    cfg = get_app_config("fileflows")
    ctrl = _get_controller()
    configured = ctrl is not None
    container_name = cfg.container_name

    return templates.TemplateResponse("fileflows.html", {
        "request": request,
        "title": "FileFlows",
        "configured": configured,
        "container_name": container_name,
    })


@router.get("/partial/nodes", response_class=HTMLResponse)
async def partial_nodes(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse("")
    try:
        nodes = ctrl.get_nodes()
        if not nodes:
            return HTMLResponse("")
        return templates.TemplateResponse("partials/fileflows_nodes.html", {
            "request": request,
            "nodes": nodes,
        })
    except Exception:
        return HTMLResponse("")


@router.get("/partial/savings", response_class=HTMLResponse)
async def partial_savings(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)
    try:
        savings = ctrl.get_savings()
        return templates.TemplateResponse("partials/fileflows_savings.html", {
            "request": request,
            "savings": savings
        })
    except Exception as e:
        return HTMLResponse(_error_html(e))


@router.get("/partial/status", response_class=HTMLResponse)
async def partial_status(request: Request, auth=Depends(require_auth)):
    ctrl = _get_controller()
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        ff_status = ctrl.get_status()
        return templates.TemplateResponse("partials/fileflows_status.html", {
            "request": request,
            "ff_status": ff_status
        })
    except Exception as e:
        return HTMLResponse(_error_html(e))


@router.post("/container/start", response_class=HTMLResponse)
async def container_start(request: Request, auth=Depends(require_auth)):
    container_name = get_app_config("fileflows").container_name

    try:
        import docker
        client = docker.from_env()
        container = client.containers.get(container_name)
        container.start()
        return HTMLResponse(f"""
        <div class="bg-green-900/30 border border-green-700 rounded-lg p-3 text-sm text-green-300">
            Container <strong>{container_name}</strong> started.
        </div>""")
    except Exception as e:
        return HTMLResponse(f'<div class="bg-red-900/30 border border-red-700 rounded-lg p-3 text-sm text-red-300">Error: {e}</div>')


@router.post("/container/stop", response_class=HTMLResponse)
async def container_stop(request: Request, auth=Depends(require_auth)):
    container_name = get_app_config("fileflows").container_name

    try:
        import docker
        client = docker.from_env()
        container = client.containers.get(container_name)
        container.stop(timeout=10)
        return HTMLResponse(f"""
        <div class="bg-yellow-900/30 border border-yellow-700 rounded-lg p-3 text-sm text-yellow-300">
            Container <strong>{container_name}</strong> stopped.
        </div>""")
    except Exception as e:
        return HTMLResponse(f'<div class="bg-red-900/30 border border-red-700 rounded-lg p-3 text-sm text-red-300">Error: {e}</div>')
