"""
Auth0 resource-server authentication for FastAPI.

The web app logs users in with Auth0 and forwards the access token as
`Authorization: Bearer <jwt>`. Here we verify the RS256 signature against the
tenant's JWKS, check issuer + audience + expiry, and use the token's `sub`
claim as the user id. Clients can no longer choose which user they are.

Env:
  AUTH0_DOMAIN     e.g. dev-abc123.us.auth0.com
  AUTH0_AUDIENCE   the API identifier you created in Auth0
  AUTH_DISABLED    "true" = local dev only; every request is the demo user
  APP_ENV          "production" refuses to start with AUTH_DISABLED=true
"""
import logging
import os
import time
from dataclasses import dataclass
from typing import Optional, Dict
from urllib.parse import unquote

import jwt
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.db.database import ensure_profile

log = logging.getLogger("auth0")

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "").strip().replace("https://", "").rstrip("/")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "").strip()
AUTH_DISABLED = os.getenv("AUTH_DISABLED", "false").strip().lower() == "true"
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()

DEV_USER_ID = "default_user"

if AUTH_DISABLED and APP_ENV == "production":
    raise RuntimeError("AUTH_DISABLED=true is not allowed when APP_ENV=production")

_bearer = HTTPBearer(auto_error=False)
_jwks_client: Optional[jwt.PyJWKClient] = None
_last_touch: Dict[str, float] = {}


@dataclass
class AuthUser:
    user_id: str
    name: Optional[str] = None
    email: Optional[str] = None
    picture: Optional[str] = None


def validate_config() -> None:
    """Called at startup so a missing Auth0 setting fails loudly, not per-request."""
    if AUTH_DISABLED:
        log.warning("AUTH_DISABLED=true - all requests run as '%s'. Local development only.", DEV_USER_ID)
        return
    missing = [k for k, v in (("AUTH0_DOMAIN", AUTH0_DOMAIN), ("AUTH0_AUDIENCE", AUTH0_AUDIENCE)) if not v]
    if missing:
        raise RuntimeError(f"Missing Auth0 settings: {', '.join(missing)} (or set AUTH_DISABLED=true for local dev)")


def _client() -> jwt.PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        _jwks_client = jwt.PyJWKClient(f"https://{AUTH0_DOMAIN}/.well-known/jwks.json", cache_keys=True, lifespan=3600)
    return _jwks_client


def verify_token(token: str) -> dict:
    try:
        signing_key = _client().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/",
            options={"require": ["exp", "iss", "aud", "sub"]},
        )
    except jwt.PyJWTError as exc:
        log.info("Rejected token: %s", exc)
        raise HTTPException(status_code=401, detail="Invalid or expired token", headers={"WWW-Authenticate": "Bearer"})


def _clip(value: Optional[str], n: int) -> Optional[str]:
    if not value:
        return None
    value = unquote(value).strip()
    return value[:n] if value else None


def get_current_user(
    request: Request,
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> AuthUser:
    if AUTH_DISABLED:
        user = AuthUser(user_id=DEV_USER_ID, name="Dev Pioneer")
    else:
        if creds is None or creds.scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Missing bearer token", headers={"WWW-Authenticate": "Bearer"})
        claims = verify_token(creds.credentials)
        # Display fields are forwarded by the web server from the Auth0 ID token.
        # They only affect this user's own profile card; identity always comes from `sub`.
        user = AuthUser(
            user_id=claims["sub"],
            name=_clip(request.headers.get("x-user-name"), 80),
            email=_clip(request.headers.get("x-user-email"), 120),
            picture=_clip(request.headers.get("x-user-picture"), 500),
        )

    now = time.time()
    if now - _last_touch.get(user.user_id, 0) > 60:
        ensure_profile(user.user_id, user.name, user.email, user.picture)
        _last_touch[user.user_id] = now
    return user
