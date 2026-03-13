"""
Error Response Models for SLO Recommendation System

Defines consistent error response structures for all API endpoints.
"""

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """Detailed error information."""
    error: str = Field(..., description="Error code")
    message: str = Field(..., description="Human-readable error message")
    detail: Optional[str] = Field(None, description="Additional error details")
    request_id: str = Field(..., description="Unique request identifier for tracking")
    timestamp: str = Field(..., description="ISO 8601 timestamp of the error")


class ValidationErrorResponse(ErrorDetail):
    """Response for validation errors (400)."""
    validation_errors: Optional[List[Dict[str, Any]]] = Field(
        None,
        description="List of validation errors with field names and messages"
    )


class AuthenticationErrorResponse(ErrorDetail):
    """Response for authentication errors (401)."""
    error: str = Field(default="authentication_failed", description="Error code")


class RateLimitErrorResponse(ErrorDetail):
    """Response for rate limit errors (429)."""
    error: str = Field(default="rate_limit_exceeded", description="Error code")
    limit: int = Field(..., description="Rate limit (requests per window)")
    window_seconds: int = Field(..., description="Rate limit window in seconds")
    retry_after: int = Field(..., description="Seconds to wait before retrying")


class NotFoundErrorResponse(ErrorDetail):
    """Response for not found errors (404)."""
    error: str = Field(default="not_found", description="Error code")
    resource_type: str = Field(..., description="Type of resource not found")
    resource_id: str = Field(..., description="ID of resource not found")


class ServerErrorResponse(ErrorDetail):
    """Response for server errors (500)."""
    error: str = Field(default="internal_server_error", description="Error code")
    error_code: Optional[str] = Field(None, description="Specific error code for debugging")


class PIIDetectionErrorResponse(ValidationErrorResponse):
    """Response for PII detection errors (400)."""
    error: str = Field(default="pii_detected", description="Error code")
    pii_patterns_found: List[str] = Field(
        ...,
        description="List of PII patterns detected (e.g., 'email', 'phone', 'ssn')"
    )


class InvalidJSONErrorResponse(ErrorDetail):
    """Response for invalid JSON errors (400)."""
    error: str = Field(default="invalid_json", description="Error code")


class MissingFieldErrorResponse(ValidationErrorResponse):
    """Response for missing required field errors (400)."""
    error: str = Field(default="missing_field", description="Error code")
    missing_field: str = Field(..., description="Name of the missing field")


class TimeoutErrorResponse(ErrorDetail):
    """Response for timeout errors (504)."""
    error: str = Field(default="request_timeout", description="Error code")
    timeout_seconds: int = Field(..., description="Timeout duration in seconds")


class FileNotFoundErrorResponse(ErrorDetail):
    """Response for file not found errors (404)."""
    error: str = Field(default="file_not_found", description="Error code")
    file_path: str = Field(..., description="Path to the file that was not found")


class ConflictErrorResponse(ErrorDetail):
    """Response for conflict errors (409)."""
    error: str = Field(default="conflict", description="Error code")
    conflict_type: str = Field(..., description="Type of conflict")


class DependencyErrorResponse(ErrorDetail):
    """Response for dependency-related errors (400)."""
    error: str = Field(default="dependency_error", description="Error code")
    dependency_issues: List[str] = Field(
        ...,
        description="List of dependency-related issues"
    )


class CircularDependencyErrorResponse(DependencyErrorResponse):
    """Response for circular dependency errors (400)."""
    error: str = Field(default="circular_dependency", description="Error code")
    cycle_services: List[str] = Field(
        ...,
        description="List of services involved in the circular dependency"
    )


class DataQualityErrorResponse(ValidationErrorResponse):
    """Response for data quality errors (400)."""
    error: str = Field(default="data_quality_error", description="Error code")
    quality_issues: List[str] = Field(
        ...,
        description="List of data quality issues"
    )


class InconsistencyErrorResponse(ValidationErrorResponse):
    """Response for inconsistency errors (400)."""
    error: str = Field(default="inconsistency_error", description="Error code")
    inconsistencies: List[Dict[str, Any]] = Field(
        ...,
        description="List of inconsistencies found"
    )


# Error response status codes mapping
ERROR_RESPONSES = {
    400: {
        "description": "Bad Request - Validation error, PII detected, or invalid input",
        "model": ValidationErrorResponse
    },
    401: {
        "description": "Unauthorized - Authentication failed or invalid API key",
        "model": AuthenticationErrorResponse
    },
    404: {
        "description": "Not Found - Resource or file not found",
        "model": NotFoundErrorResponse
    },
    409: {
        "description": "Conflict - Circular dependency or other conflict",
        "model": ConflictErrorResponse
    },
    429: {
        "description": "Too Many Requests - Rate limit exceeded",
        "model": RateLimitErrorResponse
    },
    500: {
        "description": "Internal Server Error - Processing error",
        "model": ServerErrorResponse
    },
    504: {
        "description": "Gateway Timeout - Request timeout",
        "model": TimeoutErrorResponse
    }
}
