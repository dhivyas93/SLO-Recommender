"""
Integration tests for SLO acceptance endpoint.

Tests the POST /api/v1/services/{service_id}/slos endpoint for:
- Accepting recommendations
- Modifying recommendations with custom SLOs
- Rejecting recommendations
- Error handling (invalid action, missing fields, PII detection, service not found)
- Service metadata updates
- Feedback persistence
"""

import pytest
import json
from datetime import datetime
from pathlib import Path
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
def setup_test_service(storage):
    """Set up a test service with metadata and recommendations."""
    service_id = "test-payment-api"
    
    # Create service metadata
    metadata = {
        "service_id": service_id,
        "service_name": "Test Payment API",
        "service_type": "api",
        "team": "payments-team",
        "tenant_id": "test-tenant",
        "region": "us-east-1",
        "created_at": "2024-01-01T00:00:00Z",
        "updated_at": "2024-01-15T10:00:00Z",
        "infrastructure": {
            "datastores": [
                {
                    "type": "postgresql",
                    "name": "payments-db",
                    "availability_slo": 99.95,
                    "latency_p95_ms": 45
                }
            ]
        }
    }
    storage.write_json(f"services/{service_id}/metadata.json", metadata)
    
    # Create recommendations
    recommendations = {
        "service_id": service_id,
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
        "confidence_score": 0.85
    }
    storage.write_json(f"recommendations/{service_id}/latest.json", recommendations)
    
    yield service_id
    
    # Cleanup
    import shutil
    service_dir = Path("data") / "services" / service_id
    if service_dir.exists():
        shutil.rmtree(service_dir)
    
    rec_dir = Path("data") / "recommendations" / service_id
    if rec_dir.exists():
        shutil.rmtree(rec_dir)
    
    feedback_file = Path("data") / "feedback" / f"{service_id}.json"
    if feedback_file.exists():
        feedback_file.unlink()


class TestSLOAcceptanceEndpoint:
    """Test suite for SLO acceptance endpoint."""
    
    def test_accept_slo_with_balanced_tier(self, client, setup_test_service, storage):
        """Test accepting a recommendation with balanced tier."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice",
                "reason": "Looks good based on our traffic patterns"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert data["service_id"] == service_id
        assert data["action"] == "accept"
        assert "applied_slo" in data
        assert "request_id" in data
        assert "timestamp" in data
        
        # Verify applied SLO values
        applied_slo = data["applied_slo"]
        assert applied_slo["tier"] == "balanced"
        assert applied_slo["availability"] == 99.5
        assert applied_slo["latency_p95_ms"] == 200
        assert applied_slo["latency_p99_ms"] == 400
        assert applied_slo["error_rate_percent"] == 1.0
        
        # Verify service metadata was updated
        metadata = storage.read_json(f"services/{service_id}/metadata.json")
        assert metadata["current_slo"]["availability"] == 99.5
        assert metadata["current_slo_tier"] == "balanced"
        assert "current_slo_timestamp" in metadata
        
        # Verify feedback was persisted
        feedback_data = storage.read_json(f"feedback/{service_id}.json")
        assert isinstance(feedback_data, list)
        assert len(feedback_data) == 1
        assert feedback_data[0]["action"] == "accept"
        assert feedback_data[0]["service_owner"] == "alice"
        assert feedback_data[0]["tier_selected"] == "balanced"
    
    def test_accept_slo_with_aggressive_tier(self, client, setup_test_service, storage):
        """Test accepting a recommendation with aggressive tier."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "aggressive",
                "service_owner": "bob"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify applied SLO values for aggressive tier
        applied_slo = data["applied_slo"]
        assert applied_slo["tier"] == "aggressive"
        assert applied_slo["availability"] == 99.9
        assert applied_slo["latency_p95_ms"] == 150
    
    def test_accept_slo_with_conservative_tier(self, client, setup_test_service, storage):
        """Test accepting a recommendation with conservative tier."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "conservative",
                "service_owner": "charlie"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify applied SLO values for conservative tier
        applied_slo = data["applied_slo"]
        assert applied_slo["tier"] == "conservative"
        assert applied_slo["availability"] == 99.0
        assert applied_slo["latency_p95_ms"] == 300
    
    def test_modify_slo_with_custom_values(self, client, setup_test_service, storage):
        """Test modifying a recommendation with custom SLO values."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "modify",
                "selected_tier": "balanced",
                "custom_slos": {
                    "availability": 99.7,
                    "latency_p95_ms": 180
                },
                "service_owner": "dave",
                "reason": "We have better infrastructure than system assumed"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert data["action"] == "modify"
        assert "applied_slo" in data
        
        # Verify custom values were applied
        applied_slo = data["applied_slo"]
        assert applied_slo["availability"] == 99.7
        assert applied_slo["latency_p95_ms"] == 180
        # Non-custom values should use tier defaults
        assert applied_slo["latency_p99_ms"] == 400
        assert applied_slo["error_rate_percent"] == 1.0
        
        # Verify service metadata was updated
        metadata = storage.read_json(f"services/{service_id}/metadata.json")
        assert metadata["current_slo"]["availability"] == 99.7
        assert metadata["current_slo_tier"] == "balanced_modified"
        
        # Verify feedback includes custom SLOs
        feedback_data = storage.read_json(f"feedback/{service_id}.json")
        assert feedback_data[0]["action"] == "modify"
        assert feedback_data[0]["custom_slos"]["availability"] == 99.7
    
    def test_modify_slo_with_partial_custom_values(self, client, setup_test_service, storage):
        """Test modifying with only some custom values specified."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "modify",
                "selected_tier": "balanced",
                "custom_slos": {
                    "availability": 99.8
                },
                "service_owner": "eve"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify custom value is applied
        applied_slo = data["applied_slo"]
        assert applied_slo["availability"] == 99.8
        # Other values should use tier defaults
        assert applied_slo["latency_p95_ms"] == 200
        assert applied_slo["latency_p99_ms"] == 400
    
    def test_reject_slo(self, client, setup_test_service, storage):
        """Test rejecting a recommendation."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "reject",
                "service_owner": "frank",
                "reason": "We need more aggressive targets"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response
        assert data["action"] == "reject"
        assert "applied_slo" not in data
        
        # Verify service metadata was NOT updated
        metadata = storage.read_json(f"services/{service_id}/metadata.json")
        assert "current_slo" not in metadata
        
        # Verify feedback was persisted
        feedback_data = storage.read_json(f"feedback/{service_id}.json")
        assert feedback_data[0]["action"] == "reject"
        assert feedback_data[0]["reason"] == "We need more aggressive targets"
    
    def test_multiple_feedback_entries_persisted(self, client, setup_test_service, storage):
        """Test that multiple feedback entries are persisted in append-only fashion."""
        service_id = setup_test_service
        
        # First feedback
        response1 = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response1.status_code == 200
        
        # Second feedback
        response2 = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "reject",
                "service_owner": "bob",
                "reason": "Need to reconsider"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response2.status_code == 200
        
        # Verify both entries are persisted
        feedback_data = storage.read_json(f"feedback/{service_id}.json")
        assert len(feedback_data) == 2
        assert feedback_data[0]["action"] == "accept"
        assert feedback_data[1]["action"] == "reject"
    
    def test_invalid_action_returns_400(self, client, setup_test_service):
        """Test that invalid action returns 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "invalid_action",
                "selected_tier": "balanced",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
        assert "Invalid action" in data["message"]
    
    def test_missing_action_returns_400(self, client, setup_test_service):
        """Test that missing action field returns 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "selected_tier": "balanced",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "missing_field"
        assert "action" in data["message"]
    
    def test_missing_service_owner_returns_400(self, client, setup_test_service):
        """Test that missing service_owner field returns 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "missing_field"
        assert "service_owner" in data["message"]
    
    def test_missing_selected_tier_for_accept_returns_400(self, client, setup_test_service):
        """Test that missing selected_tier for accept action returns 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "missing_field"
        assert "selected_tier" in data["message"]
    
    def test_missing_selected_tier_for_modify_returns_400(self, client, setup_test_service):
        """Test that missing selected_tier for modify action returns 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "modify",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "missing_field"
        assert "selected_tier" in data["message"]
    
    def test_invalid_selected_tier_returns_400(self, client, setup_test_service):
        """Test that invalid selected_tier returns 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "invalid_tier",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
        assert "Invalid selected_tier" in data["message"]
    
    def test_service_not_found_returns_404(self, client):
        """Test that non-existent service returns 404 error."""
        response = client.post(
            "/api/v1/services/nonexistent-service/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 404
        data = response.json()
        assert data["error"] == "not_found"
        assert "nonexistent-service" in data["detail"]
    
    def test_pii_in_service_owner_returns_400(self, client, setup_test_service):
        """Test that PII in service_owner field returns 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice",
                "reason": "My SSN is 123-45-6789"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "pii_detected"
    
    def test_invalid_json_returns_400(self, client, setup_test_service):
        """Test that invalid JSON returns 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            data="invalid json {",
            headers={
                "X-API-Key": "test-api-key-001",
                "Content-Type": "application/json"
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "invalid_json"
    
    def test_response_includes_request_id(self, client, setup_test_service):
        """Test that response includes request_id for tracing."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "request_id" in data
        assert len(data["request_id"]) > 0
    
    def test_feedback_includes_timestamp(self, client, setup_test_service, storage):
        """Test that feedback includes ISO 8601 timestamp."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        
        # Verify feedback has timestamp
        feedback_data = storage.read_json(f"feedback/{service_id}.json")
        assert "timestamp" in feedback_data[0]
        # Verify it's ISO 8601 format
        timestamp = feedback_data[0]["timestamp"]
        assert "T" in timestamp
        assert "Z" in timestamp
    
    def test_feedback_includes_request_id(self, client, setup_test_service, storage):
        """Test that feedback includes request_id for tracing."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        response_data = response.json()
        
        # Verify feedback has same request_id
        feedback_data = storage.read_json(f"feedback/{service_id}.json")
        assert feedback_data[0]["request_id"] == response_data["request_id"]
    
    def test_empty_service_id_returns_400(self, client):
        """Test that empty service_id returns 400 error."""
        response = client.post(
            "/api/v1/services//slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        # FastAPI will handle this as a path issue, but we should still get an error
        assert response.status_code in [400, 404]
    
    def test_custom_slos_with_invalid_values_returns_400(self, client, setup_test_service):
        """Test that invalid custom SLO values return 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "modify",
                "selected_tier": "balanced",
                "custom_slos": {
                    "availability": 150  # Invalid: > 100
                },
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
    
    def test_custom_slos_with_negative_latency_returns_400(self, client, setup_test_service):
        """Test that negative latency values return 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "modify",
                "selected_tier": "balanced",
                "custom_slos": {
                    "latency_p95_ms": -100  # Invalid: negative
                },
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "validation_error"
    
    def test_service_metadata_updated_with_timestamp(self, client, setup_test_service, storage):
        """Test that service metadata is updated with current_slo_timestamp."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        
        # Verify metadata has timestamp
        metadata = storage.read_json(f"services/{service_id}/metadata.json")
        assert "current_slo_timestamp" in metadata
        # Verify it's ISO 8601 format
        timestamp = metadata["current_slo_timestamp"]
        assert "T" in timestamp
        assert "Z" in timestamp
    
    def test_feedback_audit_trail_maintains_order(self, client, setup_test_service, storage):
        """Test that feedback audit trail maintains chronological order."""
        service_id = setup_test_service
        
        # Submit multiple feedback entries
        for i in range(3):
            response = client.post(
                f"/api/v1/services/{service_id}/slos",
                json={
                    "action": "accept" if i % 2 == 0 else "reject",
                    "selected_tier": "balanced" if i % 2 == 0 else None,
                    "service_owner": f"owner_{i}"
                },
                headers={"X-API-Key": "test-api-key-001"}
            )
            assert response.status_code == 200
        
        # Verify feedback maintains order
        feedback_data = storage.read_json(f"feedback/{service_id}.json")
        assert len(feedback_data) == 3
        
        # Verify timestamps are in order
        for i in range(len(feedback_data) - 1):
            assert feedback_data[i]["timestamp"] <= feedback_data[i + 1]["timestamp"]
        
        # Verify service owners are in order
        for i in range(3):
            assert feedback_data[i]["service_owner"] == f"owner_{i}"
    
    def test_modify_without_custom_slos_uses_tier_defaults(self, client, setup_test_service, storage):
        """Test that modify action without custom_slos uses tier defaults."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "modify",
                "selected_tier": "aggressive",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify all values come from aggressive tier
        applied_slo = data["applied_slo"]
        assert applied_slo["availability"] == 99.9
        assert applied_slo["latency_p95_ms"] == 150
        assert applied_slo["latency_p99_ms"] == 300
        assert applied_slo["error_rate_percent"] == 0.5
    
    def test_accept_updates_metadata_tier_field(self, client, setup_test_service, storage):
        """Test that accept action updates current_slo_tier field correctly."""
        service_id = setup_test_service
        
        # Accept with aggressive tier
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "aggressive",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        
        # Verify metadata tier field
        metadata = storage.read_json(f"services/{service_id}/metadata.json")
        assert metadata["current_slo_tier"] == "aggressive"
    
    def test_modify_updates_metadata_tier_field_with_modified_suffix(self, client, setup_test_service, storage):
        """Test that modify action updates current_slo_tier with _modified suffix."""
        service_id = setup_test_service
        
        # Modify with custom values
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "modify",
                "selected_tier": "balanced",
                "custom_slos": {
                    "availability": 99.7
                },
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        
        # Verify metadata tier field has _modified suffix
        metadata = storage.read_json(f"services/{service_id}/metadata.json")
        assert metadata["current_slo_tier"] == "balanced_modified"
    
    def test_reject_does_not_update_metadata(self, client, setup_test_service, storage):
        """Test that reject action does not update service metadata."""
        service_id = setup_test_service
        
        # First accept to set metadata
        response1 = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response1.status_code == 200
        
        # Get metadata after accept
        metadata_after_accept = storage.read_json(f"services/{service_id}/metadata.json")
        
        # Now reject
        response2 = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "reject",
                "service_owner": "bob",
                "reason": "Need to reconsider"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        assert response2.status_code == 200
        
        # Verify metadata is unchanged
        metadata_after_reject = storage.read_json(f"services/{service_id}/metadata.json")
        assert metadata_after_reject["current_slo"] == metadata_after_accept["current_slo"]
        assert metadata_after_reject["current_slo_tier"] == metadata_after_accept["current_slo_tier"]
    
    def test_feedback_includes_all_required_fields(self, client, setup_test_service, storage):
        """Test that feedback entry includes all required audit fields."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice",
                "reason": "Looks good"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        
        # Verify feedback has all required fields
        feedback_data = storage.read_json(f"feedback/{service_id}.json")
        feedback_entry = feedback_data[0]
        
        required_fields = [
            "timestamp",
            "service_id",
            "action",
            "service_owner",
            "request_id"
        ]
        
        for field in required_fields:
            assert field in feedback_entry, f"Missing required field: {field}"
    
    def test_response_structure_validation(self, client, setup_test_service):
        """Test that response has correct structure for accept action."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        required_fields = [
            "service_id",
            "action",
            "timestamp",
            "request_id",
            "message",
            "applied_slo"
        ]
        
        for field in required_fields:
            assert field in data, f"Missing required response field: {field}"
        
        # Verify applied_slo structure
        applied_slo = data["applied_slo"]
        slo_fields = [
            "tier",
            "availability",
            "latency_p95_ms",
            "latency_p99_ms",
            "error_rate_percent"
        ]
        
        for field in slo_fields:
            assert field in applied_slo, f"Missing SLO field: {field}"
    
    def test_response_structure_for_reject_action(self, client, setup_test_service):
        """Test that response has correct structure for reject action."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "reject",
                "service_owner": "alice",
                "reason": "Need more time"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify response structure
        assert "service_id" in data
        assert "action" in data
        assert "timestamp" in data
        assert "request_id" in data
        assert "message" in data
        
        # Verify applied_slo is NOT in response for reject
        assert "applied_slo" not in data
    
    def test_pii_in_reason_field_returns_400(self, client, setup_test_service):
        """Test that PII in reason field returns 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice",
                "reason": "Contact me at alice@example.com or 555-123-4567"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "pii_detected"
    
    def test_pii_email_in_service_owner_returns_400(self, client, setup_test_service):
        """Test that email address in service_owner returns 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "accept",
                "selected_tier": "balanced",
                "service_owner": "alice@example.com"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "pii_detected"
    
    def test_pii_phone_number_in_reason_returns_400(self, client, setup_test_service):
        """Test that phone number in reason returns 400 error."""
        service_id = setup_test_service
        
        response = client.post(
            f"/api/v1/services/{service_id}/slos",
            json={
                "action": "reject",
                "service_owner": "alice",
                "reason": "Call me at 555-123-4567"
            },
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert data["error"] == "pii_detected"
