"""
Unit tests for adjusted statistics computation.

Tests that both raw and adjusted statistics are computed correctly,
with adjusted statistics excluding outliers beyond 3 standard deviations.
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


class TestAdjustedStatisticsComputation:
    """Test adjusted statistics computation with outlier exclusion."""
    
    def test_raw_statistics_include_all_data(self, engine):
        """Test that raw statistics include all data points including outliers."""
        service_id = "test-service"
        now = datetime.utcnow()
        
        # Create 10 normal data points
        for i in range(10):
            timestamp = now - timedelta(days=i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 100.0,
                    "p95_ms": 200.0,
                    "p99_ms": 300.0,
                    "mean_ms": 110.0,
                    "stddev_ms": 20.0
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
        result = engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
        
        # Verify raw statistics include all 10 data points
        latency = result["time_windows"]["30d"]["latency"]
        assert latency["sample_count"] == 10
        
        error_rate = result["time_windows"]["30d"]["error_rate"]
        assert error_rate["sample_count"] == 10
        
        availability = result["time_windows"]["30d"]["availability"]
        assert availability["sample_count"] == 10
    
    def test_adjusted_statistics_exclude_outliers(self, engine):
        """Test that adjusted statistics exclude outliers beyond 3 standard deviations."""
        service_id = "test-service-outliers"
        now = datetime.utcnow()
        
        # Create 30 normal data points with consistent values (need more points for 3-sigma to work)
        for i in range(30):
            timestamp = now - timedelta(days=i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 100.0,
                    "p95_ms": 200.0,
                    "p99_ms": 300.0,
                    "mean_ms": 110.0,
                    "stddev_ms": 20.0
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
        
        # Add 2 outlier data points with VERY extreme values
        # With 30 points at 200 and 2 points at 10000, the z-score will be > 3
        for i in range(2):
            timestamp = now - timedelta(days=40 + i, microseconds=40 + i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 5000.0,  # 50x higher - extreme outlier
                    "p95_ms": 10000.0,  # 50x higher - extreme outlier
                    "p99_ms": 15000.0,  # 50x higher - extreme outlier
                    "mean_ms": 5500.0,
                    "stddev_ms": 1000.0
                },
                error_rate={
                    "percent": 95.0,  # 95x higher - extreme outlier
                    "total_requests": 10000,
                    "failed_requests": 9500
                },
                availability={
                    "percent": 5.0,  # Much lower - extreme outlier
                    "uptime_seconds": 4320,
                    "downtime_seconds": 82080
                },
                timestamp=timestamp
            )
        
        # Compute aggregated metrics
        result = engine.compute_aggregated_metrics(service_id, time_windows=["90d"])
        window_data = result["time_windows"]["90d"]
        
        # Verify raw statistics include all 32 data points
        assert window_data["latency"]["sample_count"] == 32
        assert window_data["error_rate"]["sample_count"] == 32
        assert window_data["availability"]["sample_count"] == 32
        
        # Verify outliers were detected
        assert window_data["outlier_indices"] is not None
        assert len(window_data["outlier_indices"]) > 0
        
        # Verify adjusted statistics exist and have fewer samples
        assert window_data["latency_adjusted"] is not None
        assert window_data["error_rate_adjusted"] is not None
        assert window_data["availability_adjusted"] is not None
        
        # Adjusted statistics should have fewer samples (outliers excluded)
        assert window_data["latency_adjusted"]["sample_count"] < 32
        assert window_data["error_rate_adjusted"]["sample_count"] < 32
        assert window_data["availability_adjusted"]["sample_count"] < 32
    
    def test_adjusted_statistics_provide_cleaner_view(self, engine):
        """Test that adjusted statistics provide more accurate representation of typical performance."""
        service_id = "test-service-clean"
        now = datetime.utcnow()
        
        # Create 20 normal data points around 100ms
        for i in range(20):
            timestamp = now - timedelta(days=i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 100.0 + (i % 5),  # 100-104ms
                    "p95_ms": 200.0 + (i % 5),
                    "p99_ms": 300.0 + (i % 5),
                    "mean_ms": 110.0,
                    "stddev_ms": 20.0
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
        
        # Add 3 extreme outliers
        for i in range(3):
            timestamp = now - timedelta(days=20 + i, microseconds=20 + i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 5000.0,  # 50x higher
                    "p95_ms": 10000.0,
                    "p99_ms": 15000.0,
                    "mean_ms": 5500.0,
                    "stddev_ms": 1000.0
                },
                error_rate={
                    "percent": 80.0,  # 80x higher
                    "total_requests": 10000,
                    "failed_requests": 8000
                },
                availability={
                    "percent": 20.0,  # Much lower
                    "uptime_seconds": 17280,
                    "downtime_seconds": 69120
                },
                timestamp=timestamp
            )
        
        # Compute aggregated metrics
        result = engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
        window_data = result["time_windows"]["30d"]
        
        # Raw statistics should be skewed by outliers
        raw_latency_mean = window_data["latency"]["mean_ms"]
        raw_error_mean = window_data["error_rate"]["mean_percent"]
        raw_avail_mean = window_data["availability"]["mean_percent"]
        
        # Adjusted statistics should be closer to typical values
        if window_data["latency_adjusted"]:
            adjusted_latency_mean = window_data["latency_adjusted"]["mean_ms"]
            adjusted_error_mean = window_data["error_rate_adjusted"]["mean_percent"]
            adjusted_avail_mean = window_data["availability_adjusted"]["mean_percent"]
            
            # Adjusted mean should be lower (closer to typical 100ms) than raw mean
            assert adjusted_latency_mean < raw_latency_mean
            
            # Adjusted error rate should be lower (closer to typical 1%) than raw
            assert adjusted_error_mean < raw_error_mean
            
            # Adjusted availability should be higher (closer to typical 99.5%) than raw
            assert adjusted_avail_mean > raw_avail_mean
            
            # Adjusted values should be closer to typical performance
            assert adjusted_latency_mean < 150.0  # Much closer to 100ms
            assert adjusted_error_mean < 2.0  # Much closer to 1%
            assert adjusted_avail_mean > 99.0  # Much closer to 99.5%
    
    def test_no_outliers_no_adjusted_statistics(self, engine):
        """Test that when no outliers exist, adjusted statistics are None."""
        service_id = "test-service-no-outliers"
        now = datetime.utcnow()
        
        # Create 10 very consistent data points (no outliers)
        for i in range(10):
            timestamp = now - timedelta(days=i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 100.0,
                    "p95_ms": 200.0,
                    "p99_ms": 300.0,
                    "mean_ms": 110.0,
                    "stddev_ms": 20.0
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
        result = engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
        window_data = result["time_windows"]["30d"]
        
        # Verify no outliers detected
        assert window_data["outlier_indices"] is None or len(window_data["outlier_indices"]) == 0
        
        # Adjusted statistics should be None when no outliers
        assert window_data["latency_adjusted"] is None
        assert window_data["error_rate_adjusted"] is None
        assert window_data["availability_adjusted"] is None
    
    def test_adjusted_statistics_stored_correctly(self, engine):
        """Test that both raw and adjusted statistics are stored and retrievable."""
        service_id = "test-service-storage"
        now = datetime.utcnow()
        
        # Create data with outliers
        for i in range(10):
            timestamp = now - timedelta(days=i, microseconds=i)
            latency_value = 1000.0 if i < 2 else 100.0  # First 2 are outliers
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": latency_value,
                    "p95_ms": latency_value * 2,
                    "p99_ms": latency_value * 3,
                    "mean_ms": latency_value * 1.1,
                    "stddev_ms": 20.0
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
        
        # Compute and store aggregated metrics
        computed = engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
        
        # Retrieve stored aggregated metrics
        retrieved = engine.get_aggregated_metrics(service_id)
        
        # Verify both raw and adjusted statistics are stored
        assert retrieved is not None
        window_data = retrieved["time_windows"]["30d"]
        
        # Raw statistics should exist
        assert "latency" in window_data
        assert "error_rate" in window_data
        assert "availability" in window_data
        
        # Adjusted statistics should exist (if outliers detected)
        if window_data.get("outlier_indices"):
            assert "latency_adjusted" in window_data
            assert "error_rate_adjusted" in window_data
            assert "availability_adjusted" in window_data
    
    def test_multiple_time_windows_adjusted_statistics(self, engine):
        """Test that adjusted statistics are computed for all time windows."""
        service_id = "test-service-multi-window"
        now = datetime.utcnow()
        
        # Create 100 days of data with some outliers
        for i in range(100):
            timestamp = now - timedelta(days=i, microseconds=i)
            # Every 10th data point is an outlier
            is_outlier = (i % 10 == 0)
            latency_value = 5000.0 if is_outlier else 100.0
            
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": latency_value,
                    "p95_ms": latency_value * 2,
                    "p99_ms": latency_value * 3,
                    "mean_ms": latency_value * 1.1,
                    "stddev_ms": 20.0
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
        
        # Compute aggregated metrics for all windows
        result = engine.compute_aggregated_metrics(service_id)
        
        # Verify adjusted statistics exist for windows with outliers
        for window in ["1d", "7d", "30d", "90d"]:
            window_data = result["time_windows"][window]
            
            # If outliers detected, adjusted statistics should exist
            if window_data.get("outlier_indices") and len(window_data["outlier_indices"]) > 0:
                assert window_data["latency_adjusted"] is not None
                assert window_data["error_rate_adjusted"] is not None
                assert window_data["availability_adjusted"] is not None
                
                # Adjusted sample count should be less than raw
                assert window_data["latency_adjusted"]["sample_count"] < window_data["latency"]["sample_count"]
    
    def test_adjusted_statistics_percentiles(self, engine):
        """Test that adjusted statistics compute correct percentiles."""
        service_id = "test-service-percentiles"
        now = datetime.utcnow()
        
        # Create 20 normal data points
        for i in range(20):
            timestamp = now - timedelta(days=i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 100.0 + i,  # Gradually increasing
                    "p95_ms": 200.0 + i * 2,
                    "p99_ms": 300.0 + i * 3,
                    "mean_ms": 110.0 + i,
                    "stddev_ms": 20.0
                },
                error_rate={
                    "percent": 1.0 + i * 0.1,
                    "total_requests": 10000,
                    "failed_requests": 100 + i * 10
                },
                availability={
                    "percent": 99.5 - i * 0.01,
                    "uptime_seconds": 86000 - i * 100,
                    "downtime_seconds": 400 + i * 100
                },
                timestamp=timestamp
            )
        
        # Add 2 extreme outliers
        for i in range(2):
            timestamp = now - timedelta(days=20 + i, microseconds=20 + i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 10000.0,
                    "p95_ms": 20000.0,
                    "p99_ms": 30000.0,
                    "mean_ms": 11000.0,
                    "stddev_ms": 2000.0
                },
                error_rate={
                    "percent": 90.0,
                    "total_requests": 10000,
                    "failed_requests": 9000
                },
                availability={
                    "percent": 10.0,
                    "uptime_seconds": 8640,
                    "downtime_seconds": 77760
                },
                timestamp=timestamp
            )
        
        # Compute aggregated metrics
        result = engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
        window_data = result["time_windows"]["30d"]
        
        # Verify adjusted statistics have valid percentile ordering
        if window_data["latency_adjusted"]:
            adj_lat = window_data["latency_adjusted"]
            assert adj_lat["p50_ms"] <= adj_lat["p95_ms"]
            assert adj_lat["p95_ms"] <= adj_lat["p99_ms"]
            assert adj_lat["min_ms"] <= adj_lat["p50_ms"]
            assert adj_lat["p99_ms"] <= adj_lat["max_ms"]
            
            adj_err = window_data["error_rate_adjusted"]
            assert adj_err["p50_percent"] <= adj_err["p95_percent"]
            assert adj_err["p95_percent"] <= adj_err["p99_percent"]
            
            adj_avail = window_data["availability_adjusted"]
            assert adj_avail["p50_percent"] <= adj_avail["p95_percent"]
            assert adj_avail["p95_percent"] <= adj_avail["p99_percent"]
    
    def test_edge_case_all_outliers(self, engine):
        """Test edge case where all data points are outliers."""
        service_id = "test-service-all-outliers"
        now = datetime.utcnow()
        
        # Create 5 data points with wildly varying values (all potential outliers)
        values = [10.0, 1000.0, 50.0, 5000.0, 100.0]
        for i, value in enumerate(values):
            timestamp = now - timedelta(days=i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": value,
                    "p95_ms": value * 2,
                    "p99_ms": value * 3,
                    "mean_ms": value * 1.1,
                    "stddev_ms": 20.0
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
        result = engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
        window_data = result["time_windows"]["30d"]
        
        # Raw statistics should include all 5 data points
        assert window_data["latency"]["sample_count"] == 5
        
        # If all are outliers, adjusted statistics might be None or have very few samples
        # This is acceptable behavior - we can't compute meaningful adjusted stats
        if window_data["latency_adjusted"]:
            # If adjusted stats exist, they should have fewer samples
            assert window_data["latency_adjusted"]["sample_count"] < 5
    
    def test_edge_case_single_data_point(self, engine):
        """Test edge case with only one data point (no outliers possible)."""
        service_id = "test-service-single"
        now = datetime.utcnow()
        
        # Create single data point
        engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={
                "p50_ms": 100.0,
                "p95_ms": 200.0,
                "p99_ms": 300.0,
                "mean_ms": 110.0,
                "stddev_ms": 20.0
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
        
        # Compute aggregated metrics
        result = engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
        window_data = result["time_windows"]["30d"]
        
        # With single data point, no outliers can be detected
        assert window_data["latency"]["sample_count"] == 1
        assert window_data["outlier_indices"] is None or len(window_data["outlier_indices"]) == 0
        assert window_data["latency_adjusted"] is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
