from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from templates_config import templates
from auth import require_auth
from config import get_settings, get_app_config
from controllers.docker_controller import DockerController
from controllers.sabnzbd_controller import SabnzbdController
from controllers.system_controller import SystemController
from controllers.jellyfin_controller import JellyfinController

router = APIRouter()


def _not_configured_html(app_name: str) -> str:
    return f"""<div class="text-gray-400 text-sm p-4 text-center">
        {app_name} not configured — <a href="/settings" class="text-blue-400 underline">Go to Settings</a>
    </div>"""


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request, auth=Depends(require_auth)):
    settings = get_settings()
    apps = settings.get("apps", {})

    context = {
        "request": request,
        "apps": apps,
        "title": "Dashboard"
    }

    queue_data = None
    containers_data = None
    system_data = None
    recent_media = None
    notifications = []

    sab_cfg = get_app_config("sabnzbd")
    if sab_cfg.enabled and sab_cfg.url:
        try:
            queue_data = SabnzbdController(sab_cfg.url, sab_cfg.api_key).get_queue()
        except Exception as e:
            queue_data = {"error": str(e)}

    if apps.get("docker", {}).get("enabled"):
        try:
            containers_data = DockerController().get_containers()
        except Exception as e:
            containers_data = {"error": str(e)}

    sys_cfg = get_app_config("system")
    if sys_cfg.enabled and sys_cfg.url:
        try:
            sys_ctrl = SystemController(sys_cfg.url, sys_cfg.api_key)
            system_data = sys_ctrl.get_system_status()
            try:
                system_data.update(sys_ctrl.get_live_metrics())
            except Exception:
                pass
            try:
                notifications = sys_ctrl.get_notifications()
            except Exception:
                pass
        except Exception as e:
            system_data = {"error": str(e)}

    jf_cfg = get_app_config("jellyfin")
    if jf_cfg.enabled and jf_cfg.url:
        try:
            recent_media = JellyfinController(jf_cfg.url, jf_cfg.api_key).get_recent_media(limit=5)
        except Exception as e:
            recent_media = {"error": str(e)}

    context.update({
        "queue_data": queue_data,
        "containers_data": containers_data,
        "system_data": system_data,
        "recent_media": recent_media,
        "notifications": notifications,
    })

    return templates.TemplateResponse("dashboard.html", context)


@router.get("/partial/queue", response_class=HTMLResponse)
async def partial_queue(request: Request, auth=Depends(require_auth)):
    cfg = get_app_config("sabnzbd")
    if not cfg.enabled or not cfg.url:
        return HTMLResponse(_not_configured_html("SABnzbd"))
    try:
        queue = SabnzbdController(cfg.url, cfg.api_key).get_queue()
        return templates.TemplateResponse("partials/queue_widget.html", {
            "request": request,
            "queue": queue
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 text-sm p-2">Queue error: {e}</div>')


@router.get("/partial/containers", response_class=HTMLResponse)
async def partial_containers(request: Request, auth=Depends(require_auth)):
    settings = get_settings()
    if not settings.get("apps", {}).get("docker", {}).get("enabled"):
        return HTMLResponse(_not_configured_html("Docker"))
    try:
        containers = DockerController().get_containers()
        running = sum(1 for c in containers if c["running"])
        return templates.TemplateResponse("partials/containers_widget.html", {
            "request": request,
            "containers": containers,
            "running": running,
            "total": len(containers)
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 text-sm p-2">Docker error: {e}</div>')


@router.get("/partial/system", response_class=HTMLResponse)
async def partial_system(request: Request, auth=Depends(require_auth)):
    cfg = get_app_config("system")
    if not cfg.enabled or not cfg.url:
        return HTMLResponse(_not_configured_html("System"))
    try:
        sys_ctrl = SystemController(cfg.url, cfg.api_key)
        status = sys_ctrl.get_system_status()
        try:
            status.update(sys_ctrl.get_live_metrics())
        except Exception:
            pass
        return templates.TemplateResponse("partials/system_widget.html", {
            "request": request,
            "status": status
        })
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 text-sm p-2">System error: {e}</div>')


@router.get("/partial/notifications", response_class=HTMLResponse)
async def partial_notifications(request: Request, auth=Depends(require_auth)):
    cfg = get_app_config("system")
    if not cfg.enabled or not cfg.url:
        return HTMLResponse("")
    try:
        notifications = SystemController(cfg.url, cfg.api_key).get_notifications()
        if not notifications:
            return HTMLResponse("")
        return templates.TemplateResponse("partials/notifications_banner.html", {
            "request": request,
            "notifications": notifications
        })
    except Exception:
        return HTMLResponse("")
