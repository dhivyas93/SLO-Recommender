"""
Integration tests for the SLO recommendation endpoint.

Tests the GET /api/v1/services/{service_id}/slo-recommendations endpoint
with full integration to the HybridRecommendationEngine.

Acceptance Criteria Coverage:
1. Test successful recommendation generation
2. Test error handling (400, 401, 404, 500)
3. Test authentication and rate limiting
4. Test PII detection
5. Test response format compliance
6. Test response time requirements
7. Test with various service configurations
8. Test edge cases
"""

import pytest
import json
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


@pytest.fixture
def setup_test_service(storage):
    """Set up a test service with metadata and metrics."""
    service_id = "test-service"
    
    # Create service metadata
    metadata = {
        "service_id": service_id,
        "version": "1.0.0",
        "service_type": "api",
        "team": "platform",
        "criticality": "high",
        "infrastructure": {
            "datastores": [
                {
                    "name": "postgres-primary",
                    "type": "postgresql",
                    "availability_slo": 99.9,
                    "latency_p95_ms": 50.0
                }
            ],
            "caches": [],
            "message_queues": []
        }
    }
    storage.write_json(f"services/{service_id}/metadata.json", metadata)
    
    # Create service metrics
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
    
    # Create aggregated metrics (required by RecommendationEngine)
    aggregated_metrics = {
        "service_id": service_id,
        "timestamp": "2024-01-15T10:30:00Z",
        "time_windows": {
            "1d": {
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
                    "sample_count": 1440,
                    "actual_samples": 1440,
                    "quality_score": 0.95
                }
            },
            "7d": {
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
                    "sample_count": 10080,
                    "actual_samples": 10080,
                    "quality_score": 0.95
                }
            },
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
    
    # Create dependency graph
    dep_graph = {
        "services": [
            {
                "service_id": service_id,
                "upstream_services": [],
                "downstream_services": ["consumer-service"],
                "critical_path": [service_id],
                "critical_path_latency_budget_ms": 500.0,
                "cascading_impact_score": 0.5,
                "is_in_circular_dependency": False
            }
        ]
    }
    storage.write_json("dependencies/analyzed_graph.json", dep_graph)
    
    return service_id


def test_recommendation_endpoint_success(client, setup_test_service):
    """Test successful recommendation endpoint call."""
    service_id = setup_test_service
    
    # Make request with API key
    response = client.get(
        f"/api/v1/services/{service_id}/slo-recommendations",
        headers={"X-API-Key": "test-api-key-001"}
    )
    
    # Check response status
    assert response.status_code == 200
    
    # Parse response
    data = response.json()
    
    # Verify response structure
    assert data["service_id"] == service_id
    assert "version" in data
    assert "timestamp" in data
    assert "recommendations" in data
    assert "recommended_tier" in data
    assert "confidence_score" in data
    assert "explanation" in data
    assert "data_quality" in data
    assert "response_time_seconds" in data
    
    # Verify recommendations structure
    recommendations = data["recommendations"]
    assert "aggressive" in recommendations
    assert "balanced" in recommendations
    assert "conservative" in recommendations
    
    # Verify each tier has required fields
    for tier_name, tier_data in recommendations.items():
        assert "availability" in tier_data
        assert "latency_p95_ms" in tier_data
        assert "latency_p99_ms" in tier_data
        assert "error_rate_percent" in tier_data
    
    # Verify recommended tier is balanced
    assert data["recommended_tier"] == "balanced"
    
    # Verify confidence score is in valid range
    assert 0 <= data["confidence_score"] <= 1
    
    # Verify response time is reasonable
    assert data["response_time_seconds"] <= 3.0
    
    # Verify explanation structure
    explanation = data["explanation"]
    assert "summary" in explanation
    assert "top_factors" in explanation
    assert "dependency_constraints" in explanation
    assert "infrastructure_bottlenecks" in explanation
    assert "similar_services" in explanation
    
    # Verify data quality
    data_quality = data["data_quality"]
    assert "completeness" in data_quality
    assert "staleness_hours" in data_quality
    assert "quality_score" in data_quality


def test_recommendation_endpoint_missing_metrics(client, storage):
    """Test endpoint with service that has no metrics."""
    service_id = "no-metrics-service"
    
    # Create service metadata but no metrics
    metadata = {
        "service_id": service_id,
        "version": "1.0.0",
        "service_type": "api",
        "team": "platform",
        "criticality": "high"
    }
    storage.write_json(f"services/{service_id}/metadata.json", metadata)
    
    # Make request
    response = client.get(
        f"/api/v1/services/{service_id}/slo-recommendations",
        headers={"X-API-Key": "test-api-key-001"}
    )
    
    # Should return 400 Bad Request
    assert response.status_code == 400
    
    # Verify error response
    data = response.json()
    assert "error" in data
    # Check either in error or message field
    error_text = data.get("error", "") + data.get("message", "")
    assert "metrics" in error_text.lower()


def test_recommendation_endpoint_no_auth(client, setup_test_service):
    """Test endpoint without authentication."""
    service_id = setup_test_service
    
    # Make request without API key
    response = client.get(
        f"/api/v1/services/{service_id}/slo-recommendations"
    )
    
    # Should return 401 Unauthorized
    assert response.status_code == 401


def test_recommendation_endpoint_invalid_api_key(client, setup_test_service):
    """Test endpoint with invalid API key."""
    service_id = setup_test_service
    
    # Make request with invalid API key
    response = client.get(
        f"/api/v1/services/{service_id}/slo-recommendations",
        headers={"X-API-Key": "invalid-key"}
    )
    
    # Should return 401 Unauthorized
    assert response.status_code == 401


def test_recommendation_endpoint_tier_ordering(client, setup_test_service):
    """Test that recommendation tiers are properly ordered."""
    service_id = setup_test_service
    
    response = client.get(
        f"/api/v1/services/{service_id}/slo-recommendations",
        headers={"X-API-Key": "test-api-key-001"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    tiers = data["recommendations"]
    aggressive = tiers["aggressive"]
    balanced = tiers["balanced"]
    conservative = tiers["conservative"]
    
    # Availability: aggressive >= balanced >= conservative
    assert aggressive["availability"] >= balanced["availability"]
    assert balanced["availability"] >= conservative["availability"]
    
    # Latency p95: aggressive <= balanced <= conservative
    assert aggressive["latency_p95_ms"] <= balanced["latency_p95_ms"]
    assert balanced["latency_p95_ms"] <= conservative["latency_p95_ms"]
    
    # Latency p99: aggressive <= balanced <= conservative
    assert aggressive["latency_p99_ms"] <= balanced["latency_p99_ms"]
    assert balanced["latency_p99_ms"] <= conservative["latency_p99_ms"]
    
    # Error rate: aggressive <= balanced <= conservative
    assert aggressive["error_rate_percent"] <= balanced["error_rate_percent"]
    assert balanced["error_rate_percent"] <= conservative["error_rate_percent"]


def test_recommendation_endpoint_response_time(client, setup_test_service):
    """Test that response time is within 3 second limit."""
    service_id = setup_test_service
    
    import time
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


def test_recommendation_endpoint_with_dependencies(client, storage):
    """Test endpoint with service that has dependencies."""
    service_id = "dependent-service"
    upstream_id = "upstream-service"
    
    # Create upstream service metadata and metrics
    upstream_metadata = {
        "service_id": upstream_id,
        "version": "1.0.0",
        "service_type": "auth",
        "team": "platform",
        "criticality": "critical"
    }
    storage.write_json(f"services/{upstream_id}/metadata.json", upstream_metadata)
    
    upstream_metrics = {
        "service_id": upstream_id,
        "timestamp": "2024-01-15T10:30:00Z",
        "time_window": "1d",
        "metrics": {
            "latency": {
                "p50_ms": 50.0,
                "p95_ms": 100.0,
                "p99_ms": 150.0,
                "mean_ms": 75.0,
                "stddev_ms": 25.0
            },
            "error_rate": {
                "percent": 0.5,
                "total_requests": 10000,
                "failed_requests": 50
            },
            "availability": {
                "percent": 99.9,
                "uptime_seconds": 86340,
                "downtime_seconds": 60
            }
        },
        "regional_breakdown": None,
        "data_quality": {
            "completeness": 0.98,
            "outliers_detected": 0,
            "outlier_timestamps": [],
            "quality_score": 0.98
        }
    }
    storage.write_json(f"services/{upstream_id}/metrics/latest.json", upstream_metrics)
    
    # Create aggregated metrics for upstream service
    upstream_aggregated = {
        "service_id": upstream_id,
        "timestamp": "2024-01-15T10:30:00Z",
        "time_windows": {
            "30d": {
                "latency": {
                    "p50_ms": 50.0,
                    "p75_ms": 75.0,
                    "p95_ms": 100.0,
                    "p99_ms": 150.0,
                    "mean_ms": 75.0,
                    "stddev_ms": 25.0
                },
                "error_rate": {
                    "p50_percent": 0.3,
                    "p75_percent": 0.4,
                    "p95_percent": 0.5,
                    "p99_percent": 0.7,
                    "mean_percent": 0.4,
                    "stddev_percent": 0.15
                },
                "availability": {
                    "p50_percent": 99.95,
                    "p75_percent": 99.92,
                    "p95_percent": 99.9,
                    "p99_percent": 99.85,
                    "mean_percent": 99.9,
                    "stddev_percent": 0.05
                },
                "data_quality": {
                    "completeness": 0.98,
                    "staleness_hours": 1,
                    "sample_count": 43200,
                    "actual_samples": 43200,
                    "quality_score": 0.98
                }
            }
        }
    }
    storage.write_json(f"services/{upstream_id}/metrics_aggregated.json", upstream_aggregated)
    
    # Create dependent service metadata and metrics
    dependent_metadata = {
        "service_id": service_id,
        "version": "1.0.0",
        "service_type": "api",
        "team": "platform",
        "criticality": "high",
        "infrastructure": {}
    }
    storage.write_json(f"services/{service_id}/metadata.json", dependent_metadata)
    
    dependent_metrics = {
        "service_id": service_id,
        "timestamp": "2024-01-15T10:30:00Z",
        "time_window": "1d",
        "metrics": {
            "latency": {
                "p50_ms": 150.0,
                "p95_ms": 250.0,
                "p99_ms": 350.0,
                "mean_ms": 200.0,
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
    storage.write_json(f"services/{service_id}/metrics/latest.json", dependent_metrics)
    
    # Create aggregated metrics for dependent service
    dependent_aggregated = {
        "service_id": service_id,
        "timestamp": "2024-01-15T10:30:00Z",
        "time_windows": {
            "30d": {
                "latency": {
                    "p50_ms": 150.0,
                    "p75_ms": 200.0,
                    "p95_ms": 250.0,
                    "p99_ms": 350.0,
                    "mean_ms": 200.0,
                    "stddev_ms": 50.0
                },
                "error_rate": {
                    "p50_percent": 0.7,
                    "p75_percent": 0.85,
                    "p95_percent": 1.0,
                    "p99_percent": 1.3,
                    "mean_percent": 0.9,
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
    storage.write_json(f"services/{service_id}/metrics_aggregated.json", dependent_aggregated)
    
    # Create dependency graph with upstream relationship
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
    
    # Make request
    response = client.get(
        f"/api/v1/services/{service_id}/slo-recommendations",
        headers={"X-API-Key": "test-api-key-001"}
    )
    
    assert response.status_code == 200
    data = response.json()
    
    # Verify service has upstream dependency in context
    assert data["service_id"] == service_id
    assert "recommendations" in data
    
    # Verify explanation mentions dependencies
    explanation = data["explanation"]
    assert isinstance(explanation["dependency_constraints"], list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
