"""Small, dependency-free signed bearer-token authentication layer."""

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from .database import get_session
from .models import User
from .settings import get_settings

bearer_scheme = HTTPBearer(auto_error=False)
TOKEN_LIFETIME_HOURS = 24 * 7


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 310_000)
    return f"{salt}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    try:
        salt, _ = stored.split("$", 1)
    except ValueError:
        return False
    return hmac.compare_digest(hash_password(password, salt), stored)


def _encode(data: dict) -> str:
    return base64.urlsafe_b64encode(json.dumps(data, separators=(",", ":")).encode()).rstrip(b"=").decode()


def _decode(value: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(value + "=" * (-len(value) % 4)))


def create_access_token(user: User) -> str:
    header = _encode({"alg": "HS256", "typ": "JWT"})
    payload = _encode({"sub": str(user.id), "exp": int((datetime.now(timezone.utc) + timedelta(hours=TOKEN_LIFETIME_HOURS)).timestamp())})
    signature = hmac.new(get_settings().secret_key.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
    return f"{header}.{payload}.{base64.urlsafe_b64encode(signature).rstrip(b'=').decode()}"


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), session: Session = Depends(get_session)) -> User:
    unauthorized = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.", headers={"WWW-Authenticate": "Bearer"})
    if not credentials or credentials.scheme.lower() != "bearer":
        raise unauthorized
    try:
        header, payload, signature = credentials.credentials.split(".")
        expected = hmac.new(get_settings().secret_key.encode(), f"{header}.{payload}".encode(), hashlib.sha256).digest()
        received = base64.urlsafe_b64decode(signature + "=" * (-len(signature) % 4))
        data = _decode(payload)
        if not hmac.compare_digest(expected, received) or data["exp"] < int(datetime.now(timezone.utc).timestamp()):
            raise ValueError
        user = session.get(User, int(data["sub"]))
    except (ValueError, KeyError, TypeError, json.JSONDecodeError):
        raise unauthorized
    if not user:
        raise unauthorized
    return user
