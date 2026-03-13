"""
Unit tests for regional metrics parsing functionality.

Tests for Task 11.1: Implement regional metrics parsing
"""

import pytest
from datetime import datetime
from src.engines.metrics_ingestion import MetricsIngestionEngine
from src.storage.file_storage import FileStorage


@pytest.fixture
def metrics_engine(tmp_path):
    """Create a MetricsIngestionEngine with temporary storage."""
    storage = FileStorage(base_path=str(tmp_path))
    return MetricsIngestionEngine(storage=storage)


@pytest.fixture
def base_metrics_data():
    """Base metrics data without regional breakdown."""
    return {
        "service_id": "test-service",
        "time_window": "1d",
        "latency": {
            "p50_ms": 50.0,
            "p95_ms": 100.0,
            "p99_ms": 150.0,
            "mean_ms": 60.0,
            "stddev_ms": 20.0
        },
        "error_rate": {
            "percent": 1.0,
            "total_requests": 10000,
            "failed_requests": 100
        },
        "availability": {
            "percent": 99.5,
            "uptime_seconds": 86100,
            "downtime_seconds": 300
        },
        "timestamp": datetime.utcnow()
    }


class TestRegionalMetricsParsing:
    """Test regional metrics parsing functionality."""

    def test_accept_regional_breakdown(self, metrics_engine, base_metrics_data):
        """Test that regional breakdown is accepted in metrics submission."""
        # Add regional breakdown
        base_metrics_data["regional_breakdown"] = {
            "us-east-1": {
                "latency_p95_ms": 95.0,
                "availability": 99.6
            },
            "us-west-2": {
                "latency_p95_ms": 105.0,
                "availability": 99.4
            },
            "eu-west-1": {
                "latency_p95_ms": 110.0,
                "availability": 99.3
            }
        }

        result = metrics_engine.ingest_metrics(**base_metrics_data)

        assert result["status"] == "ingested"
        assert result["validation_results"]["errors"] == []

    def test_parse_regional_metrics_data(self, metrics_engine, base_metrics_data):
        """Test that regional metrics data is parsed correctly."""
        # Add regional breakdown
        base_metrics_data["regional_breakdown"] = {
            "us-east-1": {
                "latency_p95_ms": 95.0,
                "availability": 99.6
            },
            "eu-west-1": {
                "latency_p95_ms": 110.0,
                "availability": 99.3
            }
        }

        result = metrics_engine.ingest_metrics(**base_metrics_data)

        # Retrieve the stored metrics
        latest = metrics_engine.get_latest_metrics("test-service")

        assert latest is not None
        assert latest.regional_breakdown is not None
        assert len(latest.regional_breakdown) == 2
        assert "us-east-1" in latest.regional_breakdown
        assert "eu-west-1" in latest.regional_breakdown

    def test_validate_regional_data_structure(self, metrics_engine, base_metrics_data):
        """Test that regional data structure is validated."""
        # Add regional breakdown with valid structure
        base_metrics_data["regional_breakdown"] = {
            "us-east-1": {
                "latency_p95_ms": 95.0,
                "availability": 99.6
            }
        }

        result = metrics_engine.ingest_metrics(**base_metrics_data)
        assert result["status"] == "ingested"

        # Retrieve and verify structure
        latest = metrics_engine.get_latest_metrics("test-service")
        regional = latest.regional_breakdown["us-east-1"]

        assert regional.latency_p95_ms == 95.0
        assert regional.availability == 99.6

    def test_regional_metrics_invalid_latency(self, metrics_engine, base_metrics_data):
        """Test that invalid regional latency is rejected."""
        # Add regional breakdown with invalid latency (negative)
        base_metrics_data["regional_breakdown"] = {
            "us-east-1": {
                "latency_p95_ms": -10.0,  # Invalid: must be > 0
                "availability": 99.6
            }
        }

        result = metrics_engine.ingest_metrics(**base_metrics_data)

        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0

    def test_regional_metrics_invalid_availability(self, metrics_engine, base_metrics_data):
        """Test that invalid regional availability is rejected."""
        # Add regional breakdown with invalid availability (> 100)
        base_metrics_data["regional_breakdown"] = {
            "us-east-1": {
                "latency_p95_ms": 95.0,
                "availability": 105.0  # Invalid: must be <= 100
            }
        }

        result = metrics_engine.ingest_metrics(**base_metrics_data)

        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0

    def test_regional_metrics_pii_validation(self, metrics_engine, base_metrics_data):
        """Test that regional data is validated for PII."""
        # Add regional breakdown with PII in region name
        base_metrics_data["regional_breakdown"] = {
            "john.doe@example.com": {  # PII: email address
                "latency_p95_ms": 95.0,
                "availability": 99.6
            }
        }

        result = metrics_engine.ingest_metrics(**base_metrics_data)

        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0
        assert "PII" in str(result["validation_results"]["errors"])

    def test_store_regional_metrics_with_service_metrics(self, metrics_engine, base_metrics_data):
        """Test that regional metrics are stored alongside service metrics."""
        # Add regional breakdown
        base_metrics_data["regional_breakdown"] = {
            "us-east-1": {
                "latency_p95_ms": 95.0,
                "availability": 99.6
            },
            "us-west-2": {
                "latency_p95_ms": 105.0,
                "availability": 99.4
            }
        }

        result = metrics_engine.ingest_metrics(**base_metrics_data)
        assert result["status"] == "ingested"

        # Retrieve the stored metrics
        latest = metrics_engine.get_latest_metrics("test-service")

        # Verify both service-level and regional metrics are present
        assert latest is not None
        assert latest.metrics is not None
        assert "latency" in latest.metrics
        assert latest.regional_breakdown is not None
        assert len(latest.regional_breakdown) == 2

    def test_regional_metrics_optional(self, metrics_engine, base_metrics_data):
        """Test that regional breakdown is optional."""
        # Don't include regional_breakdown
        result = metrics_engine.ingest_metrics(**base_metrics_data)

        assert result["status"] == "ingested"
        assert result["validation_results"]["errors"] == []

        # Retrieve and verify regional_breakdown is None
        latest = metrics_engine.get_latest_metrics("test-service")
        assert latest.regional_breakdown is None

    def test_multiple_regions(self, metrics_engine, base_metrics_data):
        """Test parsing multiple regions."""
        # Add regional breakdown with multiple regions
        base_metrics_data["regional_breakdown"] = {
            "us-east-1": {
                "latency_p95_ms": 95.0,
                "availability": 99.6
            },
            "us-west-2": {
                "latency_p95_ms": 105.0,
                "availability": 99.4
            },
            "eu-west-1": {
                "latency_p95_ms": 110.0,
                "availability": 99.3
            },
            "ap-southeast-1": {
                "latency_p95_ms": 120.0,
                "availability": 99.2
            }
        }

        result = metrics_engine.ingest_metrics(**base_metrics_data)

        assert result["status"] == "ingested"

        # Retrieve and verify all regions
        latest = metrics_engine.get_latest_metrics("test-service")
        assert len(latest.regional_breakdown) == 4
        assert all(region in latest.regional_breakdown for region in [
            "us-east-1", "us-west-2", "eu-west-1", "ap-southeast-1"
        ])

    def test_regional_metrics_missing_required_fields(self, metrics_engine, base_metrics_data):
        """Test that regional metrics with missing required fields are rejected."""
        # Add regional breakdown with missing availability
        base_metrics_data["regional_breakdown"] = {
            "us-east-1": {
                "latency_p95_ms": 95.0
                # Missing: availability
            }
        }

        result = metrics_engine.ingest_metrics(**base_metrics_data)

        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0

    def test_regional_metrics_boundary_values(self, metrics_engine, base_metrics_data):
        """Test regional metrics with boundary values."""
        # Add regional breakdown with boundary values
        base_metrics_data["regional_breakdown"] = {
            "us-east-1": {
                "latency_p95_ms": 0.1,  # Very small but valid
                "availability": 0.0  # Minimum valid value
            },
            "us-west-2": {
                "latency_p95_ms": 10000.0,  # Very large but valid
                "availability": 100.0  # Maximum valid value
            }
        }

        result = metrics_engine.ingest_metrics(**base_metrics_data)

        assert result["status"] == "ingested"

        # Retrieve and verify boundary values
        latest = metrics_engine.get_latest_metrics("test-service")
        assert latest.regional_breakdown["us-east-1"].latency_p95_ms == 0.1
        assert latest.regional_breakdown["us-east-1"].availability == 0.0
        assert latest.regional_breakdown["us-west-2"].latency_p95_ms == 10000.0
        assert latest.regional_breakdown["us-west-2"].availability == 100.0
