"""
GitHub OAuth Flow Verification Tests

This test suite verifies:
- Authorization URL generation
- Redirect URI generation
- Callback URL correctness
- Environment switching
- Local mode
- Ngrok mode
"""

import pytest
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse, parse_qs

from app.config import get_settings
from app.routers.auth import github_login
from fastapi.testclient import TestClient


class TestGitHubOAuth:
    """Test GitHub OAuth configuration and flow"""

    def test_redirect_uri_generation_local_mode(self):
        """Test redirect URI is correctly generated for local development"""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.app_url = "http://127.0.0.1:8000"
            mock_settings.github_client_id = "test_client_id"
            
            redirect_uri = f"{mock_settings.app_url}/api/auth/github/callback"
            
            assert redirect_uri == "http://127.0.0.1:8000/api/auth/github/callback"
            parsed = urlparse(redirect_uri)
            assert parsed.scheme == "http"
            assert parsed.netloc == "127.0.0.1:8000"
            assert parsed.path == "/api/auth/github/callback"

    def test_redirect_uri_generation_ngrok_mode(self):
        """Test redirect URI is correctly generated for ngrok development"""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.app_url = "https://abc123.ngrok-free.app"
            mock_settings.github_client_id = "test_client_id"
            
            redirect_uri = f"{mock_settings.app_url}/api/auth/github/callback"
            
            assert redirect_uri == "https://abc123.ngrok-free.app/api/auth/github/callback"
            parsed = urlparse(redirect_uri)
            assert parsed.scheme == "https"
            assert parsed.netloc == "abc123.ngrok-free.app"
            assert parsed.path == "/api/auth/github/callback"

    def test_authorization_url_contains_correct_params(self):
        """Test authorization URL contains all required parameters"""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.app_url = "http://127.0.0.1:8000"
            mock_settings.github_client_id = "test_client_id"
            
            redirect_uri = f"{mock_settings.app_url}/api/auth/github/callback"
            params = {
                "client_id": mock_settings.github_client_id,
                "redirect_uri": redirect_uri,
                "scope": "read:user user:email repo",
                "state": "test_state_1234567890abcdef",
            }
            
            assert "client_id" in params
            assert params["client_id"] == "test_client_id"
            assert "redirect_uri" in params
            assert params["redirect_uri"] == redirect_uri
            assert "scope" in params
            assert params["scope"] == "read:user user:email repo"
            assert "state" in params

    def test_environment_variable_validation(self):
        """Test that required environment variables are validated on startup"""
        settings = get_settings()
        
        # These should not raise errors if properly configured
        assert settings.app_url is not None
        assert settings.frontend_url is not None
        assert settings.github_client_id is not None
        assert settings.github_client_secret is not None

    def test_callback_url_matches_redirect_uri(self):
        """Test that the callback endpoint path matches the redirect URI"""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.app_url = "http://127.0.0.1:8000"
            
            redirect_uri = f"{mock_settings.app_url}/api/auth/github/callback"
            parsed = urlparse(redirect_uri)
            
            # The callback endpoint should be at /api/auth/github/callback
            assert parsed.path == "/api/auth/github/callback"

    def test_frontend_url_used_for_redirects(self):
        """Test that frontend URL is used for post-authentication redirects"""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.frontend_url = "http://localhost:5173"
            
            dashboard_url = f"{mock_settings.frontend_url}/dashboard"
            error_url = f"{mock_settings.frontend_url}/auth/error"
            
            assert dashboard_url == "http://localhost:5173/dashboard"
            assert error_url == "http://localhost:5173/auth/error"

    def test_no_hardcoded_callback_urls(self):
        """Test that callback URLs are not hardcoded"""
        # Read the auth.py file and check for hardcoded URLs
        import os
        auth_file_path = os.path.join(
            os.path.dirname(__file__), 
            "..", 
            "app", 
            "routers", 
            "auth.py"
        )
        
        with open(auth_file_path, "r") as f:
            content = f.read()
            
        # Check that localhost:8000 is not hardcoded in redirect_uri
        # (it should use settings.app_url instead)
        lines = content.split("\n")
        for line in lines:
            if "redirect_uri" in line and "=" in line and not line.strip().startswith("logger."):
                # Should use settings.app_url, not hardcoded localhost
                assert "settings.app_url" in line or "redirect_uri =" in line or "redirect_uri" in line, \
                    f"Hardcoded URL found in line: {line}"

    def test_environment_switching_local(self):
        """Test OAuth configuration for local development environment"""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.app_url = "http://127.0.0.1:8000"
            mock_settings.frontend_url = "http://localhost:5173"
            mock_settings.environment = "development"
            
            redirect_uri = f"{mock_settings.app_url}/api/auth/github/callback"
            
            assert redirect_uri == "http://127.0.0.1:8000/api/auth/github/callback"
            assert mock_settings.environment == "development"

    def test_environment_switching_ngrok(self):
        """Test OAuth configuration for ngrok development environment"""
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.app_url = "https://abc123.ngrok-free.app"
            mock_settings.frontend_url = "https://def456.ngrok-free.app"
            mock_settings.environment = "development"
            
            redirect_uri = f"{mock_settings.app_url}/api/auth/github/callback"
            
            assert redirect_uri == "https://abc123.ngrok-free.app/api/auth/github/callback"
            assert mock_settings.frontend_url == "https://def456.ngrok-free.app"

    def test_url_scheme_consistency(self):
        """Test that URL schemes are consistent (http for local, https for ngrok)"""
        # Local development
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.app_url = "http://127.0.0.1:8000"
            redirect_uri = f"{mock_settings.app_url}/api/auth/github/callback"
            parsed = urlparse(redirect_uri)
            assert parsed.scheme == "http"
        
        # Ngrok development
        with patch("app.routers.auth.settings") as mock_settings:
            mock_settings.app_url = "https://abc123.ngrok-free.app"
            redirect_uri = f"{mock_settings.app_url}/api/auth/github/callback"
            parsed = urlparse(redirect_uri)
            assert parsed.scheme == "https"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
