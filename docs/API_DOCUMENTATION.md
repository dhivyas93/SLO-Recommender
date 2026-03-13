# API Documentation

## Overview

The SLO Recommendation System provides a REST API for integrating SLO recommendations into developer platforms and internal tools. All endpoints require authentication via API key and are rate-limited.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

All API requests require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8000/api/v1/services/payment-api/slo-recommendations
```

### Getting an API Key

API keys are stored in `data/api_keys.json`. For testing, use one of the sample keys:

```json
{
  "key": "test-key-demo-tenant",
  "tenant_id": "demo-tenant",
  "rate_limit": 100
}
```

### Creating New API Keys

Add entries to `data/api_keys.json`:

```json
{
  "api_keys": [
    {
      "key": "your-unique-key",
      "tenant_id": "your-tenant",
      "created_at": "2024-01-15T10:00:00Z",
      "rate_limit": 100,
      "description": "Your key description"
    }
  ]
}
```

## Rate Limiting

The API enforces rate limiting per API key:

- **Default**: 100 requests per minute
- **Headers**: Rate limit information is included in all responses

### Rate Limit Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705318800
```

### Rate Limit Exceeded

When rate limit is exceeded, the API returns:

```
HTTP 429 Too Many Requests
Retry-After: 60
```

## Error Handling

### Error Response Format

All errors follow a consistent JSON format:

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid metric range",
    "details": {
      "field": "latency_p95_ms",
      "issue": "p95 must be >= p50"
    },
    "request_id": "req-12345-abcde"
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_API_KEY` | 401 | API key is missing or invalid |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `VALIDATION_ERROR` | 400 | Input validation failed |
| `PII_DETECTED` | 400 | Personal information detected in input |
| `SERVICE_NOT_FOUND` | 404 | Service does not exist |
| `DEPENDENCY_NOT_FOUND` | 404 | Dependency graph not found |
| `INTERNAL_ERROR` | 500 | Internal server error |

## Endpoints

### 1. Get SLO Recommendations

**Endpoint**: `GET /services/{service_id}/slo-recommendations`

**Description**: Get SLO recommendations for a specific service.

**Parameters**:
- `service_id` (path, required): Service identifier
- `tier` (query, optional): Filter by tier (aggressive, balanced, conservative)

**Request**:
```bash
curl -X GET "http://localhost:8000/api/v1/services/payment-api/slo-recommendations" \
  -H "X-API-Key: test-key-demo-tenant"
```

**Response** (200 OK):
```json
{
  "service_id": "payment-api",
  "version": "v1.0.0",
  "timestamp": "2024-01-15T10:30:00Z",
  "recommendations": {
    "aggressive": {
      "availability": 99.9,
      "latency_p95_ms": 150,
      "latency_p99_ms": 300,
      "error_rate_percent": 0.5
    },
    "balanced": {
      "availability": 99.5,
      "latency_p95_ms": 200,
      "latency_p99_ms": 400,
      "error_rate_percent": 1.0
    },
    "conservative": {
      "availability": 99.0,
      "latency_p95_ms": 300,
      "latency_p99_ms": 600,
      "error_rate_percent": 2.0
    }
  },
  "recommended_tier": "balanced",
  "confidence_score": 0.85,
  "explanation": {
    "summary": "Balanced tier recommended based on stable 30-day performance",
    "top_factors": [
      "Historical p95 latency: 180ms (30-day window)",
      "Downstream of auth-service (99.9% availability) requires margin",
      "PostgreSQL datastore adds 50ms baseline latency"
    ],
    "dependency_constraints": [
      "auth-service availability (99.9%) limits this service to 99.5%"
    ],
    "infrastructure_bottlenecks": [
      "PostgreSQL p95 latency: 45ms"
    ],
    "similar_services": [
      "checkout-api: 99.5% availability, 210ms p95 latency"
    ]
  },
  "data_quality": {
    "completeness": 0.98,
    "staleness_hours": 1,
    "quality_score": 0.95
  }
}
```

**Error Responses**:
- `404 Not Found`: Service not found
- `400 Bad Request`: Invalid service_id format

---

### 2. Submit Service Metrics

**Endpoint**: `POST /services/{service_id}/metrics`

**Description**: Submit operational metrics for a service.

**Parameters**:
- `service_id` (path, required): Service identifier

**Request Body**:
```json
{
  "time_window": "30d",
  "metrics": {
    "latency": {
      "p50_ms": 85,
      "p95_ms": 180,
      "p99_ms": 350,
      "mean_ms": 95,
      "stddev_ms": 45
    },
    "error_rate": {
      "percent": 0.8,
      "total_requests": 1000000,
      "failed_requests": 8000
    },
    "availability": {
      "percent": 99.6,
      "uptime_seconds": 86054,
      "downtime_seconds": 346
    }
  }
}
```

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/services/payment-api/metrics" \
  -H "X-API-Key: test-key-demo-tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "time_window": "30d",
    "metrics": {
      "latency": {
        "p50_ms": 85,
        "p95_ms": 180,
        "p99_ms": 350,
        "mean_ms": 95,
        "stddev_ms": 45
      },
      "error_rate": {
        "percent": 0.8,
        "total_requests": 1000000,
        "failed_requests": 8000
      },
      "availability": {
        "percent": 99.6,
        "uptime_seconds": 86054,
        "downtime_seconds": 346
      }
    }
  }'
```

**Response** (200 OK):
```json
{
  "service_id": "payment-api",
  "status": "accepted",
  "data_quality": {
    "completeness": 0.98,
    "outlier_count": 0,
    "quality_score": 0.98
  },
  "warnings": []
}
```

**Validation Rules**:
- `p95_ms >= p50_ms` (p95 must be >= p50)
- `p99_ms >= p95_ms` (p99 must be >= p95)
- `availability` must be 0-100
- `error_rate` must be 0-100
- No PII (email, phone, SSN) in any field

**Error Responses**:
- `400 Bad Request`: Validation failed
- `400 Bad Request`: PII detected in input

---

### 3. Submit Dependency Graph

**Endpoint**: `POST /services/dependencies`

**Description**: Submit service dependency graph (bulk ingestion).

**Request Body**:
```json
{
  "services": [
    {
      "service_id": "api-gateway",
      "dependencies": [
        {
          "target_service_id": "auth-service",
          "dependency_type": "synchronous",
          "timeout_ms": 500,
          "criticality": "high"
        },
        {
          "target_service_id": "payment-api",
          "dependency_type": "synchronous",
          "timeout_ms": 1000,
          "criticality": "high"
        }
      ]
    }
  ]
}
```

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/services/dependencies" \
  -H "X-API-Key: test-key-demo-tenant" \
  -H "Content-Type: application/json" \
  -d @dependencies.json
```

**Response** (200 OK):
```json
{
  "status": "accepted",
  "services_processed": 1,
  "edges_created": 2,
  "warnings": [
    "Service 'unknown-service' referenced but not found"
  ]
}
```

**Error Responses**:
- `400 Bad Request`: Invalid dependency format

---

### 4. Accept or Modify Recommendation

**Endpoint**: `POST /services/{service_id}/slos`

**Description**: Accept, modify, or reject a recommendation.

**Parameters**:
- `service_id` (path, required): Service identifier

**Request Body**:
```json
{
  "action": "accept",
  "tier_selected": "balanced",
  "comments": "Looks reasonable based on our traffic patterns"
}
```

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/services/payment-api/slos" \
  -H "X-API-Key: test-key-demo-tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accept",
    "tier_selected": "balanced",
    "comments": "Looks reasonable"
  }'
```

**Response** (200 OK):
```json
{
  "service_id": "payment-api",
  "action": "accept",
  "applied_slo": {
    "availability": 99.5,
    "latency_p95_ms": 200,
    "latency_p99_ms": 400,
    "error_rate_percent": 1.0
  },
  "timestamp": "2024-01-15T10:35:00Z"
}
```

**Actions**:
- `accept`: Accept the recommended tier
- `modify`: Modify specific SLO values
- `reject`: Reject the recommendation

**Error Responses**:
- `404 Not Found`: Service not found
- `400 Bad Request`: Invalid action

---

### 5. Get Recommendation History

**Endpoint**: `GET /services/{service_id}/slo-recommendations/history`

**Description**: Get all historical recommendations for a service.

**Parameters**:
- `service_id` (path, required): Service identifier
- `limit` (query, optional): Maximum number of versions (default: 10)
- `offset` (query, optional): Pagination offset (default: 0)

**Request**:
```bash
curl -X GET "http://localhost:8000/api/v1/services/payment-api/slo-recommendations/history?limit=5" \
  -H "X-API-Key: test-key-demo-tenant"
```

**Response** (200 OK):
```json
{
  "service_id": "payment-api",
  "total_versions": 3,
  "versions": [
    {
      "version": "v1.0.0",
      "timestamp": "2024-01-15T10:30:00Z",
      "recommended_tier": "balanced",
      "confidence_score": 0.85
    },
    {
      "version": "v0.9.0",
      "timestamp": "2024-01-14T15:20:00Z",
      "recommended_tier": "conservative",
      "confidence_score": 0.72
    }
  ]
}
```

---

### 6. Get Specific Recommendation Version

**Endpoint**: `GET /services/{service_id}/slo-recommendations/{version}`

**Description**: Get a specific version of a recommendation.

**Parameters**:
- `service_id` (path, required): Service identifier
- `version` (path, required): Version identifier (e.g., v1.0.0)

**Request**:
```bash
curl -X GET "http://localhost:8000/api/v1/services/payment-api/slo-recommendations/v1.0.0" \
  -H "X-API-Key: test-key-demo-tenant"
```

**Response** (200 OK): Same as "Get SLO Recommendations" endpoint

---

### 7. Impact Analysis

**Endpoint**: `POST /slos/impact-analysis`

**Description**: Analyze cascading impact of proposed SLO changes.

**Request Body**:
```json
{
  "proposed_changes": [
    {
      "service_id": "auth-service",
      "proposed_availability": 99.8
    }
  ]
}
```

**Request**:
```bash
curl -X POST "http://localhost:8000/api/v1/slos/impact-analysis" \
  -H "X-API-Key: test-key-demo-tenant" \
  -H "Content-Type: application/json" \
  -d '{
    "proposed_changes": [
      {
        "service_id": "auth-service",
        "proposed_availability": 99.8
      }
    ]
  }'
```

**Response** (200 OK):
```json
{
  "analysis": {
    "direct_impact": [
      {
        "service_id": "api-gateway",
        "impact_type": "availability_constraint",
        "recommended_adjustment": "Reduce availability to 99.8%"
      }
    ],
    "cascading_impact": [
      {
        "service_id": "order-service",
        "depth": 2,
        "impact_score": 0.45
      }
    ]
  }
}
```

---

### 8. Audit Log Export

**Endpoint**: `GET /audit/export`

**Description**: Export audit logs in JSON format.

**Parameters**:
- `start_date` (query, optional): Start date (ISO 8601)
- `end_date` (query, optional): End date (ISO 8601)
- `service_id` (query, optional): Filter by service

**Request**:
```bash
curl -X GET "http://localhost:8000/api/v1/audit/export?start_date=2024-01-01&end_date=2024-01-31" \
  -H "X-API-Key: test-key-demo-tenant"
```

**Response** (200 OK):
```json
{
  "audit_logs": [
    {
      "timestamp": "2024-01-15T10:30:00Z",
      "request_id": "req-12345-abcde",
      "api_key": "test-key-demo-tenant",
      "endpoint": "GET /services/payment-api/slo-recommendations",
      "status_code": 200,
      "service_id": "payment-api",
      "action": "recommendation_requested"
    }
  ],
  "total_records": 1
}
```

---

### 9. Evaluation Metrics

**Endpoint**: `GET /evaluation/accuracy`

**Description**: Get system-wide accuracy metrics.

**Request**:
```bash
curl -X GET "http://localhost:8000/api/v1/evaluation/accuracy" \
  -H "X-API-Key: test-key-demo-tenant"
```

**Response** (200 OK):
```json
{
  "evaluation_date": "2024-01-15",
  "metrics": {
    "overall_accuracy": 0.87,
    "aggressive_precision": 0.72,
    "balanced_precision": 0.91,
    "conservative_precision": 0.98,
    "acceptance_rate": 0.83
  },
  "by_service_type": {
    "api_gateway": {
      "accuracy": 0.92,
      "sample_size": 5
    },
    "database": {
      "accuracy": 0.95,
      "sample_size": 3
    }
  }
}
```

---

### 10. Health Check

**Endpoint**: `GET /health`

**Description**: Check API health status.

**Request**:
```bash
curl http://localhost:8000/health
```

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "components": {
    "api": "healthy",
    "file_storage": "healthy",
    "llm": "healthy"
  }
}
```

---

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request succeeded |
| 400 | Bad Request - Invalid input |
| 401 | Unauthorized - Invalid API key |
| 404 | Not Found - Resource not found |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error |

## Best Practices

### 1. Error Handling

Always check the response status code and handle errors gracefully:

```python
import requests

response = requests.get(
    "http://localhost:8000/api/v1/services/payment-api/slo-recommendations",
    headers={"X-API-Key": "test-key-demo-tenant"}
)

if response.status_code == 200:
    recommendations = response.json()
elif response.status_code == 401:
    print("Invalid API key")
elif response.status_code == 429:
    retry_after = response.headers.get("Retry-After", 60)
    print(f"Rate limited. Retry after {retry_after} seconds")
else:
    print(f"Error: {response.status_code}")
    print(response.json())
```

### 2. Rate Limiting

Monitor rate limit headers and implement backoff:

```python
remaining = int(response.headers.get("X-RateLimit-Remaining", 0))
if remaining < 10:
    print("Approaching rate limit")
```

### 3. Pagination

Use limit and offset for large result sets:

```bash
# Get first 10 versions
curl "http://localhost:8000/api/v1/services/payment-api/slo-recommendations/history?limit=10&offset=0"

# Get next 10 versions
curl "http://localhost:8000/api/v1/services/payment-api/slo-recommendations/history?limit=10&offset=10"
```

### 4. Validation

Validate input before sending:

```python
# Ensure metric relationships
assert metrics["latency"]["p95_ms"] >= metrics["latency"]["p50_ms"]
assert metrics["latency"]["p99_ms"] >= metrics["latency"]["p95_ms"]
assert 0 <= metrics["availability"]["percent"] <= 100
assert 0 <= metrics["error_rate"]["percent"] <= 100
```

## Integration Examples

### Python

```python
import requests
import json

API_KEY = "test-key-demo-tenant"
BASE_URL = "http://localhost:8000/api/v1"

def get_recommendations(service_id):
    response = requests.get(
        f"{BASE_URL}/services/{service_id}/slo-recommendations",
        headers={"X-API-Key": API_KEY}
    )
    return response.json()

def submit_metrics(service_id, metrics):
    response = requests.post(
        f"{BASE_URL}/services/{service_id}/metrics",
        headers={"X-API-Key": API_KEY},
        json=metrics
    )
    return response.json()

# Get recommendations
recs = get_recommendations("payment-api")
print(f"Recommended tier: {recs['recommended_tier']}")
print(f"Confidence: {recs['confidence_score']}")
```

### JavaScript/Node.js

```javascript
const API_KEY = "test-key-demo-tenant";
const BASE_URL = "http://localhost:8000/api/v1";

async function getRecommendations(serviceId) {
  const response = await fetch(
    `${BASE_URL}/services/${serviceId}/slo-recommendations`,
    {
      headers: { "X-API-Key": API_KEY }
    }
  );
  return response.json();
}

async function submitMetrics(serviceId, metrics) {
  const response = await fetch(
    `${BASE_URL}/services/${serviceId}/metrics`,
    {
      method: "POST",
      headers: {
        "X-API-Key": API_KEY,
        "Content-Type": "application/json"
      },
      body: JSON.stringify(metrics)
    }
  );
  return response.json();
}

// Get recommendations
const recs = await getRecommendations("payment-api");
console.log(`Recommended tier: ${recs.recommended_tier}`);
```

### cURL

```bash
# Get recommendations
curl -X GET "http://localhost:8000/api/v1/services/payment-api/slo-recommendations" \
  -H "X-API-Key: test-key-demo-tenant"

# Submit metrics
curl -X POST "http://localhost:8000/api/v1/services/payment-api/metrics" \
  -H "X-API-Key: test-key-demo-tenant" \
  -H "Content-Type: application/json" \
  -d @metrics.json

# Accept recommendation
curl -X POST "http://localhost:8000/api/v1/services/payment-api/slos" \
  -H "X-API-Key: test-key-demo-tenant" \
  -H "Content-Type: application/json" \
  -d '{"action": "accept", "tier_selected": "balanced"}'
```

## OpenAPI Specification

The API provides an OpenAPI 3.0 specification at:

```
http://localhost:8000/api/v1/docs
```

This includes:
- Interactive API documentation (Swagger UI)
- Request/response schemas
- Example values
- Try-it-out functionality

## Versioning

The API uses URL versioning (`/api/v1/`). Future versions will be available at `/api/v2/`, etc.

Current version: **v1**

## Support

For API issues or questions:
1. Check the [API Documentation](http://localhost:8000/docs)
2. Review error messages and error codes
3. Check the [Troubleshooting Guide](../README.md#-troubleshooting)
4. Open an issue in the repository
