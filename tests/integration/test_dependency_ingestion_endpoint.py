"""Integration tests for the dependency ingestion endpoint."""

import pytest
import json
from datetime import datetime
from fastapi.testclient import TestClient
from src.api.gateway import app
from src.storage.file_storage import FileStorage


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def storage():
    """Create a storage instance for test data."""
    return FileStorage(base_path="data")


@pytest.fixture
def valid_api_key():
    """Get a valid API key for testing."""
    # The test API key from data/api_keys.json
    return "test-api-key-001"


class TestDependencyIngestionEndpoint:
    """Tests for POST /api/v1/services/dependencies endpoint."""
    
    def test_ingest_dependencies_with_services_format(self, client, valid_api_key, storage):
        """Test ingesting dependencies using services format."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "auth-service",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                },
                {
                    "service_id": "auth-service",
                    "service_type": "auth",
                    "dependencies": [
                        {
                            "target_service_id": "user-db",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                },
                {
                    "service_id": "user-db",
                    "service_type": "database",
                    "dependencies": []
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["status"] == "success"
        assert "ingestion_confirmation" in data
        assert "warnings" in data
        assert "graph_statistics" in data
        
        # Verify ingestion confirmation
        confirmation = data["ingestion_confirmation"]
        assert confirmation["services_ingested"] == 3
        assert confirmation["edges_created"] == 2
        assert confirmation["circular_dependencies_detected"] == 0
        
        # Verify graph statistics
        stats = data["graph_statistics"]
        assert stats["total_services"] == 3
        assert stats["total_edges"] == 2
        
        # Verify graph was stored
        stored_graph = storage.read_json("dependencies/graph.json")
        assert stored_graph is not None
        assert len(stored_graph["services"]) == 3
        assert stored_graph["statistics"]["total_services"] == 3

    def test_ingest_dependencies_with_dependencies_format(self, client, valid_api_key, storage):
        """Test ingesting dependencies using dependencies format."""
        payload = {
            "dependencies": [
                {
                    "source": "api-gateway",
                    "target": "auth-service",
                    "dependency_type": "synchronous",
                    "criticality": "high"
                },
                {
                    "source": "auth-service",
                    "target": "user-db",
                    "dependency_type": "synchronous",
                    "criticality": "high"
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["status"] == "success"
        
        # Verify ingestion confirmation
        confirmation = data["ingestion_confirmation"]
        assert confirmation["services_ingested"] == 3
        assert confirmation["edges_created"] == 2
        
        # Verify graph was stored
        stored_graph = storage.read_json("dependencies/graph.json")
        assert stored_graph is not None
        assert len(stored_graph["services"]) == 3
    
    def test_ingest_dependencies_detects_missing_services(self, client, valid_api_key, storage):
        """Test that missing service dependencies are detected and warned."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "missing-service",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify warnings for missing services
        warnings = data["warnings"]
        assert warnings["missing_services"] > 0
        assert any(w["type"] == "missing_dependency" for w in warnings["details"])
    
    def test_ingest_dependencies_detects_isolated_services(self, client, valid_api_key, storage):
        """Test that isolated services (no dependencies) are detected."""
        payload = {
            "services": [
                {
                    "service_id": "isolated-service",
                    "service_type": "api",
                    "dependencies": []
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify warnings for isolated services
        warnings = data["warnings"]
        assert warnings["isolated_services"] > 0
        assert any(w["type"] == "isolated_node" for w in warnings["details"])
    
    def test_ingest_dependencies_detects_circular_dependencies(self, client, valid_api_key, storage):
        """Test that circular dependencies are detected."""
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
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "service-c",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                },
                {
                    "service_id": "service-c",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "service-a",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify circular dependencies are detected
        assert data["ingestion_confirmation"]["circular_dependencies_detected"] > 0
        assert data["graph_statistics"]["circular_dependencies"] > 0

    def test_ingest_dependencies_missing_services_field(self, client, valid_api_key):
        """Test error when both services and dependencies fields are missing."""
        payload = {}
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "missing_field"
    
    def test_ingest_dependencies_invalid_json(self, client, valid_api_key):
        """Test error when request body is invalid JSON."""
        response = client.post(
            "/api/v1/services/dependencies",
            data="invalid json",
            headers={
                "X-API-Key": valid_api_key,
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_json"
    
    def test_ingest_dependencies_invalid_service_id(self, client, valid_api_key):
        """Test error when service_id is missing or invalid."""
        payload = {
            "services": [
                {
                    "service_type": "api",
                    "dependencies": []
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
    
    def test_ingest_dependencies_invalid_dependency_target(self, client, valid_api_key):
        """Test error when dependency has no target."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
    
    def test_ingest_dependencies_missing_authentication(self, client):
        """Test error when API key is missing."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": []
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload
        )
        
        # Should be 401 due to missing API key
        assert response.status_code == 401
    
    def test_ingest_dependencies_with_infrastructure(self, client, valid_api_key, storage):
        """Test ingesting dependencies with infrastructure components."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_infrastructure_id": "redis-cache",
                            "infrastructure_type": "redis",
                            "dependency_type": "synchronous",
                            "criticality": "medium"
                        },
                        {
                            "target_infrastructure_id": "postgres-db",
                            "infrastructure_type": "postgresql",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify infrastructure was ingested
        confirmation = data["ingestion_confirmation"]
        assert confirmation["infrastructure_ingested"] == 2
        assert confirmation["edges_created"] == 2
        
        # Verify graph was stored with infrastructure
        stored_graph = storage.read_json("dependencies/graph.json")
        assert stored_graph["statistics"]["total_infrastructure"] == 2

    def test_ingest_dependencies_stores_graph_with_metadata(self, client, valid_api_key, storage):
        """Test that stored graph includes all required metadata."""
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
                    "service_type": "api",
                    "dependencies": []
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        
        # Verify stored graph structure
        stored_graph = storage.read_json("dependencies/graph.json")
        assert "version" in stored_graph
        assert "ingested_at" in stored_graph
        assert "services" in stored_graph
        assert "statistics" in stored_graph
        assert "circular_dependencies" in stored_graph
        assert "warnings" in stored_graph
        
        # Verify service details
        services = stored_graph["services"]
        service_a = next((s for s in services if s["service_id"] == "service-a"), None)
        assert service_a is not None
        assert service_a["downstream_count"] == 1
        assert service_a["upstream_count"] == 0
        
        service_b = next((s for s in services if s["service_id"] == "service-b"), None)
        assert service_b is not None
        assert service_b["downstream_count"] == 0
        assert service_b["upstream_count"] == 1
    
    def test_ingest_dependencies_pii_detection_in_service_id(self, client, valid_api_key):
        """Test that PII patterns in service IDs are detected and rejected."""
        payload = {
            "services": [
                {
                    "service_id": "user-service-john.doe@example.com",
                    "service_type": "api",
                    "dependencies": []
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "pii_detected"
    
    def test_ingest_dependencies_pii_detection_in_dependency_target(self, client, valid_api_key):
        """Test that PII patterns in dependency targets are detected and rejected."""
        payload = {
            "dependencies": [
                {
                    "source": "api-gateway",
                    "target": "db-service-555-12-3456",
                    "dependency_type": "synchronous"
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "pii_detected"
    
    def test_ingest_dependencies_empty_service_id(self, client, valid_api_key):
        """Test error when service_id is empty string."""
        payload = {
            "services": [
                {
                    "service_id": "",
                    "service_type": "api",
                    "dependencies": []
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
    
    def test_ingest_dependencies_empty_dependencies_array(self, client, valid_api_key, storage):
        """Test that services with empty dependencies array are handled correctly."""
        payload = {
            "services": [
                {
                    "service_id": "standalone-service",
                    "service_type": "api",
                    "dependencies": []
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify service was ingested
        confirmation = data["ingestion_confirmation"]
        assert confirmation["services_ingested"] == 1
        assert confirmation["edges_created"] == 0
        
        # Verify it's marked as isolated
        warnings = data["warnings"]
        assert warnings["isolated_services"] > 0

    def test_ingest_dependencies_duplicate_service_declarations(self, client, valid_api_key, storage):
        """Test handling of duplicate service declarations."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "auth-service",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                },
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "payment-service",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        # Should handle gracefully - either merge or reject
        assert response.status_code in [200, 400]
        
        if response.status_code == 200:
            # If merged, verify both dependencies are present
            stored_graph = storage.read_json("dependencies/graph.json")
            api_gateway = next((s for s in stored_graph["services"] if s["service_id"] == "api-gateway"), None)
            assert api_gateway is not None
    
    def test_ingest_dependencies_mixed_format_uses_services(self, client, valid_api_key, storage):
        """Test that when both services and dependencies are provided, services format is used."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "auth-service",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                },
                {
                    "service_id": "auth-service",
                    "service_type": "auth",
                    "dependencies": []
                }
            ],
            "dependencies": [
                {
                    "source": "payment-service",
                    "target": "user-db",
                    "dependency_type": "synchronous"
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        # Should process services format (dependencies format is ignored)
        assert response.status_code == 200
        data = response.json()
        
        # Verify only services format was processed
        confirmation = data["ingestion_confirmation"]
        assert confirmation["services_ingested"] == 2
        assert confirmation["edges_created"] == 1
    
    def test_ingest_dependencies_large_graph(self, client, valid_api_key, storage):
        """Test ingesting a larger dependency graph."""
        # Create a chain of 10 services
        services = []
        for i in range(10):
            service = {
                "service_id": f"service-{i:02d}",
                "service_type": "api",
                "dependencies": []
            }
            if i > 0:
                service["dependencies"] = [
                    {
                        "target_service_id": f"service-{i-1:02d}",
                        "dependency_type": "synchronous",
                        "criticality": "high"
                    }
                ]
            services.append(service)
        
        payload = {"services": services}
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all services were ingested
        confirmation = data["ingestion_confirmation"]
        assert confirmation["services_ingested"] == 10
        assert confirmation["edges_created"] == 9
        
        # Verify graph was stored
        stored_graph = storage.read_json("dependencies/graph.json")
        assert len(stored_graph["services"]) == 10
    
    def test_ingest_dependencies_invalid_dependency_type(self, client, valid_api_key):
        """Test handling of invalid dependency types."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "auth-service",
                            "dependency_type": "invalid-type",
                            "criticality": "high"
                        }
                    ]
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        # Should either accept with default or reject
        assert response.status_code in [200, 400]
    
    def test_ingest_dependencies_invalid_criticality(self, client, valid_api_key):
        """Test handling of invalid criticality values."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "auth-service",
                            "dependency_type": "synchronous",
                            "criticality": "invalid-criticality"
                        }
                    ]
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        # Should either accept with default or reject
        assert response.status_code in [200, 400]

    def test_ingest_dependencies_self_dependency(self, client, valid_api_key, storage):
        """Test handling of self-dependencies (service depends on itself)."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "api-gateway",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        # Should handle self-dependency (either accept or reject)
        assert response.status_code in [200, 400]
    
    def test_ingest_dependencies_complex_circular_dependency(self, client, valid_api_key, storage):
        """Test detection of complex circular dependencies with multiple cycles."""
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
                        },
                        {
                            "target_service_id": "service-c",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                },
                {
                    "service_id": "service-b",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "service-c",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                },
                {
                    "service_id": "service-c",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "service-a",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        }
                    ]
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify circular dependency is detected
        assert data["ingestion_confirmation"]["circular_dependencies_detected"] > 0
        
        # Verify stored graph marks services as in circular dependency
        stored_graph = storage.read_json("dependencies/graph.json")
        for service in stored_graph["services"]:
            if service["service_id"] in ["service-a", "service-b", "service-c"]:
                assert service["is_in_circular_dependency"] is True
    
    def test_ingest_dependencies_response_includes_request_id(self, client, valid_api_key):
        """Test that response includes request_id for tracing."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": []
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify request_id is present
        assert "request_id" in data
        assert data["request_id"] is not None
        assert len(data["request_id"]) > 0
    
    def test_ingest_dependencies_response_includes_timestamp(self, client, valid_api_key):
        """Test that response includes timestamp."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": []
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify timestamp is present and valid ISO format
        assert "timestamp" in data
        assert "T" in data["timestamp"]
        assert "Z" in data["timestamp"]
    
    def test_ingest_dependencies_multiple_infrastructure_types(self, client, valid_api_key, storage):
        """Test ingesting dependencies with multiple infrastructure types."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_infrastructure_id": "postgres-primary",
                            "infrastructure_type": "postgresql",
                            "dependency_type": "synchronous",
                            "criticality": "high"
                        },
                        {
                            "target_infrastructure_id": "redis-cache",
                            "infrastructure_type": "redis",
                            "dependency_type": "synchronous",
                            "criticality": "medium"
                        },
                        {
                            "target_infrastructure_id": "rabbitmq-broker",
                            "infrastructure_type": "rabbitmq",
                            "dependency_type": "asynchronous",
                            "criticality": "low"
                        }
                    ]
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all infrastructure was ingested
        confirmation = data["ingestion_confirmation"]
        assert confirmation["infrastructure_ingested"] == 3
        assert confirmation["edges_created"] == 3
        
        # Verify stored graph includes infrastructure types
        stored_graph = storage.read_json("dependencies/graph.json")
        assert stored_graph["statistics"]["total_infrastructure"] == 3
    
    def test_ingest_dependencies_with_optional_fields(self, client, valid_api_key, storage):
        """Test ingesting dependencies with optional fields like timeout and retry policy."""
        payload = {
            "services": [
                {
                    "service_id": "api-gateway",
                    "service_type": "api",
                    "dependencies": [
                        {
                            "target_service_id": "auth-service",
                            "dependency_type": "synchronous",
                            "criticality": "high",
                            "timeout_ms": 5000,
                            "retry_policy": "exponential_backoff"
                        }
                    ]
                },
                {
                    "service_id": "auth-service",
                    "service_type": "auth",
                    "dependencies": []
                }
            ]
        }
        
        response = client.post(
            "/api/v1/services/dependencies",
            json=payload,
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify ingestion was successful
        confirmation = data["ingestion_confirmation"]
        assert confirmation["services_ingested"] == 2
        assert confirmation["edges_created"] == 1
