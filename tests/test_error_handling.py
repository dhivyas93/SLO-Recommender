"""Tests for error handling and status codes."""

import pytest
import json
from datetime import datetime
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from src.api.gateway import app
from src.api.error_handler import ErrorHandler, RequestContext
from src.models.error import (
    ErrorResponse,
    ValidationErrorResponse,
    PIIErrorResponse,
    RateLimitErrorResponse,
    AuthenticationErrorResponse,
    NotFoundErrorResponse,
    ServerErrorResponse
)


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_request():
    """Create mock request."""
    request = MagicMock()
    request.url.path = "/api/v1/services/test-service/slo-recommendations"
    request.method = "GET"
    request.headers = {"X-API-Key": "test-key"}
    return request


class TestErrorResponseModels:
    """Test error response models."""

    def test_error_response_model(self):
        """Test basic error response model."""
        response = ErrorResponse(
            error="validation_error",
            message="Invalid input",
            detail="Field 'service_id' is required",
            request_id="req_123",
            timestamp="2024-01-15T10:30:00Z",
            status_code=400
        )
        assert response.error == "validation_error"
        assert response.message == "Invalid input"
        assert response.status_code == 400

    def test_validation_error_response_model(self):
        """Test validation error response model."""
        from src.models.error import ValidationErrorDetail
        
        errors = [
            ValidationErrorDetail(
                field="latency_p95",
                error="latency_p95 must be >= latency_p50",
                value=100
            )
        ]
        
        response = ValidationErrorResponse(
            error="validation_error",
            message="Validation failed",
            detail="Multiple validation errors",
            request_id="req_123",
            timestamp="2024-01-15T10:30:00Z",
            status_code=400,
            errors=errors
        )
        assert len(response.errors) == 1
        assert response.errors[0].field == "latency_p95"

    def test_pii_error_response_model(self):
        """Test PII error response model."""
        response = PIIErrorResponse(
            error="pii_detected",
            message="PII detected",
            detail="Email found in input",
            request_id="req_123",
            timestamp="2024-01-15T10:30:00Z",
            status_code=400,
            pii_types=["email", "phone"]
        )
        assert response.pii_types == ["email", "phone"]

    def test_rate_limit_error_response_model(self):
        """Test rate limit error response model."""
        response = RateLimitErrorResponse(
            error="rate_limit_exceeded",
            message="Rate limit exceeded",
            detail="Too many requests",
            request_id="req_123",
            timestamp="2024-01-15T10:30:00Z",
            status_code=429,
            retry_after=60,
            limit=100,
            remaining=0,
            reset_time="2024-01-15T10:31:00Z"
        )
        assert response.retry_after == 60
        assert response.limit == 100

    def test_authentication_error_response_model(self):
        """Test authentication error response model."""
        response = AuthenticationErrorResponse(
            error="authentication_failed",
            message="Authentication failed",
            detail="Invalid API key",
            request_id="req_123",
            timestamp="2024-01-15T10:30:00Z",
            status_code=401,
            auth_scheme="API-Key"
        )
        assert response.auth_scheme == "API-Key"

    def test_not_found_error_response_model(self):
        """Test not found error response model."""
        response = NotFoundErrorResponse(
            error="not_found",
            message="Resource not found",
            detail="Service not found",
            request_id="req_123",
            timestamp="2024-01-15T10:30:00Z",
            status_code=404,
            resource_type="service",
            resource_id="payment-api"
        )
        assert response.resource_type == "service"
        assert response.resource_id == "payment-api"

    def test_server_error_response_model(self):
        """Test server error response model."""
        response = ServerErrorResponse(
            error="internal_server_error",
            message="Server error",
            detail="Processing failed",
            request_id="req_123",
            timestamp="2024-01-15T10:30:00Z",
            status_code=500,
            error_code="REC_ENGINE_FAILED"
        )
        assert response.error_code == "REC_ENGINE_FAILED"


class TestErrorHandler:
    """Test error handler methods."""

    def test_create_error_response(self, mock_request):
        """Test creating error response."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.create_error_response(
            error_code="test_error",
            message="Test error message",
            status_code=400,
            request_context=request_context,
            detail="Test detail"
        )
        
        assert response["error"] == "test_error"
        assert response["message"] == "Test error message"
        assert response["status_code"] == 400
        assert response["detail"] == "Test detail"
        assert "request_id" in response
        assert "timestamp" in response

    def test_handle_validation_error(self, mock_request):
        """Test validation error handler."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_validation_error(
            request_context,
            "Validation failed",
            detail="Invalid input data"
        )
        
        assert response.status_code == 400
        data = json.loads(response.body)
        assert data["error"] == "validation_error"
        assert data["status_code"] == 400

    def test_handle_pii_error(self, mock_request):
        """Test PII error handler."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_pii_error(
            request_context,
            ["email", "phone"],
            "metrics_data"
        )
        
        assert response.status_code == 400
        data = json.loads(response.body)
        assert data["error"] == "pii_detected"
        assert data["pii_types"] == ["email", "phone"]

    def test_handle_authentication_error(self, mock_request):
        """Test authentication error handler."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_authentication_error(
            request_context,
            detail="Invalid API key"
        )
        
        assert response.status_code == 401
        data = json.loads(response.body)
        assert data["error"] == "authentication_failed"
        assert data["status_code"] == 401

    def test_handle_rate_limit_error(self, mock_request):
        """Test rate limit error handler."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_rate_limit_error(
            request_context,
            limit=100,
            remaining=0,
            reset_seconds=60
        )
        
        assert response.status_code == 429
        data = json.loads(response.body)
        assert data["error"] == "rate_limit_exceeded"
        assert data["retry_after"] == 60
        assert "Retry-After" in response.headers

    def test_handle_not_found_error(self, mock_request):
        """Test not found error handler."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_not_found_error(
            request_context,
            resource_type="service",
            resource_id="payment-api"
        )
        
        assert response.status_code == 404
        data = json.loads(response.body)
        assert data["error"] == "not_found"
        assert data["resource_type"] == "service"
        assert data["resource_id"] == "payment-api"

    def test_handle_server_error(self, mock_request):
        """Test server error handler."""
        request_context = RequestContext(mock_request)
        error = Exception("Test error")
        response = ErrorHandler.handle_server_error(
            request_context,
            error,
            error_code="test_error",
            detail="Test detail"
        )
        
        assert response.status_code == 500
        data = json.loads(response.body)
        assert data["error"] == "test_error"
        assert data["status_code"] == 500

    def test_handle_invalid_json_error(self, mock_request):
        """Test invalid JSON error handler."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_invalid_json_error(
            request_context,
            detail="Invalid JSON syntax"
        )
        
        assert response.status_code == 400
        data = json.loads(response.body)
        assert data["error"] == "invalid_json"

    def test_handle_missing_field_error(self, mock_request):
        """Test missing field error handler."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_missing_field_error(
            request_context,
            field_name="service_id"
        )
        
        assert response.status_code == 400
        data = json.loads(response.body)
        assert data["error"] == "missing_field"

    def test_handle_timeout_error(self, mock_request):
        """Test timeout error handler."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_timeout_error(
            request_context,
            timeout_seconds=3.0
        )
        
        assert response.status_code == 504
        data = json.loads(response.body)
        assert data["error"] == "request_timeout"

    def test_handle_file_not_found_error(self, mock_request):
        """Test file not found error handler."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_file_not_found_error(
            request_context,
            file_path="data/services/test/metrics.json"
        )
        
        assert response.status_code == 500
        data = json.loads(response.body)
        assert data["error"] == "file_not_found"

    def test_validate_and_handle_pii_with_pii(self, mock_request):
        """Test PII validation with PII present."""
        request_context = RequestContext(mock_request)
        data = {"email": "test@example.com"}
        response = ErrorHandler.validate_and_handle_pii(
            request_context,
            data,
            "test_field"
        )
        
        assert response is not None
        assert response.status_code == 400

    def test_validate_and_handle_pii_without_pii(self, mock_request):
        """Test PII validation without PII."""
        request_context = RequestContext(mock_request)
        data = {"service_id": "payment-api"}
        response = ErrorHandler.validate_and_handle_pii(
            request_context,
            data,
            "test_field"
        )
        
        assert response is None


class TestRequestContext:
    """Test request context."""

    def test_request_context_creation(self, mock_request):
        """Test creating request context."""
        context = RequestContext(mock_request)
        
        assert context.request_id is not None
        assert context.timestamp is not None
        assert context.path == "/api/v1/services/test-service/slo-recommendations"
        assert context.method == "GET"

    def test_request_context_elapsed_time(self, mock_request):
        """Test elapsed time calculation."""
        import time
        context = RequestContext(mock_request)
        time.sleep(0.1)
        elapsed = context.get_elapsed_time()
        
        assert elapsed >= 0.1


class TestErrorResponseFormat:
    """Test error response format consistency."""

    def test_error_response_has_required_fields(self, mock_request):
        """Test that error responses have all required fields."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_validation_error(
            request_context,
            "Test error"
        )
        
        data = json.loads(response.body)
        required_fields = [
            "error",
            "message",
            "detail",
            "request_id",
            "timestamp",
            "status_code",
            "path",
            "method"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"

    def test_error_response_timestamp_format(self, mock_request):
        """Test that timestamp is in ISO 8601 format."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_validation_error(
            request_context,
            "Test error"
        )
        
        data = json.loads(response.body)
        timestamp = data["timestamp"]
        
        # Should be ISO 8601 format with Z suffix
        assert timestamp.endswith("Z")
        # Should be parseable as datetime (basic check for Python 3.6 compatibility)
        assert "T" in timestamp
        assert len(timestamp) > 10  # At least YYYY-MM-DD format

    def test_error_response_request_id_format(self, mock_request):
        """Test that request_id is a valid UUID."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_validation_error(
            request_context,
            "Test error"
        )
        
        data = json.loads(response.body)
        request_id = data["request_id"]
        
        # Should be a valid UUID format
        import uuid
        uuid.UUID(request_id)


class TestErrorHandlingEdgeCases:
    """Test error handling edge cases."""

    def test_error_with_none_detail(self, mock_request):
        """Test error response with None detail."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.create_error_response(
            error_code="test_error",
            message="Test message",
            status_code=400,
            request_context=request_context,
            detail=None
        )
        
        assert response["detail"] is None

    def test_error_with_empty_string_detail(self, mock_request):
        """Test error response with empty string detail."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.create_error_response(
            error_code="test_error",
            message="Test message",
            status_code=400,
            request_context=request_context,
            detail=""
        )
        
        assert response["detail"] == ""

    def test_error_with_special_characters(self, mock_request):
        """Test error response with special characters."""
        request_context = RequestContext(mock_request)
        special_message = "Error with special chars: <>&\"'"
        response = ErrorHandler.handle_validation_error(
            request_context,
            special_message
        )
        
        data = json.loads(response.body)
        assert special_message in data["message"]

    def test_rate_limit_error_headers(self, mock_request):
        """Test that rate limit error includes proper headers."""
        request_context = RequestContext(mock_request)
        response = ErrorHandler.handle_rate_limit_error(
            request_context,
            limit=100,
            remaining=0,
            reset_seconds=60
        )
        
        assert "Retry-After" in response.headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
