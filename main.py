import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta

from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware

from auth import (
    COOKIE_NAME,
    RedirectException,
    create_token,
    decode_token,
    get_token_from_request,
)
from config import ensure_settings_exist, get_settings, get_password_hash, verify_password
from templates_config import templates
from routers import (
    dashboard,
    radarr,
    sonarr,
    sabnzbd,
    jellyfin,
    docker_router,
    system,
    chat,
    settings_router,
)
from routers import fileflows, jellyseerr, files as files_router
from routers import prowlarr, huntarr

# ---------------------------------------------------------------------------
# Brute-force protection (in-memory, resets on restart)
# ---------------------------------------------------------------------------
_login_attempts: dict[str, dict] = {}
# Soft throttle: (min_attempts, wait_seconds)
_THROTTLE = [(7, 300), (5, 120), (3, 30)]
_HARD_LOCK_AFTER = 10
_HARD_LOCK_HOURS = 24


def _check_rate_limit(ip: str) -> tuple[bool, str]:
    info = _login_attempts.get(ip)
    if not info:
        return True, ""
    count: int = info["count"]
    last_fail: datetime = info["last_fail"]
    locked_until: datetime | None = info.get("locked_until")

    if locked_until and datetime.utcnow() < locked_until:
        remaining = locked_until - datetime.utcnow()
        h = int(remaining.total_seconds() // 3600)
        m = int((remaining.total_seconds() % 3600) // 60)
        return False, f"Account gesperrt – noch {h}h {m}m. Bitte warte oder starte den Server neu."

    for threshold, delay_s in _THROTTLE:
        if count >= threshold:
            wait_until = last_fail + timedelta(seconds=delay_s)
            if datetime.utcnow() < wait_until:
                secs = int((wait_until - datetime.utcnow()).total_seconds()) + 1
                return False, f"Zu viele Fehlversuche – bitte {secs} Sekunden warten."
            break

    return True, ""


def _record_failure(ip: str):
    info = _login_attempts.get(ip, {"count": 0})
    count = info["count"] + 1
    locked_until = (
        datetime.utcnow() + timedelta(hours=_HARD_LOCK_HOURS)
        if count >= _HARD_LOCK_AFTER
        else None
    )
    _login_attempts[ip] = {"count": count, "last_fail": datetime.utcnow(), "locked_until": locked_until}


def _clear_failures(ip: str):
    _login_attempts.pop(ip, None)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure settings.json exists on startup
    ensure_settings_exist()
    yield


app = FastAPI(title="Web Admin Agent", lifespan=lifespan)

# Mount static files if directory exists
static_dir = "static"
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


# Middleware to catch RedirectException raised inside Depends
class RedirectMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except RedirectException as e:
            return RedirectResponse(url=e.location, status_code=302)


app.add_middleware(RedirectMiddleware)


# Auth routes
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    # If already authenticated, redirect to dashboard
    token = get_token_from_request(request)
    if token and decode_token(token):
        return RedirectResponse(url="/", status_code=302)

    # Check if this is a first run (still using default "admin" password)
    try:
        first_run = verify_password("admin", get_password_hash())
    except Exception:
        first_run = True

    return templates.TemplateResponse("login.html", {
        "request": request,
        "first_run": first_run,
        "error": None,
        "settings": {}
    })


@app.post("/login")
async def login(request: Request, password: str = Form(...)):
    client_ip = request.client.host if request.client else "unknown"

    allowed, rate_msg = _check_rate_limit(client_ip)
    if not allowed:
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": rate_msg,
            "first_run": False,
            "settings": {}
        }, status_code=429)

    password_hash = get_password_hash()

    if not verify_password(password, password_hash):
        _record_failure(client_ip)
        info = _login_attempts.get(client_ip, {})
        count = info.get("count", 0)
        remaining = _HARD_LOCK_AFTER - count
        hint = f" (noch {remaining} Versuch{'e' if remaining != 1 else ''} bis zur 24h-Sperre)" if count >= 3 else ""
        return templates.TemplateResponse("login.html", {
            "request": request,
            "error": f"Falsches Passwort.{hint}",
            "first_run": False,
            "settings": {}
        }, status_code=401)

    _clear_failures(client_ip)
    token = create_token({"sub": "admin"})
    response = RedirectResponse(url="/", status_code=303)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        max_age=7 * 24 * 3600,
        samesite="lax"
    )
    return response


@app.post("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


# Include all feature routers
app.include_router(dashboard.router)
app.include_router(radarr.router)
app.include_router(sonarr.router)
app.include_router(sabnzbd.router)
app.include_router(jellyfin.router)
app.include_router(docker_router.router)
app.include_router(system.router)
app.include_router(chat.router)
app.include_router(settings_router.router)
app.include_router(fileflows.router)
app.include_router(jellyseerr.router)
app.include_router(files_router.router)
app.include_router(prowlarr.router)
app.include_router(huntarr.router)


# Exception handler for RedirectException (raised from require_auth dependency)
@app.exception_handler(RedirectException)
async def redirect_exception_handler(request: Request, exc: RedirectException):
    return RedirectResponse(url=exc.location, status_code=302)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8088, reload=True)
