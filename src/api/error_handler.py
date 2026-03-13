"""Centralized error handling for API endpoints."""

import logging
import uuid
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from src.models.error import (
    ErrorResponse,
    ValidationErrorResponse,
    ValidationErrorDetail,
    PIIErrorResponse,
    RateLimitErrorResponse,
    AuthenticationErrorResponse,
    NotFoundErrorResponse,
    ServerErrorResponse
)
from src.utils.validators import PIIDetector

logger = logging.getLogger(__name__)


class RequestContext:
    """Context information for a request."""

    def __init__(self, request: Request):
        """Initialize request context."""
        self.request_id = str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat() + "Z"
        self.path = request.url.path
        self.method = request.method
        self.start_time = time.time()

    def get_elapsed_time(self) -> float:
        """Get elapsed time since request started."""
        return time.time() - self.start_time


class ErrorHandler:
    """Centralized error handler for API endpoints."""

    @staticmethod
    def create_error_response(
        error_code: str,
        message: str,
        status_code: int,
        request_context: RequestContext,
        detail: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a standardized error response.

        Args:
            error_code: Error code identifier
            message: Human-readable error message
            status_code: HTTP status code
            request_context: Request context with ID and timestamp
            detail: Additional error details
            **kwargs: Additional fields for specific error types

        Returns:
            Dictionary with error response
        """
        response = {
            "error": error_code,
            "message": message,
            "detail": detail,
            "request_id": request_context.request_id,
            "timestamp": request_context.timestamp,
            "status_code": status_code,
            "path": request_context.path,
            "method": request_context.method,
        }

        # Add any additional fields
        response.update(kwargs)

        return response

    @staticmethod
    def handle_validation_error(
        request_context: RequestContext,
        error_message: str,
        field_errors: Optional[List[ValidationErrorDetail]] = None,
        detail: Optional[str] = None
    ) -> JSONResponse:
        """
        Handle validation errors (400).

        Args:
            request_context: Request context
            error_message: Main error message
            field_errors: List of field-specific validation errors
            detail: Additional details

        Returns:
            JSONResponse with 400 status
        """
        response_data = ErrorHandler.create_error_response(
            error_code="validation_error",
            message=error_message,
            status_code=400,
            request_context=request_context,
            detail=detail or "Validation failed for input data"
        )

        if field_errors:
            response_data["errors"] = [
                {
                    "field": err.field,
                    "error": err.error,
                    "value": err.value
                }
                for err in field_errors
            ]

        logger.warning(
            f"Validation error for {request_context.method} {request_context.path}: {error_message}"
        )

        return JSONResponse(status_code=400, content=response_data)

    @staticmethod
    def handle_pii_error(
        request_context: RequestContext,
        pii_types: List[str],
        field_name: str = "input"
    ) -> JSONResponse:
        """
        Handle PII detection errors (400).

        Args:
            request_context: Request context
            pii_types: List of PII types detected
            field_name: Name of field containing PII

        Returns:
            JSONResponse with 400 status
        """
        pii_list = ", ".join(pii_types)
        response_data = ErrorHandler.create_error_response(
            error_code="pii_detected",
            message="Personally identifiable information detected in input",
            status_code=400,
            request_context=request_context,
            detail=f"PII detected in {field_name}: {pii_list}. Please remove personally identifiable information.",
            pii_types=pii_types
        )

        logger.warning(
            f"PII detected in {request_context.method} {request_context.path}: {pii_list}"
        )

        return JSONResponse(status_code=400, content=response_data)

    @staticmethod
    def handle_authentication_error(
        request_context: RequestContext,
        detail: str = "Invalid or missing API key",
        auth_scheme: str = "API-Key"
    ) -> JSONResponse:
        """
        Handle authentication errors (401).

        Args:
            request_context: Request context
            detail: Error detail message
            auth_scheme: Authentication scheme

        Returns:
            JSONResponse with 401 status
        """
        response_data = ErrorHandler.create_error_response(
            error_code="authentication_failed",
            message="Authentication failed",
            status_code=401,
            request_context=request_context,
            detail=detail,
            auth_scheme=auth_scheme
        )

        logger.warning(
            f"Authentication error for {request_context.method} {request_context.path}: {detail}"
        )

        return JSONResponse(status_code=401, content=response_data)

    @staticmethod
    def handle_rate_limit_error(
        request_context: RequestContext,
        limit: int,
        remaining: int,
        reset_seconds: int
    ) -> JSONResponse:
        """
        Handle rate limit errors (429).

        Args:
            request_context: Request context
            limit: Rate limit (requests per minute)
            remaining: Remaining requests
            reset_seconds: Seconds until rate limit resets

        Returns:
            JSONResponse with 429 status and Retry-After header
        """
        reset_time = (
            datetime.utcnow() + timedelta(seconds=reset_seconds)
        ).isoformat() + "Z"

        response_data = ErrorHandler.create_error_response(
            error_code="rate_limit_exceeded",
            message="Rate limit exceeded",
            status_code=429,
            request_context=request_context,
            detail=f"You have exceeded the rate limit of {limit} requests per minute",
            retry_after=reset_seconds,
            limit=limit,
            remaining=remaining,
            reset_time=reset_time
        )

        logger.warning(
            f"Rate limit exceeded for {request_context.method} {request_context.path}"
        )

        return JSONResponse(
            status_code=429,
            content=response_data,
            headers={
                "Retry-After": str(reset_seconds),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
                "X-RateLimit-Reset": str(int(time.time()) + reset_seconds)
            }
        )

    @staticmethod
    def handle_not_found_error(
        request_context: RequestContext,
        resource_type: str,
        resource_id: str,
        detail: Optional[str] = None
    ) -> JSONResponse:
        """
        Handle not found errors (404).

        Args:
            request_context: Request context
            resource_type: Type of resource (e.g., 'service', 'recommendation')
            resource_id: ID of resource that was not found
            detail: Additional detail message

        Returns:
            JSONResponse with 404 status
        """
        if not detail:
            detail = f"{resource_type.capitalize()} '{resource_id}' does not exist"

        response_data = ErrorHandler.create_error_response(
            error_code="not_found",
            message="Resource not found",
            status_code=404,
            request_context=request_context,
            detail=detail,
            resource_type=resource_type,
            resource_id=resource_id
        )

        logger.warning(
            f"Resource not found: {resource_type} {resource_id} for {request_context.method} {request_context.path}"
        )

        return JSONResponse(status_code=404, content=response_data)

    @staticmethod
    def handle_server_error(
        request_context: RequestContext,
        error: Exception,
        error_code: str = "internal_server_error",
        detail: Optional[str] = None
    ) -> JSONResponse:
        """
        Handle server errors (500).

        Args:
            request_context: Request context
            error: The exception that occurred
            error_code: Internal error code for debugging
            detail: Additional detail message

        Returns:
            JSONResponse with 500 status
        """
        if not detail:
            detail = "An internal server error occurred"

        response_data = ErrorHandler.create_error_response(
            error_code=error_code,
            message="An internal server error occurred",
            status_code=500,
            request_context=request_context,
            detail=detail
        )

        logger.error(
            f"Server error for {request_context.method} {request_context.path}: {str(error)}",
            exc_info=True
        )

        return JSONResponse(status_code=500, content=response_data)

    @staticmethod
    def handle_invalid_json_error(
        request_context: RequestContext,
        detail: str = "Invalid JSON in request body"
    ) -> JSONResponse:
        """
        Handle invalid JSON errors (400).

        Args:
            request_context: Request context
            detail: Error detail

        Returns:
            JSONResponse with 400 status
        """
        response_data = ErrorHandler.create_error_response(
            error_code="invalid_json",
            message="Invalid JSON in request body",
            status_code=400,
            request_context=request_context,
            detail=detail
        )

        logger.warning(
            f"Invalid JSON for {request_context.method} {request_context.path}: {detail}"
        )

        return JSONResponse(status_code=400, content=response_data)

    @staticmethod
    def handle_missing_field_error(
        request_context: RequestContext,
        field_name: str,
        detail: Optional[str] = None
    ) -> JSONResponse:
        """
        Handle missing required field errors (400).

        Args:
            request_context: Request context
            field_name: Name of missing field
            detail: Additional detail

        Returns:
            JSONResponse with 400 status
        """
        if not detail:
            detail = f"Required field '{field_name}' is missing"

        response_data = ErrorHandler.create_error_response(
            error_code="missing_field",
            message=f"Missing required field: {field_name}",
            status_code=400,
            request_context=request_context,
            detail=detail
        )

        logger.warning(
            f"Missing field '{field_name}' for {request_context.method} {request_context.path}"
        )

        return JSONResponse(status_code=400, content=response_data)

    @staticmethod
    def handle_timeout_error(
        request_context: RequestContext,
        timeout_seconds: float
    ) -> JSONResponse:
        """
        Handle timeout errors (504).

        Args:
            request_context: Request context
            timeout_seconds: Timeout duration

        Returns:
            JSONResponse with 504 status
        """
        response_data = ErrorHandler.create_error_response(
            error_code="request_timeout",
            message="Request timeout",
            status_code=504,
            request_context=request_context,
            detail=f"Request exceeded timeout of {timeout_seconds} seconds"
        )

        logger.warning(
            f"Request timeout for {request_context.method} {request_context.path}"
        )

        return JSONResponse(status_code=504, content=response_data)

    @staticmethod
    def handle_file_not_found_error(
        request_context: RequestContext,
        file_path: str,
        detail: Optional[str] = None
    ) -> JSONResponse:
        """
        Handle file not found errors (404).

        Args:
            request_context: Request context
            file_path: Path to file that was not found
            detail: Additional detail message

        Returns:
            JSONResponse with 404 status
        """
        if not detail:
            detail = f"Required data file not found: {file_path}"
            
        response_data = ErrorHandler.create_error_response(
            error_code="file_not_found",
            message="Required data file not found",
            status_code=404,
            request_context=request_context,
            detail=detail
        )

        logger.warning(
            f"File not found: {file_path} for {request_context.method} {request_context.path}"
        )

        return JSONResponse(status_code=404, content=response_data)

    @staticmethod
    def validate_and_handle_pii(
        request_context: RequestContext,
        data: Any,
        field_name: str = "input"
    ) -> Optional[JSONResponse]:
        """
        Validate data for PII and return error response if found.

        Args:
            request_context: Request context
            data: Data to validate
            field_name: Name of field for error messages

        Returns:
            JSONResponse if PII found, None otherwise
        """
        contains_pii, pii_types = PIIDetector.contains_pii(data)
        if contains_pii:
            return ErrorHandler.handle_pii_error(
                request_context,
                pii_types,
                field_name
            )
        return None
