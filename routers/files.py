import os
import shutil

import aiofiles
from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse

from auth import require_auth
from config import FILES_ROOT
from templates_config import templates

router = APIRouter(prefix="/files")

ALLOWED_ROOT = FILES_ROOT


def _safe_path(path: str | None) -> str:
    """Resolve path and ensure it stays within ALLOWED_ROOT."""
    if not path:
        return ALLOWED_ROOT
    resolved = os.path.realpath(os.path.abspath(path))
    if resolved != ALLOWED_ROOT and not resolved.startswith(ALLOWED_ROOT + "/"):
        raise ValueError("Zugriff verweigert: Pfad außerhalb des erlaubten Bereichs.")
    return resolved


def _format_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 ** 2:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 ** 3:
        return f"{size_bytes / 1024 ** 2:.1f} MB"
    else:
        return f"{size_bytes / 1024 ** 3:.2f} GB"


def _get_entries(path: str) -> list[dict]:
    entries = []
    try:
        for name in os.listdir(path):
            full = os.path.join(path, name)
            try:
                stat = os.stat(full)
                is_dir = os.path.isdir(full)
                entries.append({
                    "name": name,
                    "path": full,
                    "is_dir": is_dir,
                    "size": stat.st_size if not is_dir else 0,
                    "size_fmt": _format_size(stat.st_size) if not is_dir else "",
                })
            except (PermissionError, OSError):
                pass
    except (PermissionError, OSError):
        pass
    entries.sort(key=lambda x: (not x["is_dir"], x["name"].lower()))
    return entries


def _get_breadcrumbs(path: str) -> list[dict]:
    parts = []
    p = path
    while True:
        parent = os.path.dirname(p)
        parts.append({"name": os.path.basename(p) or p, "path": p})
        if p == ALLOWED_ROOT or parent == p:
            break
        p = parent
    parts.reverse()
    return parts


def _browser_response(request: Request, path: str):
    entries = _get_entries(path)
    breadcrumbs = _get_breadcrumbs(path)
    return templates.TemplateResponse("partials/file_browser.html", {
        "request": request,
        "current_path": path,
        "entries": entries,
        "breadcrumbs": breadcrumbs,
    })


@router.get("", response_class=HTMLResponse)
async def files_page(request: Request, auth=Depends(require_auth)):
    return templates.TemplateResponse("files.html", {
        "request": request,
        "title": "Dateien",
        "initial_path": ALLOWED_ROOT,
    })


@router.get("/browse", response_class=HTMLResponse)
async def browse(
    request: Request,
    path: str = Query(default=ALLOWED_ROOT),
    auth=Depends(require_auth),
):
    try:
        safe = _safe_path(path)
    except ValueError as e:
        return HTMLResponse(f'<div class="text-red-400 p-4 text-sm">{e}</div>')
    if not os.path.isdir(safe):
        return HTMLResponse('<div class="text-red-400 p-4 text-sm">Kein Verzeichnis.</div>')
    return _browser_response(request, safe)


@router.get("/download")
async def download(
    request: Request,
    path: str = Query(...),
    auth=Depends(require_auth),
):
    try:
        safe = _safe_path(path)
    except ValueError:
        return HTMLResponse("Zugriff verweigert.", status_code=403)
    if not os.path.isfile(safe):
        return HTMLResponse("Datei nicht gefunden.", status_code=404)
    return FileResponse(safe, filename=os.path.basename(safe))


@router.post("/upload", response_class=HTMLResponse)
async def upload(
    request: Request,
    path: str = Query(...),
    file: UploadFile = File(...),
    auth=Depends(require_auth),
):
    try:
        safe_dir = _safe_path(path)
    except ValueError as e:
        return HTMLResponse(f'<div class="text-red-400 p-4 text-sm">{e}</div>')
    if not os.path.isdir(safe_dir):
        return HTMLResponse('<div class="text-red-400 p-4 text-sm">Ungültiges Zielverzeichnis.</div>')

    filename = os.path.basename(file.filename or "upload")
    dest = os.path.join(safe_dir, filename)
    try:
        async with aiofiles.open(dest, "wb") as f:
            content = await file.read()
            await f.write(content)
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-4 text-sm">Upload fehlgeschlagen: {e}</div>')
    return _browser_response(request, safe_dir)


@router.post("/mkdir", response_class=HTMLResponse)
async def mkdir(
    request: Request,
    path: str = Form(...),
    name: str = Form(...),
    auth=Depends(require_auth),
):
    try:
        safe_dir = _safe_path(path)
        new_dir = _safe_path(os.path.join(safe_dir, os.path.basename(name)))
    except ValueError as e:
        return HTMLResponse(f'<div class="text-red-400 p-4 text-sm">{e}</div>')
    try:
        os.makedirs(new_dir, exist_ok=True)
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-4 text-sm">Fehler: {e}</div>')
    return _browser_response(request, safe_dir)


@router.post("/delete", response_class=HTMLResponse)
async def delete(
    request: Request,
    path: str = Form(...),
    current_path: str = Form(...),
    auth=Depends(require_auth),
):
    try:
        safe = _safe_path(path)
        safe_current = _safe_path(current_path)
    except ValueError as e:
        return HTMLResponse(f'<div class="text-red-400 p-4 text-sm">{e}</div>')
    if safe == ALLOWED_ROOT:
        return HTMLResponse('<div class="text-red-400 p-4 text-sm">Stammverzeichnis kann nicht gelöscht werden.</div>')
    try:
        if os.path.isdir(safe):
            shutil.rmtree(safe)
        else:
            os.remove(safe)
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-4 text-sm">Fehler: {e}</div>')
    return _browser_response(request, safe_current)


@router.get("/rename-form", response_class=HTMLResponse)
async def rename_form(
    request: Request,
    path: str = Query(...),
    index: int = Query(...),
    auth=Depends(require_auth),
):
    try:
        safe = _safe_path(path)
    except ValueError as e:
        return HTMLResponse(f'<div class="text-red-400 p-2 text-sm">{e}</div>')
    name = os.path.basename(safe)
    parent = os.path.dirname(safe)
    # Returns an inline rename form that replaces the entry row
    return HTMLResponse(f"""
<div id="entry-{index}" class="flex items-center gap-2 px-4 py-2 border-b border-gray-800 bg-gray-800/60">
    <form hx-post="/files/rename" hx-target="#file-browser" hx-swap="innerHTML" class="flex items-center gap-2 flex-1">
        <input type="hidden" name="path" value="{safe}">
        <input type="text" name="new_name" value="{name}"
            class="flex-1 bg-gray-700 border border-blue-500 rounded px-2 py-1 text-sm text-gray-100 focus:outline-none"
            autofocus>
        <button type="submit" class="text-blue-400 hover:text-blue-300 text-xs px-2 py-1 rounded bg-blue-900/40">OK</button>
        <button type="button"
            hx-get="/files/browse?path={parent}"
            hx-target="#file-browser"
            hx-swap="innerHTML"
            class="text-gray-500 hover:text-gray-300 text-xs px-2 py-1 rounded bg-gray-700">Abbrechen</button>
    </form>
</div>
""")


@router.post("/rename", response_class=HTMLResponse)
async def rename(
    request: Request,
    path: str = Form(...),
    new_name: str = Form(...),
    auth=Depends(require_auth),
):
    try:
        safe = _safe_path(path)
        parent = os.path.dirname(safe)
        new_path = _safe_path(os.path.join(parent, os.path.basename(new_name)))
    except ValueError as e:
        return HTMLResponse(f'<div class="text-red-400 p-4 text-sm">{e}</div>')
    try:
        os.rename(safe, new_path)
    except Exception as e:
        return HTMLResponse(f'<div class="text-red-400 p-4 text-sm">Fehler: {e}</div>')
    return _browser_response(request, parent)
