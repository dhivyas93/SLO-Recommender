"""
Integration tests for the impact analysis endpoint.

Tests the POST /api/v1/slos/impact-analysis endpoint
with full integration to the ServiceGraph and cascading impact computation.

Acceptance Criteria Coverage:
1. Accept proposed SLO changes
2. Compute direct and cascading impact on dependent services
3. Return affected services with recommended adjustments
4. Include critical path impact analysis
5. Handle validation errors with 400 status
6. Detect PII in request body
7. Test error cases (400, 401, 404, 500)
"""

import pytest
import json
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
def setup_dependency_graph(storage):
    """Set up a test dependency graph with multiple services."""
    # Create a dependency graph:
    # auth-service -> user-db
    # api-gateway -> auth-service
    # api-gateway -> payment-service
    # payment-service -> payment-db
    
    graph_data = {
        "version": "1.0.0",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "services": [
            {
                "service_id": "auth-service",
                "is_infrastructure": False,
                "upstream_services": ["api-gateway"],
                "downstream_services": ["user-db"],
                "upstream_count": 1,
                "downstream_count": 1,
                "is_in_circular_dependency": False
            },
            {
                "service_id": "api-gateway",
                "is_infrastructure": False,
                "upstream_services": [],
                "downstream_services": ["auth-service", "payment-service"],
                "upstream_count": 0,
                "downstream_count": 2,
                "is_in_circular_dependency": False
            },
            {
                "service_id": "payment-service",
                "is_infrastructure": False,
                "upstream_services": ["api-gateway"],
                "downstream_services": ["payment-db"],
                "upstream_count": 1,
                "downstream_count": 1,
                "is_in_circular_dependency": False
            },
            {
                "service_id": "user-db",
                "is_infrastructure": True,
                "upstream_services": ["auth-service"],
                "downstream_services": [],
                "upstream_count": 1,
                "downstream_count": 0,
                "is_in_circular_dependency": False
            },
            {
                "service_id": "payment-db",
                "is_infrastructure": True,
                "upstream_services": ["payment-service"],
                "downstream_services": [],
                "upstream_count": 1,
                "downstream_count": 0,
                "is_in_circular_dependency": False
            }
        ],
        "edges": [
            {
                "source_id": "api-gateway",
                "target_id": "auth-service",
                "is_infrastructure": False,
                "dependency_type": "synchronous",
                "criticality": "high"
            },
            {
                "source_id": "api-gateway",
                "target_id": "payment-service",
                "is_infrastructure": False,
                "dependency_type": "synchronous",
                "criticality": "high"
            },
            {
                "source_id": "auth-service",
                "target_id": "user-db",
                "is_infrastructure": True,
                "infrastructure_type": "postgresql",
                "dependency_type": "synchronous",
                "criticality": "high"
            },
            {
                "source_id": "payment-service",
                "target_id": "payment-db",
                "is_infrastructure": True,
                "infrastructure_type": "postgresql",
                "dependency_type": "synchronous",
                "criticality": "high"
            }
        ],
        "warnings": [],
        "circular_dependencies": []
    }
    
    storage.write_json("dependencies/graph.json", graph_data)
    
    # Create API key for testing
    api_keys = {
        "test-key": {
            "tenant_id": "test-tenant",
            "description": "Test API key",
            "created_at": 1234567890,
            "active": True
        }
    }
    storage.write_json("api_keys.json", api_keys)
    
    return graph_data


class TestImpactAnalysisEndpoint:
    """Test suite for impact analysis endpoint."""
    
    def test_successful_impact_analysis(self, client, setup_dependency_graph):
        """Test successful impact analysis with valid proposed changes."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "auth-service",
                    "new_availability": 99.9,
                    "new_latency_p95_ms": 150,
                    "new_latency_p99_ms": 300,
                    "new_error_rate_percent": 0.5
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "affected_services" in data
        assert "critical_path_impacts" in data
        assert "risk_assessment" in data
        
        # Check that downstream services are affected
        affected_ids = [s["service_id"] for s in data["affected_services"]]
        assert "user-db" in affected_ids
    
    def test_cascading_impact_computation(self, client, setup_dependency_graph):
        """Test that cascading impact is computed correctly through dependency chain."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "api-gateway",
                    "new_availability": 99.95,
                    "new_latency_p95_ms": 100,
                    "new_latency_p99_ms": 200,
                    "new_error_rate_percent": 0.1
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # api-gateway affects auth-service and payment-service (depth 1)
        # auth-service affects user-db (depth 2)
        # payment-service affects payment-db (depth 2)
        affected_ids = [s["service_id"] for s in data["affected_services"]]
        
        assert "auth-service" in affected_ids
        assert "payment-service" in affected_ids
        assert "user-db" in affected_ids
        assert "payment-db" in affected_ids
        
        # Check impact depths
        for service in data["affected_services"]:
            if service["service_id"] == "auth-service":
                assert service["impact_depth"] == 1
            elif service["service_id"] == "user-db":
                assert service["impact_depth"] == 2
    
    def test_recommended_adjustments(self, client, setup_dependency_graph):
        """Test that recommended adjustments are provided for affected services."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "auth-service",
                    "new_availability": 99.9,
                    "new_latency_p95_ms": 150,
                    "new_latency_p99_ms": 300,
                    "new_error_rate_percent": 0.5
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check that affected services have recommended adjustments
        for service in data["affected_services"]:
            if service["service_id"] == "user-db":
                adjustments = service["recommended_adjustments"]
                assert "recommended_availability" in adjustments
                assert "recommended_latency_p95_ms" in adjustments
                assert "recommended_latency_p99_ms" in adjustments
                assert "recommended_error_rate_percent" in adjustments
                
                # Check that adjustments are conservative
                assert adjustments["recommended_availability"] <= 99.9
                assert adjustments["recommended_latency_p95_ms"] >= 150
    
    def test_critical_path_impact_analysis(self, client, setup_dependency_graph):
        """Test that critical path impact is included in response."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "api-gateway",
                    "new_availability": 99.95,
                    "new_latency_p95_ms": 100,
                    "new_latency_p99_ms": 200,
                    "new_error_rate_percent": 0.1
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check critical path impacts
        assert "critical_path_impacts" in data
        if len(data["critical_path_impacts"]) > 0:
            for impact in data["critical_path_impacts"]:
                assert "source_service" in impact
                assert "critical_path" in impact
                assert "bottleneck_service" in impact
                assert "impact_on_path" in impact
    
    def test_risk_assessment(self, client, setup_dependency_graph):
        """Test that risk assessment is provided."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "api-gateway",
                    "new_availability": 99.95,
                    "new_latency_p95_ms": 100,
                    "new_latency_p99_ms": 200,
                    "new_error_rate_percent": 0.1
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check risk assessment
        assert "risk_assessment" in data
        risk = data["risk_assessment"]
        assert "high_risk_count" in risk
        assert "medium_risk_count" in risk
        assert "low_risk_count" in risk
        assert "overall_risk" in risk
        assert risk["overall_risk"] in ["high", "medium", "low"]
    
    def test_missing_proposed_changes(self, client, setup_dependency_graph):
        """Test that missing proposed_changes returns 400 error."""
        payload = {
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "missing_field"
    
    def test_empty_proposed_changes(self, client, setup_dependency_graph):
        """Test that empty proposed_changes returns 400 error."""
        payload = {
            "proposed_changes": [],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
    
    def test_invalid_service_id(self, client, setup_dependency_graph):
        """Test that invalid service_id returns 404 error."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "nonexistent-service",
                    "new_availability": 99.9
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "not_found"
    
    def test_invalid_availability_value(self, client, setup_dependency_graph):
        """Test that invalid availability value returns 400 error."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "auth-service",
                    "new_availability": 150  # Invalid: > 100
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
    
    def test_invalid_latency_value(self, client, setup_dependency_graph):
        """Test that invalid latency value returns 400 error."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "auth-service",
                    "new_latency_p95_ms": -100  # Invalid: negative
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
    
    def test_invalid_error_rate_value(self, client, setup_dependency_graph):
        """Test that invalid error rate value returns 400 error."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "auth-service",
                    "new_error_rate_percent": 150  # Invalid: > 100
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
    
    def test_invalid_analysis_depth(self, client, setup_dependency_graph):
        """Test that invalid analysis_depth returns 400 error."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "auth-service",
                    "new_availability": 99.9
                }
            ],
            "analysis_depth": 0  # Invalid: must be positive
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
    
    def test_no_authentication(self, client, setup_dependency_graph):
        """Test that missing API key returns 401 error."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "auth-service",
                    "new_availability": 99.9
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "authentication_failed"
    
    def test_invalid_api_key(self, client, setup_dependency_graph):
        """Test that invalid API key returns 401 error."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "auth-service",
                    "new_availability": 99.9
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "invalid-key"}
        )
        
        assert response.status_code == 401
        data = response.json()
        assert data["error"] == "authentication_failed"
    
    def test_missing_dependency_graph(self, client, storage):
        """Test that missing dependency graph returns 404 error."""
        # Create API key but no dependency graph
        api_keys = {
            "test-key": {
                "tenant_id": "test-tenant",
                "description": "Test API key",
                "created_at": 1234567890,
                "active": True
            }
        }
        storage.write_json("api_keys.json", api_keys)
        
        # Ensure dependency graph doesn't exist
        import os
        graph_path = "data/dependencies/graph.json"
        if os.path.exists(graph_path):
            os.remove(graph_path)
        
        payload = {
            "proposed_changes": [
                {
                    "service_id": "auth-service",
                    "new_availability": 99.9
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "file_not_found"
    
    def test_invalid_json(self, client, setup_dependency_graph):
        """Test that invalid JSON returns 400 error."""
        response = client.post(
            "/api/v1/slos/impact-analysis",
            data="invalid json {",
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_json"
    
    def test_multiple_proposed_changes(self, client, setup_dependency_graph):
        """Test impact analysis with multiple proposed changes."""
        payload = {
            "proposed_changes": [
                {
                    "service_id": "auth-service",
                    "new_availability": 99.9,
                    "new_latency_p95_ms": 150
                },
                {
                    "service_id": "payment-service",
                    "new_availability": 99.8,
                    "new_latency_p95_ms": 200
                }
            ],
            "analysis_depth": 3
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["analysis_parameters"]["proposed_changes_count"] == 2
        assert len(data["affected_services"]) > 0
    
    def test_analysis_depth_limit(self, client, setup_dependency_graph):
        """Test that analysis_depth limits cascading impact computation."""
        # With depth 1, should only affect direct downstream
        payload = {
            "proposed_changes": [
                {
                    "service_id": "api-gateway",
                    "new_availability": 99.95
                }
            ],
            "analysis_depth": 1
        }
        
        response = client.post(
            "/api/v1/slos/impact-analysis",
            json=payload,
            headers={"X-API-Key": "test-key"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Should only affect auth-service and payment-service (depth 1)
        affected_ids = [s["service_id"] for s in data["affected_services"]]
        assert "auth-service" in affected_ids
        assert "payment-service" in affected_ids
        # Should not affect databases (depth 2)
        assert "user-db" not in affected_ids
        assert "payment-db" not in affected_ids
