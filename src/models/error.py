"""Error response models for consistent API error handling."""

from typing import Optional, Any, Dict, List
from datetime import datetime
from pydantic import BaseModel, Field


class ErrorResponse(BaseModel):
    """Standard error response format for all API errors."""

    error: str = Field(
        ...,
        description="Error code (e.g., 'validation_error', 'not_found', 'rate_limit_exceeded')"
    )
    message: str = Field(
        ...,
        description="Human-readable error message"
    )
    detail: Optional[str] = Field(
        None,
        description="Additional details about the error"
    )
    request_id: str = Field(
        ...,
        description="Unique request ID for tracing"
    )
    timestamp: str = Field(
        ...,
        description="ISO 8601 timestamp when error occurred"
    )
    status_code: int = Field(
        ...,
        description="HTTP status code"
    )
    path: Optional[str] = Field(
        None,
        description="API endpoint path that caused the error"
    )
    method: Optional[str] = Field(
        None,
        description="HTTP method (GET, POST, etc.)"
    )

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "Invalid input provided",
                "detail": "latency_p95 must be >= latency_p50",
                "request_id": "req_abc123def456",
                "timestamp": "2024-01-15T10:30:00Z",
                "status_code": 400,
                "path": "/api/v1/services/payment-api/metrics",
                "method": "POST"
            }
        }


class ValidationErrorDetail(BaseModel):
    """Detailed validation error with field information."""

    field: str = Field(..., description="Field name that failed validation")
    error: str = Field(..., description="Error message for this field")
    value: Optional[Any] = Field(None, description="The invalid value (if safe to include)")


class ValidationErrorResponse(ErrorResponse):
    """Extended error response for validation errors with field details."""

    errors: Optional[List[ValidationErrorDetail]] = Field(
        None,
        description="List of validation errors by field"
    )

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "error": "validation_error",
                "message": "Validation failed for input data",
                "detail": "Multiple validation errors occurred",
                "request_id": "req_abc123def456",
                "timestamp": "2024-01-15T10:30:00Z",
                "status_code": 400,
                "path": "/api/v1/services/payment-api/metrics",
                "method": "POST",
                "errors": [
                    {
                        "field": "latency_p95",
                        "error": "latency_p95 must be >= latency_p50",
                        "value": 100
                    },
                    {
                        "field": "availability",
                        "error": "availability must be between 0 and 100",
                        "value": 150
                    }
                ]
            }
        }


class PIIErrorResponse(ErrorResponse):
    """Error response for PII detection."""

    pii_types: Optional[List[str]] = Field(
        None,
        description="Types of PII detected (e.g., 'email', 'phone', 'ssn')"
    )

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "error": "pii_detected",
                "message": "Personally identifiable information detected in input",
                "detail": "Please remove PII before submitting",
                "request_id": "req_abc123def456",
                "timestamp": "2024-01-15T10:30:00Z",
                "status_code": 400,
                "path": "/api/v1/services/payment-api/metrics",
                "method": "POST",
                "pii_types": ["email", "phone"]
            }
        }


class RateLimitErrorResponse(ErrorResponse):
    """Error response for rate limiting."""

    retry_after: int = Field(
        ...,
        description="Seconds to wait before retrying"
    )
    limit: int = Field(
        ...,
        description="Rate limit (requests per minute)"
    )
    remaining: int = Field(
        ...,
        description="Remaining requests in current window"
    )
    reset_time: str = Field(
        ...,
        description="ISO 8601 timestamp when rate limit resets"
    )

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "error": "rate_limit_exceeded",
                "message": "Rate limit exceeded",
                "detail": "You have exceeded the rate limit of 100 requests per minute",
                "request_id": "req_abc123def456",
                "timestamp": "2024-01-15T10:30:00Z",
                "status_code": 429,
                "path": "/api/v1/services/payment-api/slo-recommendations",
                "method": "GET",
                "retry_after": 45,
                "limit": 100,
                "remaining": 0,
                "reset_time": "2024-01-15T10:31:00Z"
            }
        }


class AuthenticationErrorResponse(ErrorResponse):
    """Error response for authentication failures."""

    auth_scheme: Optional[str] = Field(
        None,
        description="Authentication scheme expected (e.g., 'API-Key')"
    )

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "error": "authentication_failed",
                "message": "Authentication failed",
                "detail": "Invalid or missing API key",
                "request_id": "req_abc123def456",
                "timestamp": "2024-01-15T10:30:00Z",
                "status_code": 401,
                "path": "/api/v1/services/payment-api/slo-recommendations",
                "method": "GET",
                "auth_scheme": "API-Key"
            }
        }


class NotFoundErrorResponse(ErrorResponse):
    """Error response for resource not found."""

    resource_type: Optional[str] = Field(
        None,
        description="Type of resource not found (e.g., 'service', 'recommendation')"
    )
    resource_id: Optional[str] = Field(
        None,
        description="ID of the resource that was not found"
    )

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "error": "not_found",
                "message": "Resource not found",
                "detail": "Service 'payment-api' does not exist",
                "request_id": "req_abc123def456",
                "timestamp": "2024-01-15T10:30:00Z",
                "status_code": 404,
                "path": "/api/v1/services/payment-api/slo-recommendations",
                "method": "GET",
                "resource_type": "service",
                "resource_id": "payment-api"
            }
        }


class ServerErrorResponse(ErrorResponse):
    """Error response for server errors."""

    error_code: Optional[str] = Field(
        None,
        description="Internal error code for debugging"
    )

    class Config:
        """Pydantic config."""
        schema_extra = {
            "example": {
                "error": "internal_server_error",
                "message": "An internal server error occurred",
                "detail": "Failed to process recommendation",
                "request_id": "req_abc123def456",
                "timestamp": "2024-01-15T10:30:00Z",
                "status_code": 500,
                "path": "/api/v1/services/payment-api/slo-recommendations",
                "method": "GET",
                "error_code": "REC_ENGINE_FAILED"
            }
        }
