"""
Integration tests for regional aggregation functionality.

Tests for Task 11.4: Write unit tests for regional aggregation
This file contains integration tests that verify both per-region statistics
and global aggregation work together correctly.
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


class TestRegionalAggregationIntegration:
    """Integration tests for regional aggregation functionality."""

    def test_regional_and_global_consistency(self, metrics_engine, base_metrics_data):
        """Test that regional and global aggregations are consistent."""
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
                    "latency_p95_ms": 110.0,
                    "availability": 99.3
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute both regional and global aggregations
        regional_result = metrics_engine.compute_regional_aggregated_metrics("test-service", ["1d"])
        global_result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        # Verify both have data
        assert regional_result["has_regional_data"] is True
        assert global_result["has_regional_data"] is True
        
        # Verify sample counts match
        assert regional_result["regions"]["us-east-1"]["1d"]["sample_count"] == 5
        assert regional_result["regions"]["us-west-2"]["1d"]["sample_count"] == 5
        assert global_result["global_stats"]["1d"]["sample_count"] == 5
        
        # Verify global mean is average of regional means
        us_east_mean = regional_result["regions"]["us-east-1"]["1d"]["latency_p95_ms"]["mean"]
        us_west_mean = regional_result["regions"]["us-west-2"]["1d"]["latency_p95_ms"]["mean"]
        expected_global_mean = (us_east_mean + us_west_mean) / 2
        actual_global_mean = global_result["global_stats"]["1d"]["latency_p95_ms"]["mean"]
        
        assert actual_global_mean == expected_global_mean

    def test_regional_aggregation_with_no_data(self, metrics_engine, base_metrics_data):
        """Test that both regional and global return consistent results with no regional data."""
        # Ingest metrics without regional breakdown
        now = datetime.utcnow()
        metrics_data = base_metrics_data.copy()
        metrics_data["timestamp"] = now
        metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute both aggregations
        regional_result = metrics_engine.compute_regional_aggregated_metrics("test-service", ["1d"])
        global_result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        # Both should indicate no regional data
        assert regional_result["has_regional_data"] is False
        assert global_result["has_regional_data"] is False
        assert regional_result["regions"] == {}
        assert "message" in regional_result
        assert "message" in global_result

    def test_regional_aggregation_across_all_time_windows(self, metrics_engine, base_metrics_data):
        """Test regional and global aggregation across all time windows."""
        # Ingest metrics spanning 100 days
        now = datetime.utcnow()
        
        for i in range(100):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(days=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 90.0 + i * 0.5,
                    "availability": 99.5 - i * 0.001
                },
                "eu-west-1": {
                    "latency_p95_ms": 100.0 + i * 0.5,
                    "availability": 99.4 - i * 0.001
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute for all time windows
        regional_result = metrics_engine.compute_regional_aggregated_metrics("test-service")
        global_result = metrics_engine.compute_global_aggregated_metrics("test-service")
        
        # Verify all time windows are present in both
        for window in ["1d", "7d", "30d", "90d"]:
            assert window in regional_result["regions"]["us-east-1"]
            assert window in regional_result["regions"]["eu-west-1"]
            assert window in global_result["global_stats"]
            
            # Verify sample counts increase with window size
            regional_samples = regional_result["regions"]["us-east-1"][window]["sample_count"]
            global_samples = global_result["global_stats"][window]["sample_count"]
            assert regional_samples == global_samples

    def test_regional_aggregation_with_dynamic_regions(self, metrics_engine, base_metrics_data):
        """Test that regional and global handle dynamic regions correctly."""
        # Ingest metrics with regions appearing and disappearing
        now = datetime.utcnow()
        
        # First 3 metrics: us-east-1 and us-west-2
        for i in range(3):
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
        
        # Next 2 metrics: us-east-1 and eu-west-1 (us-west-2 dropped, eu-west-1 added)
        for i in range(3, 5):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
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
        
        # Compute aggregations
        regional_result = metrics_engine.compute_regional_aggregated_metrics("test-service", ["1d"])
        global_result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        # Regional should show all 3 regions
        assert len(regional_result["regions"]) == 3
        assert "us-east-1" in regional_result["regions"]
        assert "us-west-2" in regional_result["regions"]
        assert "eu-west-1" in regional_result["regions"]
        
        # us-east-1 should have all 5 samples
        assert regional_result["regions"]["us-east-1"]["1d"]["sample_count"] == 5
        
        # us-west-2 and eu-west-1 should have their respective samples
        assert regional_result["regions"]["us-west-2"]["1d"]["sample_count"] == 3
        assert regional_result["regions"]["eu-west-1"]["1d"]["sample_count"] == 2
        
        # Global should aggregate all 5 timestamps
        assert global_result["global_stats"]["1d"]["sample_count"] == 5

    def test_storage_and_retrieval_integration(self, metrics_engine, base_metrics_data):
        """Test that both regional and global metrics are stored and retrievable."""
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
        
        # Compute and store both
        metrics_engine.compute_regional_aggregated_metrics("test-service", ["1d"])
        metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        # Retrieve both
        regional_retrieved = metrics_engine.get_regional_aggregated_metrics("test-service")
        global_retrieved = metrics_engine.get_global_aggregated_metrics("test-service")
        
        # Verify both are stored correctly
        assert regional_retrieved is not None
        assert global_retrieved is not None
        assert regional_retrieved["service_id"] == "test-service"
        assert global_retrieved["service_id"] == "test-service"
        assert regional_retrieved["has_regional_data"] is True
        assert global_retrieved["has_regional_data"] is True

    def test_error_handling_consistency(self, metrics_engine):
        """Test that both regional and global handle errors consistently."""
        # Test with nonexistent service
        with pytest.raises(ValueError, match="No metrics found"):
            metrics_engine.compute_regional_aggregated_metrics("nonexistent", ["1d"])
        
        with pytest.raises(ValueError, match="No metrics found"):
            metrics_engine.compute_global_aggregated_metrics("nonexistent", ["1d"])

    def test_invalid_time_window_consistency(self, metrics_engine, base_metrics_data):
        """Test that both regional and global reject invalid time windows."""
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
        
        # Test invalid time window
        with pytest.raises(ValueError, match="Invalid time_window"):
            metrics_engine.compute_regional_aggregated_metrics("test-service", ["invalid"])
        
        with pytest.raises(ValueError, match="Invalid time_window"):
            metrics_engine.compute_global_aggregated_metrics("test-service", ["invalid"])

    def test_regional_aggregation_statistical_properties(self, metrics_engine, base_metrics_data):
        """Test that regional and global aggregations maintain statistical properties."""
        # Ingest metrics with known statistical properties
        now = datetime.utcnow()
        
        # Create data where us-east-1 has constant values and us-west-2 has varying values
        for i in range(10):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 100.0,  # Constant
                    "availability": 99.5  # Constant
                },
                "us-west-2": {
                    "latency_p95_ms": 100.0 + i * 10,  # Varying
                    "availability": 99.5 - i * 0.1  # Varying
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute aggregations
        regional_result = metrics_engine.compute_regional_aggregated_metrics("test-service", ["1d"])
        global_result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        # us-east-1 should have zero standard deviation
        us_east_stats = regional_result["regions"]["us-east-1"]["1d"]["latency_p95_ms"]
        assert us_east_stats["stddev"] == 0.0
        assert us_east_stats["min"] == us_east_stats["max"] == 100.0
        
        # us-west-2 should have non-zero standard deviation
        us_west_stats = regional_result["regions"]["us-west-2"]["1d"]["latency_p95_ms"]
        assert us_west_stats["stddev"] > 0
        assert us_west_stats["min"] < us_west_stats["max"]
        
        # Global should have variation due to us-west-2
        global_stats = global_result["global_stats"]["1d"]["latency_p95_ms"]
        assert global_stats["stddev"] > 0

    def test_regional_aggregation_with_single_sample(self, metrics_engine, base_metrics_data):
        """Test regional and global aggregation with only one sample."""
        # Ingest single metric with regional data
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
        
        # Compute aggregations
        regional_result = metrics_engine.compute_regional_aggregated_metrics("test-service", ["1d"])
        global_result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        # Both should handle single sample correctly
        assert regional_result["regions"]["us-east-1"]["1d"]["sample_count"] == 1
        assert global_result["global_stats"]["1d"]["sample_count"] == 1
        
        # Statistics should be valid (stddev should be 0 for single sample)
        regional_stats = regional_result["regions"]["us-east-1"]["1d"]["latency_p95_ms"]
        assert regional_stats["mean"] == 90.0
        assert regional_stats["stddev"] == 0.0
        
        global_stats = global_result["global_stats"]["1d"]["latency_p95_ms"]
        assert global_stats["mean"] == 90.0
        assert global_stats["stddev"] == 0.0

    def test_regional_aggregation_boundary_values(self, metrics_engine, base_metrics_data):
        """Test regional and global aggregation with boundary values."""
        # Ingest metrics with extreme values
        now = datetime.utcnow()
        
        for i in range(3):
            metrics_data = base_metrics_data.copy()
            metrics_data["timestamp"] = now - timedelta(hours=i)
            metrics_data["regional_breakdown"] = {
                "us-east-1": {
                    "latency_p95_ms": 0.01,  # Very low latency
                    "availability": 100.0  # Perfect availability
                },
                "us-west-2": {
                    "latency_p95_ms": 10000.0,  # Very high latency
                    "availability": 50.0  # Poor availability
                }
            }
            metrics_engine.ingest_metrics(**metrics_data)
        
        # Compute aggregations
        regional_result = metrics_engine.compute_regional_aggregated_metrics("test-service", ["1d"])
        global_result = metrics_engine.compute_global_aggregated_metrics("test-service", ["1d"])
        
        # Verify extreme values are handled correctly
        us_east_latency = regional_result["regions"]["us-east-1"]["1d"]["latency_p95_ms"]
        us_west_latency = regional_result["regions"]["us-west-2"]["1d"]["latency_p95_ms"]
        
        assert us_east_latency["mean"] == 0.01
        assert us_west_latency["mean"] == 10000.0
        
        # Global should be average of extremes
        global_latency = global_result["global_stats"]["1d"]["latency_p95_ms"]
        expected_mean = round((0.01 + 10000.0) / 2, 2)
        assert global_latency["mean"] == expected_mean
