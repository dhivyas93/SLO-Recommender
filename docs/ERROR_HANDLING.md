# Error Handling and Status Codes

## Overview

The SLO Recommendation System implements comprehensive, consistent error handling across all API endpoints. All errors follow a standardized JSON response format with unique request IDs for tracing, detailed error messages, and appropriate HTTP status codes.

## Error Response Format

All error responses follow this standard format:

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "detail": "Additional details about the error",
  "request_id": "unique-request-id",
  "timestamp": "2024-01-15T10:30:00Z",
  "status_code": 400,
  "path": "/api/v1/services/payment-api/metrics",
  "method": "POST"
}
```

### Required Fields

- **error**: Error code identifier (e.g., `validation_error`, `not_found`, `rate_limit_exceeded`)
- **message**: Human-readable error message
- **detail**: Additional context about the error
- **request_id**: Unique UUID for request tracing
- **timestamp**: ISO 8601 timestamp when error occurred
- **status_code**: HTTP status code
- **path**: API endpoint path
- **method**: HTTP method (GET, POST, etc.)

## HTTP Status Codes

### 400 Bad Request

Used for client errors including:
- Invalid input or validation errors
- Missing required fields
- PII detection in input
- Invalid JSON in request body
- Invalid data types or ranges

**Error Codes:**
- `validation_error`: Input validation failed
- `pii_detected`: Personally identifiable information detected
- `invalid_json`: Invalid JSON in request body
- `missing_field`: Required field is missing

**Example:**
```json
{
  "error": "validation_error",
  "message": "Validation failed for input data",
  "detail": "latency_p95 must be >= latency_p50",
  "request_id": "req_abc123def456",
  "timestamp": "2024-01-15T10:30:00Z",
  "status_code": 400,
  "path": "/api/v1/services/payment-api/metrics",
  "method": "POST"
}
```

### 401 Unauthorized

Used for authentication failures:
- Invalid or missing API key
- Expired credentials
- Insufficient permissions

**Error Code:**
- `authentication_failed`: Authentication failed

**Example:**
```json
{
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
```

### 404 Not Found

Used when requested resource doesn't exist:
- Service not found
- Recommendation version not found
- Endpoint not found

**Error Code:**
- `not_found`: Resource not found

**Example:**
```json
{
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
```

### 429 Too Many Requests

Used when rate limit is exceeded:
- More than 100 requests per minute per API key

**Error Code:**
- `rate_limit_exceeded`: Rate limit exceeded

**Headers:**
- `Retry-After`: Seconds to wait before retrying
- `X-RateLimit-Limit`: Rate limit (requests per minute)
- `X-RateLimit-Remaining`: Remaining requests in current window
- `X-RateLimit-Reset`: Unix timestamp when rate limit resets

**Example:**
```json
{
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
```

### 500 Internal Server Error

Used for server-side errors:
- Processing failures
- Unexpected exceptions
- File system errors
- LLM integration failures

**Error Codes:**
- `internal_server_error`: Unexpected server error
- `recommendation_generation_failed`: Failed to generate recommendation
- `metrics_ingestion_failed`: Failed to ingest metrics
- `dependency_ingestion_failed`: Failed to ingest dependencies
- `file_not_found`: Required data file not found

**Example:**
```json
{
  "error": "recommendation_generation_failed",
  "message": "An internal server error occurred",
  "detail": "Failed to generate recommendation: Connection timeout",
  "request_id": "req_abc123def456",
  "timestamp": "2024-01-15T10:30:00Z",
  "status_code": 500,
  "path": "/api/v1/services/payment-api/slo-recommendations",
  "method": "GET",
  "error_code": "REC_ENGINE_FAILED"
}
```

### 504 Gateway Timeout

Used when request exceeds timeout:
- Recommendation generation exceeds 3 seconds
- External service timeout

**Error Code:**
- `request_timeout`: Request timeout

**Example:**
```json
{
  "error": "request_timeout",
  "message": "Request timeout",
  "detail": "Request exceeded timeout of 3 seconds",
  "request_id": "req_abc123def456",
  "timestamp": "2024-01-15T10:30:00Z",
  "status_code": 504,
  "path": "/api/v1/services/payment-api/slo-recommendations",
  "method": "GET"
}
```

## Validation Error Details

For validation errors, the response includes field-specific error information:

```json
{
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
```

## PII Detection

The system detects and rejects personally identifiable information (PII) in all inputs:

**Detected PII Types:**
- Email addresses
- Phone numbers (US and international formats)
- Social Security Numbers (SSN)
- Credit card numbers

**Example Error:**
```json
{
  "error": "pii_detected",
  "message": "Personally identifiable information detected in input",
  "detail": "PII detected in metrics_data: email, phone. Please remove personally identifiable information.",
  "request_id": "req_abc123def456",
  "timestamp": "2024-01-15T10:30:00Z",
  "status_code": 400,
  "path": "/api/v1/services/payment-api/metrics",
  "method": "POST",
  "pii_types": ["email", "phone"]
}
```

## Request Tracing

Every error response includes a unique `request_id` (UUID) for tracing:

```
request_id: "550e8400-e29b-41d4-a716-446655440000"
```

Use this ID to:
- Track requests through logs
- Correlate with server-side logs
- Debug issues with support team
- Implement request correlation in distributed systems

## Error Handling by Endpoint

### GET /api/v1/services/{service_id}/slo-recommendations

**Possible Errors:**
- 400: Invalid service_id, PII detected, no metrics found
- 401: Authentication failed
- 404: Service not found
- 429: Rate limit exceeded
- 500: Processing error
- 504: Request timeout (> 3 seconds)

### POST /api/v1/services/{service_id}/metrics

**Possible Errors:**
- 400: Invalid service_id, invalid JSON, PII detected, missing fields
- 401: Authentication failed
- 404: Service not found
- 429: Rate limit exceeded
- 500: Processing error

### POST /api/v1/services/dependencies

**Possible Errors:**
- 400: Invalid JSON, PII detected, missing fields
- 401: Authentication failed
- 429: Rate limit exceeded
- 500: Processing error

## Error Handling Best Practices

### For API Clients

1. **Always check status code first**
   ```python
   if response.status_code == 200:
       # Success
   elif response.status_code == 400:
       # Validation error - check 'errors' field
   elif response.status_code == 401:
       # Authentication error - check API key
   elif response.status_code == 429:
       # Rate limit - wait 'retry_after' seconds
   elif response.status_code == 404:
       # Resource not found
   elif response.status_code == 500:
       # Server error - retry with backoff
   ```

2. **Use request_id for debugging**
   ```python
   request_id = response.json()["request_id"]
   print(f"Error occurred in request {request_id}")
   # Share this ID with support team
   ```

3. **Handle rate limiting gracefully**
   ```python
   if response.status_code == 429:
       retry_after = int(response.headers["Retry-After"])
       time.sleep(retry_after)
       # Retry request
   ```

4. **Parse validation errors**
   ```python
   if response.status_code == 400:
       data = response.json()
       if "errors" in data:
           for error in data["errors"]:
               print(f"Field {error['field']}: {error['error']}")
   ```

### For API Developers

1. **Always include request context**
   - Use `RequestContext` to capture request metadata
   - Include request_id in all error responses

2. **Use appropriate error codes**
   - Choose error code that best describes the issue
   - Include helpful detail message

3. **Validate input early**
   - Check for PII before processing
   - Validate required fields
   - Return 400 for validation errors

4. **Log errors appropriately**
   - Log warnings for client errors (4xx)
   - Log errors for server errors (5xx)
   - Include request_id in logs for tracing

## Implementation Details

### Error Handler Module

Location: `src/api/error_handler.py`

**Key Classes:**
- `RequestContext`: Captures request metadata (ID, timestamp, path, method)
- `ErrorHandler`: Centralized error handling with methods for each error type

**Key Methods:**
- `handle_validation_error()`: 400 validation errors
- `handle_pii_error()`: 400 PII detection
- `handle_authentication_error()`: 401 authentication failures
- `handle_rate_limit_error()`: 429 rate limit exceeded
- `handle_not_found_error()`: 404 resource not found
- `handle_server_error()`: 500 server errors
- `handle_timeout_error()`: 504 request timeout
- `validate_and_handle_pii()`: Validate data for PII

### Error Response Models

Location: `src/models/error.py`

**Pydantic Models:**
- `ErrorResponse`: Base error response
- `ValidationErrorResponse`: Validation errors with field details
- `PIIErrorResponse`: PII detection errors
- `RateLimitErrorResponse`: Rate limit errors with retry info
- `AuthenticationErrorResponse`: Authentication errors
- `NotFoundErrorResponse`: Resource not found errors
- `ServerErrorResponse`: Server errors

### Exception Handlers

Location: `src/api/gateway.py`

**Registered Handlers:**
- `RequestValidationError`: Pydantic validation errors → 400
- `HTTPException`: FastAPI HTTP exceptions → appropriate status
- `Exception`: Unhandled exceptions → 500

## Testing

Comprehensive test suite: `tests/test_error_handling.py`

**Test Coverage:**
- Error response models (7 tests)
- Error handler methods (11 tests)
- Request context (2 tests)
- Error response format (3 tests)
- Edge cases (6 tests)

**Run Tests:**
```bash
pytest tests/test_error_handling.py -v
```

## Future Enhancements

1. **Error Recovery Suggestions**
   - Include suggested actions in error responses
   - Example: "Please check your API key" for 401 errors

2. **Error Analytics**
   - Track error rates by type and endpoint
   - Identify common issues

3. **Localization**
   - Support error messages in multiple languages
   - Configurable error message templates

4. **Error Webhooks**
   - Send critical errors to external monitoring systems
   - Integration with error tracking services (Sentry, etc.)

5. **Structured Logging**
   - Structured error logs for better analysis
   - Integration with log aggregation systems
