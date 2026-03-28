import os

from fastapi import APIRouter, Request, Depends, Form
from fastapi.responses import HTMLResponse

from templates_config import templates
from auth import require_auth, get_token_from_request
from config import get_settings
from ai.agent import run_agent

router = APIRouter(prefix="/chat")

# Server-side chat history: {session_token: [messages]}
# Max 50 sessions, max 10 messages per session
_chat_sessions: dict[str, list[dict]] = {}
MAX_SESSIONS = 50
MAX_HISTORY = 10


def _get_session_key(request: Request) -> str:
    token = get_token_from_request(request)
    return token or "anonymous"


def _get_history(session_key: str) -> list[dict]:
    return _chat_sessions.get(session_key, [])


def _add_to_history(session_key: str, role: str, content: str):
    if session_key not in _chat_sessions:
        # Evict oldest session if at capacity
        if len(_chat_sessions) >= MAX_SESSIONS:
            oldest_key = next(iter(_chat_sessions))
            del _chat_sessions[oldest_key]
        _chat_sessions[session_key] = []

    _chat_sessions[session_key].append({"role": role, "content": content})

    # Keep only last MAX_HISTORY messages
    if len(_chat_sessions[session_key]) > MAX_HISTORY:
        _chat_sessions[session_key] = _chat_sessions[session_key][-MAX_HISTORY:]


@router.get("", response_class=HTMLResponse)
async def chat_page(request: Request, auth=Depends(require_auth)):
    session_key = _get_session_key(request)
    history = _get_history(session_key)
    return templates.TemplateResponse("chat.html", {
        "request": request,
        "title": "Chat",
        "history": history
    })


@router.post("/message", response_class=HTMLResponse)
async def send_message(
    request: Request,
    message: str = Form(...),
    auth=Depends(require_auth)
):
    session_key = _get_session_key(request)
    settings = get_settings()

    # Check if OpenAI is configured
    if not os.environ.get("OPENAI_API_KEY", ""):
        error_html = _render_message("assistant",
            "OpenAI API key is not configured. Please set OPENAI_API_KEY in the Docker template.")
        return HTMLResponse(_render_message("user", message) + error_html)

    # Add user message to history
    _add_to_history(session_key, "user", message)
    history = _get_history(session_key)

    # Run agent
    try:
        response = run_agent(list(history), settings)
    except Exception as e:
        response = f"Error: {str(e)}"

    # Add assistant response to history
    _add_to_history(session_key, "assistant", response)

    # Return both the user message and the assistant response as HTML fragments
    user_html = _render_message("user", message)
    assistant_html = _render_message("assistant", response)
    return HTMLResponse(user_html + assistant_html)


@router.post("/clear", response_class=HTMLResponse)
async def clear_history(request: Request, auth=Depends(require_auth)):
    session_key = _get_session_key(request)
    if session_key in _chat_sessions:
        del _chat_sessions[session_key]
    return HTMLResponse('<div id="chat-messages" class="flex flex-col gap-3 p-4"></div>')


def _render_message(role: str, content: str) -> str:
    import html as html_module
    safe_content = html_module.escape(content).replace("\n", "<br>")

    if role == "user":
        return f"""
        <div class="flex justify-end">
            <div class="max-w-xs lg:max-w-md xl:max-w-lg bg-blue-600 text-white rounded-2xl rounded-tr-sm px-4 py-2 text-sm">
                {safe_content}
            </div>
        </div>"""
    else:
        # Allow links in assistant messages (simple case)
        content_with_links = content.replace("&lt;a href=", "<a href=").replace("&lt;/a&gt;", "</a>").replace("'", "'")
        return f"""
        <div class="flex justify-start">
            <div class="max-w-xs lg:max-w-md xl:max-w-lg bg-gray-700 text-gray-100 rounded-2xl rounded-tl-sm px-4 py-2 text-sm">
                {safe_content}
            </div>
        </div>"""
