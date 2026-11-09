from itsdangerous import URLSafeTimedSerializer, BadSignature
from fastapi import Request, HTTPException
from .config import settings

_signer = URLSafeTimedSerializer(settings.SECRET_KEY, salt="auth")

def make_cookie() -> str:
    return _signer.dumps({"u": settings.ADMIN_USER})

def check_cookie(cookie: str | None) -> bool:
    if not cookie:
        return False
    try:
        _signer.loads(cookie, max_age=60 * 60 * 24 * 14)
        return True
    except BadSignature:
        return False

def require_login(request: Request):
    if not check_cookie(request.cookies.get("mp_session")):
        raise HTTPException(status_code=401, detail="login required")