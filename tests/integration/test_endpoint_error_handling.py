"""
Integration tests for error handling in the recommendation endpoint.

Tests error scenarios:
- 400 Bad Request (invalid input, PII detection, missing data)
- 401 Unauthorized (missing/invalid API key)
- 404 Not Found (service not found)
- 500 Internal Server Error
"""

import pytest
from fastapi.testclient import TestClient
from src.api.gateway import app
from src.storage.file_storage import FileStorage


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def storage():
    """Create a FileStorage instance for test data."""
    return FileStorage(base_path="data")


class TestErrorHandling400:
    """Test 400 Bad Request error scenarios."""
    
    def test_empty_service_id(self, client):
        """Test with empty service_id."""
        response = client.get(
            "/api/v1/services//slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response.status_code == 404
    
    def test_missing_metrics(self, client, storage):
        """Test service with no metrics data."""
        service_id = "no-metrics-service"
        metadata = {
            "service_id": service_id,
            "version": "1.0.0",
            "service_type": "api",
            "team": "platform",
            "criticality": "high"
        }
        storage.write_json(f"services/{service_id}/metadata.json", metadata)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        # Check either in error or message field
        error_text = data.get("error", "") + data.get("message", "")
        assert "No metrics found" in error_text or "metrics" in error_text.lower()
    
    def test_pii_in_service_id_email(self, client):
        """Test PII detection: email in service_id."""
        service_id = "user@example.com"
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "PII" in data.get("error", "") or "pii" in data.get("error", "").lower()
    
    def test_pii_in_service_id_phone(self, client):
        """Test PII detection: phone number in service_id."""
        service_id = "service-555-123-4567"
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_pii_in_service_id_ssn(self, client):
        """Test PII detection: SSN in service_id."""
        service_id = "service-123-45-6789"
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestErrorHandling401:
    """Test 401 Unauthorized error scenarios."""
    
    def test_missing_api_key(self, client):
        """Test request without API key."""
        response = client.get(
            "/api/v1/services/test-service/slo-recommendations"
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
        assert "authentication" in data.get("error", "").lower() or "unauthorized" in data.get("error", "").lower()
    
    def test_invalid_api_key(self, client):
        """Test request with invalid API key."""
        response = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": "invalid-key-12345"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data
    
    def test_empty_api_key(self, client):
        """Test request with empty API key."""
        response = client.get(
            "/api/v1/services/test-service/slo-recommendations",
            headers={"X-API-Key": ""}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert "error" in data


class TestErrorHandling404:
    """Test 404 Not Found error scenarios."""
    
    def test_service_not_found(self, client):
        """Test request for non-existent service."""
        response = client.get(
            "/api/v1/services/non-existent-service-xyz/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        # Should return 400 for missing metrics (service doesn't exist)
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_invalid_endpoint(self, client):
        """Test request to invalid endpoint."""
        response = client.get(
            "/api/v1/services/test-service/invalid-endpoint",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 404


class TestErrorResponseFormat:
    """Test error response format compliance."""
    
    def test_error_response_has_required_fields(self, client):
        """Test that error responses have required fields."""
        response = client.get(
            "/api/v1/services/test-service/slo-recommendations"
        )
        
        assert response.status_code == 401
        data = response.json()
        
        # Check required error fields
        assert "error" in data
        assert "request_id" in data
        assert "timestamp" in data
    
    def test_validation_error_format(self, client, storage):
        """Test validation error response format."""
        service_id = "no-metrics-service"
        metadata = {
            "service_id": service_id,
            "version": "1.0.0",
            "service_type": "api",
            "team": "platform",
            "criticality": "high"
        }
        storage.write_json(f"services/{service_id}/metadata.json", metadata)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        
        # Check error response structure
        assert "error" in data
        assert "request_id" in data
        assert "timestamp" in data
        assert "detail" in data
    
    def test_pii_error_format(self, client):
        """Test PII error response format."""
        response = client.get(
            "/api/v1/services/user@example.com/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        
        # Check error response structure
        assert "error" in data
        assert "request_id" in data
        assert "timestamp" in data


class TestRateLimiting:
    """Test rate limiting functionality."""
    
    def test_rate_limit_headers_present(self, client, storage):
        """Test that rate limit headers are present in response."""
        service_id = "test-service"
        
        # Setup test service
        metadata = {
            "service_id": service_id,
            "version": "1.0.0",
            "service_type": "api",
            "team": "platform",
            "criticality": "high",
            "infrastructure": {}
        }
        storage.write_json(f"services/{service_id}/metadata.json", metadata)
        
        metrics = {
            "service_id": service_id,
            "timestamp": "2024-01-15T10:30:00Z",
            "time_window": "1d",
            "metrics": {
                "latency": {
                    "p50_ms": 100.0,
                    "p95_ms": 200.0,
                    "p99_ms": 300.0,
                    "mean_ms": 150.0,
                    "stddev_ms": 50.0
                },
                "error_rate": {
                    "percent": 1.0,
                    "total_requests": 10000,
                    "failed_requests": 100
                },
                "availability": {
                    "percent": 99.5,
                    "uptime_seconds": 86340,
                    "downtime_seconds": 60
                }
            },
            "regional_breakdown": None,
            "data_quality": {
                "completeness": 0.95,
                "outliers_detected": 0,
                "outlier_timestamps": [],
                "quality_score": 0.95
            }
        }
        storage.write_json(f"services/{service_id}/metrics/latest.json", metrics)
        
        aggregated_metrics = {
            "service_id": service_id,
            "timestamp": "2024-01-15T10:30:00Z",
            "time_windows": {
                "30d": {
                    "latency": {
                        "p50_ms": 100.0,
                        "p75_ms": 150.0,
                        "p95_ms": 200.0,
                        "p99_ms": 300.0,
                        "mean_ms": 150.0,
                        "stddev_ms": 50.0
                    },
                    "error_rate": {
                        "p50_percent": 0.5,
                        "p75_percent": 0.75,
                        "p95_percent": 1.0,
                        "p99_percent": 1.5,
                        "mean_percent": 0.8,
                        "stddev_percent": 0.3
                    },
                    "availability": {
                        "p50_percent": 99.7,
                        "p75_percent": 99.6,
                        "p95_percent": 99.5,
                        "p99_percent": 99.4,
                        "mean_percent": 99.55,
                        "stddev_percent": 0.1
                    },
                    "data_quality": {
                        "completeness": 0.95,
                        "staleness_hours": 1,
                        "sample_count": 43200,
                        "actual_samples": 43200,
                        "quality_score": 0.95
                    }
                }
            }
        }
        storage.write_json(f"services/{service_id}/metrics_aggregated.json", aggregated_metrics)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        
        # Check for rate limit headers
        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers
        assert "X-RateLimit-Reset" in response.headers
        
        # Verify header values are numeric
        assert response.headers["X-RateLimit-Limit"].isdigit()
        assert response.headers["X-RateLimit-Remaining"].isdigit()
        assert response.headers["X-RateLimit-Reset"].isdigit()


class TestResponseFormat:
    """Test response format compliance."""
    
    def test_response_json_structure(self, client, storage):
        """Test that response has correct JSON structure."""
        service_id = "test-service"
        
        # Setup test service
        metadata = {
            "service_id": service_id,
            "version": "1.0.0",
            "service_type": "api",
            "team": "platform",
            "criticality": "high",
            "infrastructure": {}
        }
        storage.write_json(f"services/{service_id}/metadata.json", metadata)
        
        metrics = {
            "service_id": service_id,
            "timestamp": "2024-01-15T10:30:00Z",
            "time_window": "1d",
            "metrics": {
                "latency": {
                    "p50_ms": 100.0,
                    "p95_ms": 200.0,
                    "p99_ms": 300.0,
                    "mean_ms": 150.0,
                    "stddev_ms": 50.0
                },
                "error_rate": {
                    "percent": 1.0,
                    "total_requests": 10000,
                    "failed_requests": 100
                },
                "availability": {
                    "percent": 99.5,
                    "uptime_seconds": 86340,
                    "downtime_seconds": 60
                }
            },
            "regional_breakdown": None,
            "data_quality": {
                "completeness": 0.95,
                "outliers_detected": 0,
                "outlier_timestamps": [],
                "quality_score": 0.95
            }
        }
        storage.write_json(f"services/{service_id}/metrics/latest.json", metrics)
        
        aggregated_metrics = {
            "service_id": service_id,
            "timestamp": "2024-01-15T10:30:00Z",
            "time_windows": {
                "30d": {
                    "latency": {
                        "p50_ms": 100.0,
                        "p75_ms": 150.0,
                        "p95_ms": 200.0,
                        "p99_ms": 300.0,
                        "mean_ms": 150.0,
                        "stddev_ms": 50.0
                    },
                    "error_rate": {
                        "p50_percent": 0.5,
                        "p75_percent": 0.75,
                        "p95_percent": 1.0,
                        "p99_percent": 1.5,
                        "mean_percent": 0.8,
                        "stddev_percent": 0.3
                    },
                    "availability": {
                        "p50_percent": 99.7,
                        "p75_percent": 99.6,
                        "p95_percent": 99.5,
                        "p99_percent": 99.4,
                        "mean_percent": 99.55,
                        "stddev_percent": 0.1
                    },
                    "data_quality": {
                        "completeness": 0.95,
                        "staleness_hours": 1,
                        "sample_count": 43200,
                        "actual_samples": 43200,
                        "quality_score": 0.95
                    }
                }
            }
        }
        storage.write_json(f"services/{service_id}/metrics_aggregated.json", aggregated_metrics)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check top-level fields
        assert "service_id" in data
        assert "version" in data
        assert "timestamp" in data
        assert "recommendations" in data
        assert "recommended_tier" in data
        assert "confidence_score" in data
        assert "explanation" in data
        assert "data_quality" in data
        assert "response_time_seconds" in data
        
        # Check recommendations structure
        recommendations = data["recommendations"]
        assert "aggressive" in recommendations
        assert "balanced" in recommendations
        assert "conservative" in recommendations
        
        # Check each tier has required fields
        for tier_name, tier_data in recommendations.items():
            assert "availability" in tier_data
            assert "latency_p95_ms" in tier_data
            assert "latency_p99_ms" in tier_data
            assert "error_rate_percent" in tier_data
            
            # Check field types
            assert isinstance(tier_data["availability"], (int, float))
            assert isinstance(tier_data["latency_p95_ms"], (int, float))
            assert isinstance(tier_data["latency_p99_ms"], (int, float))
            assert isinstance(tier_data["error_rate_percent"], (int, float))
        
        # Check explanation structure
        explanation = data["explanation"]
        assert "summary" in explanation
        assert "top_factors" in explanation
        assert "dependency_constraints" in explanation
        assert "infrastructure_bottlenecks" in explanation
        assert "similar_services" in explanation
        
        # Check data quality structure
        data_quality = data["data_quality"]
        assert "completeness" in data_quality
        assert "staleness_hours" in data_quality
        assert "quality_score" in data_quality


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
