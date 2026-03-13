"""
Unit tests for global aggregation across regions.

Tests for Task 11.3: Implement global aggregation across regions
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


class TestGlobalAggregation:
    """Test global aggregation across regions functionality."""

    def test_global_aggregation_single_region(self, metrics_engine, base_metrics_data):
        """Test global aggregation with a single region."""
        # Ingest multiple metrics with single region
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
        
        # Compute global aggregated metrics
        result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        assert result["has_regional_data"] is True
        assert "1d" in result["global_stats"]
        
        stats = result["global_stats"]["1d"]
        assert stats["data_available"] is True
        assert stats["sample_count"] == 5
        assert "latency_p95_ms" in stats
        assert "availability" in stats
        
        # With single region, global stats should match regional stats
        latency_stats = stats["latency_p95_ms"]
        assert latency_stats["mean"] > 0
        assert latency_stats["median"] > 0

    def test_global_aggregation_multiple_regions(self, metrics_engine, base_metrics_data):
        """Test global aggregation averages across multiple regions."""
        # Ingest metrics with multiple regions
        now = datetime.utcnow()
        
        for i in range(5):
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
                },
                "eu-west-1": {
                    "latency_p95_ms": 110.0,
                    "availability": 99.3
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute global aggregated metrics
        result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        assert result["has_regional_data"] is True
        stats = result["global_stats"]["1d"]
        
        # Global latency should be average of regions: (90 + 100 + 110) / 3 = 100
        latency_stats = stats["latency_p95_ms"]
        assert latency_stats["mean"] == 100.0
        assert latency_stats["median"] == 100.0
        
        # Global availability should be average: (99.5 + 99.4 + 99.3) / 3 = 99.4
        availability_stats = stats["availability"]
        assert availability_stats["mean"] == 99.4

    def test_global_aggregation_varying_values(self, metrics_engine, base_metrics_data):
        """Test global aggregation with varying values over time."""
        # Ingest metrics with varying regional values
        now = datetime.utcnow()
        
        for i in range(5):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0 + i * 10,
                    "availability": 99.5 - i * 0.1
                },
                "eu-west-1": {
                    "latency_p95_ms": 100.0 + i * 10,
                    "availability": 99.4 - i * 0.1
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute global aggregated metrics
        result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        stats = result["global_stats"]["1d"]
        latency_stats = stats["latency_p95_ms"]
        
        # Should have variation in the aggregated values
        assert latency_stats["stddev"] > 0
        assert latency_stats["min"] < latency_stats["max"]
        assert latency_stats["p50"] > 0
        assert latency_stats["p95"] > 0
        assert latency_stats["p99"] > 0

    def test_global_aggregation_multiple_time_windows(self, metrics_engine, base_metrics_data):
        """Test global aggregation for multiple time windows."""
        # Ingest metrics spanning multiple days
        now = datetime.utcnow()
        
        # Add metrics for 1 day window
        for i in range(5):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0,
                    "availability": 99.5
                },
                "eu-west-1": {
                    "latency_p95_ms": 100.0,
                    "availability": 99.4
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Add metrics for 7 day window
        for i in range(5, 10):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(days=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 95.0,
                    "availability": 99.6
                },
                "eu-west-1": {
                    "latency_p95_ms": 105.0,
                    "availability": 99.5
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute for multiple windows
        result = metrics_engine.compute_global_aggregated_metrics(
            "test-service",
            ["1d", "7d"]
        )
        
        assert "1d" in result["global_stats"]
        assert "7d" in result["global_stats"]
        
        stats_1d = result["global_stats"]["1d"]
        stats_7d = result["global_stats"]["7d"]
        
        # 1d window should have 5 samples
        assert stats_1d["sample_count"] == 5
        # 7d window should have more samples
        assert stats_7d["sample_count"] >= stats_1d["sample_count"]

    def test_global_aggregation_no_regional_data(self, metrics_engine, base_metrics_data):
        """Test behavior when service has no regional data."""
        # Ingest metrics without regional breakdown
        now = datetime.utcnow()
        metrics_data = base_metrics_data.copy()
        metrics_data["timestamp"] = now
        metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute global aggregated metrics
        result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        assert result["has_regional_data"] is False
        assert "message" in result

    def test_global_aggregation_storage_and_retrieval(self, metrics_engine, base_metrics_data):
        """Test that global aggregated metrics are stored and can be retrieved."""
        # Ingest metrics with regional data
        now = datetime.utcnow()
        
        for i in range(3):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0,
                    "availability": 99.5
                },
                "eu-west-1": {
                    "latency_p95_ms": 100.0,
                    "availability": 99.4
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute and store
        result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        # Retrieve stored metrics
        retrieved = metrics_engine.get_global_aggregated_metrics("test-service")
        
        assert retrieved is not None
        assert retrieved["service_id"] == "test-service"
        assert retrieved["has_regional_data"] is True
        assert "1d" in retrieved["global_stats"]

    def test_global_aggregation_no_metrics_for_service(self, metrics_engine):
        """Test error handling when service has no metrics."""
        with pytest.raises(ValueError, match="No metrics found"):
            metrics_engine.compute_global_aggregated_metrics("nonexistent-service", ["1d"])

    def test_global_aggregation_invalid_time_window(self, metrics_engine, base_metrics_data):
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
        
        # Try to compute with invalid window
        with pytest.raises(ValueError, match="Invalid time_window"):
            metrics_engine.compute_global_aggregated_metrics("test-service", ["invalid"])

    def test_global_aggregation_all_time_windows(self, metrics_engine, base_metrics_data):
        """Test computing global statistics for all time windows."""
        # Ingest metrics spanning 100 days
        now = datetime.utcnow()
        
        for i in range(100):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(days=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0 + i,
                    "availability": 99.5
                },
                "eu-west-1": {
                    "latency_p95_ms": 100.0 + i,
                    "availability": 99.4
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute for all windows (default)
        result = metrics_engine.compute_global_aggregated_metrics("test-service")
        
        assert "1d" in result["global_stats"]
        assert "7d" in result["global_stats"]
        assert "30d" in result["global_stats"]
        assert "90d" in result["global_stats"]
        
        # Verify sample counts increase with window size
        assert result["global_stats"]["1d"]["sample_count"] <= result["global_stats"]["7d"]["sample_count"]
        assert result["global_stats"]["7d"]["sample_count"] <= result["global_stats"]["30d"]["sample_count"]
        assert result["global_stats"]["30d"]["sample_count"] <= result["global_stats"]["90d"]["sample_count"]

    def test_global_aggregation_asymmetric_regions(self, metrics_engine, base_metrics_data):
        """Test global aggregation when different timestamps have different regions."""
        # Ingest metrics with varying regions over time
        now = datetime.utcnow()
        
        # First 3 metrics have 2 regions
        for i in range(3):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0,
                    "availability": 99.5
                },
                "eu-west-1": {
                    "latency_p95_ms": 100.0,
                    "availability": 99.4
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Next 2 metrics have 3 regions
        for i in range(3, 5):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0,
                    "availability": 99.5
                },
                "eu-west-1": {
                    "latency_p95_ms": 100.0,
                    "availability": 99.4
                },
                "ap-south-1": {
                    "latency_p95_ms": 120.0,
                    "availability": 99.2
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute global aggregated metrics
        result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        stats = result["global_stats"]["1d"]
        assert stats["data_available"] is True
        assert stats["sample_count"] == 5
        
        # Global stats should handle varying number of regions per timestamp
        latency_stats = stats["latency_p95_ms"]
        assert latency_stats["mean"] > 0
        # The last 2 samples should pull the average up due to ap-south-1
        assert latency_stats["max"] > 100.0

    def test_global_aggregation_statistical_validity(self, metrics_engine, base_metrics_data):
        """Test that global aggregation maintains statistical validity."""
        # Ingest metrics with known values
        now = datetime.utcnow()
        
        for i in range(10):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 100.0,
                    "availability": 99.5
                },
                "eu-west-1": {
                    "latency_p95_ms": 100.0,
                    "availability": 99.5
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute global aggregated metrics
        result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        stats = result["global_stats"]["1d"]
        latency_stats = stats["latency_p95_ms"]
        availability_stats = stats["availability"]
        
        # With constant values, all statistics should be the same
        assert latency_stats["mean"] == 100.0
        assert latency_stats["median"] == 100.0
        assert latency_stats["min"] == 100.0
        assert latency_stats["max"] == 100.0
        assert latency_stats["stddev"] == 0.0
        
        assert availability_stats["mean"] == 99.5
        assert availability_stats["median"] == 99.5
        assert availability_stats["stddev"] == 0.0
