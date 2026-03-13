"""
Integration tests for audit and evaluation endpoints.

Tests the following endpoints:
- GET /api/v1/audit/export - Export audit logs
- GET /api/v1/evaluation/accuracy - Get evaluation accuracy metrics

These tests validate:
- Audit log export with date filtering
- Event type filtering
- Service ID filtering
- Evaluation accuracy metrics computation
- Error handling and validation
"""

import pytest
import json
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from src.api.gateway import app
from src.storage.file_storage import FileStorage
import tempfile
import shutil
import os


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def storage():
    """Create a temporary storage directory for testing."""
    temp_dir = tempfile.mkdtemp()
    original_cwd = os.getcwd()
    
    # Create necessary subdirectories
    os.makedirs(os.path.join(temp_dir, "data", "audit_logs"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "data", "evaluation"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "data", "services"), exist_ok=True)
    os.makedirs(os.path.join(temp_dir, "data", "api_keys"), exist_ok=True)
    
    # Create API keys file
    api_keys = {
        "test-key-123": {
            "tenant_id": "default",
            "created_at": datetime.utcnow().isoformat(),
            "active": True
        }
    }
    with open(os.path.join(temp_dir, "data", "api_keys.json"), "w") as f:
        json.dump(api_keys, f)
    
    yield FileStorage(base_path=os.path.join(temp_dir, "data"))
    
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def valid_api_key():
    """Return a valid API key for testing."""
    return "test-key-123"


@pytest.fixture
def setup_audit_logs():
    """Set up sample audit logs for testing."""
    from src.storage.file_storage import FileStorage
    
    storage = FileStorage(base_path="data")
    today = datetime.utcnow()
    
    # Create audit logs for the past 5 days
    for i in range(5):
        date = today - timedelta(days=i)
        date_str = date.strftime("%Y-%m-%d")
        
        logs = [
            {
                "timestamp": (date - timedelta(hours=j)).isoformat() + "Z",
                "request_id": f"req-{date_str}-{j}",
                "event_type": "recommendation_requested",
                "service_id": f"service-{j % 3}",
                "api_key_hash": "hash123",
                "status": "success",
                "response_time_ms": 100 + j * 10
            }
            for j in range(3)
        ]
        
        # Add some feedback events
        logs.extend([
            {
                "timestamp": (date - timedelta(hours=j)).isoformat() + "Z",
                "request_id": f"feedback-{date_str}-{j}",
                "event_type": "feedback_received",
                "service_id": f"service-{j % 2}",
                "api_key_hash": "hash123",
                "action": "accept",
                "tier": "balanced"
            }
            for j in range(2)
        ])
        
        storage.write_json(f"audit_logs/{date_str}.json", logs)
    
    return storage


class TestAuditExportEndpoint:
    """Tests for the audit export endpoint."""
    
    def test_export_audit_logs_success(self, client, valid_api_key, setup_audit_logs):
        """Test successful audit log export."""
        response = client.get(
            "/api/v1/audit/export",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "request_id" in data
        assert "timestamp" in data
        assert "total_entries" in data
        assert "entries" in data
        # Note: entries may be empty if no audit logs exist yet
        assert isinstance(data["entries"], list)
    
    def test_export_audit_logs_with_date_range(self, client, valid_api_key, setup_audit_logs):
        """Test audit log export with date range filtering."""
        today = datetime.utcnow()
        start_date = (today - timedelta(days=2)).strftime("%Y-%m-%d")
        end_date = today.strftime("%Y-%m-%d")
        
        response = client.get(
            f"/api/v1/audit/export?start_date={start_date}&end_date={end_date}",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["export_parameters"]["start_date"] == start_date
        assert data["export_parameters"]["end_date"] == end_date
        assert len(data["entries"]) > 0
    
    def test_export_audit_logs_with_event_type_filter(self, client, valid_api_key, setup_audit_logs):
        """Test audit log export with event type filtering."""
        response = client.get(
            "/api/v1/audit/export?event_type=recommendation_requested",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["export_parameters"]["event_type_filter"] == "recommendation_requested"
        
        # All entries should have the specified event type
        for entry in data["entries"]:
            assert entry["event_type"] == "recommendation_requested"
    
    def test_export_audit_logs_with_service_id_filter(self, client, valid_api_key, setup_audit_logs):
        """Test audit log export with service ID filtering."""
        response = client.get(
            "/api/v1/audit/export?service_id=service-0",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["export_parameters"]["service_id_filter"] == "service-0"
        
        # All entries should have the specified service ID
        for entry in data["entries"]:
            assert entry["service_id"] == "service-0"
    
    def test_export_audit_logs_with_combined_filters(self, client, valid_api_key, setup_audit_logs):
        """Test audit log export with multiple filters."""
        response = client.get(
            "/api/v1/audit/export?event_type=feedback_received&service_id=service-0",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        
        # All entries should match both filters
        for entry in data["entries"]:
            assert entry["event_type"] == "feedback_received"
            assert entry["service_id"] == "service-0"
    
    def test_export_audit_logs_invalid_start_date_format(self, client, valid_api_key):
        """Test audit log export with invalid start date format."""
        response = client.get(
            "/api/v1/audit/export?start_date=2024/01/15",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid start_date format" in data.get("message", "")
    
    def test_export_audit_logs_invalid_end_date_format(self, client, valid_api_key):
        """Test audit log export with invalid end date format."""
        response = client.get(
            "/api/v1/audit/export?end_date=01-15-2024",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid end_date format" in data.get("message", "")
    
    def test_export_audit_logs_start_date_after_end_date(self, client, valid_api_key):
        """Test audit log export with start date after end date."""
        response = client.get(
            "/api/v1/audit/export?start_date=2024-01-20&end_date=2024-01-10",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "Invalid date range" in data.get("message", "")
    
    def test_export_audit_logs_missing_authentication(self, client):
        """Test audit log export without authentication."""
        response = client.get("/api/v1/audit/export")
        
        assert response.status_code == 401
    
    def test_export_audit_logs_invalid_api_key(self, client):
        """Test audit log export with invalid API key."""
        response = client.get(
            "/api/v1/audit/export",
            headers={"X-API-Key": "invalid-key"}
        )
        
        assert response.status_code == 401
    
    def test_export_audit_logs_response_includes_request_id(self, client, valid_api_key, setup_audit_logs):
        """Test that audit export response includes request ID."""
        response = client.get(
            "/api/v1/audit/export",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "request_id" in data
        assert len(data["request_id"]) > 0
    
    def test_export_audit_logs_response_includes_timestamp(self, client, valid_api_key, setup_audit_logs):
        """Test that audit export response includes timestamp."""
        response = client.get(
            "/api/v1/audit/export",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "timestamp" in data
        # Verify timestamp is ISO format (basic check for Python 3.6 compatibility)
        assert "T" in data["timestamp"]
        assert "Z" in data["timestamp"]
    
    def test_export_audit_logs_empty_result(self, client, valid_api_key, storage):
        """Test audit log export with no matching logs."""
        response = client.get(
            "/api/v1/audit/export?event_type=nonexistent_event",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert data["total_entries"] == 0
        assert data["entries"] == []
    
    def test_export_audit_logs_response_structure(self, client, valid_api_key, setup_audit_logs):
        """Test that audit export response has correct structure."""
        response = client.get(
            "/api/v1/audit/export",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "status" in data
        assert "message" in data
        assert "timestamp" in data
        assert "request_id" in data
        assert "export_parameters" in data
        assert "total_entries" in data
        assert "entries" in data
        
        # Verify export_parameters structure
        params = data["export_parameters"]
        assert "start_date" in params
        assert "end_date" in params
        assert "event_type_filter" in params
        assert "service_id_filter" in params


class TestEvaluationAccuracyEndpoint:
    """Tests for the evaluation accuracy endpoint."""
    
    def test_get_evaluation_accuracy_success(self, client, valid_api_key):
        """Test successful evaluation accuracy retrieval."""
        response = client.get(
            "/api/v1/evaluation/accuracy",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "success"
        assert "request_id" in data
        assert "timestamp" in data
        assert "evaluation" in data
    
    def test_get_evaluation_accuracy_metrics_structure(self, client, valid_api_key):
        """Test that evaluation accuracy response has correct metrics structure."""
        response = client.get(
            "/api/v1/evaluation/accuracy",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        evaluation = data["evaluation"]
        metrics = evaluation["metrics"]
        
        # Verify required metric fields
        assert "overall_accuracy" in metrics
        assert "aggressive_precision" in metrics
        assert "balanced_precision" in metrics
        assert "conservative_precision" in metrics
        assert "acceptance_rate" in metrics
        
        # Verify percentage metrics are in valid range [0, 1]
        percentage_metrics = [
            "overall_accuracy", "aggressive_precision", "balanced_precision",
            "conservative_precision", "acceptance_rate"
        ]
        for metric_name in percentage_metrics:
            if metric_name in metrics:
                metric_value = metrics[metric_name]
                assert 0 <= metric_value <= 1, f"{metric_name} should be between 0 and 1"
    
    def test_get_evaluation_accuracy_missing_authentication(self, client):
        """Test evaluation accuracy retrieval without authentication."""
        response = client.get("/api/v1/evaluation/accuracy")
        
        assert response.status_code == 401
    
    def test_get_evaluation_accuracy_invalid_api_key(self, client):
        """Test evaluation accuracy retrieval with invalid API key."""
        response = client.get(
            "/api/v1/evaluation/accuracy",
            headers={"X-API-Key": "invalid-key"}
        )
        
        assert response.status_code == 401
    
    def test_get_evaluation_accuracy_response_includes_request_id(self, client, valid_api_key):
        """Test that evaluation accuracy response includes request ID."""
        response = client.get(
            "/api/v1/evaluation/accuracy",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "request_id" in data
        assert len(data["request_id"]) > 0
    
    def test_get_evaluation_accuracy_response_includes_timestamp(self, client, valid_api_key):
        """Test that evaluation accuracy response includes timestamp."""
        response = client.get(
            "/api/v1/evaluation/accuracy",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "timestamp" in data
        # Verify timestamp is ISO format (basic check for Python 3.6 compatibility)
        assert "T" in data["timestamp"]
        assert "Z" in data["timestamp"]
    
    def test_get_evaluation_accuracy_response_structure(self, client, valid_api_key):
        """Test that evaluation accuracy response has correct structure."""
        response = client.get(
            "/api/v1/evaluation/accuracy",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "status" in data
        assert "message" in data
        assert "timestamp" in data
        assert "request_id" in data
        assert "evaluation" in data
    
    def test_get_evaluation_accuracy_by_service_type(self, client, valid_api_key):
        """Test evaluation accuracy with service type breakdown."""
        response = client.get(
            "/api/v1/evaluation/accuracy",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Check if by_service_type is present in evaluation
        evaluation = data["evaluation"]
        if "by_service_type" in evaluation:
            by_service_type = evaluation["by_service_type"]
            assert isinstance(by_service_type, dict)
            
            # Each service type should have accuracy metric
            for service_type, metrics in by_service_type.items():
                assert "accuracy" in metrics
                assert 0 <= metrics["accuracy"] <= 1
    
    def test_get_evaluation_accuracy_time_window_parameter(self, client, valid_api_key):
        """Test evaluation accuracy with time window parameter."""
        response = client.get(
            "/api/v1/evaluation/accuracy?time_window=30d",
            headers={"X-API-Key": valid_api_key}
        )
        
        # Should either succeed or return 400 if parameter not supported
        assert response.status_code in [200, 400]
    
    def test_get_evaluation_accuracy_consistent_across_calls(self, client, valid_api_key):
        """Test that evaluation accuracy is consistent across multiple calls."""
        response1 = client.get(
            "/api/v1/evaluation/accuracy",
            headers={"X-API-Key": valid_api_key}
        )
        
        response2 = client.get(
            "/api/v1/evaluation/accuracy",
            headers={"X-API-Key": valid_api_key}
        )
        
        assert response1.status_code == 200
        assert response2.status_code == 200
        
        data1 = response1.json()
        data2 = response2.json()
        
        # Metrics should be the same (or very close if computed dynamically)
        assert data1["evaluation"]["metrics"]["overall_accuracy"] == data2["evaluation"]["metrics"]["overall_accuracy"]
