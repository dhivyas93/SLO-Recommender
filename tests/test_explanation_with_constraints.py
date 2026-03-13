"""
Integration tests for explanation generation with dependencies and infrastructure.
"""

import pytest
from datetime import datetime, timedelta
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
def service_with_dependencies(storage, metrics_engine):
    """Create a service with dependencies and metrics."""
    service_id = "payment-api"
    upstream_id = "auth-service"
    
    # Create metrics for both services
    base_time = datetime.utcnow() - timedelta(days=29)
    
    for i in range(30):
        timestamp = base_time + timedelta(days=i)
        
        # Metrics for payment-api (higher availability to trigger constraint)
        metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="30d",
            latency={
                "p50_ms": 85,
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
                "percent": 99.95,  # Higher than upstream to trigger constraint
                "uptime_seconds": 86357,
                "downtime_seconds": 43
            },
            timestamp=timestamp
        )
        
        # Metrics for auth-service
        metrics_engine.ingest_metrics(
            service_id=upstream_id,
            time_window="30d",
            latency={
                "p50_ms": 40,
                "p95_ms": 50,
                "p99_ms": 80,
                "mean_ms": 45,
                "stddev_ms": 10
            },
            error_rate={
                "percent": 0.1,
                "total_requests": 2000000,
                "failed_requests": 2000
            },
            availability={
                "percent": 99.9,
                "uptime_seconds": 86313,
                "downtime_seconds": 87
            },
            timestamp=timestamp
        )
    
    # Compute aggregated metrics
    metrics_engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
    metrics_engine.compute_aggregated_metrics(upstream_id, time_windows=["30d"])
    
    # Create dependency graph
    analyzed_graph = {
        "version": "1.0",
        "analyzed_at": datetime.utcnow().isoformat(),
        "services": [
            {
                "service_id": service_id,
                "upstream_services": [upstream_id],
                "downstream_services": [],
                "upstream_count": 1,
                "downstream_count": 0,
                "depth_from_root": 1,
                "fanout": 0,
                "cascading_impact_score": 0.5,
                "critical_paths": [
                    {
                        "path": [upstream_id, service_id],
                        "total_latency_budget_ms": 450,
                        "bottleneck_service": service_id
                    }
                ],
                "is_in_circular_dependency": False
            }
        ]
    }
    storage.write_json("dependencies/analyzed_graph.json", analyzed_graph)
    
    # Create upstream service recommendation
    upstream_recommendation = {
        "service_id": upstream_id,
        "version": "v1.0.0",
        "timestamp": datetime.utcnow().isoformat(),
        "recommendations": {
            "balanced": {
                "availability": 99.9,
                "latency_p95_ms": 50,
                "latency_p99_ms": 80,
                "error_rate_percent": 0.1
            }
        }
    }
    storage.write_json(f"recommendations/{upstream_id}/latest.json", upstream_recommendation)
    
    return service_id


@pytest.fixture
def service_with_infrastructure(storage, metrics_engine):
    """Create a service with infrastructure and metrics."""
    service_id = "data-service"
    
    # Create metrics
    base_time = datetime.utcnow() - timedelta(days=29)
    
    for i in range(30):
        timestamp = base_time + timedelta(days=i)
        
        metrics_engine.ingest_metrics(
            service_id=service_id,
            time_window="30d",
            latency={
                "p50_ms": 85,
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
            timestamp=timestamp
        )
    
    # Compute aggregated metrics
    metrics_engine.compute_aggregated_metrics(service_id, time_windows=["30d"])
    
    # Create service metadata with infrastructure
    service_metadata = {
        "service_id": service_id,
        "service_type": "api",
        "infrastructure": {
            "datastores": [
                {
                    "type": "postgresql",
                    "name": "main-db",
                    "availability_slo": 99.95,
                    "latency_p95_ms": 45
                }
            ],
            "caches": [
                {
                    "type": "redis",
                    "name": "cache",
                    "hit_rate": 0.85
                }
            ]
        }
    }
    storage.write_json(f"services/{service_id}/metadata.json", service_metadata)
    
    return service_id


class TestExplanationWithDependencies:
    """Test explanation generation with dependency constraints."""
    
    def test_explanation_includes_dependency_constraints(
        self, recommendation_engine, service_with_dependencies
    ):
        """Test that explanation includes dependency constraints when applied."""
        service_id = service_with_dependencies
        
        # Compute recommendations
        base_result = recommendation_engine.compute_base_recommendations(service_id)
        base_recommendations = base_result["base_recommendations"]
        
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
        
        # Verify dependency constraints are mentioned
        assert len(explanation["dependency_constraints"]) > 0
        
        # Verify top factors mention dependencies
        top_factors_text = " ".join(explanation["top_factors"])
        assert "auth-service" in top_factors_text or "Depends on" in top_factors_text


class TestExplanationWithInfrastructure:
    """Test explanation generation with infrastructure constraints."""
    
    def test_explanation_includes_infrastructure_bottlenecks(
        self, recommendation_engine, service_with_infrastructure
    ):
        """Test that explanation includes infrastructure bottlenecks when identified."""
        service_id = service_with_infrastructure
        
        # Compute recommendations
        base_result = recommendation_engine.compute_base_recommendations(service_id)
        base_recommendations = base_result["base_recommendations"]
        
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
        
        # Verify top factors mention infrastructure
        top_factors_text = " ".join(explanation["top_factors"])
        assert "datastore" in top_factors_text or "postgresql" in top_factors_text or "Uses" in top_factors_text
