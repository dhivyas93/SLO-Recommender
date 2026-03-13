"""
Unit tests for tier generation in RecommendationEngine.
"""

import pytest
from datetime import datetime, timedelta

from src.engines.recommendation_engine import RecommendationEngine
from src.engines.metrics_ingestion import MetricsIngestionEngine
from src.storage.file_storage import FileStorage


@pytest.fixture
def test_data_dir(tmp_path):
    """Create a temporary data directory for tests."""
    data_dir = tmp_path / "test_tier_gen"
    data_dir.mkdir()
    return data_dir


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


def create_service_with_metrics(metrics_engine, service_id, latency_base=180, availability_base=99.6, error_rate_base=0.8):
    """Helper to create a service with historical metrics."""
    base_time = datetime.utcnow() - timedelta(days=29)
    
    for i in range(30):
        timestamp = base_time + timedelta(days=i)
        metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="30d",
            latency={
                "p50_ms": latency_base - 100 + (i % 5),
                "p95_ms": latency_base + (i % 10),
                "p99_ms": latency_base + 170 + (i % 15),
                "mean_ms": latency_base - 85 + (i % 5),
                "stddev_ms": 45
            },
            error_rate={
                "percent": error_rate_base + (i % 3) * 0.1,
                "total_requests": 1000000,
                "failed_requests": int(error_rate_base * 10000) + (i % 3) * 1000
            },
            availability={
                "percent": availability_base - (i % 3) * 0.1,
                "uptime_seconds": 86054,
                "downtime_seconds": 346
            },
            timestamp=timestamp
        )
    
    metrics_engine.compute_aggregated_metrics(service_id, time_windows=["30d"])


class TestTierGeneration:
    """Test tier generation functionality."""
    
    def test_generate_tiers_basic(self, recommendation_engine, metrics_engine):
        """Test basic tier generation with typical metrics."""
        service_id = "test-service-basic"
        create_service_with_metrics(metrics_engine, service_id)
        
        constrained_recs = {
            "availability": 99.0,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.generate_tiers(
            service_id=service_id,
            constrained_recommendations=constrained_recs,
            time_window="30d"
        )
        
        # Verify structure
        assert "tiers" in result
        assert "metadata" in result
        assert "aggressive" in result["tiers"]
        assert "balanced" in result["tiers"]
        assert "conservative" in result["tiers"]
        
        # Verify balanced tier matches constrained recommendations
        balanced = result["tiers"]["balanced"]
        assert balanced["availability"] == constrained_recs["availability"]
        assert balanced["latency_p95_ms"] == constrained_recs["latency_p95_ms"]
        assert balanced["latency_p99_ms"] == constrained_recs["latency_p99_ms"]
        assert balanced["error_rate_percent"] == constrained_recs["error_rate_percent"]
    
    def test_tier_ordering_availability(self, recommendation_engine, metrics_engine):
        """Test that availability ordering is correct: aggressive >= balanced >= conservative."""
        service_id = "test-service-avail"
        create_service_with_metrics(metrics_engine, service_id)
        
        constrained_recs = {
            "availability": 99.0,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.generate_tiers(
            service_id=service_id,
            constrained_recommendations=constrained_recs,
            time_window="30d"
        )
        
        tiers = result["tiers"]
        aggressive = tiers["aggressive"]
        balanced = tiers["balanced"]
        conservative = tiers["conservative"]
        
        # Availability: aggressive >= balanced >= conservative (higher is better)
        assert aggressive["availability"] >= balanced["availability"]
        assert balanced["availability"] >= conservative["availability"]
    
    def test_tier_ordering_latency(self, recommendation_engine, metrics_engine):
        """Test that latency ordering is correct: aggressive <= balanced <= conservative."""
        service_id = "test-service-latency"
        create_service_with_metrics(metrics_engine, service_id)
        
        constrained_recs = {
            "availability": 99.0,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.generate_tiers(
            service_id=service_id,
            constrained_recommendations=constrained_recs,
            time_window="30d"
        )
        
        tiers = result["tiers"]
        aggressive = tiers["aggressive"]
        balanced = tiers["balanced"]
        conservative = tiers["conservative"]
        
        # Latency: aggressive <= balanced <= conservative (lower is better)
        assert aggressive["latency_p95_ms"] <= balanced["latency_p95_ms"]
        assert balanced["latency_p95_ms"] <= conservative["latency_p95_ms"]
        assert aggressive["latency_p99_ms"] <= balanced["latency_p99_ms"]
        assert balanced["latency_p99_ms"] <= conservative["latency_p99_ms"]
    
    def test_tier_ordering_error_rate(self, recommendation_engine, metrics_engine):
        """Test that error rate ordering is correct: aggressive <= balanced <= conservative."""
        service_id = "test-service-error"
        create_service_with_metrics(metrics_engine, service_id)
        
        constrained_recs = {
            "availability": 99.0,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.generate_tiers(
            service_id=service_id,
            constrained_recommendations=constrained_recs,
            time_window="30d"
        )
        
        tiers = result["tiers"]
        aggressive = tiers["aggressive"]
        balanced = tiers["balanced"]
        conservative = tiers["conservative"]
        
        # Error rate: aggressive <= balanced <= conservative (lower is better)
        assert aggressive["error_rate_percent"] <= balanced["error_rate_percent"]
        assert balanced["error_rate_percent"] <= conservative["error_rate_percent"]
    
    def test_aggressive_constrained_recommendations(self, recommendation_engine, metrics_engine):
        """Test tier generation when constrained recommendations are more aggressive than historical."""
        service_id = "test-service-aggressive-constrained"
        # Create service with higher latency
        create_service_with_metrics(metrics_engine, service_id, latency_base=300, availability_base=98.5, error_rate_base=2.0)
        
        # Constrained recommendations are very aggressive (better than historical)
        constrained_recs = {
            "availability": 99.5,  # Higher than historical
            "latency_p95_ms": 100.0,  # Lower than historical
            "latency_p99_ms": 200.0,  # Lower than historical
            "error_rate_percent": 0.5  # Lower than historical
        }
        
        result = recommendation_engine.generate_tiers(
            service_id=service_id,
            constrained_recommendations=constrained_recs,
            time_window="30d"
        )
        
        tiers = result["tiers"]
        aggressive = tiers["aggressive"]
        balanced = tiers["balanced"]
        conservative = tiers["conservative"]
        
        # Aggressive tier should match balanced tier (since constrained is already aggressive)
        assert aggressive["availability"] >= balanced["availability"]
        assert aggressive["latency_p95_ms"] <= balanced["latency_p95_ms"]
        assert aggressive["latency_p99_ms"] <= balanced["latency_p99_ms"]
        assert aggressive["error_rate_percent"] <= balanced["error_rate_percent"]
        
        # Conservative tier should be based on historical p95
        assert conservative["availability"] <= balanced["availability"]
        assert conservative["latency_p95_ms"] >= balanced["latency_p95_ms"]
        assert conservative["latency_p99_ms"] >= balanced["latency_p99_ms"]
        assert conservative["error_rate_percent"] >= balanced["error_rate_percent"]
    
    def test_conservative_constrained_recommendations(self, recommendation_engine, metrics_engine):
        """Test tier generation when constrained recommendations are more conservative than historical."""
        service_id = "test-service-conservative-constrained"
        # Create service with low latency
        create_service_with_metrics(metrics_engine, service_id, latency_base=100, availability_base=99.9, error_rate_base=0.5)
        
        # Constrained recommendations are very conservative (worse than historical)
        constrained_recs = {
            "availability": 98.0,  # Lower than historical
            "latency_p95_ms": 500.0,  # Higher than historical
            "latency_p99_ms": 800.0,  # Higher than historical
            "error_rate_percent": 5.0  # Higher than historical
        }
        
        result = recommendation_engine.generate_tiers(
            service_id=service_id,
            constrained_recommendations=constrained_recs,
            time_window="30d"
        )
        
        tiers = result["tiers"]
        aggressive = tiers["aggressive"]
        balanced = tiers["balanced"]
        conservative = tiers["conservative"]
        
        # Aggressive tier should be based on historical p75
        assert aggressive["availability"] >= balanced["availability"]
        assert aggressive["latency_p95_ms"] <= balanced["latency_p95_ms"]
        assert aggressive["latency_p99_ms"] <= balanced["latency_p99_ms"]
        assert aggressive["error_rate_percent"] <= balanced["error_rate_percent"]
        
        # Conservative tier should match balanced tier (since constrained is already conservative)
        assert conservative["availability"] <= balanced["availability"]
        assert conservative["latency_p95_ms"] >= balanced["latency_p95_ms"]
        assert conservative["latency_p99_ms"] >= balanced["latency_p99_ms"]
        assert conservative["error_rate_percent"] >= balanced["error_rate_percent"]
    
    def test_metadata_structure(self, recommendation_engine, metrics_engine):
        """Test that metadata contains expected information."""
        service_id = "test-service-metadata"
        create_service_with_metrics(metrics_engine, service_id)
        
        constrained_recs = {
            "availability": 99.0,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.generate_tiers(
            service_id=service_id,
            constrained_recommendations=constrained_recs,
            time_window="30d"
        )
        
        metadata = result["metadata"]
        
        # Verify metadata structure
        assert metadata["service_id"] == service_id
        assert metadata["time_window"] == "30d"
        assert "generated_at" in metadata
        assert "tier_definitions" in metadata
        assert "historical_percentiles" in metadata
        assert "ordering_enforced" in metadata
        assert "data_quality" in metadata
        
        # Verify tier definitions
        tier_defs = metadata["tier_definitions"]
        assert "aggressive" in tier_defs
        assert "balanced" in tier_defs
        assert "conservative" in tier_defs
        
        # Verify historical percentiles
        hist_percentiles = metadata["historical_percentiles"]
        assert "availability" in hist_percentiles
        assert "latency_p95" in hist_percentiles
        assert "latency_p99" in hist_percentiles
        assert "error_rate" in hist_percentiles
    
    def test_missing_service_metrics(self, recommendation_engine):
        """Test that appropriate error is raised when service has no metrics."""
        service_id = "nonexistent-service"
        
        constrained_recs = {
            "availability": 99.0,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 1.0
        }
        
        with pytest.raises(ValueError, match="No aggregated metrics found"):
            recommendation_engine.generate_tiers(
                service_id=service_id,
                constrained_recommendations=constrained_recs,
                time_window="30d"
            )
    
    def test_invalid_time_window(self, recommendation_engine, metrics_engine):
        """Test that appropriate error is raised for invalid time window."""
        service_id = "test-service-invalid-window"
        create_service_with_metrics(metrics_engine, service_id)
        
        constrained_recs = {
            "availability": 99.0,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 1.0
        }
        
        with pytest.raises(ValueError, match="Time window .* not found"):
            recommendation_engine.generate_tiers(
                service_id=service_id,
                constrained_recommendations=constrained_recs,
                time_window="90d"  # Not computed
            )
