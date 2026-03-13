"""
Tests for rate limiting middleware integration.

Tests verify:
1. Rate limiting middleware is properly integrated into FastAPI app
2. 100 requests/minute limit is enforced per API key
3. 429 status code returned when limit exceeded
4. Rate limit headers included in responses
5. Middleware works with existing APIKeyManager and RateLimiter classes
"""

import pytest
import time
import json
from pathlib import Path
from fastapi.testclient import TestClient
from src.api.gateway import app
from src.api.auth import APIKeyManager, RateLimiter, AuthMiddleware


@pytest.fixture(autouse=True)
def setup_api_keys():
    """Ensure API keys file exists before each test."""
    api_keys_file = Path("data/api_keys.json")
    api_keys_file.parent.mkdir(parents=True, exist_ok=True)
    
    api_keys = {
        "test-api-key-001": {
            "tenant_id": "tenant-1",
            "description": "Test API key for tenant 1",
            "created_at": 1705334400,
            "active": True
        },
        "test-api-key-002": {
            "tenant_id": "tenant-2",
            "description": "Test API key for tenant 2",
            "created_at": 1705334400,
            "active": True
        }
    }
    
    with open(api_keys_file, 'w') as f:
        json.dump(api_keys, f)
    
    # Recreate global instances to pick up the new API keys file
    import src.api.auth as auth_module
    auth_module.api_key_manager = auth_module.APIKeyManager()
    auth_module.rate_limiter = auth_module.RateLimiter()
    auth_module.auth_middleware = auth_module.AuthMiddleware(
        auth_module.api_key_manager,
        auth_module.rate_limiter
    )
    
    yield
    
    # Cleanup after test
    if api_keys_file.exists():
        api_keys_file.unlink()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def valid_api_key():
    """Valid API key for testing."""
    return "test-api-key-001"


@pytest.fixture
def invalid_api_key():
    """Invalid API key for testing."""
    return "invalid-api-key-xyz"


class TestRateLimitingMiddlewareIntegration:
    """Test rate limiting middleware integration."""
    
    def test_health_check_no_auth_required(self, client):
        """Health check endpoint should not require authentication."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"
    
    def test_missing_api_key_returns_401(self, client):
        """Request without API key should return 401."""
        response = client.get("/api/v1/services/test-service/slo-recommendations")
        assert response.status_code == 401
        assert "X-API-Key" in response.json()["detail"]
    
    def test_invalid_api_key_returns_401(self, client, invalid_api_key):
        """Request with invalid API key should return 401."""
        response = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": invalid_api_key}
        )
        assert response.status_code == 401
        assert "Invalid API key" in response.json()["detail"]
    
    def test_valid_api_key_returns_200(self, client, valid_api_key):
        """Request with valid API key should succeed."""
        response = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 200
        assert response.json()["service_id"] == "test-service"
    
    def test_rate_limit_headers_present(self, client, valid_api_key):
        """Response should include rate limit headers."""
        response = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 200
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        
        # Verify header values
        assert response.headers["X-RateLimit-Limit"] == "100"
        assert int(response.headers["X-RateLimit-Remaining"]) <= 100
        assert int(response.headers["X-RateLimit-Reset"]) > 0
    
    def test_rate_limit_decrements(self, client, valid_api_key):
        """Rate limit remaining should decrement with each request."""
        # First request
        response1 = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        remaining1 = int(response1.headers["X-RateLimit-Remaining"])
        
        # Second request
        response2 = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        remaining2 = int(response2.headers["X-RateLimit-Remaining"])
        
        # Remaining should decrease
        assert remaining2 < remaining1
        assert remaining2 == remaining1 - 1
    
    def test_rate_limit_enforced_at_100_requests(self, client, valid_api_key):
        """Rate limit should be enforced at 100 requests/minute."""
        # Make 100 requests
        for i in range(100):
            response = client.get(
                "/api/v1/services/test-service/slo-recommendations",
                headers={"X-API-Key": valid_api_key}
            )
            assert response.status_code == 200
        
        # 101st request should be rate limited
        response = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 429
        assert "Rate limit exceeded" in response.json()["detail"]
    
    def test_rate_limit_exceeded_returns_429(self, client, valid_api_key):
        """Rate limit exceeded should return 429 status code."""
        # Exhaust rate limit
        for i in range(100):
            client.get(
                "/api/v1/services/test-service/slo-recommendations",
                headers={"X-API-Key": valid_api_key}
            )
        
        # Next request should be rate limited
        response = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 429
    
    def test_rate_limit_headers_on_429(self, client, valid_api_key):
        """Rate limit headers should be present on 429 response."""
        # Exhaust rate limit
        for i in range(100):
            client.get(
                "/api/v1/services/test-service/slo-recommendations",
                headers={"X-API-Key": valid_api_key}
            )
        
        # Next request should be rate limited
        response = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 429
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        assert "Retry-After" in response.headers
        
        # Remaining should be 0
        assert response.headers["X-RateLimit-Remaining"] == "0"
    
    def test_different_api_keys_have_separate_limits(self, client):
        """Different API keys should have separate rate limits."""
        api_key_1 = "test-api-key-001"
        api_key_2 = "test-api-key-002"
        
        # Make 50 requests with key 1
        for i in range(50):
            response = client.get(
                "/api/v1/services/test-service/slo-recommendations",
                headers={"X-API-Key": api_key_1}
            )
            assert response.status_code == 200
        
        # Make 50 requests with key 2 - should all succeed
        for i in range(50):
            response = client.get(
                "/api/v1/services/test-service/slo-recommendations",
                headers={"X-API-Key": api_key_2}
            )
            assert response.status_code == 200
        
        # Both keys should have 50 remaining
        response1 = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": api_key_1}
        )
        response2 = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": api_key_2}
        )
        
        remaining1 = int(response1.headers["X-RateLimit-Remaining"])
        remaining2 = int(response2.headers["X-RateLimit-Remaining"])
        
        assert remaining1 == 49  # 100 - 50 - 1
        assert remaining2 == 49  # 100 - 50 - 1
    
    def test_rate_limit_applies_to_all_endpoints(self, client, valid_api_key):
        """Rate limit should apply to all protected endpoints."""
        endpoints = [
            ("GET", "/api/v1/services/test-service/slo-recommendations"),
            ("POST", "/api/v1/services/test-service/metrics"),
            ("POST", "/api/v1/services/dependencies")
        ]
        
        # Make requests to different endpoints (33 * 3 = 99 requests)
        for i in range(33):
            for method, endpoint in endpoints:
                if method == "GET":
                    response = client.get(
                        endpoint,
                        headers={"X-API-Key": valid_api_key}
                    )
                else:
                    response = client.post(
                        endpoint,
                        headers={"X-API-Key": valid_api_key},
                        json={"data": "test"}
                    )
                assert response.status_code == 200
        
        # Make one more request to reach 100
        response = client.get(
            endpoints[0][1],
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 200
        
        # Next request should be rate limited
        response = client.get(
            endpoints[0][1],
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 429
    
    def test_tenant_id_in_request_state(self, client, valid_api_key):
        """Tenant ID should be available in request state."""
        response = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        assert response.status_code == 200
        assert response.json()["tenant_id"] == "tenant-1"
    
    def test_post_endpoint_rate_limited(self, client, valid_api_key):
        """POST endpoints should also be rate limited."""
        # Make 100 POST requests
        for i in range(100):
            response = client.post(
                "/api/v1/services/test-service/metrics",
                headers={"X-API-Key": valid_api_key},
                json={"data": "test"}
            )
            assert response.status_code == 200
        
        # 101st request should be rate limited
        response = client.post(
            "/api/v1/services/test-service/metrics",
            headers={"X-API-Key": valid_api_key},
            json={"data": "test"}
        )
        assert response.status_code == 429


class TestRateLimiterClass:
    """Test RateLimiter class directly."""
    
    def test_rate_limiter_initialization(self):
        """RateLimiter should initialize with correct limit."""
        limiter = RateLimiter(requests_per_minute=100)
        assert limiter.requests_per_minute == 100
    
    def test_is_rate_limited_false_initially(self):
        """New API key should not be rate limited."""
        limiter = RateLimiter(requests_per_minute=100)
        assert not limiter.is_rate_limited("test-key")
    
    def test_is_rate_limited_after_100_requests(self):
        """API key should be rate limited after 100 requests."""
        limiter = RateLimiter(requests_per_minute=100)
        
        for i in range(100):
            assert not limiter.is_rate_limited("test-key")
        
        assert limiter.is_rate_limited("test-key")
    
    def test_get_remaining_requests(self):
        """get_remaining_requests should return correct count."""
        limiter = RateLimiter(requests_per_minute=100)
        
        assert limiter.get_remaining_requests("test-key") == 100
        
        limiter.is_rate_limited("test-key")
        assert limiter.get_remaining_requests("test-key") == 99
        
        limiter.is_rate_limited("test-key")
        assert limiter.get_remaining_requests("test-key") == 98
    
    def test_get_reset_time(self):
        """get_reset_time should return seconds until reset."""
        limiter = RateLimiter(requests_per_minute=100)
        
        # Initially no requests, reset time should be 0
        assert limiter.get_reset_time("test-key") == 0
        
        # After first request, reset time should be ~60 seconds
        limiter.is_rate_limited("test-key")
        reset_time = limiter.get_reset_time("test-key")
        assert 59 <= reset_time <= 60


class TestAuthMiddlewareClass:
    """Test AuthMiddleware class directly."""
    
    def test_auth_middleware_initialization(self):
        """AuthMiddleware should initialize with managers."""
        middleware = AuthMiddleware()
        assert middleware.api_key_manager is not None
        assert middleware.rate_limiter is not None
    
    def test_get_rate_limit_headers(self):
        """get_rate_limit_headers should return correct headers."""
        from unittest.mock import Mock
        
        middleware = AuthMiddleware()
        request = Mock()
        request.state.api_key = "test-key"
        
        # Make a request to populate rate limiter
        middleware.rate_limiter.is_rate_limited("test-key")
        
        headers = middleware.get_rate_limit_headers(request)
        
        assert "X-RateLimit-Limit" in headers
        assert "X-RateLimit-Remaining" in headers
        assert "X-RateLimit-Reset" in headers
        assert headers["X-RateLimit-Limit"] == "100"
