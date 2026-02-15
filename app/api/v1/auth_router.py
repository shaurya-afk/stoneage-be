import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

from app.db.supabase import get_supabase

auth_router = APIRouter(prefix="/auth", tags=["auth"])


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class GoogleTokenRequest(BaseModel):
    token: str


@auth_router.post("/signup")
async def signup(body: SignUpRequest):
    """Create a new user with email and password."""
    client = get_supabase()
    if not client:
        raise HTTPException(503, "Supabase auth not configured")
    try:
        response = client.auth.sign_up(
            {"email": body.email, "password": body.password}
        )
        user = response.user
        session = response.session
        if not user:
            msg = getattr(response, "message", None) or "Signup failed"
            raise HTTPException(400, str(msg))
        return {
            "user": {
                "id": user.id,
                "email": user.email,
            },
            "session": {
                "access_token": session.access_token if session else None,
                "refresh_token": session.refresh_token if session else None,
                "expires_at": session.expires_at if session else None,
            } if session else None,
        }
    except Exception as e:
        raise HTTPException(400, str(e))


@auth_router.post("/signin")
async def signin(body: SignInRequest):
    """Sign in with email and password."""
    client = get_supabase()
    if not client:
        raise HTTPException(503, "Supabase auth not configured")
    try:
        response = client.auth.sign_in_with_password(
            {"email": body.email, "password": body.password}
        )
        user = response.user
        session = response.session
        if not user or not session:
            raise HTTPException(401, "Invalid email or password")
        return {
            "user": {"id": user.id, "email": user.email},
            "session": {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_at": session.expires_at,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, str(e))


@auth_router.get("/google/url")
async def google_oauth_url(redirect_to: str | None = None):
    """Get the Google OAuth URL for redirect-based sign-in."""
    client = get_supabase()
    if not client:
        raise HTTPException(503, "Supabase auth not configured")
    try:
        options = {}
        if redirect_to:
            options["redirect_to"] = redirect_to
        response = client.auth.sign_in_with_oauth(
            {"provider": "google", "options": options} if options else {"provider": "google"}
        )
        url = getattr(response, "url", None) or (
            getattr(response, "data", {}) or {}
        ).get("url")
        if not url:
            raise HTTPException(500, "Could not get Google OAuth URL")
        return {"url": url}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))


@auth_router.post("/google")
async def google_signin(body: GoogleTokenRequest):
    """Sign in with Google ID token (from Google Sign-In button)."""
    client = get_supabase()
    if not client:
        raise HTTPException(503, "Supabase auth not configured")
    try:
        response = client.auth.sign_in_with_id_token(
            {"provider": "google", "token": body.token}
        )
        user = response.user
        session = response.session
        if not user or not session:
            raise HTTPException(401, "Invalid Google token")
        return {
            "user": {"id": user.id, "email": user.email},
            "session": {
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
                "expires_at": session.expires_at,
            },
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(401, str(e))
