"""
Unit tests for explanation generation in RecommendationEngine.
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
    service_id = "test-service-explanation"
    
    # Ingest multiple metrics over time to build history
    base_time = datetime.utcnow() - timedelta(days=29)
    
    for i in range(30):
        timestamp = base_time + timedelta(days=i)
        
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


class TestExplanationGeneration:
    """Test explanation generation functionality."""
    
    def test_generate_explanation_basic(self, recommendation_engine, sample_service_with_metrics):
        """Test basic explanation generation with minimal constraints."""
        service_id = sample_service_with_metrics
        
        # Compute base recommendations
        base_result = recommendation_engine.compute_base_recommendations(service_id)
        base_recommendations = base_result["base_recommendations"]
        
        # Apply dependency constraints (no dependencies, so should be unchanged)
        dep_result = recommendation_engine.apply_dependency_constraints(
            service_id=service_id,
            base_recommendations=base_recommendations
        )
        constrained_recommendations = dep_result["constrained_recommendations"]
        dependency_metadata = dep_result["metadata"]
        
        # Apply infrastructure constraints (no infrastructure, so should be unchanged)
        infra_result = recommendation_engine.apply_infrastructure_constraints(
            service_id=service_id,
            constrained_recommendations=constrained_recommendations
        )
        infrastructure_constrained_recommendations = infra_result["infrastructure_constrained_recommendations"]
        infrastructure_metadata = infra_result["metadata"]
        
        # Generate explanation
        explanation = recommendation_engine.generate_explanation(
            service_id=service_id,
            base_recommendations=base_recommendations,
            constrained_recommendations=constrained_recommendations,
            infrastructure_constrained_recommendations=infrastructure_constrained_recommendations,
            dependency_metadata=dependency_metadata,
            infrastructure_metadata=infrastructure_metadata,
            confidence_score=0.85,
            time_window="30d"
        )
        
        # Verify explanation structure
        assert "summary" in explanation
        assert "top_factors" in explanation
        assert "dependency_constraints" in explanation
        assert "infrastructure_bottlenecks" in explanation
        assert "similar_services" in explanation
        
        # Verify summary is a non-empty string
        assert isinstance(explanation["summary"], str)
        assert len(explanation["summary"]) > 0
        
        # Verify top_factors has 1-3 items
        assert isinstance(explanation["top_factors"], list)
        assert 1 <= len(explanation["top_factors"]) <= 3
        
        # Verify all factors are non-empty strings
        for factor in explanation["top_factors"]:
            assert isinstance(factor, str)
            assert len(factor) > 0
        
        # Verify dependency_constraints is a list
        assert isinstance(explanation["dependency_constraints"], list)
        
        # Verify infrastructure_bottlenecks is a list
        assert isinstance(explanation["infrastructure_bottlenecks"], list)
        
        # Verify similar_services is a list (placeholder, should be empty)
        assert isinstance(explanation["similar_services"], list)
        assert len(explanation["similar_services"]) == 0  # Placeholder
    
    def test_explanation_contains_historical_metrics(self, recommendation_engine, sample_service_with_metrics):
        """Test that explanation includes historical metrics in top factors."""
        service_id = sample_service_with_metrics
        
        # Compute base recommendations
        base_result = recommendation_engine.compute_base_recommendations(service_id)
        base_recommendations = base_result["base_recommendations"]
        
        # Apply constraints
        dep_result = recommendation_engine.apply_dependency_constraints(
            service_id=service_id,
            base_recommendations=base_recommendations
        )
        constrained_recommendations = dep_result["constrained_recommendations"]
        dependency_metadata = dep_result["metadata"]
        
        infra_result = recommendation_engine.apply_infrastructure_constraints(
            service_id=service_id,
            constrained_recommendations=constrained_recommendations
        )
        infrastructure_constrained_recommendations = infra_result["infrastructure_constrained_recommendations"]
        infrastructure_metadata = infra_result["metadata"]
        
        # Generate explanation
        explanation = recommendation_engine.generate_explanation(
            service_id=service_id,
            base_recommendations=base_recommendations,
            constrained_recommendations=constrained_recommendations,
            infrastructure_constrained_recommendations=infrastructure_constrained_recommendations,
            dependency_metadata=dependency_metadata,
            infrastructure_metadata=infrastructure_metadata,
            confidence_score=0.85,
            time_window="30d"
        )
        
        # Verify that at least one top factor mentions historical metrics
        top_factors_text = " ".join(explanation["top_factors"])
        assert "Historical" in top_factors_text or "p95" in top_factors_text or "availability" in top_factors_text
    
    def test_explanation_with_no_metrics(self, recommendation_engine):
        """Test that appropriate error is raised when service has no metrics."""
        service_id = "nonexistent-service"
        
        # Create dummy recommendations
        base_recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 200,
            "latency_p99_ms": 400,
            "error_rate_percent": 1.0
        }
        
        dependency_metadata = {"upstream_services_checked": []}
        infrastructure_metadata = {"datastore_constraints": []}
        
        # Should raise ValueError
        with pytest.raises(ValueError, match="No aggregated metrics found"):
            recommendation_engine.generate_explanation(
                service_id=service_id,
                base_recommendations=base_recommendations,
                constrained_recommendations=base_recommendations,
                infrastructure_constrained_recommendations=base_recommendations,
                dependency_metadata=dependency_metadata,
                infrastructure_metadata=infrastructure_metadata,
                confidence_score=0.85,
                time_window="30d"
            )
    
    def test_explanation_summary_reflects_confidence(self, recommendation_engine, sample_service_with_metrics):
        """Test that summary reflects confidence level."""
        service_id = sample_service_with_metrics
        
        # Compute base recommendations
        base_result = recommendation_engine.compute_base_recommendations(service_id)
        base_recommendations = base_result["base_recommendations"]
        
        # Apply constraints
        dep_result = recommendation_engine.apply_dependency_constraints(
            service_id=service_id,
            base_recommendations=base_recommendations
        )
        constrained_recommendations = dep_result["constrained_recommendations"]
        dependency_metadata = dep_result["metadata"]
        
        infra_result = recommendation_engine.apply_infrastructure_constraints(
            service_id=service_id,
            constrained_recommendations=constrained_recommendations
        )
        infrastructure_constrained_recommendations = infra_result["infrastructure_constrained_recommendations"]
        infrastructure_metadata = infra_result["metadata"]
        
        # Test high confidence
        explanation_high = recommendation_engine.generate_explanation(
            service_id=service_id,
            base_recommendations=base_recommendations,
            constrained_recommendations=constrained_recommendations,
            infrastructure_constrained_recommendations=infrastructure_constrained_recommendations,
            dependency_metadata=dependency_metadata,
            infrastructure_metadata=infrastructure_metadata,
            confidence_score=0.85,
            time_window="30d"
        )
        assert "high confidence" in explanation_high["summary"]
        
        # Test moderate confidence
        explanation_moderate = recommendation_engine.generate_explanation(
            service_id=service_id,
            base_recommendations=base_recommendations,
            constrained_recommendations=constrained_recommendations,
            infrastructure_constrained_recommendations=infrastructure_constrained_recommendations,
            dependency_metadata=dependency_metadata,
            infrastructure_metadata=infrastructure_metadata,
            confidence_score=0.65,
            time_window="30d"
        )
        assert "moderate confidence" in explanation_moderate["summary"]
        
        # Test low confidence
        explanation_low = recommendation_engine.generate_explanation(
            service_id=service_id,
            base_recommendations=base_recommendations,
            constrained_recommendations=constrained_recommendations,
            infrastructure_constrained_recommendations=infrastructure_constrained_recommendations,
            dependency_metadata=dependency_metadata,
            infrastructure_metadata=infrastructure_metadata,
            confidence_score=0.45,
            time_window="30d"
        )
        assert "low confidence" in explanation_low["summary"]
