"""
Unit tests for per-region statistics computation.

Tests for Task 11.2: Implement per-region statistics computation
"""

import pytest
from datetime import datetime, timedelta
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
        }
    }


class TestPerRegionStatistics:
    """Test per-region statistics computation functionality."""

    def test_compute_regional_stats_single_region(self, metrics_engine, base_metrics_data):
        """Test computing statistics for a single region."""
        # Ingest multiple metrics with regional data
        now = datetime.utcnow()
        
        for i in range(5):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0 + i * 5,
                    "availability": 99.5 - i * 0.1
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute regional aggregated metrics
        result = metrics_engine.compute_regional_aggregated_metrics("test-service", ["1d"])
        
        assert result["has_regional_data"] is True
        assert "us-east-1" in result["regions"]
        assert "1d" in result["regions"]["us-east-1"]
        
        stats = result["regions"]["us-east-1"]["1d"]
        assert stats["data_available"] is True
        assert stats["sample_count"] == 5
        assert "latency_p95_ms" in stats
        assert "availability" in stats

    def test_compute_regional_stats_multiple_regions(self, metrics_engine, base_metrics_data):
        """Test computing statistics for multiple regions."""
        # Ingest metrics with multiple regions
        now = datetime.utcnow()
        
        for i in range(5):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0 + i * 5,
                    "availability": 99.5 - i * 0.1
                },
                "us-west-2": {
                    "latency_p95_ms": 100.0 + i * 5,
                    "availability": 99.4 - i * 0.1
                },
                "eu-west-1": {
                    "latency_p95_ms": 110.0 + i * 5,
                    "availability": 99.3 - i * 0.1
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute regional aggregated metrics
        result = metrics_engine.compute_regional_aggregated_metrics("test-service", ["1d"])
        
        assert result["has_regional_data"] is True
        assert len(result["regions"]) == 3
        assert "us-east-1" in result["regions"]
        assert "us-west-2" in result["regions"]
        assert "eu-west-1" in result["regions"]
        
        # Verify each region has stats
        for region in ["us-east-1", "us-west-2", "eu-west-1"]:
            assert "1d" in result["regions"][region]
            stats = result["regions"][region]["1d"]
            assert stats["data_available"] is True
            assert stats["sample_count"] == 5

    def test_regional_stats_mean_median_percentiles(self, metrics_engine, base_metrics_data):
        """Test that mean, median, and percentiles are computed correctly."""
        # Ingest metrics with known values
        now = datetime.utcnow()
        latency_values = [90.0, 95.0, 100.0, 105.0, 110.0]
        availability_values = [99.5, 99.4, 99.3, 99.2, 99.1]
        
        for i, (lat, avail) in enumerate(zip(latency_values, availability_values)):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": lat,
                    "availability": avail
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute regional aggregated metrics
        result = metrics_engine.compute_regional_aggregated_metrics("test-service", ["1d"])
        
        stats = result["regions"]["us-east-1"]["1d"]
        
        # Check latency statistics
        latency_stats = stats["latency_p95_ms"]
        assert latency_stats["mean"] == 100.0  # (90+95+100+105+110)/5
        assert latency_stats["median"] == 100.0
        assert latency_stats["min"] == 90.0
        assert latency_stats["max"] == 110.0
        assert "p50" in latency_stats
        assert "p95" in latency_stats
        assert "p99" in latency_stats
        assert "stddev" in latency_stats
        
        # Check availability statistics
        availability_stats = stats["availability"]
        assert availability_stats["mean"] == 99.3  # (99.5+99.4+99.3+99.2+99.1)/5
        assert availability_stats["median"] == 99.3
        assert availability_stats["min"] == 99.1
        assert availability_stats["max"] == 99.5

    def test_regional_stats_multiple_time_windows(self, metrics_engine, base_metrics_data):
        """Test computing statistics for multiple time windows."""
        # Ingest metrics spanning multiple days
        now = datetime.utcnow()
        
        # Ingest data for 10 days
        for i in range(10):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(days=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0 + i * 2,
                    "availability": 99.5 - i * 0.05
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute for multiple time windows
        result = metrics_engine.compute_regional_aggregated_metrics(
            "test-service", 
            ["1d", "7d"]
        )
        
        region_stats = result["regions"]["us-east-1"]
        
        # Check 1d window (should have 1-2 samples)
        assert "1d" in region_stats
        stats_1d = region_stats["1d"]
        assert stats_1d["data_available"] is True
        assert stats_1d["sample_count"] >= 1
        
        # Check 7d window (should have more samples)
        assert "7d" in region_stats
        stats_7d = region_stats["7d"]
        assert stats_7d["data_available"] is True
        assert stats_7d["sample_count"] >= stats_1d["sample_count"]

    def test_regional_stats_incomplete_data(self, metrics_engine, base_metrics_data):
        """Test handling regions with incomplete data across time windows."""
        # Ingest metrics where some regions have data only in certain windows
        now = datetime.utcnow()
        
        # Recent data for us-east-1
        for i in range(2):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0,
                    "availability": 99.5
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Older data for eu-west-1 (outside 1d window)
        for i in range(2, 5):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(days=i)
            metrics_data["regional_breakdown"] = {
                "eu-west-1": {
                    "latency_p95_ms": 110.0,
                    "availability": 99.3
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute for 1d and 7d windows
        result = metrics_engine.compute_regional_aggregated_metrics(
            "test-service",
            ["1d", "7d"]
        )
        
        # us-east-1 should have data in 1d window
        assert result["regions"]["us-east-1"]["1d"]["data_available"] is True
        assert result["regions"]["us-east-1"]["1d"]["sample_count"] > 0
        
        # eu-west-1 should NOT have data in 1d window
        assert result["regions"]["eu-west-1"]["1d"]["data_available"] is False
        assert result["regions"]["eu-west-1"]["1d"]["sample_count"] == 0
        
        # eu-west-1 should have data in 7d window
        assert result["regions"]["eu-west-1"]["7d"]["data_available"] is True
        assert result["regions"]["eu-west-1"]["7d"]["sample_count"] > 0

    def test_regional_stats_no_regional_data(self, metrics_engine, base_metrics_data):
        """Test behavior when service has no regional data."""
        # Ingest metrics without regional breakdown
        now = datetime.utcnow()
        metrics_data = base_metrics_data.copy()
        metrics_data["timestamp"] = now
        metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute regional aggregated metrics
        result = metrics_engine.compute_regional_aggregated_metrics("test-service", ["1d"])
        
        assert result["has_regional_data"] is False
        assert result["regions"] == {}
        assert "message" in result

    def test_regional_stats_storage_and_retrieval(self, metrics_engine, base_metrics_data):
        """Test that regional aggregated metrics are stored and can be retrieved."""
        # Ingest metrics with regional data
        now = datetime.utcnow()
        
        for i in range(3):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0 + i * 5,
                    "availability": 99.5 - i * 0.1
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute and store
        result = metrics_engine.compute_regional_aggregated_metrics("test-service", ["1d"])
        
        # Retrieve stored data
        retrieved = metrics_engine.get_regional_aggregated_metrics("test-service")
        
        assert retrieved is not None
        assert retrieved["service_id"] == "test-service"
        assert retrieved["has_regional_data"] is True
        assert "us-east-1" in retrieved["regions"]

    def test_regional_stats_varying_regions_over_time(self, metrics_engine, base_metrics_data):
        """Test handling when different regions appear in different time periods."""
        # Ingest metrics with varying regions
        now = datetime.utcnow()
        
        # Day 1: us-east-1 and us-west-2
        for i in range(2):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0,
                    "availability": 99.5
                },
                "us-west-2": {
                    "latency_p95_ms": 100.0,
                    "availability": 99.4
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Day 2: us-east-1 and eu-west-1 (us-west-2 dropped, eu-west-1 added)
        for i in range(2, 4):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(days=2, hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 95.0,
                    "availability": 99.4
                },
                "eu-west-1": {
                    "latency_p95_ms": 110.0,
                    "availability": 99.3
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute for 7d window
        result = metrics_engine.compute_regional_aggregated_metrics("test-service", ["7d"])
        
        # All three regions should appear in results
        assert len(result["regions"]) == 3
        assert "us-east-1" in result["regions"]
        assert "us-west-2" in result["regions"]
        assert "eu-west-1" in result["regions"]
        
        # us-east-1 should have data from both periods
        assert result["regions"]["us-east-1"]["7d"]["sample_count"] == 4
        
        # us-west-2 and eu-west-1 should have data from their respective periods
        assert result["regions"]["us-west-2"]["7d"]["sample_count"] == 2
        assert result["regions"]["eu-west-1"]["7d"]["sample_count"] == 2

    def test_regional_stats_no_metrics_for_service(self, metrics_engine):
        """Test error handling when service has no metrics."""
        with pytest.raises(ValueError, match="No metrics found"):
            metrics_engine.compute_regional_aggregated_metrics("nonexistent-service", ["1d"])

    def test_regional_stats_invalid_time_window(self, metrics_engine, base_metrics_data):
        """Test error handling for invalid time window."""
        # Ingest at least one metric
        now = datetime.utcnow()
        metrics_data = base_metrics_data.copy()
        metrics_data["timestamp"] = now
        metrics_data["regional_breakdown"] = {
            "us-east-1": {
                "latency_p95_ms": 90.0,
                "availability": 99.5
            }
        }
        metrics_engine.ingest_metrics(**metrics_data)
        
        with pytest.raises(ValueError, match="Invalid time_window"):
            metrics_engine.compute_regional_aggregated_metrics("test-service", ["invalid"])

    def test_regional_stats_all_time_windows(self, metrics_engine, base_metrics_data):
        """Test computing statistics for all time windows."""
        # Ingest metrics spanning 100 days
        now = datetime.utcnow()
        
        for i in range(100):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(days=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0 + i * 0.5,
                    "availability": 99.5 - i * 0.001
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute for all time windows (default)
        result = metrics_engine.compute_regional_aggregated_metrics("test-service")
        
        region_stats = result["regions"]["us-east-1"]
        
        # All time windows should be present
        assert "1d" in region_stats
        assert "7d" in region_stats
        assert "30d" in region_stats
        assert "90d" in region_stats
        
        # Sample counts should increase with window size
        assert region_stats["1d"]["sample_count"] <= region_stats["7d"]["sample_count"]
        assert region_stats["7d"]["sample_count"] <= region_stats["30d"]["sample_count"]
        assert region_stats["30d"]["sample_count"] <= region_stats["90d"]["sample_count"]
