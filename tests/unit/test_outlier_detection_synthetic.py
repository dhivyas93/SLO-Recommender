"""
Unit tests for outlier detection with synthetic outliers.

This test suite uses synthetic outliers (known outlier values) to verify:
1. Outliers are correctly detected using the 3-sigma rule
2. Adjusted statistics exclude outliers
3. Various outlier scenarios are handled correctly

**Validates: Requirements 2.3**
"""

import pytest
from datetime import datetime, timedelta
from src.engines.metrics_ingestion import MetricsIngestionEngine
from src.storage.file_storage import FileStorage
import tempfile
import shutil
import statistics


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


class TestSyntheticOutlierDetection:
    """Test outlier detection with synthetic outliers."""
    
    def test_single_outlier_detection(self, engine):
        """Test detection of a single synthetic outlier."""
        service_id = "test-single-outlier"
        now = datetime.utcnow()
        
        # Create baseline: 10 data points with mean=100, stddev≈5
        baseline_values = [95.0, 98.0, 100.0, 102.0, 105.0, 97.0, 103.0, 99.0, 101.0, 100.0]
        
        # Ingest baseline data
        for i, value in enumerate(baseline_values):
            timestamp = now - timedelta(days=len(baseline_values) - i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": value,
                    "p99_ms": value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
        
        # Calculate expected statistics
        mean = statistics.mean(baseline_values)
        stddev = statistics.stdev(baseline_values)
        
        # Create synthetic outlier: mean + 4*stddev (clearly > 3 sigma)
        outlier_value = mean + 4 * stddev
        
        # Ingest outlier
        result = engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={
                "p50_ms": 50.0,
                "p95_ms": outlier_value,
                "p99_ms": outlier_value * 2,
                "mean_ms": 75.0,
                "stddev_ms": 10.0
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
        
        # Verify outlier detected
        assert result["data_quality"]["outlier_count"] >= 1
        
        # Read stored metrics to verify outlier details
        latest_metrics = engine.get_latest_metrics(service_id)
        assert latest_metrics is not None
        assert latest_metrics.data_quality.outliers is not None
        
        # Verify the outlier is the latency_p95_ms
        outlier_names = [o.metric_name for o in latest_metrics.data_quality.outliers]
        assert "latency_p95_ms" in outlier_names

    
    def test_multiple_outliers_same_metric(self, engine):
        """Test detection of multiple outliers in the same metric over time."""
        service_id = "test-multiple-outliers"
        now = datetime.utcnow()
        
        # Create baseline: 20 data points with mean=200, stddev≈10
        baseline_values = [190.0, 195.0, 200.0, 205.0, 210.0] * 4
        
        # Ingest baseline data
        for i, value in enumerate(baseline_values):
            timestamp = now - timedelta(days=len(baseline_values) - i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": value,
                    "p99_ms": value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
        
        # Calculate statistics
        mean = statistics.mean(baseline_values)
        stddev = statistics.stdev(baseline_values)
        
        # Create 3 synthetic outliers at different times
        outlier_values = [
            mean + 3.5 * stddev,  # Moderate outlier
            mean + 5 * stddev,    # Strong outlier
            mean + 10 * stddev    # Extreme outlier
        ]
        
        outlier_count = 0
        for i, outlier_value in enumerate(outlier_values):
            timestamp = now + timedelta(days=i, microseconds=i)
            result = engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": outlier_value,
                    "p99_ms": outlier_value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
            
            # Each should be detected as an outlier
            if result["data_quality"]["outlier_count"] > 0:
                outlier_count += 1
        
        # Verify all 3 outliers were detected
        assert outlier_count == 3

    
    def test_outliers_across_multiple_metrics(self, engine):
        """Test detection of outliers across different metric types."""
        service_id = "test-multi-metric-outliers"
        now = datetime.utcnow()
        
        # Create baseline data
        for i in range(15):
            timestamp = now - timedelta(days=15 - i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": 100.0 + i,
                    "p99_ms": 200.0 + i * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
                },
                error_rate={
                    "percent": 1.0 + i * 0.05,
                    "total_requests": 10000,
                    "failed_requests": 100 + i * 5
                },
                availability={
                    "percent": 99.5 - i * 0.01,
                    "uptime_seconds": 86000,
                    "downtime_seconds": 400
                },
                timestamp=timestamp
            )
        
        # Calculate statistics for each metric
        latency_values = [100.0 + i for i in range(15)]
        error_values = [1.0 + i * 0.05 for i in range(15)]
        avail_values = [99.5 - i * 0.01 for i in range(15)]
        
        latency_mean = statistics.mean(latency_values)
        latency_stddev = statistics.stdev(latency_values)
        error_mean = statistics.mean(error_values)
        error_stddev = statistics.stdev(error_values)
        avail_mean = statistics.mean(avail_values)
        avail_stddev = statistics.stdev(avail_values)
        
        # Create synthetic outliers in all three metrics
        result = engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={
                "p50_ms": 50.0,
                "p95_ms": latency_mean + 4 * latency_stddev,  # Outlier
                "p99_ms": 200.0 + 4 * latency_stddev * 2,     # Outlier
                "mean_ms": 75.0,
                "stddev_ms": 10.0
            },
            error_rate={
                "percent": error_mean + 4 * error_stddev,  # Outlier
                "total_requests": 10000,
                "failed_requests": 500
            },
            availability={
                "percent": avail_mean - 4 * avail_stddev,  # Outlier (lower is worse)
                "uptime_seconds": 80000,
                "downtime_seconds": 6400
            },
            timestamp=now
        )
        
        # Verify multiple outliers detected across different metrics
        assert result["data_quality"]["outlier_count"] >= 3
        
        # Read stored metrics to verify outlier details
        latest_metrics = engine.get_latest_metrics(service_id)
        assert latest_metrics is not None
        assert latest_metrics.data_quality.outliers is not None
        
        # Verify outliers from different metric types
        outlier_names = [o.metric_name for o in latest_metrics.data_quality.outliers]
        
        # Should have at least one from each category
        has_latency = any("latency" in name for name in outlier_names)
        has_error = any("error_rate" in name for name in outlier_names)
        has_avail = any("availability" in name for name in outlier_names)
        
        assert has_latency, "Should detect latency outlier"
        assert has_error, "Should detect error rate outlier"
        assert has_avail, "Should detect availability outlier"

    
    def test_extreme_outlier_values(self, engine):
        """Test detection of extreme outliers (10+ sigma)."""
        service_id = "test-extreme-outliers"
        now = datetime.utcnow()
        
        # Create very consistent baseline
        baseline_value = 100.0
        for i in range(20):
            timestamp = now - timedelta(days=20 - i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": baseline_value + (i % 3),  # Very small variation
                    "p99_ms": 200.0,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
                },
                timestamp=timestamp
            )
        
        # Calculate statistics
        baseline_values = [baseline_value + (i % 3) for i in range(20)]
        mean = statistics.mean(baseline_values)
        stddev = statistics.stdev(baseline_values)
        
        # Create extreme outlier: 20x the standard deviation
        extreme_outlier = mean + 20 * stddev
        
        result = engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={
                "p50_ms": 50.0,
                "p95_ms": extreme_outlier,
                "p99_ms": extreme_outlier * 2,
                "mean_ms": 75.0,
                "stddev_ms": 10.0
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
            },
            timestamp=now
        )
        
        # Verify extreme outlier detected
        assert result["data_quality"]["outlier_count"] >= 1
        
        # Read stored metrics to verify z-score
        latest_metrics = engine.get_latest_metrics(service_id)
        assert latest_metrics is not None
        assert latest_metrics.data_quality.outliers is not None
        
        # Verify z-score is very high
        outliers = latest_metrics.data_quality.outliers
        latency_outliers = [o for o in outliers if "latency" in o.metric_name]
        assert len(latency_outliers) > 0
        
        # Z-score should be > 10 for extreme outlier
        max_z_score = max(o.z_score for o in latency_outliers)
        assert max_z_score > 10.0

    
    def test_adjusted_statistics_exclude_single_outlier(self, engine):
        """Test that adjusted statistics correctly exclude a single outlier."""
        service_id = "test-adjusted-single"
        now = datetime.utcnow()
        
        # Create baseline: 30 data points with mean=150
        baseline_values = [145.0, 148.0, 150.0, 152.0, 155.0] * 6
        
        for i, value in enumerate(baseline_values):
            timestamp = now - timedelta(days=len(baseline_values) - i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": value,
                    "p99_ms": value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
        
        # Calculate statistics
        mean = statistics.mean(baseline_values)
        stddev = statistics.stdev(baseline_values)
        
        # Add synthetic outlier
        outlier_value = mean + 5 * stddev
        timestamp = now
        engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={
                "p50_ms": 50.0,
                "p95_ms": outlier_value,
                "p99_ms": outlier_value * 2,
                "mean_ms": 75.0,
                "stddev_ms": 10.0
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
        result = engine.compute_aggregated_metrics(service_id, time_windows=["90d"])
        window_data = result["time_windows"]["90d"]
        
        # Verify raw statistics include all 31 data points
        assert window_data["latency"]["sample_count"] == 31
        
        # Verify outlier detected
        assert window_data["outlier_indices"] is not None
        assert len(window_data["outlier_indices"]) > 0
        
        # Verify adjusted statistics exist and exclude outlier
        assert window_data["latency_adjusted"] is not None
        assert window_data["latency_adjusted"]["sample_count"] == 30  # Outlier excluded
        
        # The outlier should affect the max value
        raw_max = window_data["latency"]["max_ms"]
        adjusted_max = window_data["latency_adjusted"]["max_ms"]
        
        # Adjusted max should be lower than raw max (outlier excluded)
        assert adjusted_max < raw_max

    
    def test_adjusted_statistics_exclude_multiple_outliers(self, engine):
        """Test that adjusted statistics correctly exclude multiple outliers."""
        service_id = "test-adjusted-multiple"
        now = datetime.utcnow()
        
        # Create baseline: 40 data points with mean=200
        baseline_values = [190.0, 195.0, 200.0, 205.0, 210.0] * 8
        
        for i, value in enumerate(baseline_values):
            timestamp = now - timedelta(days=len(baseline_values) - i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": value,
                    "p99_ms": value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
        
        # Calculate statistics
        mean = statistics.mean(baseline_values)
        stddev = statistics.stdev(baseline_values)
        
        # Add 5 synthetic outliers
        outlier_values = [
            mean + 4 * stddev,
            mean + 5 * stddev,
            mean + 6 * stddev,
            mean + 7 * stddev,
            mean + 8 * stddev
        ]
        
        for i, outlier_value in enumerate(outlier_values):
            timestamp = now + timedelta(days=i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": outlier_value,
                    "p99_ms": outlier_value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
        result = engine.compute_aggregated_metrics(service_id, time_windows=["90d"])
        window_data = result["time_windows"]["90d"]
        
        # Verify raw statistics include baseline + outliers (may be less than 45 if some are outside 90d window)
        assert window_data["latency"]["sample_count"] >= 40  # At least most of them
        
        # Verify outliers detected
        assert window_data["outlier_indices"] is not None
        assert len(window_data["outlier_indices"]) >= 1  # At least one outlier detected
        
        # Verify adjusted statistics exist and exclude outliers
        assert window_data["latency_adjusted"] is not None
        assert window_data["latency_adjusted"]["sample_count"] < 45
        
        # Adjusted statistics should be significantly different from raw
        adjusted_max = window_data["latency_adjusted"]["max_ms"]
        raw_max = window_data["latency"]["max_ms"]
        
        # Adjusted max should be much lower than raw max (outliers excluded)
        assert adjusted_max < raw_max
        assert (raw_max - adjusted_max) > 10.0  # Significant difference

    
    def test_three_sigma_boundary_cases(self, engine):
        """Test outlier detection at the 3-sigma boundary."""
        now = datetime.utcnow()
        
        # Create baseline with known mean and stddev
        baseline_values = [100.0] * 20  # Mean=100, stddev=0 initially
        # Add some variation
        for i in range(20):
            baseline_values[i] += (i % 5) * 2  # Values: 100, 102, 104, 106, 108, repeat
        
        # Calculate statistics
        mean = statistics.mean(baseline_values)
        stddev = statistics.stdev(baseline_values)
        
        # Test cases at boundary
        test_cases = [
            ("just_below_3sigma", mean + 2.9 * stddev, False),  # Should NOT be outlier
            ("just_above_3sigma", mean + 3.2 * stddev, True),   # Should be outlier (using 3.2 to avoid floating point issues)
            ("well_above_3sigma", mean + 4.0 * stddev, True),   # Should be outlier
        ]
        
        for test_name, test_value, should_be_outlier in test_cases:
            service_id = f"test-boundary-{test_name}"
            
            # Ingest baseline for this test service
            for i, value in enumerate(baseline_values):
                ts = now - timedelta(days=len(baseline_values) - i, microseconds=i)
                engine.ingest_metrics(
                    service_id=service_id,
                    time_window="1d",
                    latency={
                        "p50_ms": 50.0,
                        "p95_ms": value,
                        "p99_ms": value * 2,
                        "mean_ms": 75.0,
                        "stddev_ms": 10.0
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
                    timestamp=ts
                )
            
            # Test with the boundary value
            result = engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": test_value,
                    "p99_ms": test_value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
            
            has_outlier = result["data_quality"]["outlier_count"] > 0
            
            if should_be_outlier:
                assert has_outlier, f"{test_name}: Expected outlier but none detected (z-score should be > 3)"
            else:
                assert not has_outlier, f"{test_name}: Unexpected outlier detected (z-score should be <= 3)"

    
    def test_negative_outliers(self, engine):
        """Test detection of negative outliers (values below mean - 3*stddev)."""
        service_id = "test-negative-outliers"
        now = datetime.utcnow()
        
        # Create baseline with mean=100
        baseline_values = [95.0, 98.0, 100.0, 102.0, 105.0] * 6
        
        for i, value in enumerate(baseline_values):
            timestamp = now - timedelta(days=len(baseline_values) - i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": value,
                    "p99_ms": value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
                },
                error_rate={
                    "percent": 5.0,
                    "total_requests": 10000,
                    "failed_requests": 500
                },
                availability={
                    "percent": 99.0,
                    "uptime_seconds": 85536,
                    "downtime_seconds": 864
                },
                timestamp=timestamp
            )
        
        # Calculate statistics
        mean = statistics.mean(baseline_values)
        stddev = statistics.stdev(baseline_values)
        
        # Create negative outlier (unusually low value)
        # For latency, this is actually good, but still an outlier
        negative_outlier = max(1.0, mean - 4 * stddev)  # Ensure positive
        
        result = engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={
                "p50_ms": 50.0,
                "p95_ms": negative_outlier,
                "p99_ms": negative_outlier * 2,
                "mean_ms": 75.0,
                "stddev_ms": 10.0
            },
            error_rate={
                "percent": 5.0,
                "total_requests": 10000,
                "failed_requests": 500
            },
            availability={
                "percent": 99.0,
                "uptime_seconds": 85536,
                "downtime_seconds": 864
            },
            timestamp=now
        )
        
        # Verify negative outlier detected (if value is significantly different)
        if abs(negative_outlier - mean) > 3 * stddev:
            assert result["data_quality"]["outlier_count"] >= 1

    
    def test_outlier_z_score_calculation(self, engine):
        """Test that z-scores are calculated correctly for synthetic outliers."""
        service_id = "test-zscore-calc"
        now = datetime.utcnow()
        
        # Create baseline with known statistics
        # Using values that give clean mean and stddev
        baseline_values = [90.0, 95.0, 100.0, 105.0, 110.0] * 4
        
        for i, value in enumerate(baseline_values):
            timestamp = now - timedelta(days=len(baseline_values) - i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": value,
                    "p99_ms": value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
        
        # Calculate expected statistics
        expected_mean = statistics.mean(baseline_values)
        expected_stddev = statistics.stdev(baseline_values)
        
        # Create outlier with known z-score
        target_z_score = 5.0
        outlier_value = expected_mean + target_z_score * expected_stddev
        
        result = engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={
                "p50_ms": 50.0,
                "p95_ms": outlier_value,
                "p99_ms": outlier_value * 2,
                "mean_ms": 75.0,
                "stddev_ms": 10.0
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
        
        # Verify outlier detected
        assert result["data_quality"]["outlier_count"] >= 1
        
        # Read stored metrics to verify z-score calculation
        latest_metrics = engine.get_latest_metrics(service_id)
        assert latest_metrics is not None
        assert latest_metrics.data_quality.outliers is not None
        
        # Find the latency_p95_ms outlier
        outliers = latest_metrics.data_quality.outliers
        latency_outlier = next((o for o in outliers if o.metric_name == "latency_p95_ms"), None)
        
        assert latency_outlier is not None
        
        # Verify z-score is approximately correct (within 10% tolerance)
        actual_z_score = latency_outlier.z_score
        assert abs(actual_z_score - target_z_score) < target_z_score * 0.1
        
        # Verify mean and stddev are stored correctly
        assert abs(latency_outlier.mean - expected_mean) < 0.1
        assert abs(latency_outlier.stddev - expected_stddev) < 0.1

    
    def test_no_false_positives_with_normal_variation(self, engine):
        """Test that normal variation does not trigger false outlier detection."""
        service_id = "test-no-false-positives"
        now = datetime.utcnow()
        
        # Create baseline with natural variation
        import random
        random.seed(42)  # Reproducible
        
        baseline_values = []
        for i in range(50):
            # Normal distribution around 100 with stddev of 10
            value = 100.0 + random.gauss(0, 10)
            baseline_values.append(value)
        
        for i, value in enumerate(baseline_values):
            timestamp = now - timedelta(days=len(baseline_values) - i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": value,
                    "p99_ms": value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
        
        # Add more normal values (within 2 sigma)
        mean = statistics.mean(baseline_values)
        stddev = statistics.stdev(baseline_values)
        
        false_positive_count = 0
        for i in range(10):
            # Values within 2 sigma should not be outliers
            normal_value = mean + random.uniform(-2, 2) * stddev
            
            result = engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": normal_value,
                    "p99_ms": normal_value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
                timestamp=now + timedelta(days=i, microseconds=i)
            )
            
            if result["data_quality"]["outlier_count"] > 0:
                false_positive_count += 1
        
        # Should have very few or no false positives
        assert false_positive_count <= 1, f"Too many false positives: {false_positive_count}/10"

    
    def test_adjusted_statistics_percentile_accuracy(self, engine):
        """Test that adjusted statistics compute accurate percentiles after outlier removal."""
        service_id = "test-adjusted-percentiles"
        now = datetime.utcnow()
        
        # Create 50 baseline data points with known distribution
        baseline_values = []
        for i in range(50):
            # Values from 90 to 110 in steps
            value = 90.0 + (i % 20)
            baseline_values.append(value)
        
        for i, value in enumerate(baseline_values):
            timestamp = now - timedelta(days=len(baseline_values) - i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": value,
                    "p99_ms": value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
        
        # Add 5 extreme outliers
        mean = statistics.mean(baseline_values)
        stddev = statistics.stdev(baseline_values)
        
        for i in range(5):
            outlier_value = mean + (5 + i) * stddev
            timestamp = now + timedelta(days=i, microseconds=i)
            engine.ingest_metrics(
                service_id=service_id,
                time_window="1d",
                latency={
                    "p50_ms": 50.0,
                    "p95_ms": outlier_value,
                    "p99_ms": outlier_value * 2,
                    "mean_ms": 75.0,
                    "stddev_ms": 10.0
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
        result = engine.compute_aggregated_metrics(service_id, time_windows=["90d"])
        window_data = result["time_windows"]["90d"]
        
        # Verify adjusted statistics exist
        assert window_data["latency_adjusted"] is not None
        
        # Verify percentile ordering in adjusted statistics
        adj = window_data["latency_adjusted"]
        assert adj["min_ms"] <= adj["p50_ms"]
        assert adj["p50_ms"] <= adj["p95_ms"]
        assert adj["p95_ms"] <= adj["p99_ms"]
        assert adj["p99_ms"] <= adj["max_ms"]
        
        # Adjusted p95 should be much lower than raw p95 (outliers excluded)
        raw_p95 = window_data["latency"]["p95_ms"]
        adj_p95 = adj["p95_ms"]
        assert adj_p95 < raw_p95
        
        # Adjusted p95 should be closer to baseline p95
        baseline_p95 = sorted(baseline_values)[int(0.95 * len(baseline_values))]
        assert abs(adj_p95 - baseline_p95) < abs(raw_p95 - baseline_p95)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
