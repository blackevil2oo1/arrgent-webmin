from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

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


@router.get("", response_class=HTMLResponse)
async def fileflows_page(request: Request, auth=Depends(require_auth)):
    cfg = get_app_config("fileflows")
    ctrl = _get_controller()
    configured = ctrl is not None

    nodes = None
    if configured:
        try:
            nodes = ctrl.get_nodes()
        except Exception:
            nodes = []

    container_name = cfg.container_name

    return templates.TemplateResponse("fileflows.html", {
        "request": request,
        "title": "FileFlows",
        "configured": configured,
        "nodes": nodes,
        "container_name": container_name,
    })


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
        return HTMLResponse(f'<div class="text-red-400 p-3 text-sm">Savings error: {e}</div>')


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
        return HTMLResponse(f'<div class="text-red-400 p-2 text-sm">FileFlows error: {e}</div>')


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
