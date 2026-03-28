from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse

from templates_config import templates
from auth import require_auth
from config import get_settings
from controllers.docker_controller import DockerController

router = APIRouter(prefix="/docker")

NOT_CONFIGURED = """<div class="bg-yellow-900/30 border border-yellow-700 rounded-lg p-6 text-center">
    <p class="text-yellow-300 mb-2">Docker is not enabled.</p>
    <a href="/settings" class="text-blue-400 underline">Go to Settings</a>
</div>"""


def _get_controller(settings: dict):
    cfg = settings.get("apps", {}).get("docker", {})
    if not cfg.get("enabled"):
        return None
    return DockerController()


@router.get("", response_class=HTMLResponse)
async def docker_page(request: Request, auth=Depends(require_auth)):
    settings = get_settings()
    ctrl = _get_controller(settings)
    configured = ctrl is not None

    containers = None
    if configured:
        try:
            containers = ctrl.get_containers()
        except Exception as e:
            containers = {"error": str(e)}

    return templates.TemplateResponse("docker.html", {
        "request": request,
        "title": "Docker",
        "configured": configured,
        "containers": containers
    })


@router.get("/partial/status", response_class=HTMLResponse)
async def partial_status(request: Request, auth=Depends(require_auth)):
    settings = get_settings()
    ctrl = _get_controller(settings)
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        containers = ctrl.get_containers()
        return templates.TemplateResponse("partials/docker_containers.html", {
            "request": request,
            "containers": containers
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-2 text-sm">Docker error: {e}</div>')


@router.post("/action", response_class=HTMLResponse)
async def container_action(
    request: Request,
    name: str = Form(...),
    action: str = Form(...),
    auth=Depends(require_auth)
):
    settings = get_settings()
    ctrl = _get_controller(settings)
    if not ctrl:
        return HTMLResponse(NOT_CONFIGURED)

    try:
        if action == "start":
            result = ctrl.start_container(name)
        elif action == "stop":
            result = ctrl.stop_container(name)
        elif action == "restart":
            result = ctrl.restart_container(name)
        else:
            return HTMLResponse(f'<div class="text-red-400 p-2 text-sm">Unknown action: {action}</div>')

        # Return updated container list
        containers = ctrl.get_containers()
        return templates.TemplateResponse("partials/docker_containers.html", {
            "request": request,
            "containers": containers,
            "action_result": result
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-2 text-sm">Action error: {e}</div>')
