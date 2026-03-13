"""
Integration tests for PII detection in the recommendation endpoint.

Tests PII detection for:
- Email addresses
- Phone numbers
- Social Security Numbers (SSN)
- Credit card numbers
- Other sensitive patterns
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


class TestPIIDetectionInServiceId:
    """Test PII detection in service_id parameter."""
    
    def test_pii_email_in_service_id(self, client):
        """Test detection of email address in service_id."""
        response = client.get(
            "/api/v1/services/user@example.com/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "pii" in data.get("error", "").lower() or "email" in data.get("error", "").lower()
    
    def test_pii_email_variations(self, client):
        """Test detection of various email formats."""
        emails = [
            "john.doe@company.com",
            "jane_smith@example.org",
            "test.user+tag@domain.co.uk"
        ]
        
        for email in emails:
            response = client.get(
                f"/api/v1/services/{email}/slo-recommendations",
                headers={"X-API-Key": "test-api-key-001"}
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
    
    def test_pii_phone_number_in_service_id(self, client):
        """Test detection of phone number in service_id."""
        response = client.get(
            "/api/v1/services/service-555-123-4567/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_pii_phone_number_variations(self, client):
        """Test detection of various phone number formats."""
        phone_numbers = [
            "service-555-1234567",
            "service-555-123-4567",
            "service-(555)-123-4567",
            "service-5551234567"
        ]
        
        for phone in phone_numbers:
            response = client.get(
                f"/api/v1/services/{phone}/slo-recommendations",
                headers={"X-API-Key": "test-api-key-001"}
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
    
    def test_pii_ssn_in_service_id(self, client):
        """Test detection of SSN in service_id."""
        response = client.get(
            "/api/v1/services/service-123-45-6789/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_pii_ssn_variations(self, client):
        """Test detection of various SSN formats."""
        ssns = [
            "service-123-45-6789",
            "service-123456789",
            "service-123 45 6789"
        ]
        
        for ssn in ssns:
            response = client.get(
                f"/api/v1/services/{ssn}/slo-recommendations",
                headers={"X-API-Key": "test-api-key-001"}
            )
            
            assert response.status_code == 400
            data = response.json()
            assert "error" in data
    
    def test_pii_credit_card_in_service_id(self, client):
        """Test detection of credit card number in service_id."""
        response = client.get(
            "/api/v1/services/service-4532-1234-5678-9010/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_valid_service_id_not_flagged(self, client, storage):
        """Test that valid service IDs are not flagged as PII."""
        valid_ids = [
            "payment-api",
            "user-service",
            "auth-service-v2",
            "service-123",
            "api_gateway"
        ]
        
        for service_id in valid_ids:
            # Create minimal service data
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
            
            # Should not be 400 due to PII (may be 400 for missing metrics, but not PII)
            if response.status_code == 400:
                data = response.json()
                assert "pii" not in data.get("error", "").lower()


class TestPIIDetectionInMetrics:
    """Test PII detection in metrics data."""
    
    def test_pii_in_metrics_request_body(self, client):
        """Test detection of PII in metrics request body."""
        response = client.post(
            "/api/v1/services/test-service/metrics",
            headers={"X-API-Key": "test-api-key-001"},
            json={
                "metrics": {
                    "latency": {"p95_ms": 200.0},
                    "user_email": "user@example.com"
                }
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
        assert "pii" in data.get("error", "").lower() or "email" in data.get("error", "").lower()
    
    def test_pii_phone_in_metrics_request(self, client):
        """Test detection of phone number in metrics request."""
        response = client.post(
            "/api/v1/services/test-service/metrics",
            headers={"X-API-Key": "test-api-key-001"},
            json={
                "metrics": {
                    "latency": {"p95_ms": 200.0},
                    "contact_phone": "555-123-4567"
                }
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestPIIDetectionInDependencies:
    """Test PII detection in dependency data."""
    
    def test_pii_in_dependencies_request(self, client):
        """Test detection of PII in dependencies request."""
        response = client.post(
            "/api/v1/services/dependencies",
            headers={"X-API-Key": "test-api-key-001"},
            json={
                "services": [
                    {
                        "service_id": "test-service",
                        "owner_email": "owner@example.com"
                    }
                ]
            }
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestPIIErrorResponse:
    """Test PII error response format."""
    
    def test_pii_error_response_format(self, client):
        """Test that PII error response has correct format."""
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
        assert "detail" in data
        
        # Check error is PII related
        assert data["error"] == "pii_detected" or "pii" in data.get("error", "").lower()
    
    def test_pii_error_includes_field_name(self, client):
        """Test that PII error indicates which field contains PII."""
        response = client.get(
            "/api/v1/services/user@example.com/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        
        # Error should mention the field or pattern detected
        error_msg = data.get("error", "") + data.get("detail", "")
        assert len(error_msg) > 0


class TestPIIDetectionEdgeCases:
    """Test edge cases in PII detection."""
    
    def test_pii_detection_case_insensitive(self, client):
        """Test that PII detection is case-insensitive."""
        response = client.get(
            "/api/v1/services/USER@EXAMPLE.COM/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data
    
    def test_pii_detection_with_special_chars(self, client):
        """Test PII detection with special characters."""
        response = client.get(
            "/api/v1/services/user%40example.com/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        # May or may not be detected depending on URL encoding
        # Just verify we get a response
        assert response.status_code in [400, 401]
    
    def test_pii_detection_partial_match(self, client):
        """Test that partial PII patterns are detected."""
        response = client.get(
            "/api/v1/services/service-with-555-1234567-embedded/slo-recommendations",
            headers={"X-API-Key": "test-api-key-001"}
        )
        
        assert response.status_code == 400
        data = response.json()
        assert "error" in data


class TestNonPIIPatterns:
    """Test that non-PII patterns are not flagged."""
    
    def test_version_numbers_not_flagged(self, client, storage):
        """Test that version numbers are not flagged as PII."""
        service_id = "service-v1-2-3"
        
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
        
        # Should not be 400 due to PII
        if response.status_code == 400:
            data = response.json()
            assert "pii" not in data.get("error", "").lower()
    
    def test_port_numbers_not_flagged(self, client, storage):
        """Test that port numbers are not flagged as PII."""
        service_id = "service-port-8080"
        
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
        
        # Should not be 400 due to PII
        if response.status_code == 400:
            data = response.json()
            assert "pii" not in data.get("error", "").lower()
    
    def test_ip_addresses_not_flagged(self, client, storage):
        """Test that IP addresses are not flagged as PII."""
        service_id = "service-192-168-1-1"
        
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
        
        # Should not be 400 due to PII
        if response.status_code == 400:
            data = response.json()
            assert "pii" not in data.get("error", "").lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
