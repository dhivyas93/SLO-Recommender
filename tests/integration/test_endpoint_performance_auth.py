"""
Integration tests for performance and authentication in the recommendation endpoint.

Tests:
- Response time requirements (< 3 seconds)
- Authentication with various API keys
- Rate limiting behavior
- Edge cases with various service configurations
"""

import pytest
import time
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


def create_test_service(storage, service_id, **kwargs):
    """Helper to create a test service with metadata and metrics."""
    metadata = {
        "service_id": service_id,
        "version": kwargs.get("version", "1.0.0"),
        "service_type": kwargs.get("service_type", "api"),
        "team": kwargs.get("team", "platform"),
        "criticality": kwargs.get("criticality", "high"),
        "infrastructure": kwargs.get("infrastructure", {})
    }
    storage.write_json(f"services/{service_id}/metadata.json", metadata)
    
    metrics = {
        "service_id": service_id,
        "timestamp": "2024-01-15T10:30:00Z",
        "time_window": "1d",
        "metrics": {
            "latency": {
                "p50_ms": kwargs.get("p50_ms", 100.0),
                "p95_ms": kwargs.get("p95_ms", 200.0),
                "p99_ms": kwargs.get("p99_ms", 300.0),
                "mean_ms": kwargs.get("mean_ms", 150.0),
                "stddev_ms": kwargs.get("stddev_ms", 50.0)
            },
            "error_rate": {
                "percent": kwargs.get("error_rate", 1.0),
                "total_requests": 10000,
                "failed_requests": 100
            },
            "availability": {
                "percent": kwargs.get("availability", 99.5),
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
                    "p50_ms": kwargs.get("p50_ms", 100.0),
                    "p75_ms": kwargs.get("p75_ms", 150.0),
                    "p95_ms": kwargs.get("p95_ms", 200.0),
                    "p99_ms": kwargs.get("p99_ms", 300.0),
                    "mean_ms": kwargs.get("mean_ms", 150.0),
                    "stddev_ms": kwargs.get("stddev_ms", 50.0)
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


class TestResponseTime:
    """Test response time requirements."""
    
    def test_response_time_under_3_seconds(self, client, storage):
        """Test that response time is under 3 seconds."""
        service_id = "perf-test-service"
        create_test_service(storage, service_id)
        
        start = time.time()
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed <= 3.0
        
        # Also check the response_time_seconds field
        data = response.json()
        assert data["response_time_seconds"] <= 3.0
    
    def test_response_time_field_present(self, client, storage):
        """Test that response includes response_time_seconds field."""
        service_id = "perf-test-service-2"
        create_test_service(storage, service_id)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "response_time_seconds" in data
        assert isinstance(data["response_time_seconds"], (int, float))
        assert data["response_time_seconds"] > 0


class TestAuthentication:
    """Test authentication functionality."""
    
    def test_valid_api_key_accepted(self, client, storage):
        """Test that valid API key is accepted."""
        service_id = "auth-test-service"
        create_test_service(storage, service_id)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
    
    def test_missing_api_key_rejected(self, client, storage):
        """Test that missing API key is rejected."""
        service_id = "auth-test-service-2"
        create_test_service(storage, service_id)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations"
        )
        
        assert response.status_code == 401
    
    def test_invalid_api_key_rejected(self, client, storage):
        """Test that invalid API key is rejected."""
        service_id = "auth-test-service-3"
        create_test_service(storage, service_id)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "invalid-key-xyz"}
        )
        
        assert response.status_code == 401
    
    def test_empty_api_key_rejected(self, client, storage):
        """Test that empty API key is rejected."""
        service_id = "auth-test-service-4"
        create_test_service(storage, service_id)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": ""}
        )
        
        assert response.status_code == 401


class TestEdgeCases:
    """Test edge cases with various service configurations."""
    
    def test_service_with_high_latency(self, client, storage):
        """Test service with very high latency."""
        service_id = "high-latency-service"
        create_test_service(
            storage, service_id,
            p50_ms=5000.0,
            p95_ms=10000.0,
            p99_ms=15000.0,
            mean_ms=8000.0,
            stddev_ms=2000.0
        )
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify recommendations are reasonable
        tiers = data["recommendations"]
        assert tiers["balanced"]["latency_p95_ms"] > 0
        assert tiers["balanced"]["latency_p99_ms"] > tiers["balanced"]["latency_p95_ms"]
    
    def test_service_with_low_availability(self, client, storage):
        """Test service with low availability."""
        service_id = "low-availability-service"
        create_test_service(
            storage, service_id,
            availability=90.0
        )
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify recommendations respect minimum thresholds
        tiers = data["recommendations"]
        assert tiers["conservative"]["availability"] >= 90.0
    
    def test_service_with_high_error_rate(self, client, storage):
        """Test service with high error rate."""
        service_id = "high-error-service"
        create_test_service(
            storage, service_id,
            error_rate=5.0
        )
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify recommendations are generated
        assert "recommendations" in data
        assert "balanced" in data["recommendations"]
    
    def test_service_with_infrastructure_constraints(self, client, storage):
        """Test service with infrastructure constraints."""
        service_id = "infra-constrained-service"
        infrastructure = {
            "datastores": [
                {
                    "name": "postgres-primary",
                    "type": "postgresql",
                    "availability_slo": 99.9,
                    "latency_p95_ms": 50.0
                }
            ],
            "caches": [
                {
                    "name": "redis-cache",
                    "type": "redis",
                    "availability_slo": 99.95,
                    "latency_p95_ms": 5.0
                }
            ]
        }
        create_test_service(
            storage, service_id,
            infrastructure=infrastructure
        )
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify infrastructure constraints are mentioned in explanation
        explanation = data["explanation"]
        assert "infrastructure_bottlenecks" in explanation
    
    def test_service_with_dependencies(self, client, storage):
        """Test service with upstream dependencies."""
        upstream_id = "upstream-service"
        service_id = "dependent-service"
        
        # Create upstream service
        create_test_service(
            storage, upstream_id,
            availability=99.9,
            p95_ms=100.0
        )
        
        # Create dependent service
        create_test_service(
            storage, service_id,
            availability=99.5,
            p95_ms=200.0
        )
        
        # Create dependency graph
        dep_graph = {
            "services": [
                {
                    "service_id": upstream_id,
                    "upstream_services": [],
                    "downstream_services": [service_id],
                    "critical_path": [upstream_id],
                    "critical_path_latency_budget_ms": 500.0,
                    "cascading_impact_score": 0.8,
                    "is_in_circular_dependency": False
                },
                {
                    "service_id": service_id,
                    "upstream_services": [upstream_id],
                    "downstream_services": [],
                    "critical_path": [upstream_id, service_id],
                    "critical_path_latency_budget_ms": 500.0,
                    "cascading_impact_score": 0.5,
                    "is_in_circular_dependency": False
                }
            ]
        }
        storage.write_json("dependencies/analyzed_graph.json", dep_graph)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify dependency constraints are mentioned
        explanation = data["explanation"]
        assert "dependency_constraints" in explanation
    
    def test_service_with_very_low_latency(self, client, storage):
        """Test service with very low latency."""
        service_id = "low-latency-service"
        create_test_service(
            storage, service_id,
            p50_ms=1.0,
            p95_ms=5.0,
            p99_ms=10.0,
            mean_ms=3.0,
            stddev_ms=1.0
        )
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify recommendations are reasonable
        tiers = data["recommendations"]
        assert tiers["balanced"]["latency_p95_ms"] > 0
    
    def test_service_with_perfect_availability(self, client, storage):
        """Test service with perfect availability."""
        service_id = "perfect-availability-service"
        create_test_service(
            storage, service_id,
            availability=100.0
        )
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify recommendations are generated
        tiers = data["recommendations"]
        assert tiers["balanced"]["availability"] > 0
    
    def test_service_with_zero_error_rate(self, client, storage):
        """Test service with zero error rate."""
        service_id = "zero-error-service"
        create_test_service(
            storage, service_id,
            error_rate=0.0
        )
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify recommendations are generated
        tiers = data["recommendations"]
        assert tiers["balanced"]["error_rate_percent"] >= 0


class TestConfidenceScore:
    """Test confidence score calculation."""
    
    def test_confidence_score_in_valid_range(self, client, storage):
        """Test that confidence score is between 0 and 1."""
        service_id = "confidence-test-service"
        create_test_service(storage, service_id)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        confidence = data["confidence_score"]
        assert 0 <= confidence <= 1
    
    def test_confidence_score_is_numeric(self, client, storage):
        """Test that confidence score is numeric."""
        service_id = "confidence-test-service-2"
        create_test_service(storage, service_id)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        confidence = data["confidence_score"]
        assert isinstance(confidence, (int, float))


class TestTierOrdering:
    """Test that recommendation tiers are properly ordered."""
    
    def test_tier_ordering_availability(self, client, storage):
        """Test that availability tiers are ordered correctly."""
        service_id = "tier-order-test-1"
        create_test_service(storage, service_id)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        tiers = data["recommendations"]
        aggressive = tiers["aggressive"]["availability"]
        balanced = tiers["balanced"]["availability"]
        conservative = tiers["conservative"]["availability"]
        
        # Availability: aggressive >= balanced >= conservative
        assert aggressive >= balanced
        assert balanced >= conservative
    
    def test_tier_ordering_latency_p95(self, client, storage):
        """Test that latency p95 tiers are ordered correctly."""
        service_id = "tier-order-test-2"
        create_test_service(storage, service_id)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        tiers = data["recommendations"]
        aggressive = tiers["aggressive"]["latency_p95_ms"]
        balanced = tiers["balanced"]["latency_p95_ms"]
        conservative = tiers["conservative"]["latency_p95_ms"]
        
        # Latency p95: aggressive <= balanced <= conservative
        assert aggressive <= balanced
        assert balanced <= conservative
    
    def test_tier_ordering_error_rate(self, client, storage):
        """Test that error rate tiers are ordered correctly."""
        service_id = "tier-order-test-3"
        create_test_service(storage, service_id)
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        tiers = data["recommendations"]
        aggressive = tiers["aggressive"]["error_rate_percent"]
        balanced = tiers["balanced"]["error_rate_percent"]
        conservative = tiers["conservative"]["error_rate_percent"]
        
        # Error rate: aggressive <= balanced <= conservative
        assert aggressive <= balanced
        assert balanced <= conservative


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
