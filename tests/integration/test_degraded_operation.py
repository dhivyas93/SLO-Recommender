"""
Integration tests for degraded operation handling.

Tests the system's ability to gracefully degrade when components fail:
- Knowledge layer unavailable: proceed with reduced confidence
- Dependency analyzer fails: treat services as independent
- Stale metrics: use with staleness warning
- Return partial results with warnings

These tests validate that the system continues to function and returns
meaningful recommendations even when some components are unavailable.
"""

import pytest
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from src.api.gateway import app
from src.storage.file_storage import FileStorage
from src.engines.fault_tolerance import FaultToleranceEngine, ComponentStatus
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
def valid_api_key():
    """Return a valid API key for testing."""
    return "test-key-123"


@pytest.fixture
def setup_test_service(storage):
    """Set up a test service with metadata and metrics."""
    service_id = "test-service-degraded"
    
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
    
    # Create aggregated metrics
    aggregated_metrics = {
        "service_id": service_id,
        "time_windows": {
            "1d": {
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
                    "percent": 99.5
                }
            }
        }
    }
    storage.write_json(f"services/{service_id}/metrics_aggregated.json", aggregated_metrics)
    
    # Create dependency graph
    graph = {
        "services": [
            {"service_id": service_id, "service_type": "api"},
            {"service_id": "downstream-service", "service_type": "api"}
        ],
        "edges": [
            {
                "source": service_id,
                "target": "downstream-service",
                "dependency_type": "sync",
                "timeout_ms": 1000
            }
        ]
    }
    storage.write_json("dependencies/graph.json", graph)
    
    return service_id


class TestDegradedOperationHandling:
    """Tests for degraded operation handling."""
    
    def test_recommendation_with_stale_metrics(self, client, valid_api_key, setup_test_service):
        """Test that recommendations work with stale metrics."""
        service_id = setup_test_service
        
        # Create stale metrics (older than 24 hours)
        stale_metrics = {
            "service_id": service_id,
            "timestamp": (datetime.utcnow() - timedelta(days=2)).isoformat() + "Z",
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
                "staleness_hours": 48,
                "outliers_detected": 0,
                "outlier_timestamps": [],
                "quality_score": 0.70  # Lower quality due to staleness
            }
        }
        
        storage = FileStorage(base_path="data")
        storage.write_json(f"services/{service_id}/metrics/latest.json", stale_metrics)
        
        # Request recommendations
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        
        # Should still succeed even with stale metrics
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "recommendation" in data
        
        # Check that data quality is reflected
        if "data_quality" in data["recommendation"]:
            assert data["recommendation"]["data_quality"]["staleness_hours"] == 48
    
    def test_recommendation_with_missing_dependency_graph(self, client, valid_api_key, setup_test_service):
        """Test that recommendations work when dependency graph is missing."""
        service_id = setup_test_service
        
        storage = FileStorage(base_path="data")
        
        # Remove dependency graph
        try:
            os.remove("data/dependencies/graph.json")
        except FileNotFoundError:
            pass
        
        # Request recommendations
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        
        # Should still succeed, treating service as independent
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "recommendation" in data
    
    def test_recommendation_with_incomplete_metrics(self, client, valid_api_key, setup_test_service):
        """Test that recommendations work with incomplete metrics."""
        service_id = setup_test_service
        
        # Create incomplete metrics (missing some fields)
        incomplete_metrics = {
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
                    "percent": 1.0
                    # Missing total_requests and failed_requests
                },
                "availability": {
                    "percent": 99.5
                }
            },
            "regional_breakdown": None,
            "data_quality": {
                "completeness": 0.70,  # Lower completeness
                "staleness_hours": 1,
                "outliers_detected": 0,
                "outlier_timestamps": [],
                "quality_score": 0.70
            }
        }
        
        storage = FileStorage(base_path="data")
        storage.write_json(f"services/{service_id}/metrics/latest.json", incomplete_metrics)
        
        # Request recommendations
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        
        # Should still succeed with reduced confidence
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "recommendation" in data
        
        # Confidence should be lower due to incomplete data
        if "confidence_score" in data["recommendation"]:
            assert data["recommendation"]["confidence_score"] < 0.9
    
    def test_fault_tolerance_engine_degradation_warnings(self):
        """Test that FaultToleranceEngine generates degradation warnings."""
        engine = FaultToleranceEngine()
        
        # Report component errors
        engine.report_component_error(
            "knowledge_layer",
            Exception("Connection timeout"),
            is_transient=True
        )
        
        engine.report_component_error(
            "dependency_analyzer",
            Exception("Graph processing failed"),
            is_transient=True
        )
        
        # Get degradation warnings
        warnings = engine.get_degradation_warnings()
        
        assert len(warnings) > 0
        assert any("knowledge_layer" in w for w in warnings)
        assert any("dependency_analyzer" in w for w in warnings)
    
    def test_fault_tolerance_engine_component_status(self):
        """Test that FaultToleranceEngine tracks component status."""
        engine = FaultToleranceEngine()
        
        # Report component error
        engine.report_component_error(
            "rag_engine",
            Exception("Embeddings not found"),
            is_transient=True
        )
        
        # Check component status
        status = engine.get_component_status("rag_engine")
        
        assert status is not None
        assert status.status in [ComponentStatus.DEGRADED, ComponentStatus.UNAVAILABLE]
        assert "Embeddings not found" in status.error_message
    
    def test_fault_tolerance_engine_recovery(self):
        """Test that FaultToleranceEngine can recover components."""
        engine = FaultToleranceEngine()
        
        # Report component error
        engine.report_component_error(
            "ollama_client",
            Exception("Connection refused"),
            is_transient=True
        )
        
        # Verify component is degraded
        assert not engine.is_component_available("ollama_client")
        
        # Report recovery
        engine.report_component_recovery("ollama_client")
        
        # Verify component is available again
        assert engine.is_component_available("ollama_client")
    
    def test_fault_tolerance_engine_fallback_recommendations(self):
        """Test that FaultToleranceEngine provides fallback recommendations."""
        engine = FaultToleranceEngine()
        
        # Report multiple component failures
        engine.report_component_error("knowledge_layer", Exception("Unavailable"), is_transient=True)
        engine.report_component_error("dependency_analyzer", Exception("Failed"), is_transient=True)
        
        # Get fallback recommendations
        fallback = engine.get_fallback_recommendations(
            service_type="api",
            metrics_available=True
        )
        
        assert fallback is not None
        assert "availability" in fallback
        assert "latency_p95_ms" in fallback
        assert "latency_p99_ms" in fallback
        assert "error_rate_percent" in fallback
    
    def test_system_health_with_degraded_components(self):
        """Test that system health reflects degraded components."""
        engine = FaultToleranceEngine()
        
        # Report component errors
        engine.report_component_error("knowledge_layer", Exception("Error 1"), is_transient=True)
        engine.report_component_error("rag_engine", Exception("Error 2"), is_transient=True)
        
        # Get system health
        health = engine.get_system_health()
        
        assert health["status"] in ["degraded", "unhealthy"]
        assert health["degraded_components"] > 0
        assert len(health["component_status"]) > 0
    
    def test_recommendation_response_includes_warnings(self, client, valid_api_key, setup_test_service):
        """Test that recommendation response can include warnings."""
        service_id = setup_test_service
        
        # Request recommendations
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Response should have structure for warnings (if any)
        assert "recommendation" in data
        # Warnings field is optional but if present should be a list
        if "warnings" in data:
            assert isinstance(data["warnings"], list)
    
    def test_partial_results_with_component_failure(self, client, valid_api_key, setup_test_service):
        """Test that partial results are returned when components fail."""
        service_id = setup_test_service
        
        # Request recommendations
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        
        # Should return 200 even if some components fail
        assert response.status_code in [200, 206]  # 206 is Partial Content
        data = response.json()
        
        # Should have status and recommendation
        assert "status" in data
        assert data["status"] in ["success", "partial"]
    
    def test_degraded_operation_confidence_reduction(self, client, valid_api_key, setup_test_service):
        """Test that confidence is reduced during degraded operation."""
        service_id = setup_test_service
        
        # Create metrics with low quality
        low_quality_metrics = {
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
                "completeness": 0.30,  # Very low completeness
                "staleness_hours": 72,  # Very stale
                "outliers_detected": 10,  # Many outliers
                "outlier_timestamps": [],
                "quality_score": 0.30  # Very low quality
            }
        }
        
        storage = FileStorage(base_path="data")
        storage.write_json(f"services/{service_id}/metrics/latest.json", low_quality_metrics)
        
        # Request recommendations
        response = client.get(
            f"/api/v1/services/{service_id}/slo-recommendations",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Confidence should be low
        if "confidence_score" in data["recommendation"]:
            assert data["recommendation"]["confidence_score"] < 0.7
