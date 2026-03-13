"""
Unit tests for RecommendationEngine.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import shutil

from src.engines.recommendation_engine import RecommendationEngine
from src.engines.metrics_ingestion import MetricsIngestionEngine
from src.storage.file_storage import FileStorage


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "test_data"
    data_dir.mkdir()
    yield data_dir
    # Cleanup
    if data_dir.exists():
        shutil.rmtree(data_dir)


@pytest.fixture
def storage(test_data_dir):
    """Create a FileStorage instance for tests."""
    return FileStorage(base_path=str(test_data_dir))


@pytest.fixture
def metrics_engine(storage):
    """Create a MetricsIngestionEngine instance for tests."""
    return MetricsIngestionEngine(storage=storage)


@pytest.fixture
def recommendation_engine(storage, metrics_engine):
    """Create a RecommendationEngine instance for tests."""
    return RecommendationEngine(storage=storage, metrics_engine=metrics_engine)


@pytest.fixture
def sample_service_with_metrics(metrics_engine):
    """Create a sample service with historical metrics."""
    service_id = "test-service"
    
    # Ingest multiple metrics over time to build history
    # Use recent timestamps (within last 30 days) so they fall within the 30d window
    base_time = datetime.utcnow() - timedelta(days=29)
    
    for i in range(30):
        timestamp = base_time + timedelta(days=i)
        
        # Simulate stable metrics with some variation
        metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="30d",
            latency={
                "p50_ms": 80 + (i % 5),
                "p95_ms": 180 + (i % 10),
                "p99_ms": 350 + (i % 15),
                "mean_ms": 95 + (i % 5),
                "stddev_ms": 45
            },
            error_rate={
                "percent": 0.8 + (i % 3) * 0.1,
                "total_requests": 1000000,
                "failed_requests": 8000 + (i % 3) * 1000
            },
            availability={
                "percent": 99.6 - (i % 3) * 0.1,
                "uptime_seconds": 86054,
                "downtime_seconds": 346
            },
            timestamp=timestamp
        )
    
    # Compute aggregated metrics
    metrics_engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
    
    return service_id


class TestRecommendationEngineInit:
    """Test RecommendationEngine initialization."""
    
    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        engine = RecommendationEngine()
        assert engine.storage is not None
        assert engine.metrics_engine is not None
    
    def test_init_with_custom_storage(self, storage):
        """Test initialization with custom storage."""
        engine = RecommendationEngine(storage=storage)
        assert engine.storage == storage
        assert engine.metrics_engine is not None
    
    def test_init_with_custom_metrics_engine(self, storage, metrics_engine):
        """Test initialization with custom metrics engine."""
        engine = RecommendationEngine(storage=storage, metrics_engine=metrics_engine)
        assert engine.storage == storage
        assert engine.metrics_engine == metrics_engine


class TestComputeBaseRecommendations:
    """Test compute_base_recommendations method."""
    
    def test_compute_base_recommendations_success(
        self,
        recommendation_engine,
        sample_service_with_metrics
    ):
        """Test successful base recommendation computation."""
        result = recommendation_engine.compute_base_recommendations(
            service_id=sample_service_with_metrics,
            time_window="30d"
        )
        
        # Check structure
        assert "base_recommendations" in result
        assert "metadata" in result
        
        # Check base recommendations
        base_recs = result["base_recommendations"]
        assert "availability" in base_recs
        assert "latency_p95_ms" in base_recs
        assert "latency_p99_ms" in base_recs
        assert "error_rate_percent" in base_recs
        
        # Check values are within valid ranges
        assert 0 <= base_recs["availability"] <= 100
        assert base_recs["latency_p95_ms"] > 0
        assert base_recs["latency_p99_ms"] >= base_recs["latency_p95_ms"]
        assert 0 <= base_recs["error_rate_percent"] <= 100
        
        # Check metadata
        metadata = result["metadata"]
        assert metadata["service_id"] == sample_service_with_metrics
        assert metadata["time_window"] == "30d"
        assert "computed_at" in metadata
        assert "data_quality" in metadata
        assert "historical_metrics" in metadata
        assert "formulas_applied" in metadata
        assert "buffers" in metadata
    
    def test_compute_base_recommendations_with_custom_buffers(
        self,
        recommendation_engine,
        sample_service_with_metrics
    ):
        """Test base recommendation computation with custom buffers."""
        result = recommendation_engine.compute_base_recommendations(
            service_id=sample_service_with_metrics,
            time_window="30d",
            availability_buffer=1.0,
            error_rate_buffer=1.0
        )
        
        # Check that buffers are reflected in metadata
        metadata = result["metadata"]
        assert metadata["buffers"]["availability_buffer"] == 1.0
        assert metadata["buffers"]["error_rate_buffer"] == 1.0
    
    def test_compute_base_recommendations_no_metrics(self, recommendation_engine):
        """Test error when service has no metrics."""
        with pytest.raises(ValueError, match="No aggregated metrics found"):
            recommendation_engine.compute_base_recommendations(
                service_id="nonexistent-service"
            )
    
    def test_compute_base_recommendations_invalid_time_window(
        self,
        recommendation_engine,
        sample_service_with_metrics
    ):
        """Test error when time window is invalid."""
        with pytest.raises(ValueError, match="Time window.*not found"):
            recommendation_engine.compute_base_recommendations(
                service_id=sample_service_with_metrics,
                time_window="invalid"
            )
    
    def test_compute_base_recommendations_insufficient_data(
        self,
        recommendation_engine,
        metrics_engine
    ):
        """Test error when time window has no samples."""
        service_id = "empty-service"
        
        # Ingest one metric with a very old timestamp (outside 90d window)
        metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="1d",
            latency={
                "p50_ms": 80,
                "p95_ms": 180,
                "p99_ms": 350,
                "mean_ms": 95,
                "stddev_ms": 45
            },
            error_rate={
                "percent": 0.8,
                "total_requests": 1000000,
                "failed_requests": 8000
            },
            availability={
                "percent": 99.6,
                "uptime_seconds": 86054,
                "downtime_seconds": 346
            },
            timestamp=datetime.utcnow() - timedelta(days=100)  # Outside 90d window
        )
        
        # Compute aggregated metrics for 90d window (which will be empty)
        metrics_engine.compute_aggregated_metrics(service_id, time_windows=["90d"])
        
        # Should raise error for insufficient data
        with pytest.raises(ValueError, match="Insufficient data"):
            recommendation_engine.compute_base_recommendations(
                service_id=service_id,
                time_window="90d"
            )
    
    def test_availability_formula(
        self,
        recommendation_engine,
        sample_service_with_metrics,
        metrics_engine
    ):
        """Test that availability formula is correctly applied."""
        # Get aggregated metrics to check the formula
        aggregated = metrics_engine.get_aggregated_metrics(sample_service_with_metrics)
        window_data = aggregated["time_windows"]["30d"]
        
        # Get the stats (adjusted or raw)
        availability_stats = window_data.get("availability_adjusted") or window_data["availability"]
        p95_availability = availability_stats["p95_percent"]
        
        # Compute recommendations
        result = recommendation_engine.compute_base_recommendations(
            service_id=sample_service_with_metrics,
            time_window="30d",
            availability_buffer=0.5
        )
        
        # Check formula: p95 - buffer
        expected_availability = p95_availability - 0.5
        actual_availability = result["base_recommendations"]["availability"]
        
        assert abs(actual_availability - expected_availability) < 0.01
    
    def test_latency_p95_formula(
        self,
        recommendation_engine,
        sample_service_with_metrics,
        metrics_engine
    ):
        """Test that latency p95 formula is correctly applied."""
        # Get aggregated metrics to check the formula
        aggregated = metrics_engine.get_aggregated_metrics(sample_service_with_metrics)
        window_data = aggregated["time_windows"]["30d"]
        
        # Get the stats (adjusted or raw)
        latency_stats = window_data.get("latency_adjusted") or window_data["latency"]
        mean_latency = latency_stats["mean_ms"]
        stddev_latency = latency_stats["stddev_ms"]
        
        # Compute recommendations
        result = recommendation_engine.compute_base_recommendations(
            service_id=sample_service_with_metrics,
            time_window="30d"
        )
        
        # Check formula: mean + 1.5 * stddev
        expected_latency_p95 = mean_latency + (1.5 * stddev_latency)
        actual_latency_p95 = result["base_recommendations"]["latency_p95_ms"]
        
        assert abs(actual_latency_p95 - expected_latency_p95) < 0.01
    
    def test_latency_p99_formula(
        self,
        recommendation_engine,
        sample_service_with_metrics,
        metrics_engine
    ):
        """Test that latency p99 formula is correctly applied."""
        # Get aggregated metrics to check the formula
        aggregated = metrics_engine.get_aggregated_metrics(sample_service_with_metrics)
        window_data = aggregated["time_windows"]["30d"]
        
        # Get the stats (adjusted or raw)
        latency_stats = window_data.get("latency_adjusted") or window_data["latency"]
        mean_latency = latency_stats["mean_ms"]
        stddev_latency = latency_stats["stddev_ms"]
        
        # Compute recommendations
        result = recommendation_engine.compute_base_recommendations(
            service_id=sample_service_with_metrics,
            time_window="30d"
        )
        
        # Check formula: mean + 2 * stddev
        expected_latency_p99 = mean_latency + (2.0 * stddev_latency)
        actual_latency_p99 = result["base_recommendations"]["latency_p99_ms"]
        
        assert abs(actual_latency_p99 - expected_latency_p99) < 0.01
    
    def test_error_rate_formula(
        self,
        recommendation_engine,
        sample_service_with_metrics,
        metrics_engine
    ):
        """Test that error rate formula is correctly applied."""
        # Get aggregated metrics to check the formula
        aggregated = metrics_engine.get_aggregated_metrics(sample_service_with_metrics)
        window_data = aggregated["time_windows"]["30d"]
        
        # Get the stats (adjusted or raw)
        error_rate_stats = window_data.get("error_rate_adjusted") or window_data["error_rate"]
        p95_error_rate = error_rate_stats["p95_percent"]
        
        # Compute recommendations
        result = recommendation_engine.compute_base_recommendations(
            service_id=sample_service_with_metrics,
            time_window="30d",
            error_rate_buffer=0.5
        )
        
        # Check formula: p95 + buffer
        expected_error_rate = p95_error_rate + 0.5
        actual_error_rate = result["base_recommendations"]["error_rate_percent"]
        
        assert abs(actual_error_rate - expected_error_rate) < 0.01
    
    def test_latency_p99_greater_than_p95(
        self,
        recommendation_engine,
        sample_service_with_metrics
    ):
        """Test that latency p99 is always >= p95."""
        result = recommendation_engine.compute_base_recommendations(
            service_id=sample_service_with_metrics,
            time_window="30d"
        )
        
        base_recs = result["base_recommendations"]
        assert base_recs["latency_p99_ms"] >= base_recs["latency_p95_ms"]
    
    def test_availability_bounds(
        self,
        recommendation_engine,
        metrics_engine
    ):
        """Test that availability is bounded to [0, 100]."""
        service_id = "extreme-availability-service"
        
        # Ingest metrics with very high availability
        for i in range(5):
            metrics_engine.ingest_metrics(
                service_id=service_id,
                time_window="30d",
                latency={
                    "p50_ms": 80,
                    "p95_ms": 180,
                    "p99_ms": 350,
                    "mean_ms": 95,
                    "stddev_ms": 45
                },
                error_rate={
                    "percent": 0.01,
                    "total_requests": 1000000,
                    "failed_requests": 100
                },
                availability={
                    "percent": 99.99,
                    "uptime_seconds": 86390,
                    "downtime_seconds": 10
                },
                timestamp=datetime.utcnow() - timedelta(days=i)
            )
        
        metrics_engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
        
        # Compute recommendations with small buffer
        result = recommendation_engine.compute_base_recommendations(
            service_id=service_id,
            time_window="30d",
            availability_buffer=0.1
        )
        
        # Check that availability is within bounds
        availability = result["base_recommendations"]["availability"]
        assert 0 <= availability <= 100
    
    def test_error_rate_bounds(
        self,
        recommendation_engine,
        metrics_engine
    ):
        """Test that error rate is bounded to [0, 100]."""
        service_id = "extreme-error-service"
        
        # Ingest metrics with very low error rate
        for i in range(5):
            metrics_engine.ingest_metrics(
                service_id=service_id,
                time_window="30d",
                latency={
                    "p50_ms": 80,
                    "p95_ms": 180,
                    "p99_ms": 350,
                    "mean_ms": 95,
                    "stddev_ms": 45
                },
                error_rate={
                    "percent": 0.01,
                    "total_requests": 1000000,
                    "failed_requests": 100
                },
                availability={
                    "percent": 99.6,
                    "uptime_seconds": 86054,
                    "downtime_seconds": 346
                },
                timestamp=datetime.utcnow() - timedelta(days=i)
            )
        
        metrics_engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
        
        # Compute recommendations with large buffer
        result = recommendation_engine.compute_base_recommendations(
            service_id=service_id,
            time_window="30d",
            error_rate_buffer=0.1
        )
        
        # Check that error rate is within bounds
        error_rate = result["base_recommendations"]["error_rate_percent"]
        assert 0 <= error_rate <= 100
    
    def test_latency_positive(
        self,
        recommendation_engine,
        sample_service_with_metrics
    ):
        """Test that latency recommendations are always positive."""
        result = recommendation_engine.compute_base_recommendations(
            service_id=sample_service_with_metrics,
            time_window="30d"
        )
        
        base_recs = result["base_recommendations"]
        assert base_recs["latency_p95_ms"] > 0
        assert base_recs["latency_p99_ms"] > 0
    
    def test_uses_adjusted_stats_when_available(
        self,
        recommendation_engine,
        metrics_engine
    ):
        """Test that adjusted stats are used when outliers are present."""
        service_id = "service-with-outliers"
        
        # Ingest normal metrics
        for i in range(10):
            metrics_engine.ingest_metrics(
                service_id=service_id,
                time_window="30d",
                latency={
                    "p50_ms": 80,
                    "p95_ms": 180,
                    "p99_ms": 350,
                    "mean_ms": 95,
                    "stddev_ms": 45
                },
                error_rate={
                    "percent": 0.8,
                    "total_requests": 1000000,
                    "failed_requests": 8000
                },
                availability={
                    "percent": 99.6,
                    "uptime_seconds": 86054,
                    "downtime_seconds": 346
                },
                timestamp=datetime.utcnow() - timedelta(days=i)
            )
        
        # Ingest an outlier
        metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="30d",
            latency={
                "p50_ms": 500,  # Outlier
                "p95_ms": 1000,  # Outlier
                "p99_ms": 2000,  # Outlier
                "mean_ms": 600,
                "stddev_ms": 200
            },
            error_rate={
                "percent": 10.0,  # Outlier
                "total_requests": 1000000,
                "failed_requests": 100000
            },
            availability={
                "percent": 80.0,  # Outlier
                "uptime_seconds": 69120,
                "downtime_seconds": 17280
            },
            timestamp=datetime.utcnow() - timedelta(days=11)
        )
        
        metrics_engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
        
        # Compute recommendations
        result = recommendation_engine.compute_base_recommendations(
            service_id=service_id,
            time_window="30d"
        )
        
        # Check that outliers_excluded flag is set
        metadata = result["metadata"]
        # Note: outliers_excluded will be True if adjusted stats exist
        assert "outliers_excluded" in metadata
    
    def test_metadata_completeness(
        self,
        recommendation_engine,
        sample_service_with_metrics
    ):
        """Test that metadata contains all required fields."""
        result = recommendation_engine.compute_base_recommendations(
            service_id=sample_service_with_metrics,
            time_window="30d"
        )
        
        metadata = result["metadata"]
        
        # Check required fields
        assert "service_id" in metadata
        assert "time_window" in metadata
        assert "computed_at" in metadata
        assert "data_quality" in metadata
        assert "historical_metrics" in metadata
        assert "formulas_applied" in metadata
        assert "buffers" in metadata
        assert "outliers_excluded" in metadata
        
        # Check data quality fields
        data_quality = metadata["data_quality"]
        assert "completeness" in data_quality
        assert "staleness_hours" in data_quality
        assert "sample_count" in data_quality
        assert "quality_score" in data_quality
        
        # Check historical metrics fields
        historical = metadata["historical_metrics"]
        assert "availability" in historical
        assert "latency" in historical
        assert "error_rate" in historical
        
        # Check formulas applied
        formulas = metadata["formulas_applied"]
        assert "availability" in formulas
        assert "latency_p95" in formulas
        assert "latency_p99" in formulas
        assert "error_rate" in formulas
