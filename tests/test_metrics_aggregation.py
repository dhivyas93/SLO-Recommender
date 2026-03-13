"""
Unit tests for metrics aggregation functionality.
"""

import pytest
from datetime import datetime, timedelta
from src.engines.metrics_ingestion import MetricsIngestionEngine
from src.storage.file_storage import FileStorage
import tempfile
import shutil


@pytest.fixture
def temp_storage():
    """Create temporary storage for testing."""
    temp_dir = tempfile.mkdtemp()
    storage = FileStorage(base_path=temp_dir)
    yield storage
    shutil.rmtree(temp_dir)


@pytest.fixture
def engine(temp_storage):
    """Create MetricsIngestionEngine with temporary storage."""
    return MetricsIngestionEngine(storage=temp_storage)


@pytest.fixture
def sample_metrics_data(engine):
    """Create sample metrics data for testing."""
    service_id = "test-service"
    now = datetime.utcnow()
    
    # Create metrics for different time points
    metrics_data = []
    for i in range(10):
        # Add microseconds offset to ensure unique timestamps
        timestamp = now - timedelta(days=i, microseconds=i)
        result = engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={
                "p50_ms": 100 + i * 5,
                "p95_ms": 200 + i * 10,
                "p99_ms": 300 + i * 15,
                "mean_ms": 110 + i * 5,
                "stddev_ms": 20 + i
            },
            error_rate={
                "percent": 1.0 + i * 0.1,
                "total_requests": 10000,
                "failed_requests": int(100 + i * 10)
            },
            availability={
                "percent": 99.5 - i * 0.05,
                "uptime_seconds": 86000,
                "downtime_seconds": 400 + i * 10
            },
            timestamp=timestamp
        )
        metrics_data.append(result)
    
    return service_id, metrics_data


class TestTimeWindowAggregation:
    """Test time window aggregation logic."""
    
    def test_compute_aggregated_metrics_all_windows(self, engine, sample_metrics_data):
        """Test computing aggregated metrics for all time windows."""
        service_id, _ = sample_metrics_data
        
        # Compute aggregated metrics
        result = engine.compute_aggregated_metrics(service_id)
        
        # Verify structure
        assert result["service_id"] == service_id
        assert "computed_at" in result
        assert "time_windows" in result
        
        # Verify all time windows are present
        assert "1d" in result["time_windows"]
        assert "7d" in result["time_windows"]
        assert "30d" in result["time_windows"]
        assert "90d" in result["time_windows"]
    
    def test_compute_aggregated_metrics_single_window(self, engine, sample_metrics_data):
        """Test computing aggregated metrics for a single time window."""
        service_id, _ = sample_metrics_data
        
        # Compute only 7d window
        result = engine.compute_aggregated_metrics(service_id, time_windows=["7d"])
        
        # Verify only 7d window is present
        assert "7d" in result["time_windows"]
        assert "1d" not in result["time_windows"]
        assert "30d" not in result["time_windows"]
        assert "90d" not in result["time_windows"]
    
    def test_aggregated_latency_statistics(self, engine, sample_metrics_data):
        """Test latency statistics aggregation."""
        service_id, _ = sample_metrics_data
        
        result = engine.compute_aggregated_metrics(service_id, time_windows=["7d"])
        latency = result["time_windows"]["7d"]["latency"]
        
        # Verify all required fields are present
        assert "mean_ms" in latency
        assert "median_ms" in latency
        assert "stddev_ms" in latency
        assert "p50_ms" in latency
        assert "p95_ms" in latency
        assert "p99_ms" in latency
        assert "min_ms" in latency
        assert "max_ms" in latency
        assert "sample_count" in latency
        
        # Verify sample count is correct (7 days of data: day 0-6 inclusive)
        assert latency["sample_count"] == 7
        
        # Verify values are reasonable
        assert latency["mean_ms"] > 0
        assert latency["p95_ms"] >= latency["p50_ms"]
        assert latency["p99_ms"] >= latency["p95_ms"]
        assert latency["max_ms"] >= latency["min_ms"]
    
    def test_aggregated_error_rate_statistics(self, engine, sample_metrics_data):
        """Test error rate statistics aggregation."""
        service_id, _ = sample_metrics_data
        
        result = engine.compute_aggregated_metrics(service_id, time_windows=["7d"])
        error_rate = result["time_windows"]["7d"]["error_rate"]
        
        # Verify all required fields are present
        assert "mean_percent" in error_rate
        assert "median_percent" in error_rate
        assert "stddev_percent" in error_rate
        assert "p50_percent" in error_rate
        assert "p95_percent" in error_rate
        assert "p99_percent" in error_rate
        assert "min_percent" in error_rate
        assert "max_percent" in error_rate
        assert "total_requests" in error_rate
        assert "total_failed_requests" in error_rate
        assert "sample_count" in error_rate
        
        # Verify sample count (7 days of data: day 0-6 inclusive)
        assert error_rate["sample_count"] == 7
        
        # Verify values are in valid range
        assert 0 <= error_rate["mean_percent"] <= 100
        assert 0 <= error_rate["p95_percent"] <= 100
        assert error_rate["total_requests"] > 0
    
    def test_aggregated_availability_statistics(self, engine, sample_metrics_data):
        """Test availability statistics aggregation."""
        service_id, _ = sample_metrics_data
        
        result = engine.compute_aggregated_metrics(service_id, time_windows=["7d"])
        availability = result["time_windows"]["7d"]["availability"]
        
        # Verify all required fields are present
        assert "mean_percent" in availability
        assert "median_percent" in availability
        assert "stddev_percent" in availability
        assert "p50_percent" in availability
        assert "p95_percent" in availability
        assert "p99_percent" in availability
        assert "min_percent" in availability
        assert "max_percent" in availability
        assert "total_uptime_seconds" in availability
        assert "total_downtime_seconds" in availability
        assert "sample_count" in availability
        
        # Verify sample count (7 days of data: day 0-6 inclusive)
        assert availability["sample_count"] == 7
        
        # Verify values are in valid range
        assert 0 <= availability["mean_percent"] <= 100
        assert 0 <= availability["p95_percent"] <= 100
    
    def test_data_quality_indicators(self, engine, sample_metrics_data):
        """Test data quality indicators for time windows."""
        service_id, _ = sample_metrics_data
        
        result = engine.compute_aggregated_metrics(service_id, time_windows=["7d"])
        quality = result["time_windows"]["7d"]["data_quality"]
        
        # Verify all required fields are present
        assert "completeness" in quality
        assert "staleness_hours" in quality
        assert "expected_samples" in quality
        assert "actual_samples" in quality
        assert "quality_score" in quality
        
        # Verify values are in valid range
        assert 0 <= quality["completeness"] <= 1
        assert quality["staleness_hours"] >= 0
        assert quality["expected_samples"] == 7
        # We have 7 samples (day 0-6)
        assert quality["actual_samples"] == 7
        assert 0 <= quality["quality_score"] <= 1
    
    def test_incomplete_data_handling(self, engine):
        """Test handling of incomplete data with quality indicators."""
        service_id = "incomplete-service"
        now = datetime.utcnow()
        
        # Create only 3 data points for a 7-day window
        for i in range(3):
            # Add microseconds offset to ensure unique timestamps
            timestamp = now - timedelta(days=i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 100,
                    "p95_ms": 200,
                    "p99_ms": 300,
                    "mean_ms": 110,
                    "stddev_ms": 20
                },
                error_rate={
                    "percent": 1.0,
                    "total_requests": 10000,
                    "failed_requests": 100
                },
                availability={
                    "percent": 99.5,
                    "uptime_seconds": 86000,
                    "downtime_seconds": 400
                },
                timestamp=timestamp
            )
        
        # Compute aggregated metrics
        result = engine.compute_aggregated_metrics(service_id, time_windows=["7d"])
        quality = result["time_windows"]["7d"]["data_quality"]
        
        # Verify incomplete data is reflected in quality indicators
        assert quality["expected_samples"] == 7
        # We have 3 samples (day 0, 1, 2)
        assert quality["actual_samples"] == 3
        assert quality["completeness"] < 1.0
        assert quality["completeness"] == pytest.approx(3/7, rel=0.01)
    
    def test_empty_window_handling(self, engine):
        """Test handling of time windows with no data."""
        service_id = "empty-service"
        now = datetime.utcnow()
        
        # Create only 1 recent data point
        engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={
                "p50_ms": 100,
                "p95_ms": 200,
                "p99_ms": 300,
                "mean_ms": 110,
                "stddev_ms": 20
            },
            error_rate={
                "percent": 1.0,
                "total_requests": 10000,
                "failed_requests": 100
            },
            availability={
                "percent": 99.5,
                "uptime_seconds": 86000,
                "downtime_seconds": 400
            },
            timestamp=now
        )
        
        # Compute aggregated metrics for 90d window (should be empty)
        result = engine.compute_aggregated_metrics(service_id, time_windows=["90d"])
        window_data = result["time_windows"]["90d"]
        quality = window_data["data_quality"]
        
        # Verify empty window has appropriate quality indicators
        assert quality["actual_samples"] == 1
        assert quality["completeness"] < 1.0
    
    def test_storage_and_retrieval(self, engine, sample_metrics_data):
        """Test storing and retrieving aggregated metrics."""
        service_id, _ = sample_metrics_data
        
        # Compute and store aggregated metrics
        computed = engine.compute_aggregated_metrics(service_id)
        
        # Retrieve aggregated metrics
        retrieved = engine.get_aggregated_metrics(service_id)
        
        # Verify retrieved data matches computed data
        assert retrieved is not None
        assert retrieved["service_id"] == service_id
        assert "time_windows" in retrieved
        assert "1d" in retrieved["time_windows"]
        assert "7d" in retrieved["time_windows"]
        assert "30d" in retrieved["time_windows"]
        assert "90d" in retrieved["time_windows"]
    
    def test_invalid_time_window(self, engine, sample_metrics_data):
        """Test error handling for invalid time windows."""
        service_id, _ = sample_metrics_data
        
        # Try to compute with invalid time window
        with pytest.raises(ValueError, match="Invalid time_window"):
            engine.compute_aggregated_metrics(service_id, time_windows=["5d"])
    
    def test_no_metrics_error(self, engine):
        """Test error when service has no metrics."""
        service_id = "nonexistent-service"
        
        # Try to compute aggregated metrics for service with no data
        with pytest.raises(ValueError, match="No metrics found"):
            engine.compute_aggregated_metrics(service_id)
    
    def test_percentile_calculation(self, engine):
        """Test percentile calculation helper method."""
        values = [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
        
        # Test various percentiles (use pytest.approx for floating point comparison)
        assert engine._percentile(values, 50) == pytest.approx(55.0)  # Median
        assert engine._percentile(values, 95) == pytest.approx(95.5)
        assert engine._percentile(values, 99) == pytest.approx(99.1)
        assert engine._percentile(values, 0) == pytest.approx(10.0)
        assert engine._percentile(values, 100) == pytest.approx(100.0)
    
    def test_multiple_time_windows_different_data(self, engine):
        """Test that different time windows contain different amounts of data."""
        service_id = "multi-window-service"
        now = datetime.utcnow()
        
        # Create 10 days of data
        for i in range(10):
            # Add microseconds offset to ensure unique timestamps
            timestamp = now - timedelta(days=i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 100,
                    "p95_ms": 200,
                    "p99_ms": 300,
                    "mean_ms": 110,
                    "stddev_ms": 20
                },
                error_rate={
                    "percent": 1.0,
                    "total_requests": 10000,
                    "failed_requests": 100
                },
                availability={
                    "percent": 99.5,
                    "uptime_seconds": 86000,
                    "downtime_seconds": 400
                },
                timestamp=timestamp
            )
        
        # Compute aggregated metrics
        result = engine.compute_aggregated_metrics(service_id)
        
        # Verify different sample counts for different windows
        # 1d window: only day 0 (1 sample)
        assert result["time_windows"]["1d"]["latency"]["sample_count"] == 1
        # 7d window: days 0-6 (7 samples)
        assert result["time_windows"]["7d"]["latency"]["sample_count"] == 7
        # 30d window: all 10 days (10 samples)
        assert result["time_windows"]["30d"]["latency"]["sample_count"] == 10
        # 90d window: all 10 days (10 samples)
        assert result["time_windows"]["90d"]["latency"]["sample_count"] == 10


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
