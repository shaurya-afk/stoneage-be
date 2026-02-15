import os

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

security = HTTPBearer(auto_error=False)


def _is_auth_configured() -> bool:
    return bool(os.getenv("SUPABASE_JWT_SECRET"))


async def get_current_user(
    cred: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict | None:
    """
    Verify Supabase JWT from Authorization: Bearer <token>.
    Returns decoded token payload with user info (sub, email, etc.).
    When SUPABASE_JWT_SECRET is not set, returns None (auth disabled).
    """
    if not _is_auth_configured():
        return None
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    secret = os.getenv("SUPABASE_JWT_SECRET")
    try:
        payload = jwt.decode(
            cred.credentials,
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
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
