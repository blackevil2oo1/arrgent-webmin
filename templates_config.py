"""Shared Jinja2Templates instance with global context injection."""
from urllib.parse import quote as urlquote
from fastapi.templating import Jinja2Templates
from config import get_settings

_templates = Jinja2Templates(directory="templates")

# Add a global function to get current settings for nav rendering
_templates.env.globals["get_settings"] = get_settings
_templates.env.globals["urlquote"] = urlquote

templates = _templates
