from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, Request
from fastapi.responses import RedirectResponse
from jose import JWTError, jwt

from config import get_session_secret

COOKIE_NAME = "waa_session"
TOKEN_EXPIRE_DAYS = 7
ALGORITHM = "HS256"


def _get_secret() -> str:
    return get_session_secret()


def create_token(data: dict) -> str:
    secret = _get_secret()
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(days=TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, secret, algorithm=ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        secret = _get_secret()
        payload = jwt.decode(token, secret, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_token_from_request(request: Request) -> Optional[str]:
    return request.cookies.get(COOKIE_NAME)


def require_auth(request: Request) -> dict:
    token = get_token_from_request(request)
    if not token:
        raise _redirect_to_login()
    payload = decode_token(token)
    if not payload:
        raise _redirect_to_login()
    return payload


def _redirect_to_login():
    from fastapi import HTTPException
    # We use a special exception that main.py catches to redirect
    return RedirectException(location="/login")


class RedirectException(Exception):
    def __init__(self, location: str):
        self.location = location
