"""
Unit tests for MetricsIngestionEngine.

Tests metrics ingestion, validation, storage, and retrieval functionality.
"""

import pytest
import json
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

from src.engines.metrics_ingestion import MetricsIngestionEngine
from src.storage.file_storage import FileStorage
from src.models.metrics import MetricsData, LatencyMetrics, ErrorRateMetrics, AvailabilityMetrics


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory for testing."""
    temp_dir = tempfile.mkdtemp()
    storage = FileStorage(base_path=temp_dir)
    yield storage
    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def metrics_engine(temp_storage):
    """Create a MetricsIngestionEngine with temporary storage."""
    return MetricsIngestionEngine(storage=temp_storage)


@pytest.fixture
def sample_metrics_data():
    """Create sample metrics data for testing."""
    return {
        "service_id": "test-service",
        "time_window": "30d",
        "timestamp": datetime.utcnow(),
        "latency": {
            "p50_ms": 50.0,
            "p95_ms": 150.0,
            "p99_ms": 300.0,
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
            "uptime_seconds": 86313,  # ~99.9% of 24 hours
            "downtime_seconds": 87  # ~0.1% of 24 hours
        }
    }


class TestMetricsStorage:
    """Test metrics storage functionality."""
    
    def test_store_metrics_creates_timestamped_file(self, metrics_engine, temp_storage, sample_metrics_data):
        """Test that storing metrics creates a timestamped file."""
        # Ingest metrics
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Verify the timestamped file was created
        timestamp_str = sample_metrics_data["timestamp"].strftime("%Y%m%d_%H%M%S")
        metrics_path = Path(temp_storage.base_path) / "services" / "test-service" / "metrics" / f"{timestamp_str}.json"
        
        assert metrics_path.exists(), "Timestamped metrics file should be created"
        
        # Verify file contents
        with open(metrics_path, 'r') as f:
            stored_data = json.load(f)
        
        assert stored_data["service_id"] == "test-service"
        # Metrics are stored in a nested "metrics" dict
        assert stored_data["metrics"]["latency"]["p50_ms"] == 50.0
        assert stored_data["metrics"]["latency"]["p95_ms"] == 150.0
        assert stored_data["metrics"]["error_rate"]["percent"] == 0.5
        assert stored_data["metrics"]["availability"]["percent"] == 99.9
    
    def test_store_metrics_updates_latest_pointer(self, metrics_engine, temp_storage, sample_metrics_data):
        """Test that storing metrics updates the latest.json pointer."""
        # Ingest metrics
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Verify latest.json was created
        latest_path = Path(temp_storage.base_path) / "services" / "test-service" / "metrics" / "latest.json"
        
        assert latest_path.exists(), "latest.json should be created"
        
        # Verify latest.json contents match the stored metrics
        with open(latest_path, 'r') as f:
            latest_data = json.load(f)
        
        assert latest_data["service_id"] == "test-service"
        assert latest_data["metrics"]["latency"]["p50_ms"] == 50.0
    
    def test_store_multiple_metrics_maintains_history(self, metrics_engine, temp_storage, sample_metrics_data):
        """Test that storing multiple metrics maintains history."""
        # Ingest first metrics
        first_timestamp = datetime.utcnow()
        sample_metrics_data["timestamp"] = first_timestamp
        metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Ingest second metrics with different values
        second_timestamp = first_timestamp + timedelta(hours=1)
        sample_metrics_data["timestamp"] = second_timestamp
        sample_metrics_data["latency"]["p50_ms"] = 60.0
        metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Verify both files exist
        first_timestamp_str = first_timestamp.strftime("%Y%m%d_%H%M%S")
        second_timestamp_str = second_timestamp.strftime("%Y%m%d_%H%M%S")
        
        first_path = Path(temp_storage.base_path) / "services" / "test-service" / "metrics" / f"{first_timestamp_str}.json"
        second_path = Path(temp_storage.base_path) / "services" / "test-service" / "metrics" / f"{second_timestamp_str}.json"
        
        assert first_path.exists(), "First metrics file should exist"
        assert second_path.exists(), "Second metrics file should exist"
        
        # Verify latest.json points to the most recent
        latest_path = Path(temp_storage.base_path) / "services" / "test-service" / "metrics" / "latest.json"
        with open(latest_path, 'r') as f:
            latest_data = json.load(f)
        
        assert latest_data["metrics"]["latency"]["p50_ms"] == 60.0, "latest.json should contain most recent metrics"
    
    def test_store_metrics_creates_directory_structure(self, metrics_engine, temp_storage, sample_metrics_data):
        """Test that storing metrics creates the necessary directory structure."""
        # Ingest metrics
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Verify directory structure
        service_dir = Path(temp_storage.base_path) / "services" / "test-service"
        metrics_dir = service_dir / "metrics"
        
        assert service_dir.exists(), "Service directory should be created"
        assert metrics_dir.exists(), "Metrics directory should be created"
    
    def test_store_metrics_handles_datetime_serialization(self, metrics_engine, temp_storage, sample_metrics_data):
        """Test that datetime objects are properly serialized to ISO format."""
        # Ingest metrics
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Read the stored file
        timestamp_str = sample_metrics_data["timestamp"].strftime("%Y%m%d_%H%M%S")
        metrics_path = Path(temp_storage.base_path) / "services" / "test-service" / "metrics" / f"{timestamp_str}.json"
        
        with open(metrics_path, 'r') as f:
            stored_data = json.load(f)
        
        # Verify timestamp is in ISO format string
        assert isinstance(stored_data["timestamp"], str), "Timestamp should be serialized as string"
        assert "T" in stored_data["timestamp"], "Timestamp should be in ISO format"
        
        # Verify it can be parsed back
        from dateutil.parser import parse
        parsed_timestamp = parse(stored_data["timestamp"])
        assert isinstance(parsed_timestamp, datetime)
    
    def test_store_metrics_with_data_quality(self, metrics_engine, temp_storage, sample_metrics_data):
        """Test that data quality information is stored correctly."""
        # Ingest metrics
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Read the stored file
        timestamp_str = sample_metrics_data["timestamp"].strftime("%Y%m%d_%H%M%S")
        metrics_path = Path(temp_storage.base_path) / "services" / "test-service" / "metrics" / f"{timestamp_str}.json"
        
        with open(metrics_path, 'r') as f:
            stored_data = json.load(f)
        
        # Verify data quality is present
        assert "data_quality" in stored_data
        assert "completeness" in stored_data["data_quality"]
        assert "quality_score" in stored_data["data_quality"]
        assert stored_data["data_quality"]["completeness"] == 1.0
    
    def test_retrieve_stored_metrics(self, metrics_engine, temp_storage, sample_metrics_data):
        """Test that stored metrics can be retrieved."""
        # Ingest metrics
        metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Retrieve metrics
        retrieved = metrics_engine.get_latest_metrics("test-service")
        
        assert retrieved is not None
        assert retrieved.service_id == "test-service"
        assert retrieved.metrics["latency"].p50_ms == 50.0
        assert retrieved.metrics["latency"].p95_ms == 150.0
        assert retrieved.metrics["error_rate"].percent == 0.5
        assert retrieved.metrics["availability"].percent == 99.9
    
    def test_store_metrics_for_multiple_services(self, metrics_engine, temp_storage, sample_metrics_data):
        """Test that metrics for multiple services are stored separately."""
        # Ingest metrics for first service
        sample_metrics_data["service_id"] = "service-1"
        metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Ingest metrics for second service
        sample_metrics_data["service_id"] = "service-2"
        sample_metrics_data["latency"]["p50_ms"] = 100.0
        metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Verify both services have their own directories
        service1_dir = Path(temp_storage.base_path) / "services" / "service-1" / "metrics"
        service2_dir = Path(temp_storage.base_path) / "services" / "service-2" / "metrics"
        
        assert service1_dir.exists()
        assert service2_dir.exists()
        
        # Verify each service has correct data
        retrieved1 = metrics_engine.get_latest_metrics("service-1")
        retrieved2 = metrics_engine.get_latest_metrics("service-2")
        
        assert retrieved1.metrics["latency"].p50_ms == 50.0
        assert retrieved2.metrics["latency"].p50_ms == 100.0


class TestMetricsValidation:
    """Test metrics validation functionality."""
    
    def test_valid_metrics_accepted(self, metrics_engine, sample_metrics_data):
        """Test that valid metrics are accepted and stored correctly."""
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert result["service_id"] == "test-service"
        assert result["data_quality"]["completeness"] == 1.0
        assert result["validation_results"]["errors"] == []
    
    def test_latency_percentile_validation_p95_less_than_p50(self, metrics_engine, sample_metrics_data):
        """Test that p95 < p50 is rejected."""
        sample_metrics_data["latency"]["p95_ms"] = 40.0  # Less than p50 (50.0)
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0
        assert "p95_ms must be >= p50_ms" in result["validation_results"]["errors"][0]
    
    def test_latency_percentile_validation_p99_less_than_p95(self, metrics_engine, sample_metrics_data):
        """Test that p99 < p95 is rejected."""
        sample_metrics_data["latency"]["p99_ms"] = 100.0  # Less than p95 (150.0)
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0
        assert "p99_ms must be >= p95_ms" in result["validation_results"]["errors"][0]
    
    def test_latency_percentile_validation_valid_ordering(self, metrics_engine, sample_metrics_data):
        """Test that valid percentile ordering (p50 <= p95 <= p99) is accepted."""
        sample_metrics_data["latency"]["p50_ms"] = 50.0
        sample_metrics_data["latency"]["p95_ms"] = 150.0
        sample_metrics_data["latency"]["p99_ms"] = 300.0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert result["validation_results"]["errors"] == []
    
    def test_availability_range_validation_above_100(self, metrics_engine, sample_metrics_data):
        """Test that availability > 100% is rejected."""
        sample_metrics_data["availability"]["percent"] = 101.0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0
    
    def test_availability_range_validation_negative(self, metrics_engine, sample_metrics_data):
        """Test that negative availability is rejected."""
        sample_metrics_data["availability"]["percent"] = -1.0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0
    
    def test_availability_range_validation_valid_range(self, metrics_engine, sample_metrics_data):
        """Test that availability in valid range (0-100) is accepted."""
        for percent in [0.0, 50.0, 99.9, 100.0]:
            sample_metrics_data["availability"]["percent"] = percent
            result = metrics_engine.ingest_metrics(**sample_metrics_data)
            assert result["status"] == "ingested", f"Availability {percent}% should be accepted"
    
    def test_error_rate_range_validation_above_100(self, metrics_engine, sample_metrics_data):
        """Test that error rate > 100% is rejected."""
        sample_metrics_data["error_rate"]["percent"] = 101.0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0
    
    def test_error_rate_range_validation_negative(self, metrics_engine, sample_metrics_data):
        """Test that negative error rate is rejected."""
        sample_metrics_data["error_rate"]["percent"] = -1.0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0
    
    def test_error_rate_range_validation_valid_range(self, metrics_engine, sample_metrics_data):
        """Test that error rate in valid range (0-100) is accepted."""
        for percent in [0.0, 0.5, 10.0, 100.0]:
            sample_metrics_data["error_rate"]["percent"] = percent
            sample_metrics_data["error_rate"]["failed_requests"] = int(percent * 100)
            result = metrics_engine.ingest_metrics(**sample_metrics_data)
            assert result["status"] == "ingested", f"Error rate {percent}% should be accepted"
    
    def test_failed_requests_exceeds_total_requests(self, metrics_engine, sample_metrics_data):
        """Test that failed_requests > total_requests is rejected."""
        sample_metrics_data["error_rate"]["total_requests"] = 1000
        sample_metrics_data["error_rate"]["failed_requests"] = 1500
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0
        assert "failed_requests cannot exceed total_requests" in result["validation_results"]["errors"][0]
    
    def test_negative_latency_values(self, metrics_engine, sample_metrics_data):
        """Test that negative latency values are rejected."""
        sample_metrics_data["latency"]["p50_ms"] = -10.0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0
    
    def test_zero_latency_values(self, metrics_engine, sample_metrics_data):
        """Test that zero latency values are rejected (must be > 0)."""
        sample_metrics_data["latency"]["p50_ms"] = 0.0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0
    
    def test_invalid_time_window(self, metrics_engine, sample_metrics_data):
        """Test that invalid time window raises ValueError."""
        sample_metrics_data["time_window"] = "5d"  # Not in allowed list
        
        with pytest.raises(ValueError) as exc_info:
            metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert "Invalid time_window" in str(exc_info.value)
    
    def test_valid_time_windows(self, metrics_engine, sample_metrics_data):
        """Test that all valid time windows are accepted."""
        for time_window in ["1d", "7d", "30d", "90d"]:
            sample_metrics_data["time_window"] = time_window
            result = metrics_engine.ingest_metrics(**sample_metrics_data)
            assert result["status"] == "ingested", f"Time window {time_window} should be accepted"


class TestErrorRateConsistency:
    """Test error rate consistency validation."""
    
    def test_error_rate_consistency_valid(self, metrics_engine, sample_metrics_data):
        """Test that consistent error rate data passes validation."""
        sample_metrics_data["error_rate"]["percent"] = 5.0
        sample_metrics_data["error_rate"]["total_requests"] = 10000
        sample_metrics_data["error_rate"]["failed_requests"] = 500  # 5%
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert result["validation_results"]["errors"] == []
    
    def test_error_rate_consistency_warning(self, metrics_engine, sample_metrics_data):
        """Test that inconsistent error rate generates warning."""
        sample_metrics_data["error_rate"]["percent"] = 5.0
        sample_metrics_data["error_rate"]["total_requests"] = 10000
        sample_metrics_data["error_rate"]["failed_requests"] = 100  # Actually 1%, not 5%
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert len(result["validation_results"]["warnings"]) > 0
        assert any("Error rate inconsistency" in w for w in result["validation_results"]["warnings"])
    
    def test_error_rate_zero_total_requests_with_failures(self, metrics_engine, sample_metrics_data):
        """Test that failed_requests > 0 with total_requests = 0 is rejected."""
        sample_metrics_data["error_rate"]["percent"] = 0.0
        sample_metrics_data["error_rate"]["total_requests"] = 0
        sample_metrics_data["error_rate"]["failed_requests"] = 5
        
        # This should be rejected because failed_requests > total_requests
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "rejected"
        assert len(result["validation_results"]["errors"]) > 0
    
    def test_error_rate_zero_total_requests_with_percent(self, metrics_engine, sample_metrics_data):
        """Test warning when total_requests=0 but percent>0."""
        sample_metrics_data["error_rate"]["percent"] = 5.0
        sample_metrics_data["error_rate"]["total_requests"] = 0
        sample_metrics_data["error_rate"]["failed_requests"] = 0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert len(result["validation_results"]["warnings"]) > 0
        assert any("percent > 0 but total_requests = 0" in w for w in result["validation_results"]["warnings"])


class TestAvailabilityConsistency:
    """Test availability consistency validation."""
    
    def test_availability_consistency_valid(self, metrics_engine, sample_metrics_data):
        """Test that consistent availability data passes validation."""
        sample_metrics_data["availability"]["percent"] = 99.9
        sample_metrics_data["availability"]["uptime_seconds"] = 86313
        sample_metrics_data["availability"]["downtime_seconds"] = 87
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        # May have warnings but should not have errors
        assert result["validation_results"]["errors"] == []
    
    def test_availability_consistency_warning(self, metrics_engine, sample_metrics_data):
        """Test that inconsistent availability generates warning."""
        sample_metrics_data["availability"]["percent"] = 99.9
        sample_metrics_data["availability"]["uptime_seconds"] = 80000
        sample_metrics_data["availability"]["downtime_seconds"] = 6400  # Actually ~92.6%, not 99.9%
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert len(result["validation_results"]["warnings"]) > 0
        assert any("Availability inconsistency" in w for w in result["validation_results"]["warnings"])
    
    def test_availability_100_with_downtime(self, metrics_engine, sample_metrics_data):
        """Test warning when availability is 100% but downtime_seconds > 0."""
        sample_metrics_data["availability"]["percent"] = 100.0
        sample_metrics_data["availability"]["uptime_seconds"] = 86400
        sample_metrics_data["availability"]["downtime_seconds"] = 10
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert len(result["validation_results"]["warnings"]) > 0
        assert any("availability is 100% but downtime_seconds=" in w for w in result["validation_results"]["warnings"])
    
    def test_availability_zero_total_time(self, metrics_engine, sample_metrics_data):
        """Test warning when both uptime and downtime are zero."""
        sample_metrics_data["availability"]["percent"] = 50.0
        sample_metrics_data["availability"]["uptime_seconds"] = 0
        sample_metrics_data["availability"]["downtime_seconds"] = 0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert len(result["validation_results"]["warnings"]) > 0
        assert any("percent > 0 but both uptime_seconds and downtime_seconds = 0" in w for w in result["validation_results"]["warnings"])


class TestDataQualityAssessment:
    """Test data quality assessment computation."""
    
    def test_data_quality_completeness_all_fields(self, metrics_engine, sample_metrics_data):
        """Test completeness score when all required fields are present."""
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert result["data_quality"]["completeness"] == 1.0
    
    def test_data_quality_completeness_with_request_volume(self, metrics_engine, sample_metrics_data):
        """Test completeness score when optional request_volume is included."""
        sample_metrics_data["request_volume"] = {
            "requests_per_second": 100.0,
            "peak_rps": 200.0
        }
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert result["data_quality"]["completeness"] == 1.0
    
    def test_data_quality_high_error_rate_reduces_score(self, metrics_engine, sample_metrics_data):
        """Test that high error rate (>10%) reduces quality score."""
        sample_metrics_data["error_rate"]["percent"] = 15.0
        sample_metrics_data["error_rate"]["failed_requests"] = 1500
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        # Quality score should be reduced (< 1.0)
        assert result["data_quality"]["quality_score"] < 1.0
    
    def test_data_quality_low_availability_reduces_score(self, metrics_engine, sample_metrics_data):
        """Test that low availability (<90%) reduces quality score."""
        sample_metrics_data["availability"]["percent"] = 85.0
        sample_metrics_data["availability"]["uptime_seconds"] = 73440
        sample_metrics_data["availability"]["downtime_seconds"] = 12960
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        # Quality score should be reduced (< 1.0)
        assert result["data_quality"]["quality_score"] < 1.0
    
    def test_data_quality_both_issues_compound(self, metrics_engine, sample_metrics_data):
        """Test that both high error rate and low availability compound to reduce score further."""
        sample_metrics_data["error_rate"]["percent"] = 15.0
        sample_metrics_data["error_rate"]["failed_requests"] = 1500
        sample_metrics_data["availability"]["percent"] = 85.0
        sample_metrics_data["availability"]["uptime_seconds"] = 73440
        sample_metrics_data["availability"]["downtime_seconds"] = 12960
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        # Quality score should be significantly reduced
        assert result["data_quality"]["quality_score"] < 0.85


class TestMetricsQualityWarnings:
    """Test metrics quality warning generation."""
    
    def test_high_error_rate_warning(self, metrics_engine, sample_metrics_data):
        """Test warning for high error rate (>10%)."""
        sample_metrics_data["error_rate"]["percent"] = 12.0
        sample_metrics_data["error_rate"]["failed_requests"] = 1200
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert len(result["validation_results"]["warnings"]) > 0
        assert any("High error rate detected" in w for w in result["validation_results"]["warnings"])
    
    def test_low_availability_warning(self, metrics_engine, sample_metrics_data):
        """Test warning for low availability (<90%)."""
        sample_metrics_data["availability"]["percent"] = 88.0
        sample_metrics_data["availability"]["uptime_seconds"] = 76032
        sample_metrics_data["availability"]["downtime_seconds"] = 10368
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert len(result["validation_results"]["warnings"]) > 0
        assert any("Low availability detected" in w for w in result["validation_results"]["warnings"])
    
    def test_no_warnings_for_good_metrics(self, metrics_engine, sample_metrics_data):
        """Test that good metrics don't generate quality warnings."""
        # Use default sample_metrics_data which has good values
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        # Should not have quality warnings (may have other warnings)
        quality_warnings = [w for w in result["validation_results"]["warnings"] 
                          if "High error rate" in w or "Low availability" in w]
        assert len(quality_warnings) == 0


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_zero_error_rate(self, metrics_engine, sample_metrics_data):
        """Test handling of zero error rate."""
        sample_metrics_data["error_rate"]["percent"] = 0.0
        sample_metrics_data["error_rate"]["failed_requests"] = 0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert result["validation_results"]["errors"] == []
    
    def test_100_percent_error_rate(self, metrics_engine, sample_metrics_data):
        """Test handling of 100% error rate."""
        sample_metrics_data["error_rate"]["percent"] = 100.0
        sample_metrics_data["error_rate"]["total_requests"] = 1000
        sample_metrics_data["error_rate"]["failed_requests"] = 1000
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        # Should have quality warning
        assert any("High error rate" in w for w in result["validation_results"]["warnings"])
    
    def test_zero_availability(self, metrics_engine, sample_metrics_data):
        """Test handling of 0% availability."""
        sample_metrics_data["availability"]["percent"] = 0.0
        sample_metrics_data["availability"]["uptime_seconds"] = 0
        sample_metrics_data["availability"]["downtime_seconds"] = 86400
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        # Should have quality warning
        assert any("Low availability" in w for w in result["validation_results"]["warnings"])
    
    def test_100_percent_availability(self, metrics_engine, sample_metrics_data):
        """Test handling of 100% availability."""
        sample_metrics_data["availability"]["percent"] = 100.0
        sample_metrics_data["availability"]["uptime_seconds"] = 86400
        sample_metrics_data["availability"]["downtime_seconds"] = 0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert result["validation_results"]["errors"] == []
    
    def test_equal_percentiles(self, metrics_engine, sample_metrics_data):
        """Test handling of equal percentile values (p50 = p95 = p99)."""
        sample_metrics_data["latency"]["p50_ms"] = 100.0
        sample_metrics_data["latency"]["p95_ms"] = 100.0
        sample_metrics_data["latency"]["p99_ms"] = 100.0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert result["validation_results"]["errors"] == []
    
    def test_very_small_latency_values(self, metrics_engine, sample_metrics_data):
        """Test handling of very small latency values."""
        sample_metrics_data["latency"]["p50_ms"] = 0.001
        sample_metrics_data["latency"]["p95_ms"] = 0.002
        sample_metrics_data["latency"]["p99_ms"] = 0.003
        sample_metrics_data["latency"]["mean_ms"] = 0.0015
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert result["validation_results"]["errors"] == []
    
    def test_very_large_latency_values(self, metrics_engine, sample_metrics_data):
        """Test handling of very large latency values."""
        sample_metrics_data["latency"]["p50_ms"] = 10000.0
        sample_metrics_data["latency"]["p95_ms"] = 50000.0
        sample_metrics_data["latency"]["p99_ms"] = 100000.0
        sample_metrics_data["latency"]["mean_ms"] = 20000.0
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert result["validation_results"]["errors"] == []
    
    def test_missing_optional_fields(self, metrics_engine, sample_metrics_data):
        """Test that missing optional fields (request_volume, regional_breakdown) are handled."""
        # Remove optional fields if present
        sample_metrics_data.pop("request_volume", None)
        sample_metrics_data.pop("regional_breakdown", None)
        
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        
        assert result["status"] == "ingested"
        assert result["validation_results"]["errors"] == []
    
    def test_timestamp_defaults_to_now(self, metrics_engine, sample_metrics_data):
        """Test that timestamp defaults to current time if not provided."""
        sample_metrics_data.pop("timestamp", None)
        
        before = datetime.utcnow()
        result = metrics_engine.ingest_metrics(**sample_metrics_data)
        after = datetime.utcnow()
        
        assert result["status"] == "ingested"
        # Timestamp should be between before and after
        from dateutil.parser import parse
        result_timestamp = parse(result["timestamp"])
        assert before <= result_timestamp <= after


class TestMetricsRetrieval:
    """Test metrics retrieval functionality."""
    
    def test_get_latest_metrics_returns_most_recent(self, metrics_engine, sample_metrics_data):
        """Test that get_latest_metrics returns the most recent metrics."""
        # Ingest first metrics
        first_timestamp = datetime.utcnow()
        sample_metrics_data["timestamp"] = first_timestamp
        sample_metrics_data["latency"]["p50_ms"] = 50.0
        metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Ingest second metrics
        second_timestamp = first_timestamp + timedelta(hours=1)
        sample_metrics_data["timestamp"] = second_timestamp
        sample_metrics_data["latency"]["p50_ms"] = 60.0
        metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Get latest
        latest = metrics_engine.get_latest_metrics("test-service")
        
        assert latest is not None
        assert latest.metrics["latency"].p50_ms == 60.0
    
    def test_get_latest_metrics_nonexistent_service(self, metrics_engine):
        """Test that get_latest_metrics returns None for nonexistent service."""
        latest = metrics_engine.get_latest_metrics("nonexistent-service")
        
        assert latest is None
    
    def test_get_metrics_returns_all_metrics(self, metrics_engine, sample_metrics_data):
        """Test that get_metrics returns all stored metrics."""
        # Ingest multiple metrics
        for i in range(3):
            timestamp = datetime.utcnow() + timedelta(hours=i)
            sample_metrics_data["timestamp"] = timestamp
            sample_metrics_data["latency"]["p50_ms"] = 50.0 + i * 10
            metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Get all metrics
        all_metrics = metrics_engine.get_metrics("test-service")
        
        assert len(all_metrics) == 3
    
    def test_get_metrics_filter_by_time_window(self, metrics_engine, sample_metrics_data):
        """Test that get_metrics can filter by time window."""
        # Ingest metrics with different time windows
        sample_metrics_data["time_window"] = "1d"
        metrics_engine.ingest_metrics(**sample_metrics_data)
        
        sample_metrics_data["time_window"] = "7d"
        sample_metrics_data["timestamp"] = datetime.utcnow() + timedelta(hours=1)
        metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Get only 1d metrics
        metrics_1d = metrics_engine.get_metrics("test-service", time_window="1d")
        
        assert len(metrics_1d) == 1
        assert metrics_1d[0].time_window == "1d"
    
    def test_get_metrics_with_limit(self, metrics_engine, sample_metrics_data):
        """Test that get_metrics respects limit parameter."""
        # Ingest multiple metrics
        for i in range(5):
            timestamp = datetime.utcnow() + timedelta(hours=i)
            sample_metrics_data["timestamp"] = timestamp
            metrics_engine.ingest_metrics(**sample_metrics_data)
        
        # Get with limit
        limited_metrics = metrics_engine.get_metrics("test-service", limit=3)
        
        assert len(limited_metrics) == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
