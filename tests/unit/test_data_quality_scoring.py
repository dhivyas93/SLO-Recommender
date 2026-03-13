"""
Unit tests for data quality scoring functionality.

Tests the enhanced data quality scoring implementation including:
- Completeness score computation
- Staleness indicator
- Outlier detection (3-sigma rule)
- Overall quality score (weighted combination)
"""

import pytest
from datetime import datetime, timedelta
from src.engines.metrics_ingestion import MetricsIngestionEngine
from src.storage.file_storage import FileStorage


@pytest.fixture
def temp_storage(tmp_path):
    """Create temporary storage for testing."""
    return FileStorage(base_path=str(tmp_path))


@pytest.fixture
def metrics_engine(temp_storage):
    """Create MetricsIngestionEngine with temporary storage."""
    return MetricsIngestionEngine(storage=temp_storage)


class TestDataQualityScoring:
    """Test data quality scoring with outlier detection."""
    
    def test_quality_score_with_no_outliers(self, metrics_engine):
        """Test quality score when metrics are normal (no outliers)."""
        service_id = "test-service"
        
        # Ingest first metric (establishes baseline)
        result1 = metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={"p50_ms": 100, "p95_ms": 200, "p99_ms": 300, "mean_ms": 110, "stddev_ms": 20},
            error_rate={"percent": 1.0, "total_requests": 10000, "failed_requests": 100},
            availability={"percent": 99.5, "uptime_seconds": 86000, "downtime_seconds": 400},
            timestamp=datetime.utcnow() - timedelta(days=5)
        )
        
        # Ingest more metrics with similar values (no outliers)
        for i in range(1, 5):
            metrics_engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={"p50_ms": 100 + i, "p95_ms": 200 + i, "p99_ms": 300 + i, "mean_ms": 110 + i, "stddev_ms": 20},
                error_rate={"percent": 1.0 + i * 0.1, "total_requests": 10000, "failed_requests": 100 + i * 10},
                availability={"percent": 99.5 - i * 0.01, "uptime_seconds": 86000, "downtime_seconds": 400 + i * 10},
                timestamp=datetime.utcnow() - timedelta(days=5-i)
            )
        
        # Ingest current metric (should have no outliers)
        result = metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={"p50_ms": 103, "p95_ms": 203, "p99_ms": 303, "mean_ms": 113, "stddev_ms": 20},
            error_rate={"percent": 1.3, "total_requests": 10000, "failed_requests": 130},
            availability={"percent": 99.47, "uptime_seconds": 86000, "downtime_seconds": 450}
        )
        
        # Verify no outliers detected
        assert result["data_quality"]["outlier_count"] == 0
        # Quality score should be high (no outliers, fresh data, complete)
        assert result["data_quality"]["quality_score"] >= 0.8
    
    def test_quality_score_with_outliers(self, metrics_engine):
        """Test quality score when metrics contain outliers."""
        service_id = "test-service-outliers"
        
        # Ingest baseline metrics with some variation (not identical)
        for i in range(5):
            metrics_engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={"p50_ms": 100 + i, "p95_ms": 200 + i, "p99_ms": 300 + i, "mean_ms": 110 + i, "stddev_ms": 20},
                error_rate={"percent": 1.0 + i * 0.05, "total_requests": 10000, "failed_requests": 100 + i * 5},
                availability={"percent": 99.5 - i * 0.01, "uptime_seconds": 86000, "downtime_seconds": 400 + i * 10},
                timestamp=datetime.utcnow() - timedelta(days=5-i)
            )
        
        # Ingest metric with outlier values (way beyond 3 standard deviations)
        result = metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={"p50_ms": 500, "p95_ms": 1000, "p99_ms": 1500, "mean_ms": 550, "stddev_ms": 100},
            error_rate={"percent": 15.0, "total_requests": 10000, "failed_requests": 1500},
            availability={"percent": 85.0, "uptime_seconds": 73440, "downtime_seconds": 12960}
        )
        
        # Verify outliers detected
        assert result["data_quality"]["outlier_count"] > 0
        # Quality score should be reduced due to outliers
        assert result["data_quality"]["quality_score"] < 0.9
    
    def test_completeness_score_all_fields(self, metrics_engine):
        """Test completeness score when all fields are present."""
        result = metrics_engine.ingest_metrics(
            service_id="test-service",
            time_window="1d",
            latency={"p50_ms": 100, "p95_ms": 200, "p99_ms": 300, "mean_ms": 110, "stddev_ms": 20},
            error_rate={"percent": 1.0, "total_requests": 10000, "failed_requests": 100},
            availability={"percent": 99.5, "uptime_seconds": 86000, "downtime_seconds": 400},
            request_volume={"requests_per_second": 100.0, "peak_rps": 200.0}
        )
        
        assert result["data_quality"]["completeness"] == 1.0
    
    def test_staleness_indicator(self, metrics_engine):
        """Test staleness indicator computation."""
        service_id = "test-service-staleness"
        
        # Ingest old metric
        old_timestamp = datetime.utcnow() - timedelta(hours=48)
        metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={"p50_ms": 100, "p95_ms": 200, "p99_ms": 300, "mean_ms": 110, "stddev_ms": 20},
            error_rate={"percent": 1.0, "total_requests": 10000, "failed_requests": 100},
            availability={"percent": 99.5, "uptime_seconds": 86000, "downtime_seconds": 400},
            timestamp=old_timestamp
        )
        
        # Ingest new metric
        result = metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={"p50_ms": 100, "p95_ms": 200, "p99_ms": 300, "mean_ms": 110, "stddev_ms": 20},
            error_rate={"percent": 1.0, "total_requests": 10000, "failed_requests": 100},
            availability={"percent": 99.5, "uptime_seconds": 86000, "downtime_seconds": 400}
        )
        
        # Staleness should be approximately 48 hours
        assert result["data_quality"]["staleness_hours"] >= 47
        assert result["data_quality"]["staleness_hours"] <= 49
    
    def test_quality_score_weighted_combination(self, metrics_engine):
        """Test that quality score is a weighted combination of factors."""
        service_id = "test-service-weighted"
        
        # Create baseline with consistent metrics
        for i in range(5):
            metrics_engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={"p50_ms": 100, "p95_ms": 200, "p99_ms": 300, "mean_ms": 110, "stddev_ms": 20},
                error_rate={"percent": 1.0, "total_requests": 10000, "failed_requests": 100},
                availability={"percent": 99.5, "uptime_seconds": 86000, "downtime_seconds": 400},
                timestamp=datetime.utcnow() - timedelta(hours=i)
            )
        
        # Ingest fresh metric with no outliers
        result = metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={"p50_ms": 101, "p95_ms": 201, "p99_ms": 301, "mean_ms": 111, "stddev_ms": 20},
            error_rate={"percent": 1.1, "total_requests": 10000, "failed_requests": 110},
            availability={"percent": 99.5, "uptime_seconds": 86000, "downtime_seconds": 400}
        )
        
        # Quality score should be high (completeness=1.0, fresh data, no outliers)
        # Expected: 0.4 (completeness) + 0.3 (staleness) + 0.3 (outliers) = 1.0
        assert result["data_quality"]["completeness"] == 1.0
        assert result["data_quality"]["staleness_hours"] < 5  # Should be less than 5 hours
        assert result["data_quality"]["outlier_count"] == 0
        assert result["data_quality"]["quality_score"] >= 0.9
    
    def test_outlier_detection_with_insufficient_data(self, metrics_engine):
        """Test that outlier detection handles insufficient historical data gracefully."""
        service_id = "test-service-new"
        
        # Ingest first metric (no historical data to compare)
        result = metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={"p50_ms": 1000, "p95_ms": 2000, "p99_ms": 3000, "mean_ms": 1100, "stddev_ms": 200},
            error_rate={"percent": 10.0, "total_requests": 10000, "failed_requests": 1000},
            availability={"percent": 90.0, "uptime_seconds": 77760, "downtime_seconds": 8640}
        )
        
        # Should not detect outliers (insufficient data)
        assert result["data_quality"]["outlier_count"] == 0
    
    def test_quality_score_penalties(self, metrics_engine):
        """Test that quality score applies penalties for severe issues."""
        service_id = "test-service-penalties"
        
        # Ingest metric with high error rate and low availability
        result = metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={"p50_ms": 100, "p95_ms": 200, "p99_ms": 300, "mean_ms": 110, "stddev_ms": 20},
            error_rate={"percent": 15.0, "total_requests": 10000, "failed_requests": 1500},
            availability={"percent": 85.0, "uptime_seconds": 73440, "downtime_seconds": 12960}
        )
        
        # Quality score should be reduced due to penalties
        # High error rate (>10%) and low availability (<90%) both apply 0.9 multiplier
        assert result["data_quality"]["quality_score"] < 0.85


class TestWindowQualityScoring:
    """Test time window quality scoring with outlier detection."""
    
    def test_window_quality_outlier_detection(self, metrics_engine):
        """Test that window quality detects outliers within the window."""
        service_id = "test-service-window-outliers"
        now = datetime.utcnow()
        
        # Create 7 days of data with one outlier
        for i in range(7):
            if i == 3:
                # Insert outlier
                latency_p95 = 2000  # Way higher than normal
            else:
                latency_p95 = 200 + i
            
            metrics_engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={"p50_ms": 100 + i, "p95_ms": latency_p95, "p99_ms": 300 + i, "mean_ms": 110 + i, "stddev_ms": 20},
                error_rate={"percent": 1.0 + i * 0.1, "total_requests": 10000, "failed_requests": 100 + i * 10},
                availability={"percent": 99.5 - i * 0.01, "uptime_seconds": 86000, "downtime_seconds": 400 + i * 10},
                timestamp=now - timedelta(days=i)
            )
        
        # Compute aggregated metrics
        result = metrics_engine.compute_aggregated_metrics(service_id, time_windows=["7d"])
        quality = result["time_windows"]["7d"]["data_quality"]
        
        # Quality score should be reduced due to outliers
        # Note: The outlier detection in window quality looks at the distribution within the window
        assert quality["quality_score"] < 1.0
        assert quality["quality_score"] > 0.0
