"""
Tests for authentication session cookies, cross-site SameSite/Secure configuration,
CORS header behavior, and /api/auth/me authentication.
"""
from unittest.mock import patch

import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.utils.auth import delete_session_cookie, set_session_cookie

settings = get_settings()
client = TestClient(app)


# ── Test 1: Production session cookie attributes ─────────────────────────────

def test_production_session_cookie_attributes():
    """In Production environment, session_token cookie must be SameSite=none, Secure=True, HttpOnly=True, Domain=None."""
    res = Response()
    with patch("app.utils.auth.settings.environment", "Production"):
        set_session_cookie(res, "test_token_12345")

    cookie_header = res.headers.get("set-cookie")
    assert cookie_header is not None, "Set-Cookie header must be present"
    assert "session_token=test_token_12345" in cookie_header
    assert "HttpOnly" in cookie_header or "httponly" in cookie_header.lower()
    assert "SameSite=none" in cookie_header or "samesite=none" in cookie_header.lower()
    assert "Secure" in cookie_header or "secure" in cookie_header.lower()
    assert "Domain=" not in cookie_header, "Production cookie must be host-only (Domain omitted)"


# ── Test 2: Development session cookie attributes ────────────────────────────

def test_development_session_cookie_attributes():
    """In Development environment, session_token cookie uses SameSite=lax, Secure=False, Domain=localhost."""
    res = Response()
    with patch("app.utils.auth.settings.environment", "development"):
        set_session_cookie(res, "test_token_12345")

    cookie_header = res.headers.get("set-cookie")
    assert cookie_header is not None
    assert "session_token=test_token_12345" in cookie_header
    assert "SameSite=lax" in cookie_header or "samesite=lax" in cookie_header.lower()
    assert "Domain=localhost" in cookie_header or "domain=localhost" in cookie_header.lower()


# ── Test 3: Delete cookie attributes match set_cookie ────────────────────────

def test_delete_session_cookie_attributes():
    """delete_session_cookie must produce matching SameSite/Secure/Domain parameters."""
    res = Response()
    with patch("app.utils.auth.settings.environment", "Production"):
        delete_session_cookie(res)

    cookie_header = res.headers.get("set-cookie")
    assert cookie_header is not None
    assert "session_token=" in cookie_header
    assert "SameSite=none" in cookie_header or "samesite=none" in cookie_header.lower()


# ── Test 4: Unauthenticated /api/auth/me returns 401 ─────────────────────────

def test_unauthenticated_me_returns_401():
    """Requesting /api/auth/me without a session_token cookie must return 401 Unauthorized."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


# ── Test 5: CORS headers allow frontend origin and credentials ───────────────

def test_cors_allows_frontend_origin_and_credentials():
    """CORS OPTIONS preflight must respond with Access-Control-Allow-Credentials: true."""
    frontend_origin = settings.frontend_url.rstrip("/")
    headers = {
        "Origin": frontend_origin,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "cookie",
    }
    response = client.options("/api/auth/me", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == frontend_origin
    assert response.headers.get("access-control-allow-credentials") == "true"
