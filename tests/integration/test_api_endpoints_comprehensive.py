"""
Comprehensive integration tests for all API endpoints.

Tests the complete workflow:
1. Dependency ingestion
2. Metrics ingestion
3. Recommendation generation
4. SLO acceptance
5. Audit and evaluation

These tests validate the actual response structure returned by the API.
"""

import pytest
import json
import time
from datetime import datetime
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
def setup_complete_scenario(storage):
    """Set up a complete scenario with services, dependencies, and metrics."""
    # Create two services: auth-service and api-gateway
    # auth-service is upstream, api-gateway depends on it
    
    # 1. Create auth-service metadata
    auth_metadata = {
        "service_id": "auth-service",
        "version": "1.0.0",
        "service_type": "auth",
        "team": "platform",
        "criticality": "critical",
        "infrastructure": {}
    }
    storage.write_json("services/auth-service/metadata.json", auth_metadata)
    
    # 2. Create auth-service metrics
    auth_metrics_aggregated = {
        "service_id": "auth-service",
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
    storage.write_json("services/auth-service/metrics_aggregated.json", auth_metrics_aggregated)
    
    # 3. Create api-gateway metadata
    api_metadata = {
        "service_id": "api-gateway",
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
    storage.write_json("services/api-gateway/metadata.json", api_metadata)
    
    # 4. Create api-gateway metrics
    api_metrics_aggregated = {
        "service_id": "api-gateway",
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
    storage.write_json("services/api-gateway/metrics_aggregated.json", api_metrics_aggregated)
    
    # 5. Create dependency graph
    dep_graph = {
        "services": [
            {
                "service_id": "auth-service",
                "upstream_services": [],
                "downstream_services": ["api-gateway"],
                "critical_path": ["auth-service"],
                "critical_path_latency_budget_ms": 500.0,
                "cascading_impact_score": 0.8,
                "is_in_circular_dependency": False
            },
            {
                "service_id": "api-gateway",
                "upstream_services": ["auth-service"],
                "downstream_services": [],
                "critical_path": ["auth-service", "api-gateway"],
                "critical_path_latency_budget_ms": 500.0,
                "cascading_impact_score": 0.5,
                "is_in_circular_dependency": False
            }
        ]
    }
    storage.write_json("dependencies/analyzed_graph.json", dep_graph)
    
    return {
        "auth_service": "auth-service",
        "api_gateway": "api-gateway"
    }


class TestRecommendationEndpoint:
    """Tests for GET /api/v1/services/{service_id}/slo-recommendations"""
    
    def test_recommendation_endpoint_success(self, client, setup_complete_scenario):
        """Test successful recommendation endpoint call."""
        service_id = setup_complete_scenario["api_gateway"]
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["status"] == "success"
        assert "timestamp" in data
        assert "request_id" in data
        assert "recommendation" in data
        
        # Verify recommendation structure
        rec = data["recommendation"]
        assert rec["service_id"] == service_id
        assert "recommendations" in rec
        assert "confidence_score" in rec
        assert "explanation" in rec
        assert "data_quality" in rec
        
        # Verify recommendations structure
        recommendations = rec["recommendations"]
        assert "aggressive" in recommendations
        assert "balanced" in recommendations
        assert "conservative" in recommendations
        
        # Verify each tier has required fields
        for tier_name, tier_data in recommendations.items():
            assert "availability" in tier_data
            assert "latency_p95_ms" in tier_data
            assert "latency_p99_ms" in tier_data
            assert "error_rate_percent" in tier_data
        
        # Verify confidence score is in valid range
        assert 0 <= rec["confidence_score"] <= 1
        
        # Verify explanation structure
        explanation = rec["explanation"]
        assert "summary" in explanation
        assert "top_factors" in explanation
        assert "dependency_constraints" in explanation
        assert "infrastructure_bottlenecks" in explanation
        assert "similar_services" in explanation
    
    def test_recommendation_endpoint_no_auth(self, client, setup_complete_scenario):
        """Test endpoint without authentication."""
        service_id = setup_complete_scenario["api_gateway"]
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations"
        )
        
        assert response.status_code == 401
    
    def test_recommendation_endpoint_invalid_api_key(self, client, setup_complete_scenario):
        """Test endpoint with invalid API key."""
        service_id = setup_complete_scenario["api_gateway"]
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "invalid-key"}
        )
        
        assert response.status_code == 401
    
    def test_recommendation_endpoint_tier_ordering(self, client, setup_complete_scenario):
        """Test that recommendation tiers are properly ordered."""
        service_id = setup_complete_scenario["api_gateway"]
        
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        tiers = data["recommendation"]["recommendations"]
        
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
    
    def test_recommendation_endpoint_response_time(self, client, setup_complete_scenario):
        """Test that response time is within 3 second limit."""
        service_id = setup_complete_scenario["api_gateway"]
        
        start = time.time()
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        elapsed = time.time() - start
        
        assert response.status_code == 200
        assert elapsed <= 3.0


class TestSLOAcceptanceEndpoint:
    """Tests for POST /api/v1/services/{service_id}/slos"""
    
    def test_accept_slo_with_balanced_tier(self, client, setup_complete_scenario):
        """Test accepting SLO with balanced tier."""
        service_id = setup_complete_scenario["api_gateway"]
        
        payload = {
            "action": "accept",
            "selected_tier": "balanced",
            "service_owner": "platform-team"
        }
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "request_id" in data
    
    def test_modify_slo_with_custom_values(self, client, setup_complete_scenario):
        """Test modifying SLO with custom values."""
        service_id = setup_complete_scenario["api_gateway"]
        
        payload = {
            "action": "modify",
            "selected_tier": "balanced",
            "custom_slos": {
                "availability": 99.5,
                "latency_p95_ms": 250.0,
                "latency_p99_ms": 400.0,
                "error_rate_percent": 1.0
            },
            "service_owner": "platform-team"
        }
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
    
    def test_reject_slo(self, client, setup_complete_scenario):
        """Test rejecting SLO."""
        service_id = setup_complete_scenario["api_gateway"]
        
        payload = {
            "action": "reject",
            "reason": "Need more time to analyze",
            "service_owner": "platform-team"
        }
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestDependencyIngestionEndpoint:
    """Tests for POST /api/v1/services/dependencies"""
    
    def test_ingest_dependencies_success(self, client, storage):
        """Test successful dependency ingestion."""
        payload = {
            "services": [
                {
                    "service_id": "service-a",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "service-b",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                },
                {
                    "service_id": "service-b",
                    "service_type": "database",
                    "dependencies": []
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestMetricsIngestionEndpoint:
    """Tests for POST /api/v1/services/{service_id}/metrics"""
    
    def test_metrics_ingestion_success(self, client, storage):
        """Test successful metrics ingestion."""
        service_id = "test-metrics-service"
        
        # Create service metadata first
        metadata = {
            "service_id": service_id,
            "version": "1.0.0",
            "service_type": "api",
            "team": "platform",
            "criticality": "high"
        }
        storage.write_json(f"services/{service_id}/metadata.json", metadata)
        
        payload = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
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
            }
        }
        
        response = client.post(
            f"/api/v1/services/{service_id}/metrics",
            json=payload,
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"


class TestAuditAndEvaluationEndpoints:
    """Tests for audit and evaluation endpoints"""
    
    def test_audit_export_endpoint(self, client):
        """Test audit log export endpoint."""
        response = client.get(
            "/api/v1/audit/export",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "entries" in data or "audit_logs" in data
    
    def test_evaluation_accuracy_endpoint(self, client):
        """Test evaluation accuracy endpoint."""
        response = client.get(
            "/api/v1/evaluation/accuracy",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "evaluation" in data or "metrics" in data


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
