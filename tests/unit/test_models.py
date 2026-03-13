"""Unit tests for Pydantic data models."""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.service import ServiceMetadata, Infrastructure, Datastore, Cache, CurrentSLO
from src.models.metrics import MetricsData, LatencyMetrics, ErrorRateMetrics, AvailabilityMetrics
from src.models.dependency import DependencyGraph, ServiceDependency, DependencyEdge
from src.models.recommendation import Recommendation, SLOTier, RecommendationExplanation, ConfidenceScore


class TestServiceModels:
    """Tests for service models."""

    def test_valid_datastore(self):
        """Test valid datastore creation."""
        datastore = Datastore(
            type="postgresql",
            name="payments-db",
            availability_slo=99.95,
            latency_p95_ms=45.0
        )
        assert datastore.type == "postgresql"
        assert datastore.availability_slo == 99.95

    def test_datastore_invalid_availability(self):
        """Test datastore with invalid availability."""
        with pytest.raises(ValidationError):
            Datastore(
                type="postgresql",
                name="payments-db",
                availability_slo=101,  # Invalid
                latency_p95_ms=45.0
            )

    def test_valid_current_slo(self):
        """Test valid CurrentSLO."""
        slo = CurrentSLO(
            availability=99.9,
            latency_p95_ms=100,
            latency_p99_ms=200,
            error_rate_percent=0.5
        )
        assert slo.availability == 99.9

    def test_current_slo_invalid_latency_ordering(self):
        """Test CurrentSLO with p99 < p95."""
        with pytest.raises(ValidationError, match="p99.*must be.*p95"):
            CurrentSLO(
                availability=99.9,
                latency_p95_ms=200,
                latency_p99_ms=100,  # Invalid: p99 < p95
                error_rate_percent=0.5
            )

    def test_valid_service_metadata(self):
        """Test valid ServiceMetadata."""
        metadata = ServiceMetadata(
            service_id="payment-api",
            service_name="Payment API",
            service_type="api",
            team="payments-team",
            tenant_id="acme-corp",
            region="us-east-1",
            created_at=datetime.now(),
            updated_at=datetime.now()
        )
        assert metadata.service_id == "payment-api"


class TestMetricsModels:
    """Tests for metrics models."""

    def test_valid_latency_metrics(self):
        """Test valid LatencyMetrics."""
        latency = LatencyMetrics(
            p50_ms=50,
            p95_ms=100,
            p99_ms=150,
            mean_ms=60,
            stddev_ms=20
        )
        assert latency.p50_ms == 50

    def test_latency_metrics_invalid_p95(self):
        """Test LatencyMetrics with p95 < p50."""
        with pytest.raises(ValidationError, match="p95.*must be.*p50"):
            LatencyMetrics(
                p50_ms=100,
                p95_ms=50,  # Invalid
                p99_ms=150,
                mean_ms=60,
                stddev_ms=20
            )

    def test_latency_metrics_invalid_p99(self):
        """Test LatencyMetrics with p99 < p95."""
        with pytest.raises(ValidationError, match="p99.*must be.*p95"):
            LatencyMetrics(
                p50_ms=50,
                p95_ms=100,
                p99_ms=75,  # Invalid
                mean_ms=60,
                stddev_ms=20
            )

    def test_valid_error_rate_metrics(self):
        """Test valid ErrorRateMetrics."""
        error_rate = ErrorRateMetrics(
            percent=0.5,
            total_requests=1000,
            failed_requests=5
        )
        assert error_rate.percent == 0.5

    def test_error_rate_failed_exceeds_total(self):
        """Test ErrorRateMetrics with failed > total."""
        with pytest.raises(ValidationError, match="failed_requests cannot exceed total_requests"):
            ErrorRateMetrics(
                percent=0.5,
                total_requests=1000,
                failed_requests=1001  # Invalid
            )

    def test_valid_availability_metrics(self):
        """Test valid AvailabilityMetrics."""
        availability = AvailabilityMetrics(
            percent=99.9,
            uptime_seconds=86000,
            downtime_seconds=400
        )
        assert availability.percent == 99.9


class TestDependencyModels:
    """Tests for dependency models."""

    def test_valid_dependency_edge(self):
        """Test valid DependencyEdge."""
        edge = DependencyEdge(
            target_service_id="auth-service",
            dependency_type="synchronous",
            timeout_ms=500,
            criticality="high"
        )
        assert edge.target_service_id == "auth-service"

    def test_valid_service_dependency(self):
        """Test valid ServiceDependency."""
        dep = ServiceDependency(
            service_id="payment-api",
            dependencies=[
                DependencyEdge(
                    target_service_id="auth-service",
                    dependency_type="synchronous",
                    criticality="high"
                )
            ]
        )
        assert dep.service_id == "payment-api"
        assert len(dep.dependencies) == 1

    def test_valid_dependency_graph(self):
        """Test valid DependencyGraph."""
        graph = DependencyGraph(
            version="1.0",
            updated_at=datetime.now(),
            services=[
                ServiceDependency(
                    service_id="api-gateway",
                    dependencies=[]
                )
            ]
        )
        assert graph.version == "1.0"


class TestRecommendationModels:
    """Tests for recommendation models."""

    def test_valid_slo_tier(self):
        """Test valid SLOTier."""
        tier = SLOTier(
            availability=99.9,
            latency_p95_ms=100,
            latency_p99_ms=200,
            error_rate_percent=0.5
        )
        assert tier.availability == 99.9

    def test_slo_tier_invalid_latency_ordering(self):
        """Test SLOTier with p99 < p95."""
        with pytest.raises(ValidationError, match="p99.*must be.*p95"):
            SLOTier(
                availability=99.9,
                latency_p95_ms=200,
                latency_p99_ms=100,  # Invalid
                error_rate_percent=0.5
            )

    def test_valid_recommendation_explanation(self):
        """Test valid RecommendationExplanation."""
        explanation = RecommendationExplanation(
            summary="Balanced tier recommended",
            top_factors=["Factor 1", "Factor 2", "Factor 3"]
        )
        assert len(explanation.top_factors) == 3

    def test_recommendation_explanation_too_few_factors(self):
        """Test RecommendationExplanation with < 1 factors."""
        with pytest.raises(ValidationError):
            RecommendationExplanation(
                summary="Test",
                top_factors=[]  # Too few
            )

    def test_valid_confidence_score(self):
        """Test valid ConfidenceScore."""
        confidence = ConfidenceScore(
            data_completeness=0.25,
            historical_stability=0.28,
            dependency_clarity=0.18,
            knowledge_base_match=0.15,
            total=0.86
        )
        assert confidence.total == 0.86

    def test_confidence_score_invalid_total(self):
        """Test ConfidenceScore with mismatched total."""
        with pytest.raises(ValidationError, match="does not match sum of components"):
            ConfidenceScore(
                data_completeness=0.25,
                historical_stability=0.28,
                dependency_clarity=0.18,
                knowledge_base_match=0.15,
                total=0.50  # Doesn't match sum
            )

    def test_valid_recommendation(self):
        """Test valid Recommendation."""
        from src.models.recommendation import DataQualityInfo
        
        recommendation = Recommendation(
            service_id="payment-api",
            version="v1.0.0",
            timestamp=datetime.now(),
            recommendations={
                "balanced": SLOTier(
                    availability=99.9,
                    latency_p95_ms=100,
                    latency_p99_ms=200,
                    error_rate_percent=0.5
                )
            },
            recommended_tier="balanced",
            confidence_score=0.85,
            explanation=RecommendationExplanation(
                summary="Test summary",
                top_factors=["Factor 1", "Factor 2", "Factor 3"]
            ),
            data_quality=DataQualityInfo(
                completeness=0.95,
                staleness_hours=2,
                quality_score=0.92
            )
        )
        assert recommendation.service_id == "payment-api"
