"""
Integration tests for multi-tenant support.

Tests tenant isolation, tenant-specific standards, and multi-tenant API operations.
"""

import pytest
import json
from datetime import datetime
from fastapi.testclient import TestClient
from src.api.gateway import app
from src.storage.file_storage import FileStorage
from src.storage.tenant_storage import TenantStorageFactory
from src.engines.tenant_standards import TenantStandardsManager
import tempfile
import shutil
import os


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def storage():
    """Create a FileStorage instance for test data."""
    return FileStorage(base_path="data")


@pytest.fixture
def tenant_storage_factory():
    """Create a TenantStorageFactory."""
    return TenantStorageFactory(base_path="data")


@pytest.fixture
def tenant1_api_key():
    """Return API key for tenant 1."""
    return "tenant1-key-123"


@pytest.fixture
def tenant2_api_key():
    """Return API key for tenant 2."""
    return "tenant2-key-456"


@pytest.fixture
def setup_multi_tenant_services(tenant_storage_factory):
    """Set up services for multiple tenants."""
    tenants = ["tenant1", "tenant2"]
    services = {}
    
    for tenant_id in tenants:
        tenant_storage = tenant_storage_factory.get_tenant_storage(tenant_id)
        services[tenant_id] = []
        
        # Create 2 services per tenant
        for i in range(1, 3):
            service_id = f"{tenant_id}-service-{i}"
            services[tenant_id].append(service_id)
            
            # Create service metadata
            metadata = {
                "service_id": service_id,
                "version": "1.0.0",
                "service_type": "api",
                "team": f"{tenant_id}-team",
                "criticality": "high" if i == 1 else "medium",
                "infrastructure": {
                    "datastores": [],
                    "caches": [],
                    "message_queues": []
                }
            }
            tenant_storage.write_json(f"services/{service_id}/metadata.json", metadata)
            
            # Create service metrics
            metrics = {
                "service_id": service_id,
                "timestamp": "2024-01-15T10:30:00Z",
                "time_window": "1d",
                "metrics": {
                    "latency": {
                        "p50_ms": 100.0 + i * 10,
                        "p95_ms": 200.0 + i * 20,
                        "p99_ms": 300.0 + i * 30,
                        "mean_ms": 150.0 + i * 15,
                        "stddev_ms": 50.0
                    },
                    "error_rate": {
                        "percent": 1.0 + i * 0.5,
                        "total_requests": 10000,
                        "failed_requests": 100 + i * 50
                    },
                    "availability": {
                        "percent": 99.5 - i * 0.2,
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
            tenant_storage.write_json(f"services/{service_id}/metrics/latest.json", metrics)
            
            # Create aggregated metrics
            aggregated_metrics = {
                "service_id": service_id,
                "time_windows": {
                    "1d": {
                        "latency": {
                            "p50_ms": 100.0 + i * 10,
                            "p95_ms": 200.0 + i * 20,
                            "p99_ms": 300.0 + i * 30,
                            "mean_ms": 150.0 + i * 15,
                            "stddev_ms": 50.0
                        },
                        "error_rate": {
                            "percent": 1.0 + i * 0.5,
                            "total_requests": 10000,
                            "failed_requests": 100 + i * 50
                        },
                        "availability": {
                            "percent": 99.5 - i * 0.2
                        }
                    }
                }
            }
            tenant_storage.write_json(f"services/{service_id}/metrics_aggregated.json", aggregated_metrics)
        
        # Create dependency graph for tenant
        graph = {
            "services": [
                {"service_id": services[tenant_id][0], "service_type": "api"},
                {"service_id": services[tenant_id][1], "service_type": "api"}
            ],
            "edges": [
                {
                    "source": services[tenant_id][0],
                    "target": services[tenant_id][1],
                    "dependency_type": "sync",
                    "timeout_ms": 1000
                }
            ]
        }
        tenant_storage.write_json("dependencies/graph.json", graph)
    
    return services


class TestMultiTenantIsolation:
    """Tests for tenant isolation."""
    
    def test_tenant_storage_isolation(self, tenant_storage_factory):
        """Test that tenant storage is properly isolated."""
        tenant1_storage = tenant_storage_factory.get_tenant_storage("tenant1")
        tenant2_storage = tenant_storage_factory.get_tenant_storage("tenant2")
        
        # Write data to tenant1
        tenant1_storage.write_json("test/data.json", {"tenant": "tenant1", "value": 123})
        
        # Write different data to tenant2
        tenant2_storage.write_json("test/data.json", {"tenant": "tenant2", "value": 456})
        
        # Verify isolation
        tenant1_data = tenant1_storage.read_json("test/data.json")
        tenant2_data = tenant2_storage.read_json("test/data.json")
        
        assert tenant1_data["tenant"] == "tenant1"
        assert tenant1_data["value"] == 123
        
        assert tenant2_data["tenant"] == "tenant2"
        assert tenant2_data["value"] == 456
    
    def test_tenant_storage_factory_caching(self, tenant_storage_factory):
        """Test that TenantStorageFactory caches tenant storage instances."""
        storage1 = tenant_storage_factory.get_tenant_storage("tenant1")
        storage2 = tenant_storage_factory.get_tenant_storage("tenant1")
        
        # Should return the same instance
        assert storage1 is storage2
    
    def test_tenant_storage_factory_clear_cache(self, tenant_storage_factory):
        """Test that TenantStorageFactory can clear cache."""
        storage1 = tenant_storage_factory.get_tenant_storage("tenant1")
        tenant_storage_factory.clear_cache("tenant1")
        storage2 = tenant_storage_factory.get_tenant_storage("tenant1")
        
        # Should return different instances after cache clear
        assert storage1 is not storage2


class TestMultiTenantAPIEndpoints:
    """Tests for multi-tenant API endpoints."""
    
    def test_recommendation_endpoint_tenant_isolation(
        self, client, tenant1_api_key, tenant2_api_key, setup_multi_tenant_services
    ):
        """Test that recommendation endpoint respects tenant isolation."""
        services = setup_multi_tenant_services
        
        # Request recommendation for tenant1 service
        response1 = client.get(
            f"/api/v1/services/{services['tenant1'][0]}/slo-recommendations",
            headers={"X-API-Key": tenant1_api_key}
        )
        
        # Request recommendation for tenant2 service
        response2 = client.get(
            f"/api/v1/services/{services['tenant2'][0]}/slo-recommendations",
            headers={"X-API-Key": tenant2_api_key}
        )
        
        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        # Verify service IDs in responses
        data1 = response1.json()
        data2 = response2.json()
        
        assert data1["recommendation"]["service_id"] == services['tenant1'][0]
        assert data2["recommendation"]["service_id"] == services['tenant2'][0]
    
    def test_metrics_ingestion_tenant_isolation(
        self, client, tenant1_api_key, tenant2_api_key, setup_multi_tenant_services
    ):
        """Test that metrics ingestion respects tenant isolation."""
        services = setup_multi_tenant_services
        
        # Ingest metrics for tenant1
        metrics1 = {
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
        
        response1 = client.post(
            f"/api/v1/services/{services['tenant1'][0]}/metrics",
            json=metrics1,
            headers={"X-API-Key": tenant1_api_key}
        )
        
        # Ingest metrics for tenant2
        metrics2 = {
            "metrics": {
                "latency": {
                    "p50_ms": 150.0,
                    "p95_ms": 250.0,
                    "p99_ms": 350.0,
                    "mean_ms": 200.0,
                    "stddev_ms": 60.0
                },
                "error_rate": {
                    "percent": 2.0,
                    "total_requests": 20000,
                    "failed_requests": 400
                },
                "availability": {
                    "percent": 98.5,
                    "uptime_seconds": 85340,
                    "downtime_seconds": 1060
                }
            }
        }
        
        response2 = client.post(
            f"/api/v1/services/{services['tenant2'][0]}/metrics",
            json=metrics2,
            headers={"X-API-Key": tenant2_api_key}
        )
        
        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200
    
    def test_dependency_ingestion_tenant_isolation(
        self, client, tenant1_api_key, tenant2_api_key, setup_multi_tenant_services
    ):
        """Test that dependency ingestion respects tenant isolation."""
        services = setup_multi_tenant_services
        
        # Ingest dependencies for tenant1
        deps1 = {
            "services": [
                {"service_id": services['tenant1'][0], "service_type": "api"},
                {"service_id": services['tenant1'][1], "service_type": "api"}
            ],
            "dependencies": [
                {
                    "source_id": services['tenant1'][0],
                    "target_id": services['tenant1'][1],
                    "dependency_type": "sync",
                    "timeout_ms": 1000
                }
            ]
        }
        
        response1 = client.post(
            "/api/v1/services/dependencies",
            json=deps1,
            headers={"X-API-Key": tenant1_api_key}
        )
        
        # Ingest dependencies for tenant2
        deps2 = {
            "services": [
                {"service_id": services['tenant2'][0], "service_type": "api"},
                {"service_id": services['tenant2'][1], "service_type": "api"}
            ],
            "dependencies": [
                {
                    "source_id": services['tenant2'][0],
                    "target_id": services['tenant2'][1],
                    "dependency_type": "sync",
                    "timeout_ms": 2000
                }
            ]
        }
        
        response2 = client.post(
            "/api/v1/services/dependencies",
            json=deps2,
            headers={"X-API-Key": tenant2_api_key}
        )
        
        # Both should succeed
        assert response1.status_code == 200
        assert response2.status_code == 200


class TestTenantSpecificStandards:
    """Tests for tenant-specific standards."""
    
    def test_tenant_standards_manager_default_standards(self):
        """Test that TenantStandardsManager returns default standards."""
        manager = TenantStandardsManager()
        
        standards = manager.get_tenant_standards("unknown-tenant")
        
        assert "api_gateway" in standards
        assert "database" in standards
        assert "cache" in standards
    
    def test_tenant_standards_manager_service_type_standard(self):
        """Test getting specific service type standard."""
        manager = TenantStandardsManager()
        
        availability = manager.get_service_type_standard(
            "tenant1",
            "api_gateway",
            "availability"
        )
        
        assert availability == 99.99
    
    def test_tenant_standards_manager_criticality_adjustments(self):
        """Test criticality-based adjustments."""
        manager = TenantStandardsManager()
        
        # Get adjustments for critical service
        critical_adjustments = manager.get_criticality_adjustments("tenant1", "critical")
        
        assert critical_adjustments["availability_multiplier"] > 1.0
        assert critical_adjustments["latency_multiplier"] < 1.0
        assert critical_adjustments["error_rate_multiplier"] < 1.0
        
        # Get adjustments for low criticality service
        low_adjustments = manager.get_criticality_adjustments("tenant1", "low")
        
        assert low_adjustments["availability_multiplier"] < 1.0
        assert low_adjustments["latency_multiplier"] > 1.0
        assert low_adjustments["error_rate_multiplier"] > 1.0
    
    def test_tenant_standards_manager_apply_criticality_adjustment(self):
        """Test applying criticality adjustments to SLO."""
        manager = TenantStandardsManager()
        
        base_slo = {
            "availability": 99.0,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 500.0,
            "error_rate_percent": 1.0
        }
        
        # Apply critical adjustment
        critical_slo = manager.apply_criticality_adjustment(
            "tenant1",
            "critical",
            base_slo
        )
        
        # Availability should be higher (stricter)
        assert critical_slo["availability"] > base_slo["availability"]
        
        # Latency should be lower (faster)
        assert critical_slo["latency_p95_ms"] < base_slo["latency_p95_ms"]
        assert critical_slo["latency_p99_ms"] < base_slo["latency_p99_ms"]
        
        # Error rate should be lower
        assert critical_slo["error_rate_percent"] < base_slo["error_rate_percent"]
    
    def test_tenant_standards_manager_set_custom_standards(self, storage):
        """Test setting custom standards for a tenant."""
        manager = TenantStandardsManager(storage)
        
        custom_standards = {
            "api_gateway": {
                "availability": 99.5,
                "latency_p95_ms": 150,
                "latency_p99_ms": 400,
                "error_rate_percent": 0.5
            },
            "database": {
                "availability": 99.8,
                "latency_p95_ms": 75,
                "latency_p99_ms": 250,
                "error_rate_percent": 0.1
            }
        }
        
        # Set custom standards
        manager.set_tenant_standards("custom-tenant", custom_standards)
        
        # Retrieve and verify
        retrieved_standards = manager.get_tenant_standards("custom-tenant")
        
        assert retrieved_standards["api_gateway"]["availability"] == 99.5
        assert retrieved_standards["database"]["latency_p95_ms"] == 75
    
    def test_tenant_standards_validation(self):
        """Test that invalid standards are rejected."""
        manager = TenantStandardsManager()
        
        # Invalid: availability out of range
        invalid_standards = {
            "api_gateway": {
                "availability": 150.0  # Invalid: > 100
            }
        }
        
        with pytest.raises(ValueError):
            manager.set_tenant_standards("tenant1", invalid_standards)
        
        # Invalid: negative latency
        invalid_standards = {
            "api_gateway": {
                "latency_p95_ms": -100.0  # Invalid: negative
            }
        }
        
        with pytest.raises(ValueError):
            manager.set_tenant_standards("tenant1", invalid_standards)


class TestMultiTenantDataIsolation:
    """Tests for data isolation between tenants."""
    
    def test_tenant_data_not_accessible_across_tenants(self, tenant_storage_factory):
        """Test that tenant data is not accessible across tenants."""
        tenant1_storage = tenant_storage_factory.get_tenant_storage("tenant1")
        tenant2_storage = tenant_storage_factory.get_tenant_storage("tenant2")
        
        # Write data to tenant1
        tenant1_storage.write_json("services/service1/metadata.json", {
            "service_id": "service1",
            "tenant": "tenant1"
        })
        
        # Try to read from tenant2 (should fail or return empty)
        try:
            tenant2_data = tenant2_storage.read_json("services/service1/metadata.json")
            # If it doesn't fail, it should be empty or different
            assert tenant2_data.get("tenant") != "tenant1"
        except FileNotFoundError:
            # Expected: tenant2 cannot access tenant1's data
            pass
    
    def test_tenant_id_validation(self, tenant_storage_factory):
        """Test that invalid tenant IDs are rejected."""
        with pytest.raises(ValueError):
            tenant_storage_factory.get_tenant_storage("")
        
        with pytest.raises(ValueError):
            tenant_storage_factory.get_tenant_storage("   ")
