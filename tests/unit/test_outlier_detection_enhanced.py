"""
Tests for enhanced outlier detection with detailed outlier information.
"""

import pytest
from datetime import datetime, timedelta
from src.engines.metrics_ingestion import MetricsIngestionEngine
from src.storage.file_storage import FileStorage
import tempfile
import json
from pathlib import Path


@pytest.fixture
def temp_storage():
    """Create a temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    storage = FileStorage(temp_dir)
    yield storage


@pytest.fixture
def metrics_engine(temp_storage):
    """Create a MetricsIngestionEngine with temporary storage."""
    return MetricsIngestionEngine(temp_storage)


class TestEnhancedOutlierDetection:
    """Test enhanced outlier detection with detailed information."""

    def test_outlier_details_stored(self, metrics_engine, temp_storage):
        """Test that outlier details are stored with metrics."""
        service_id = "test-service-outlier-details"
        
        # Ingest baseline metrics with variation
        latencies = [140.0, 145.0, 150.0, 155.0, 160.0]
        for i, lat in enumerate(latencies):
            metrics_engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                timestamp=datetime(2026, 3, 9, 23, 0, 0) - timedelta(hours=i),
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": lat,
                    "p99_ms": lat * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 25.0
                },
                error_rate={
                    "percent": 0.5,
                    "total_requests": 10000,
                    "failed_requests": 50
                },
                availability={
                    "percent": 99.9,
                    "uptime_seconds": 86313,
                    "downtime_seconds": 87
                }
            )
        
        # Ingest outlier metrics
        result = metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            timestamp=datetime(2026, 3, 10, 0, 0, 0),
            latency={
                "p50_ms": 50.0,
                "p95_ms": 250.0,  # Outlier
                "p99_ms": 500.0,  # Outlier
                "mean_ms": 75.0,
                "stddev_ms": 25.0
            },
            error_rate={
                "percent": 0.5,
                "total_requests": 10000,
                "failed_requests": 50
            },
            availability={
                "percent": 99.9,
                "uptime_seconds": 86313,
                "downtime_seconds": 87
            }
        )
        
        # Verify outliers were detected
        assert result["data_quality"]["outlier_count"] == 2
        
        # Read the stored file to check outlier details
        latest_path = Path(temp_storage.base_path) / "services" / service_id / "metrics" / "latest.json"
        with open(latest_path, 'r') as f:
            stored_data = json.load(f)
        
        # Verify outlier details are present
        assert "outliers" in stored_data["data_quality"]
        assert stored_data["data_quality"]["outliers"] is not None
        assert len(stored_data["data_quality"]["outliers"]) == 2
        
        # Verify outlier structure
        outlier = stored_data["data_quality"]["outliers"][0]
        assert "metric_name" in outlier
        assert "value" in outlier
        assert "z_score" in outlier
        assert "mean" in outlier
        assert "stddev" in outlier
        
        # Verify outlier values
        assert outlier["metric_name"] == "latency_p95_ms"
        assert outlier["value"] == 250.0
        assert outlier["z_score"] > 3.0  # Should be significantly > 3
        assert outlier["mean"] == 150.0  # Mean of baseline metrics
        assert outlier["stddev"] > 0  # Should have non-zero stddev

    def test_no_outliers_when_normal(self, metrics_engine):
        """Test that no outliers are detected for normal metrics."""
        service_id = "test-service-normal"
        
        # Ingest baseline metrics
        for i in range(5):
            metrics_engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                timestamp=datetime(2026, 3, 9, 23, 0, 0) - timedelta(hours=i),
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": 150.0,
                    "p99_ms": 300.0,
                    "mean_ms": 75.0,
                    "stddev_ms": 25.0
                },
                error_rate={
                    "percent": 0.5,
                    "total_requests": 10000,
                    "failed_requests": 50
                },
                availability={
                    "percent": 99.9,
                    "uptime_seconds": 86313,
                    "downtime_seconds": 87
                }
            )
        
        # Ingest normal metrics (within expected range)
        result = metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            timestamp=datetime(2026, 3, 10, 0, 0, 0),
            latency={
                "p50_ms": 50.0,
                "p95_ms": 155.0,  # Slightly higher but not an outlier
                "p99_ms": 310.0,
                "mean_ms": 75.0,
                "stddev_ms": 25.0
            },
            error_rate={
                "percent": 0.5,
                "total_requests": 10000,
                "failed_requests": 50
            },
            availability={
                "percent": 99.9,
                "uptime_seconds": 86313,
                "downtime_seconds": 87
            }
        )
        
        # Verify no outliers detected
        assert result["data_quality"]["outlier_count"] == 0

    def test_multiple_metric_outliers(self, metrics_engine, temp_storage):
        """Test detection of outliers across multiple metric types."""
        service_id = "test-service-multi-outlier"
        
        # Ingest baseline metrics with variation
        for i in range(5):
            metrics_engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                timestamp=datetime(2026, 3, 9, 23, 0, 0) - timedelta(hours=i),
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": 150.0 + i,
                    "p99_ms": 300.0 + i * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 25.0
                },
                error_rate={
                    "percent": 0.5 + i * 0.1,
                    "total_requests": 10000,
                    "failed_requests": 50 + i * 10
                },
                availability={
                    "percent": 99.9 - i * 0.01,
                    "uptime_seconds": 86313,
                    "downtime_seconds": 87
                }
            )
        
        # Ingest metrics with outliers in multiple categories
        result = metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            timestamp=datetime(2026, 3, 10, 0, 0, 0),
            latency={
                "p50_ms": 50.0,
                "p95_ms": 250.0,  # Outlier
                "p99_ms": 500.0,  # Outlier
                "mean_ms": 75.0,
                "stddev_ms": 25.0
            },
            error_rate={
                "percent": 5.0,  # Outlier
                "total_requests": 10000,
                "failed_requests": 500
            },
            availability={
                "percent": 95.0,  # Outlier
                "uptime_seconds": 82800,
                "downtime_seconds": 3600
            }
        )
        
        # Verify multiple outliers detected
        assert result["data_quality"]["outlier_count"] >= 2
        
        # Read the stored file to check outlier details
        latest_path = Path(temp_storage.base_path) / "services" / service_id / "metrics" / "latest.json"
        with open(latest_path, 'r') as f:
            stored_data = json.load(f)
        
        # Verify outliers from different metric types
        outlier_metrics = [o["metric_name"] for o in stored_data["data_quality"]["outliers"]]
        assert len(outlier_metrics) >= 2
        
        # Check that we have outliers from different categories
        metric_categories = set()
        for metric_name in outlier_metrics:
            if "latency" in metric_name:
                metric_categories.add("latency")
            elif "error_rate" in metric_name:
                metric_categories.add("error_rate")
            elif "availability" in metric_name:
                metric_categories.add("availability")
        
        assert len(metric_categories) >= 2  # At least 2 different categories

    def test_outlier_z_score_accuracy(self, metrics_engine, temp_storage):
        """Test that z-scores are calculated correctly."""
        service_id = "test-service-zscore"
        
        # Ingest baseline metrics with known values
        latencies = [100.0, 110.0, 120.0, 130.0, 140.0]
        for i, lat in enumerate(latencies):
            metrics_engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                timestamp=datetime(2026, 3, 9, 23, 0, 0) - timedelta(hours=i),
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": lat,
                    "p99_ms": 300.0,
                    "mean_ms": 75.0,
                    "stddev_ms": 25.0
                },
                error_rate={
                    "percent": 0.5,
                    "total_requests": 10000,
                    "failed_requests": 50
                },
                availability={
                    "percent": 99.9,
                    "uptime_seconds": 86313,
                    "downtime_seconds": 87
                }
            )
        
        # Ingest outlier
        result = metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            timestamp=datetime(2026, 3, 10, 0, 0, 0),
            latency={
                "p50_ms": 50.0,
                "p95_ms": 200.0,  # Outlier
                "p99_ms": 300.0,
                "mean_ms": 75.0,
                "stddev_ms": 25.0
            },
            error_rate={
                "percent": 0.5,
                "total_requests": 10000,
                "failed_requests": 50
            },
            availability={
                "percent": 99.9,
                "uptime_seconds": 86313,
                "downtime_seconds": 87
            }
        )
        
        # Read the stored file
        latest_path = Path(temp_storage.base_path) / "services" / service_id / "metrics" / "latest.json"
        with open(latest_path, 'r') as f:
            stored_data = json.load(f)
        
        # Verify z-score calculation
        # Mean of [100, 110, 120, 130, 140] = 120
        # Stddev ≈ 15.81
        # Z-score for 200 = (200 - 120) / 15.81 ≈ 5.06
        if stored_data["data_quality"]["outliers"]:
            outlier = stored_data["data_quality"]["outliers"][0]
            assert outlier["mean"] == 120.0
            assert 15.0 < outlier["stddev"] < 16.0  # Approximately 15.81
            assert 5.0 < outlier["z_score"] < 5.2  # Approximately 5.06
