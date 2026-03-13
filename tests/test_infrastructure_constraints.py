"""
Unit tests for infrastructure constraint application logic.
"""

import pytest
from datetime import datetime
from src.engines.recommendation_engine import RecommendationEngine
from src.storage.file_storage import FileStorage


@pytest.fixture
def storage(tmp_path):
    """Create a temporary FileStorage instance."""
    return FileStorage(base_path=str(tmp_path / "data"))


@pytest.fixture
def recommendation_engine(storage):
    """Create a RecommendationEngine instance."""
    return RecommendationEngine(storage=storage)


@pytest.fixture
def constrained_recommendations():
    """Sample constrained recommendations."""
    return {
        "availability": 99.5,
        "latency_p95_ms": 200.0,
        "latency_p99_ms": 400.0,
        "error_rate_percent": 1.0
    }


class TestInfrastructureConstraintsValidation:
    """Test input validation for apply_infrastructure_constraints."""
    
    def test_missing_required_keys(self, recommendation_engine):
        """Test error when constrained_recommendations is missing required keys."""
        incomplete_recs = {
            "availability": 99.5,
            "latency_p95_ms": 200.0
            # Missing latency_p99_ms and error_rate_percent
        }
        
        with pytest.raises(ValueError, match="missing required keys"):
            recommendation_engine.apply_infrastructure_constraints(
                service_id="test-service",
                constrained_recommendations=incomplete_recs
            )


class TestInfrastructureConstraintsNoMetadata:
    """Test apply_infrastructure_constraints when no service metadata exists."""
    
    def test_no_service_metadata(self, recommendation_engine, constrained_recommendations):
        """Test when no service metadata exists."""
        result = recommendation_engine.apply_infrastructure_constraints(
            service_id="nonexistent-service",
            constrained_recommendations=constrained_recommendations
        )
        
        # Should return recommendations unchanged
        assert result["infrastructure_constrained_recommendations"] == constrained_recommendations
        assert "No service metadata available" in result["constraints_applied"][0]
        assert result["metadata"]["note"] == "No service metadata found for nonexistent-service"


class TestInfrastructureConstraintsDatastore:
    """Test datastore constraint application."""
    
    def test_availability_constrained_by_datastore(
        self,
        recommendation_engine,
        constrained_recommendations,
        storage
    ):
        """Test availability is constrained by datastore SLO."""
        # Create service metadata with datastore
        service_metadata = {
            "service_id": "test-service",
            "infrastructure": {
                "datastores": [
                    {
                        "name": "postgres-db",
                        "type": "postgresql",
                        "availability_slo": 99.9,
                        "latency_p95_ms": 50.0
                    }
                ],
                "caches": [],
                "message_queues": []
            }
        }
        
        storage.write_json("services/test-service/metadata.json", service_metadata)
        
        # Base recommendation: 99.5%
        # Datastore SLO: 99.9%
        # Expected constraint: 99.9% - 0.5% = 99.4%
        
        result = recommendation_engine.apply_infrastructure_constraints(
            service_id="test-service",
            constrained_recommendations=constrained_recommendations,
            availability_margin=0.5
        )
        
        constrained = result["infrastructure_constrained_recommendations"]
        
        # Availability should be constrained
        assert constrained["availability"] == 99.4
        assert constrained["availability"] < constrained_recommendations["availability"]
        
        # Check constraints_applied
        assert len(result["constraints_applied"]) > 0
        assert "postgres-db" in result["constraints_applied"][0]
        assert "Availability constrained" in result["constraints_applied"][0]
        
        # Check metadata
        assert len(result["metadata"]["datastore_constraints"]) > 0
        constraint = result["metadata"]["datastore_constraints"][0]
        assert constraint["datastore"] == "postgres-db"
        assert constraint["datastore_availability"] == 99.9
        assert constraint["margin"] == 0.5
        assert constraint["original_value"] == 99.5
        assert constraint["constrained_value"] == 99.4
    
    def test_latency_constrained_by_datastore(
        self,
        recommendation_engine,
        storage
    ):
        """Test latency is constrained by datastore latency."""
        service_metadata = {
            "service_id": "test-service",
            "infrastructure": {
                "datastores": [
                    {
                        "name": "postgres-db",
                        "type": "postgresql",
                        "availability_slo": 99.9,
                        "latency_p95_ms": 100.0  # High latency datastore
                    }
                ],
                "caches": [],
                "message_queues": []
            }
        }
        
        storage.write_json("services/test-service/metadata.json", service_metadata)
        
        # Create aggressive recommendation that's too low
        aggressive_recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 50.0,  # Too aggressive - below datastore capability
            "latency_p99_ms": 100.0,
            "error_rate_percent": 1.0
        }
        
        # Datastore latency: 100ms
        # Network overhead: 5ms
        # Expected constraint: 100ms + 5ms = 105ms (raised from 50ms)
        
        result = recommendation_engine.apply_infrastructure_constraints(
            service_id="test-service",
            constrained_recommendations=aggressive_recommendations,
            network_overhead_ms=5.0
        )
        
        constrained = result["infrastructure_constrained_recommendations"]
        
        # Latency should be raised to meet datastore constraint
        assert constrained["latency_p95_ms"] == 105.0
        assert constrained["latency_p95_ms"] > aggressive_recommendations["latency_p95_ms"]
        
        # p99 should be adjusted to maintain ratio
        assert constrained["latency_p99_ms"] >= constrained["latency_p95_ms"]
        assert constrained["latency_p99_ms"] == 105.0 * 1.5  # Adjusted to maintain ratio
        
        # Check constraints_applied
        assert any("Latency p95 constrained" in c for c in result["constraints_applied"])
        
        # Check metadata
        constraint = result["metadata"]["datastore_constraints"][1]  # Second constraint (latency)
        assert constraint["constraint_type"] == "latency"
        assert constraint["datastore_latency"] == 100.0
        assert constraint["network_overhead"] == 5.0
        assert constraint["original_value_ms"] == 50.0
        assert constraint["constrained_value_ms"] == 105.0
    
    def test_datastore_without_slo(
        self,
        recommendation_engine,
        constrained_recommendations,
        storage
    ):
        """Test datastore without availability SLO or latency."""
        service_metadata = {
            "service_id": "test-service",
            "infrastructure": {
                "datastores": [
                    {
                        "name": "unknown-db",
                        "type": "unknown",
                        # No availability_slo or latency_p95_ms
                    }
                ],
                "caches": [],
                "message_queues": []
            }
        }
        
        storage.write_json("services/test-service/metadata.json", service_metadata)
        
        result = recommendation_engine.apply_infrastructure_constraints(
            service_id="test-service",
            constrained_recommendations=constrained_recommendations
        )
        
        # Should not apply constraints
        assert result["infrastructure_constrained_recommendations"] == constrained_recommendations
        
        # Check metadata
        constraints = result["metadata"]["datastore_constraints"]
        assert len(constraints) == 2  # One for availability, one for latency
        assert all(c["applied"] == False for c in constraints)
        assert any("No availability SLO" in c["reason"] for c in constraints)
        assert any("No latency defined" in c["reason"] for c in constraints)


class TestInfrastructureConstraintsCache:
    """Test cache benefit application."""
    
    def test_cache_benefit_applied(
        self,
        recommendation_engine,
        constrained_recommendations,
        storage
    ):
        """Test cache benefit is applied for high hit rate."""
        service_metadata = {
            "service_id": "cached-service",
            "infrastructure": {
                "caches": [
                    {
                        "name": "redis-cache",
                        "type": "redis",
                        "hit_rate": 0.9  # High hit rate
                    }
                ],
                "datastores": [],
                "message_queues": []
            }
        }
        
        storage.write_json("services/cached-service/metadata.json", service_metadata)
        
        result = recommendation_engine.apply_infrastructure_constraints(
            service_id="cached-service",
            constrained_recommendations=constrained_recommendations,
            cache_hit_rate_threshold=0.8,
            cache_latency_reduction_factor=0.3
        )
        
        constrained = result["infrastructure_constrained_recommendations"]
        
        # Latency should be reduced
        # Reduction factor: 0.9 * 0.3 = 0.27
        # p95: 200ms * (1 - 0.27) = 146ms
        # p99: 400ms * (1 - 0.27) = 292ms
        assert constrained["latency_p95_ms"] == pytest.approx(146.0, rel=0.01)
        assert constrained["latency_p99_ms"] == pytest.approx(292.0, rel=0.01)
        
        # Check constraints_applied
        assert any("cache" in c.lower() for c in result["constraints_applied"])
        assert any("Latency reduced" in c for c in result["constraints_applied"])
        
        # Check metadata
        cache_benefits = result["metadata"]["cache_benefits"]
        assert len(cache_benefits) == 1
        benefit = cache_benefits[0]
        assert benefit["applied"] == True
        assert benefit["hit_rate"] == 0.9
        assert benefit["latency_reduction_factor"] == 0.27
    
    def test_cache_below_threshold(
        self,
        recommendation_engine,
        constrained_recommendations,
        storage
    ):
        """Test cache benefit not applied for low hit rate."""
        service_metadata = {
            "service_id": "low-cache-service",
            "infrastructure": {
                "caches": [
                    {
                        "name": "redis-cache",
                        "type": "redis",
                        "hit_rate": 0.5  # Low hit rate
                    }
                ],
                "datastores": [],
                "message_queues": []
            }
        }
        
        storage.write_json("services/low-cache-service/metadata.json", service_metadata)
        
        result = recommendation_engine.apply_infrastructure_constraints(
            service_id="low-cache-service",
            constrained_recommendations=constrained_recommendations,
            cache_hit_rate_threshold=0.8
        )
        
        # Should not apply cache benefit
        assert result["infrastructure_constrained_recommendations"] == constrained_recommendations
        
        # Check metadata
        cache_benefits = result["metadata"]["cache_benefits"]
        assert len(cache_benefits) == 1
        benefit = cache_benefits[0]
        assert benefit["applied"] == False
        assert "below threshold" in benefit["reason"]


class TestInfrastructureConstraintsMessageQueues:
    """Test message queue bottleneck identification."""
    
    def test_message_queue_bottleneck(
        self,
        recommendation_engine,
        constrained_recommendations,
        storage
    ):
        """Test message queue identified as bottleneck."""
        service_metadata = {
            "service_id": "queue-service",
            "infrastructure": {
                "message_queues": [
                    {
                        "name": "rabbitmq-queue",
                        "type": "rabbitmq"
                    }
                ],
                "datastores": [],
                "caches": []
            }
        }
        
        storage.write_json("services/queue-service/metadata.json", service_metadata)
        
        result = recommendation_engine.apply_infrastructure_constraints(
            service_id="queue-service",
            constrained_recommendations=constrained_recommendations
        )
        
        # Should identify message queue as bottleneck
        bottlenecks = result["bottlenecks_identified"]
        assert len(bottlenecks) > 0
        assert any("message queue" in b.lower() for b in bottlenecks)
        assert any("rabbitmq" in b for b in bottlenecks)


class TestInfrastructureConstraintsCombined:
    """Test combined infrastructure constraints."""
    
    def test_all_constraints_applied(
        self,
        recommendation_engine,
        storage
    ):
        """Test all infrastructure constraints applied together."""
        service_metadata = {
            "service_id": "complex-service",
            "infrastructure": {
                "datastores": [
                    {
                        "name": "postgres-db",
                        "type": "postgresql",
                        "availability_slo": 99.9,
                        "latency_p95_ms": 50.0
                    }
                ],
                "caches": [
                    {
                        "name": "redis-cache",
                        "type": "redis",
                        "hit_rate": 0.85
                    }
                ],
                "message_queues": [
                    {
                        "name": "kafka-queue",
                        "type": "kafka"
                    }
                ]
            }
        }
        
        storage.write_json("services/complex/metadata.json", service_metadata)
        
        # Create recommendations that will be constrained
        optimistic_recs = {
            "availability": 99.99,  # Higher than datastore
            "latency_p95_ms": 30.0,  # Lower than datastore + network
            "latency_p99_ms": 60.0,
            "error_rate_percent": 0.1
        }
        
        result = recommendation_engine.apply_infrastructure_constraints(
            service_id="complex",
            constrained_recommendations=optimistic_recs,
            network_overhead_ms=5.0,
            availability_margin=0.5,
            cache_hit_rate_threshold=0.8,
            cache_latency_reduction_factor=0.3
        )
        
        constrained = result["infrastructure_constrained_recommendations"]
        
        # Availability should be constrained by datastore
        assert constrained["availability"] == 99.4  # 99.9 - 0.5
        
        # Latency should be constrained by datastore + network, then reduced by cache
        # Constrained to: 50ms + 5ms = 55ms
        # Reduced by cache: 55ms * (1 - 0.85*0.3) = 55ms * 0.745 = 40.975ms
        expected_latency = 55.0 * (1 - 0.85 * 0.3)
        assert constrained["latency_p95_ms"] == pytest.approx(expected_latency, rel=0.01)
        
        # Should have multiple constraints applied
        assert len(result["constraints_applied"]) >= 2
        
        # Should identify bottlenecks
        assert len(result["bottlenecks_identified"]) > 0
        
        # Should have metadata for all components
        metadata = result["metadata"]
        assert len(metadata["datastore_constraints"]) > 0
        assert len(metadata["cache_benefits"]) > 0
        assert len(metadata["infrastructure_components"]["message_queues"]) > 0


class TestInfrastructureConstraintsEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_multiple_datastores_most_restrictive_wins(
        self,
        recommendation_engine,
        constrained_recommendations,
        storage
    ):
        """Test that the most restrictive datastore constraint is applied."""
        service_metadata = {
            "service_id": "multi-db-service",
            "infrastructure": {
                "datastores": [
                    {
                        "name": "high-availability-db",
                        "type": "postgresql",
                        "availability_slo": 99.99,
                        "latency_p95_ms": 10.0
                    },
                    {
                        "name": "low-availability-db",
                        "type": "mongodb",
                        "availability_slo": 99.0,  # Most restrictive
                        "latency_p95_ms": 20.0
                    }
                ],
                "caches": [],
                "message_queues": []
            }
        }
        
        storage.write_json("services/multi-db/metadata.json", service_metadata)
        
        result = recommendation_engine.apply_infrastructure_constraints(
            service_id="multi-db",
            constrained_recommendations=constrained_recommendations,
            availability_margin=0.5
        )
        
        constrained = result["infrastructure_constrained_recommendations"]
        
        # Should be constrained by the lower availability datastore
        # 99.0% - 0.5% = 98.5%
        assert constrained["availability"] == 98.5
        
        # Should have constraints from both datastores
        assert len(result["metadata"]["datastore_constraints"]) >= 2
    
    def test_zero_margin(
        self,
        recommendation_engine,
        storage
    ):
        """Test with zero availability margin."""
        service_metadata = {
            "service_id": "test-service",
            "infrastructure": {
                "datastores": [
                    {
                        "name": "postgres-db",
                        "type": "postgresql",
                        "availability_slo": 99.9,
                        "latency_p95_ms": 50.0
                    }
                ],
                "caches": [],
                "message_queues": []
            }
        }
        
        storage.write_json("services/test/metadata.json", service_metadata)
        
        # Create recommendations that exceed datastore availability
        high_availability_recs = {
            "availability": 99.95,  # Higher than datastore
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.apply_infrastructure_constraints(
            service_id="test",
            constrained_recommendations=high_availability_recs,
            availability_margin=0.0
        )
        
        constrained = result["infrastructure_constrained_recommendations"]
        
        # With zero margin, should be constrained to datastore availability
        # Constraint: service availability <= datastore availability - margin
        # 99.95% > 99.9% - 0.0%, so constrain to 99.9%
        assert constrained["availability"] == 99.9
    
    def test_recommendations_already_meet_constraints(
        self,
        recommendation_engine,
        storage
    ):
        """Test when recommendations already meet all infrastructure constraints."""
        service_metadata = {
            "service_id": "conservative-service",
            "infrastructure": {
                "datastores": [
                    {
                        "name": "postgres-db",
                        "type": "postgresql",
                        "availability_slo": 99.9,
                        "latency_p95_ms": 50.0
                    }
                ],
                "caches": [],
                "message_queues": []
            }
        }
        
        storage.write_json("services/conservative/metadata.json", service_metadata)
        
        # Create conservative recommendations
        conservative_recs = {
            "availability": 98.0,  # Well below datastore
            "latency_p95_ms": 100.0,  # Well above datastore + network
            "latency_p99_ms": 200.0,
            "error_rate_percent": 2.0
        }
        
        result = recommendation_engine.apply_infrastructure_constraints(
            service_id="conservative",
            constrained_recommendations=conservative_recs
        )
        
        # Should return recommendations unchanged
        assert result["infrastructure_constrained_recommendations"] == conservative_recs
        assert "No infrastructure constraints applied" in result["constraints_applied"][0]
