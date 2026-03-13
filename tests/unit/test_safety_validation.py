"""
Unit tests for safety validation in RecommendationEngine.

Tests the safety guardrails that ensure recommendations are:
1. Achievable based on historical performance
2. Meeting minimum threshold requirements
3. Consistent across dependency chains
"""

import pytest
from datetime import datetime, timedelta
from src.engines.recommendation_engine import RecommendationEngine
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


@pytest.fixture
def recommendation_engine(temp_storage, metrics_engine):
    """Create RecommendationEngine with temporary storage."""
    return RecommendationEngine(storage=temp_storage, metrics_engine=metrics_engine)


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


class TestValidateAchievability:
    """Test achievability validation."""
    
    def test_achievable_recommendations_no_adjustments(self, recommendation_engine, metrics_engine):
        """Test that achievable recommendations require no adjustments."""
        service_id = "test-service-achievable"
        create_service_with_metrics(metrics_engine, service_id)
        
        # Create recommendations that are achievable (based on historical data)
        recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.validate_achievability(
            service_id=service_id,
            recommendations=recommendations,
            time_window="30d"
        )
        
        # Should not require adjustments
        validated = result["validated_recommendations"]
        assert validated["availability"] == recommendations["availability"]
        assert validated["latency_p95_ms"] == recommendations["latency_p95_ms"]
        assert validated["latency_p99_ms"] == recommendations["latency_p99_ms"]
        assert validated["error_rate_percent"] == recommendations["error_rate_percent"]
        
        # Should indicate no adjustments needed
        assert "No adjustments needed" in result["adjustments_made"][0]
        assert len(result["warnings"]) == 0
    
    def test_availability_exceeds_historical_p99(self, recommendation_engine, metrics_engine):
        """Test that availability exceeding historical p99 is adjusted."""
        service_id = "test-service-high-avail"
        create_service_with_metrics(metrics_engine, service_id, availability_base=95.0)
        
        # Create recommendations with unrealistic availability
        recommendations = {
            "availability": 99.99,  # Much higher than historical (95%)
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.validate_achievability(
            service_id=service_id,
            recommendations=recommendations,
            time_window="30d",
            availability_max_increase=1.0
        )
        
        # Should be adjusted
        validated = result["validated_recommendations"]
        assert validated["availability"] < recommendations["availability"]
        assert validated["availability"] <= 95.0 + 1.0  # historical p99 + max_increase
        
        # Should have adjustment and warning
        assert len(result["adjustments_made"]) > 0
        assert any("Availability adjusted" in adj for adj in result["adjustments_made"])
        assert len(result["warnings"]) > 0
        assert any("exceeds" in w.lower() for w in result["warnings"])
    
    def test_latency_p95_too_aggressive(self, recommendation_engine, metrics_engine):
        """Test that latency p95 below historical p50 is adjusted."""
        service_id = "test-service-aggressive-latency"
        create_service_with_metrics(metrics_engine, service_id, latency_base=180)
        
        # Create recommendations with unrealistic latency (too aggressive)
        recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 30.0,  # Much lower than historical p50 (~80ms)
            "latency_p99_ms": 60.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.validate_achievability(
            service_id=service_id,
            recommendations=recommendations,
            time_window="30d",
            latency_max_decrease_percent=0.2  # 20% decrease allowed
        )
        
        # Should be adjusted
        validated = result["validated_recommendations"]
        assert validated["latency_p95_ms"] > recommendations["latency_p95_ms"]
        
        # Should have adjustment and warning
        assert len(result["adjustments_made"]) > 0
        assert any("Latency p95 adjusted" in adj for adj in result["adjustments_made"])
        assert len(result["warnings"]) > 0
    
    def test_latency_p99_below_p95(self, recommendation_engine, metrics_engine):
        """Test that latency p99 is adjusted to be >= p95."""
        service_id = "test-service-p99-p95"
        create_service_with_metrics(metrics_engine, service_id)
        
        # Create recommendations where p99 < p95 (invalid)
        recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 100.0,  # Less than p95 (invalid)
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.validate_achievability(
            service_id=service_id,
            recommendations=recommendations,
            time_window="30d"
        )
        
        # Should be adjusted
        validated = result["validated_recommendations"]
        assert validated["latency_p99_ms"] >= validated["latency_p95_ms"]
        
        # Should have adjustment
        assert len(result["adjustments_made"]) > 0
    
    def test_error_rate_too_aggressive(self, recommendation_engine, metrics_engine):
        """Test that error rate below historical p50 is adjusted."""
        service_id = "test-service-aggressive-error"
        create_service_with_metrics(metrics_engine, service_id, error_rate_base=0.8)
        
        # Create recommendations with unrealistic error rate
        recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 0.1  # Much lower than historical p50 (~0.8%)
        }
        
        result = recommendation_engine.validate_achievability(
            service_id=service_id,
            recommendations=recommendations,
            time_window="30d",
            error_rate_max_decrease_percent=0.2  # 20% decrease allowed
        )
        
        # Should be adjusted
        validated = result["validated_recommendations"]
        assert validated["error_rate_percent"] > recommendations["error_rate_percent"]
        
        # Should have adjustment and warning
        assert len(result["adjustments_made"]) > 0
        assert any("Error rate adjusted" in adj for adj in result["adjustments_made"])
    
    def test_missing_required_keys(self, recommendation_engine, metrics_engine):
        """Test that error is raised for missing required keys."""
        service_id = "test-service"
        create_service_with_metrics(metrics_engine, service_id)
        
        # Create incomplete recommendations
        incomplete_recs = {
            "availability": 99.5,
            "latency_p95_ms": 200.0
            # Missing latency_p99_ms and error_rate_percent
        }
        
        with pytest.raises(ValueError, match="missing required keys"):
            recommendation_engine.validate_achievability(
                service_id=service_id,
                recommendations=incomplete_recs,
                time_window="30d"
            )
    
    def test_no_metrics_available(self, recommendation_engine):
        """Test that error is raised when no metrics are available."""
        service_id = "nonexistent-service"
        
        recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 1.0
        }
        
        with pytest.raises(ValueError, match="No aggregated metrics found"):
            recommendation_engine.validate_achievability(
                service_id=service_id,
                recommendations=recommendations,
                time_window="30d"
            )
    
    def test_metadata_structure(self, recommendation_engine, metrics_engine):
        """Test that metadata contains expected information."""
        service_id = "test-service-metadata"
        create_service_with_metrics(metrics_engine, service_id)
        
        recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 200.0,
            "latency_p99_ms": 400.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.validate_achievability(
            service_id=service_id,
            recommendations=recommendations,
            time_window="30d"
        )
        
        metadata = result["metadata"]
        
        # Verify metadata structure
        assert metadata["service_id"] == service_id
        assert metadata["time_window"] == "30d"
        assert "validated_at" in metadata
        assert "validation_details" in metadata
        assert "historical_metrics" in metadata
        assert "data_quality" in metadata
        
        # Verify validation details
        validation_details = metadata["validation_details"]
        assert "availability_validation" in validation_details
        assert "latency_validation" in validation_details
        assert "error_rate_validation" in validation_details
        assert "thresholds" in validation_details


class TestValidateMinimumThresholds:
    """Test minimum threshold validation."""
    
    def test_recommendations_meet_all_thresholds(self, recommendation_engine):
        """Test that recommendations meeting all thresholds require no adjustments."""
        recommendations = {
            "availability": 95.0,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 2.0
        }
        
        result = recommendation_engine.validate_minimum_thresholds(
            recommendations=recommendations,
            min_availability=90.0,
            min_latency_ms=1.0,
            min_error_rate=0.0,
            max_error_rate=100.0
        )
        
        # Should not require adjustments
        validated = result["validated_recommendations"]
        assert validated == recommendations
        
        # Should indicate no adjustments needed
        assert "No adjustments needed" in result["adjustments_made"][0]
        assert len(result["warnings"]) == 0
    
    def test_availability_below_minimum(self, recommendation_engine):
        """Test that availability below minimum is adjusted."""
        recommendations = {
            "availability": 85.0,  # Below minimum of 90%
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 2.0
        }
        
        result = recommendation_engine.validate_minimum_thresholds(
            recommendations=recommendations,
            min_availability=90.0
        )
        
        # Should be adjusted
        validated = result["validated_recommendations"]
        assert validated["availability"] == 90.0
        
        # Should have adjustment and warning
        assert len(result["adjustments_made"]) > 0
        assert any("Availability adjusted" in adj for adj in result["adjustments_made"])
        assert len(result["warnings"]) > 0
    
    def test_latency_p95_below_minimum(self, recommendation_engine):
        """Test that latency p95 below minimum is adjusted."""
        recommendations = {
            "availability": 95.0,
            "latency_p95_ms": 0.5,  # Below minimum of 1.0ms
            "latency_p99_ms": 1.0,
            "error_rate_percent": 2.0
        }
        
        result = recommendation_engine.validate_minimum_thresholds(
            recommendations=recommendations,
            min_latency_ms=1.0
        )
        
        # Should be adjusted
        validated = result["validated_recommendations"]
        assert validated["latency_p95_ms"] == 1.0
        
        # Should have adjustment
        assert len(result["adjustments_made"]) > 0
    
    def test_latency_p99_below_p95(self, recommendation_engine):
        """Test that latency p99 is adjusted to be >= p95."""
        recommendations = {
            "availability": 95.0,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 50.0,  # Less than p95
            "error_rate_percent": 2.0
        }
        
        result = recommendation_engine.validate_minimum_thresholds(
            recommendations=recommendations,
            min_latency_ms=1.0
        )
        
        # Should be adjusted
        validated = result["validated_recommendations"]
        assert validated["latency_p99_ms"] >= validated["latency_p95_ms"]
        
        # Should have adjustment
        assert len(result["adjustments_made"]) > 0
    
    def test_error_rate_below_minimum(self, recommendation_engine):
        """Test that error rate below minimum is adjusted."""
        recommendations = {
            "availability": 95.0,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": -1.0  # Below minimum of 0%
        }
        
        result = recommendation_engine.validate_minimum_thresholds(
            recommendations=recommendations,
            min_error_rate=0.0
        )
        
        # Should be adjusted
        validated = result["validated_recommendations"]
        assert validated["error_rate_percent"] == 0.0
        
        # Should have adjustment
        assert len(result["adjustments_made"]) > 0
    
    def test_error_rate_above_maximum(self, recommendation_engine):
        """Test that error rate above maximum is adjusted."""
        recommendations = {
            "availability": 95.0,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 150.0  # Above maximum of 100%
        }
        
        result = recommendation_engine.validate_minimum_thresholds(
            recommendations=recommendations,
            max_error_rate=100.0
        )
        
        # Should be adjusted
        validated = result["validated_recommendations"]
        assert validated["error_rate_percent"] == 100.0
        
        # Should have adjustment
        assert len(result["adjustments_made"]) > 0
    
    def test_missing_required_keys(self, recommendation_engine):
        """Test that error is raised for missing required keys."""
        incomplete_recs = {
            "availability": 95.0,
            "latency_p95_ms": 100.0
            # Missing latency_p99_ms and error_rate_percent
        }
        
        with pytest.raises(ValueError, match="missing required keys"):
            recommendation_engine.validate_minimum_thresholds(
                recommendations=incomplete_recs
            )
    
    def test_invalid_min_availability(self, recommendation_engine):
        """Test that error is raised for invalid min_availability."""
        recommendations = {
            "availability": 95.0,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 2.0
        }
        
        with pytest.raises(ValueError, match="min_availability must be in range"):
            recommendation_engine.validate_minimum_thresholds(
                recommendations=recommendations,
                min_availability=150.0  # Invalid
            )
    
    def test_invalid_min_latency(self, recommendation_engine):
        """Test that error is raised for invalid min_latency_ms."""
        recommendations = {
            "availability": 95.0,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 2.0
        }
        
        with pytest.raises(ValueError, match="min_latency_ms must be positive"):
            recommendation_engine.validate_minimum_thresholds(
                recommendations=recommendations,
                min_latency_ms=0.0  # Invalid (must be positive)
            )
    
    def test_invalid_error_rate_range(self, recommendation_engine):
        """Test that error is raised for invalid error rate range."""
        recommendations = {
            "availability": 95.0,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 2.0
        }
        
        with pytest.raises(ValueError, match="min_error_rate .* cannot be greater than"):
            recommendation_engine.validate_minimum_thresholds(
                recommendations=recommendations,
                min_error_rate=50.0,
                max_error_rate=10.0  # Invalid (min > max)
            )
    
    def test_metadata_structure(self, recommendation_engine):
        """Test that metadata contains expected information."""
        recommendations = {
            "availability": 95.0,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 2.0
        }
        
        result = recommendation_engine.validate_minimum_thresholds(
            recommendations=recommendations,
            min_availability=90.0,
            min_latency_ms=1.0,
            min_error_rate=0.0,
            max_error_rate=100.0
        )
        
        metadata = result["metadata"]
        
        # Verify metadata structure
        assert "validated_at" in metadata
        assert "validation_details" in metadata
        assert "thresholds_applied" in metadata
        assert "validation_summary" in metadata
        
        # Verify validation details
        validation_details = metadata["validation_details"]
        assert "availability_validation" in validation_details
        assert "latency_p95_validation" in validation_details
        assert "latency_p99_validation" in validation_details
        assert "error_rate_validation" in validation_details
        assert "thresholds" in validation_details
    
    def test_multiple_adjustments(self, recommendation_engine):
        """Test that multiple adjustments are tracked correctly."""
        recommendations = {
            "availability": 85.0,  # Below minimum
            "latency_p95_ms": 0.5,  # Below minimum
            "latency_p99_ms": 1.0,
            "error_rate_percent": 150.0  # Above maximum
        }
        
        result = recommendation_engine.validate_minimum_thresholds(
            recommendations=recommendations,
            min_availability=90.0,
            min_latency_ms=1.0,
            min_error_rate=0.0,
            max_error_rate=100.0
        )
        
        # Should have multiple adjustments
        assert len(result["adjustments_made"]) >= 3
        assert len(result["warnings"]) >= 3
        
        # Verify all values were adjusted
        validated = result["validated_recommendations"]
        assert validated["availability"] == 90.0
        assert validated["latency_p95_ms"] == 1.0
        assert validated["error_rate_percent"] == 100.0


class TestValidateDependencyChainConsistency:
    """Test dependency chain consistency validation."""
    
    def test_no_dependency_graph(self, recommendation_engine):
        """Test that validation passes when no dependency graph exists."""
        recommendations = {
            "availability": 99.9,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 0.5
        }
        
        result = recommendation_engine.validate_dependency_chain_consistency(
            service_id="independent-service",
            recommendations=recommendations
        )
        
        # Should be consistent (no graph to check)
        assert result["is_consistent"] == True
        assert len(result["inconsistencies"]) == 0
        assert "No dependency graph available" in result["metadata"]["note"]
    
    def test_service_not_in_graph(self, recommendation_engine, temp_storage):
        """Test that validation passes when service not in graph."""
        # Create empty analyzed graph
        analyzed_graph = {"services": []}
        temp_storage.write_json("dependencies/analyzed_graph.json", analyzed_graph)
        
        recommendations = {
            "availability": 99.9,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 0.5
        }
        
        result = recommendation_engine.validate_dependency_chain_consistency(
            service_id="unknown-service",
            recommendations=recommendations
        )
        
        # Should be consistent (service not in graph)
        assert result["is_consistent"] == True
        assert len(result["inconsistencies"]) == 0
        assert "not found in dependency graph" in result["metadata"]["note"]
    
    def test_missing_required_keys(self, recommendation_engine):
        """Test that error is raised for missing required keys."""
        incomplete_recs = {
            "availability": 99.9,
            "latency_p95_ms": 100.0
            # Missing latency_p99_ms and error_rate_percent
        }
        
        with pytest.raises(ValueError, match="missing required keys"):
            recommendation_engine.validate_dependency_chain_consistency(
                service_id="test-service",
                recommendations=incomplete_recs
            )


class TestSafetyValidationIntegration:
    """Test integration of multiple safety validations."""
    
    def test_all_validations_together(self, recommendation_engine, metrics_engine):
        """Test that all safety validations work together."""
        service_id = "test-service-all-validations"
        create_service_with_metrics(metrics_engine, service_id)
        
        # Create recommendations that need multiple adjustments
        recommendations = {
            "availability": 99.99,  # Too high
            "latency_p95_ms": 20.0,  # Too low
            "latency_p99_ms": 50.0,  # Too low
            "error_rate_percent": 0.1  # Too low
        }
        
        # Apply achievability validation
        achievability_result = recommendation_engine.validate_achievability(
            service_id=service_id,
            recommendations=recommendations,
            time_window="30d"
        )
        
        # Apply minimum threshold validation
        threshold_result = recommendation_engine.validate_minimum_thresholds(
            recommendations=achievability_result["validated_recommendations"],
            min_availability=90.0,
            min_latency_ms=1.0,
            min_error_rate=0.0,
            max_error_rate=100.0
        )
        
        # Apply dependency chain consistency validation
        consistency_result = recommendation_engine.validate_dependency_chain_consistency(
            service_id=service_id,
            recommendations=threshold_result["validated_recommendations"]
        )
        
        # Final recommendations should be safe
        final_recs = threshold_result["validated_recommendations"]
        
        # Verify all constraints are met
        assert final_recs["availability"] >= 90.0
        assert final_recs["availability"] <= 100.0
        assert final_recs["latency_p95_ms"] >= 1.0
        assert final_recs["latency_p99_ms"] >= final_recs["latency_p95_ms"]
        assert final_recs["error_rate_percent"] >= 0.0
        assert final_recs["error_rate_percent"] <= 100.0
        
        # Should have adjustments from both validations
        total_adjustments = len(achievability_result["adjustments_made"]) + len(threshold_result["adjustments_made"])
        assert total_adjustments > 0
        
        # Consistency validation should complete without errors
        assert "is_consistent" in consistency_result
        assert "inconsistencies" in consistency_result
