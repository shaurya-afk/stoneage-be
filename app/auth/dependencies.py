import base64
import os
import time

import jwt
import requests
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from cryptography.hazmat.primitives.asymmetric.ec import (
    EllipticCurvePublicNumbers,
    SECP256R1,
)
from cryptography.hazmat.backends import default_backend

security = HTTPBearer(auto_error=False)

# JWKS cache: {kid: (public_key, expiry_time)}
_jwks_cache: dict[str, tuple] = {}
_JWKS_CACHE_TTL_SEC = 300


def _is_auth_configured() -> bool:
    return bool(os.getenv("SUPABASE_JWT_SECRET") or os.getenv("SUPABASE_URL"))


def _get_jwks_url() -> str | None:
    url = (os.getenv("SUPABASE_URL") or "").rstrip("/")
    if not url:
        return None
    if not url.startswith("http"):
        url = f"https://{url}"
    return f"{url}/auth/v1/.well-known/jwks.json"


def _b64url_decode(value: str) -> bytes:
    padding = 4 - len(value) % 4
    if padding != 4:
        value += "=" * padding
    return base64.urlsafe_b64decode(value)


def _jwk_to_public_key(jwk: dict):
    """Convert EC P-256 JWK to cryptography public key."""
    x = int.from_bytes(_b64url_decode(jwk["x"]), "big")
    y = int.from_bytes(_b64url_decode(jwk["y"]), "big")
    numbers = EllipticCurvePublicNumbers(x, y, SECP256R1())
    return numbers.public_key(default_backend())


def _get_public_key_for_kid(kid: str):
    """Fetch JWKS and return public key for the given kid. Cached."""
    now = time.time()
    if kid in _jwks_cache:
        key, expiry = _jwks_cache[kid]
        if now < expiry:
            return key
        del _jwks_cache[kid]

    jwks_url = _get_jwks_url()
    if not jwks_url:
        return None
    try:
        resp = requests.get(jwks_url, timeout=10)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        return None

    keys = data.get("keys") or []
    for key_dict in keys:
        if key_dict.get("kid") == kid and key_dict.get("kty") == "EC":
            try:
                pub_key = _jwk_to_public_key(key_dict)
                _jwks_cache[kid] = (pub_key, now + _JWKS_CACHE_TTL_SEC)
                return pub_key
            except Exception:
                return None
    return None


async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """
    Verify Supabase JWT from Authorization: Bearer <token>.
    Supports both new JWT Signing Keys (ES256 via JWKS) and legacy HS256 secret.
    Returns decoded token payload with user info (sub, email, etc.).
    When neither SUPABASE_JWT_SECRET nor SUPABASE_URL is set, returns None (auth disabled).
    """
    if not _is_auth_configured():
        return None
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = cred.credentials
    unverified = jwt.get_unverified_header(token)
    alg = unverified.get("alg")
    kid = unverified.get("kid")

    # New Supabase tokens: ES256 signed with JWT Signing Keys (JWKS)
    if alg == "ES256" and kid and _get_jwks_url():
        pub_key = _get_public_key_for_kid(kid)
        if not pub_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: could not fetch signing key",
            )
        try:
            payload = jwt.decode(
                token,
                pub_key,
                algorithms=["ES256"],
                audience="authenticated",
                options={"verify_aud": True},
            )
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expired",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )

    # Legacy tokens: HS256 with JWT Secret
    secret = os.getenv("SUPABASE_JWT_SECRET")
    if not secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    try:
        payload = jwt.decode(
            token,
            secret,
            algorithms=["HS256"],
            audience="authenticated",
            options={"verify_aud": True},
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
        )
    except jwt.InvalidSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: signature verification failed. Ensure SUPABASE_JWT_SECRET is the JWT Secret from Supabase Project Settings → API (not the anon or service_role key).",
        )
    except jwt.InvalidAudienceError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: audience mismatch",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
