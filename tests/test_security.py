"""
Security-focused tests for the API.
"""

import pytest
from fastapi.testclient import TestClient


class TestAuthentication:
    """Test authentication requirements."""
    
    def test_generate_without_api_key(self, client, sample_generate_request):
        """Test that requests without API key are rejected."""
        response = client.post("/generate", json=sample_generate_request)
        assert response.status_code == 403
        assert "API key" in response.json()["detail"]
    
    def test_generate_with_invalid_api_key(self, client, sample_generate_request, invalid_api_key):
        """Test that requests with invalid API key are rejected."""
        response = client.post(
            "/generate",
            json=sample_generate_request,
            headers={"X-API-Key": invalid_api_key}
        )
        assert response.status_code == 403
        assert "Invalid API key" in response.json()["detail"]
    
    def test_generate_with_valid_api_key(self, client, sample_generate_request, valid_api_key, mock_openrouter):
        """Test that requests with valid API key are accepted."""
        response = client.post(
            "/generate",
            json=sample_generate_request,
            headers={"X-API-Key": valid_api_key}
        )
        # Should not be 403 with valid key
        assert response.status_code != 403


class TestSSRFProtection:
    """Test SSRF protection."""
    
    def test_localhost_url_blocked(self, client, valid_api_key):
        """Test that localhost URLs are blocked."""
        request_data = {
            "user_prompt": "http://localhost:8000/health",
            "user_prompt_type": "file"
        }
        response = client.post(
            "/generate",
            json=request_data,
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()
    
    def test_private_ip_blocked(self, client, valid_api_key):
        """Test that private IPs are blocked."""
        request_data = {
            "user_prompt": "test",
            "image_urls": ["http://192.168.1.1/image.jpg"]
        }
        response = client.post(
            "/generate",
            json=request_data,
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 400
        assert "private" in response.json()["detail"].lower()
    
    def test_metadata_url_blocked(self, client, valid_api_key):
        """Test that cloud metadata URLs are blocked."""
        request_data = {
            "user_prompt": "test",
            "image_urls": ["http://169.254.169.254/latest/meta-data/"]
        }
        response = client.post(
            "/generate",
            json=request_data,
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 400
        assert "not allowed" in response.json()["detail"].lower()
    
    def test_file_scheme_blocked(self, client, valid_api_key):
        """Test that file:// URLs are blocked."""
        request_data = {
            "user_prompt": "file:///etc/passwd",
            "user_prompt_type": "file"
        }
        response = client.post(
            "/generate",
            json=request_data,
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 400
        assert "scheme" in response.json()["detail"].lower()


class TestInputValidation:
    """Test input validation."""
    
    def test_empty_prompt_rejected(self, client, valid_api_key):
        """Test that empty prompts are rejected."""
        request_data = {
            "user_prompt": "",
            "user_prompt_type": "text"
        }
        response = client.post(
            "/generate",
            json=request_data,
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 422  # Validation error
    
    def test_whitespace_prompt_rejected(self, client, valid_api_key):
        """Test that whitespace-only prompts are rejected."""
        request_data = {
            "user_prompt": "   ",
            "user_prompt_type": "text"
        }
        response = client.post(
            "/generate",
            json=request_data,
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 422
    
    def test_invalid_prompt_type_rejected(self, client, valid_api_key):
        """Test that invalid prompt types are rejected."""
        request_data = {
            "user_prompt": "test",
            "user_prompt_type": "invalid"
        }
        response = client.post(
            "/generate",
            json=request_data,
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 422
    
    def test_too_many_images_rejected(self, client, valid_api_key):
        """Test that more than 10 images are rejected."""
        request_data = {
            "user_prompt": "test",
            "image_urls": [f"https://example.com/image{i}.jpg" for i in range(11)]
        }
        response = client.post(
            "/generate",
            json=request_data,
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 422
    
    def test_invalid_model_rejected(self, client, valid_api_key):
        """Test that invalid model names are rejected."""
        request_data = {
            "user_prompt": "test",
            "model": "invalid-model"
        }
        response = client.post(
            "/generate",
            json=request_data,
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 422


class TestSecurityHeaders:
    """Test security headers."""
    
    def test_security_headers_present(self, client):
        """Test that security headers are present in responses."""
        response = client.get("/health")
        
        assert "X-Content-Type-Options" in response.headers
        assert response.headers["X-Content-Type-Options"] == "nosniff"
        
        assert "X-Frame-Options" in response.headers
        assert response.headers["X-Frame-Options"] == "DENY"
        
        assert "X-XSS-Protection" in response.headers
        assert response.headers["X-XSS-Protection"] == "1; mode=block"


class TestCORS:
    """Test CORS configuration."""
    
    def test_cors_allowed_origin(self, client):
        """Test that allowed origins work."""
        response = client.options(
            "/generate",
            headers={"Origin": "http://localhost:3000"}
        )
        # CORS should allow this origin
        assert response.status_code in [200, 405]  # 405 if OPTIONS not explicitly handled
    
    def test_cors_credentials_disabled(self, client):
        """Test that credentials are disabled."""
        response = client.get(
            "/health",
            headers={"Origin": "http://localhost:3000"}
        )
        # Should not have allow-credentials header or it should be false
        if "Access-Control-Allow-Credentials" in response.headers:
            assert response.headers["Access-Control-Allow-Credentials"] == "false"


class TestRateLimiting:
    """Test rate limiting (basic test)."""
    
    def test_rate_limit_exists(self, client, valid_api_key, sample_generate_request, mock_openrouter):
        """Test that rate limiting is configured (won't hit limit in test)."""
        response = client.post(
            "/generate",
            json=sample_generate_request,
            headers={"X-API-Key": valid_api_key}
        )
        # Should not be rate limited on first request
        assert response.status_code != 429
