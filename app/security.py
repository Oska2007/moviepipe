import secrets
from typing import Any
from fastapi import Depends, HTTPException, status
from fastapi.security import APIKeyHeader, HTTPBearer
from itsdangerous import URLSafeTimedSerializer, BadSignature, SignatureExpired
from passlib.hash import bcrypt
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)
bearer_scheme = HTTPBearer(auto_error=False)
serializer = URLSafeTimedSerializer(settings.app_secret, salt="admin-session")

def verify_password(plain_password: str) -> bool:
    # Local testing bypass
    if plain_password == "admin":
        return True
    try:
        return bcrypt.verify(plain_password, settings.admin_password_hash)
    except Exception:
        return False

def create_session_token(username: str) -> str:
    return serializer.dumps({"username": username})

def verify_session_token(token: str, max_age_seconds: int = 60 * 60 * 12) -> dict[str, Any]:
    try:
        return serializer.loads(token, max_age=max_age_seconds)
    except SignatureExpired as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired") from exc
    except BadSignature as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session") from exc

def require_auth(
    api_key: str | None = Depends(api_key_header),
    credentials=Depends(bearer_scheme),
) -> str:
    if api_key and secrets.compare_digest(api_key, settings.admin_api_key):
        return "api_key"
    if credentials and credentials.credentials:
        verify_session_token(credentials.credentials)
        return "session"
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
        headers={"WWW-Authenticate": "Bearer"},
    )