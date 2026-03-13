"""
Unit tests for bottleneck identification functionality.

Tests the identify_infrastructure_bottlenecks method which provides
detailed analysis of infrastructure components that limit SLO recommendations.
"""

import pytest
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


class TestBottleneckIdentificationActiveBottlenecks:
    """Test identification of active bottlenecks."""
    
    def test_datastore_availability_bottleneck(self, recommendation_engine):
        """Test identification of datastore as availability bottleneck."""
        infrastructure = {
            "datastores": [
                {
                    "name": "postgres-db",
                    "type": "postgresql",
                    "availability_slo": 99.0,
                    "latency_p95_ms": 50.0
                }
            ],
            "caches": [],
            "message_queues": []
        }
        
        # Original recommendation was higher, but constrained by datastore
        original_recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        # After constraint: availability reduced to datastore limit
        constrained_recommendations = {
            "availability": 98.5,  # 99.0 - 0.5 margin
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.identify_infrastructure_bottlenecks(
            service_id="test-service",
            infrastructure_constrained_recommendations=constrained_recommendations,
            original_recommendations=original_recommendations,
            infrastructure=infrastructure,
            availability_margin=0.5
        )
        
        # Should identify as active bottleneck
        assert len(result["bottlenecks"]) == 1
        bottleneck = result["bottlenecks"][0]
        
        assert bottleneck["component_type"] == "datastore"
        assert bottleneck["component_name"] == "postgres-db"
        assert bottleneck["constraint_type"] == "availability"
        assert bottleneck["severity"] == "high"
        assert bottleneck["impact"]["metric"] == "availability"
        assert bottleneck["impact"]["original_value"] == 99.5
        assert bottleneck["impact"]["constrained_value"] == 98.5
        assert bottleneck["impact"]["reduction"] == 1.0
        assert "postgres-db" in bottleneck["description"]
        assert "limits service availability" in bottleneck["description"]
    
    def test_datastore_latency_bottleneck(self, recommendation_engine):
        """Test identification of datastore as latency bottleneck."""
        infrastructure = {
            "datastores": [
                {
                    "name": "slow-db",
                    "type": "mongodb",
                    "availability_slo": 99.9,
                    "latency_p95_ms": 200.0
                }
            ],
            "caches": [],
            "message_queues": []
        }
        
        # Original recommendation was too aggressive
        original_recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 50.0,  # Too low
            "latency_p99_ms": 100.0,
            "error_rate_percent": 1.0
        }
        
        # After constraint: latency raised to datastore minimum
        constrained_recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 205.0,  # 200 + 5 network overhead
            "latency_p99_ms": 307.5,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.identify_infrastructure_bottlenecks(
            service_id="test-service",
            infrastructure_constrained_recommendations=constrained_recommendations,
            original_recommendations=original_recommendations,
            infrastructure=infrastructure,
            network_overhead_ms=5.0
        )
        
        # Should identify as active bottleneck
        assert len(result["bottlenecks"]) == 1
        bottleneck = result["bottlenecks"][0]
        
        assert bottleneck["component_type"] == "datastore"
        assert bottleneck["component_name"] == "slow-db"
        assert bottleneck["constraint_type"] == "latency"
        assert bottleneck["severity"] == "high"
        assert bottleneck["impact"]["metric"] == "latency_p95_ms"
        assert bottleneck["impact"]["original_value"] == 50.0
        assert bottleneck["impact"]["constrained_value"] == 205.0
        assert bottleneck["impact"]["increase"] == 155.0
        assert "slow-db" in bottleneck["description"]
        assert "sets minimum service latency" in bottleneck["description"]
    
    def test_multiple_bottlenecks(self, recommendation_engine):
        """Test identification of multiple bottlenecks."""
        infrastructure = {
            "datastores": [
                {
                    "name": "db1",
                    "type": "postgresql",
                    "availability_slo": 99.0,
                    "latency_p95_ms": 100.0
                },
                {
                    "name": "db2",
                    "type": "mongodb",
                    "availability_slo": 98.5,  # Even more restrictive
                    "latency_p95_ms": 150.0
                }
            ],
            "caches": [],
            "message_queues": []
        }
        
        original_recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 50.0,
            "latency_p99_ms": 100.0,
            "error_rate_percent": 1.0
        }
        
        # Both datastores constrain
        constrained_recommendations = {
            "availability": 98.0,  # 98.5 - 0.5 margin (most restrictive)
            "latency_p95_ms": 155.0,  # 150 + 5 network (most restrictive)
            "latency_p99_ms": 232.5,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.identify_infrastructure_bottlenecks(
            service_id="test-service",
            infrastructure_constrained_recommendations=constrained_recommendations,
            original_recommendations=original_recommendations,
            infrastructure=infrastructure,
            availability_margin=0.5,
            network_overhead_ms=5.0
        )
        
        # Should identify multiple bottlenecks
        assert len(result["bottlenecks"]) >= 2
        
        # Check that both datastores are identified
        bottleneck_names = [b["component_name"] for b in result["bottlenecks"]]
        assert "db1" in bottleneck_names or "db2" in bottleneck_names


class TestBottleneckIdentificationNearBottlenecks:
    """Test identification of near-bottlenecks."""
    
    def test_near_availability_bottleneck(self, recommendation_engine):
        """Test identification of near-bottleneck for availability."""
        infrastructure = {
            "datastores": [
                {
                    "name": "postgres-db",
                    "type": "postgresql",
                    "availability_slo": 99.5,
                    "latency_p95_ms": 50.0
                }
            ],
            "caches": [],
            "message_queues": []
        }
        
        # Service availability is close to datastore limit (within 1% headroom)
        original_recommendations = {
            "availability": 98.6,  # Close to 99.5 - 0.5 = 99.0
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        constrained_recommendations = original_recommendations.copy()
        
        result = recommendation_engine.identify_infrastructure_bottlenecks(
            service_id="test-service",
            infrastructure_constrained_recommendations=constrained_recommendations,
            original_recommendations=original_recommendations,
            infrastructure=infrastructure,
            availability_margin=0.5
        )
        
        # Should identify as near-bottleneck
        assert len(result["near_bottlenecks"]) == 1
        near_bottleneck = result["near_bottlenecks"][0]
        
        assert near_bottleneck["component_type"] == "datastore"
        assert near_bottleneck["component_name"] == "postgres-db"
        assert near_bottleneck["constraint_type"] == "availability"
        assert near_bottleneck["severity"] == "medium"
        assert near_bottleneck["headroom"] == pytest.approx(99.0 - 98.6, abs=0.1)
        assert "close to limiting" in near_bottleneck["description"]
    
    def test_near_latency_bottleneck(self, recommendation_engine):
        """Test identification of near-bottleneck for latency."""
        infrastructure = {
            "datastores": [
                {
                    "name": "postgres-db",
                    "type": "postgresql",
                    "availability_slo": 99.9,
                    "latency_p95_ms": 100.0
                }
            ],
            "caches": [],
            "message_queues": []
        }
        
        # Service latency is close to datastore minimum (within 10ms headroom)
        original_recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 110.0,  # Close to 100 + 5 = 105
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        constrained_recommendations = original_recommendations.copy()
        
        result = recommendation_engine.identify_infrastructure_bottlenecks(
            service_id="test-service",
            infrastructure_constrained_recommendations=constrained_recommendations,
            original_recommendations=original_recommendations,
            infrastructure=infrastructure,
            network_overhead_ms=5.0
        )
        
        # Should identify as near-bottleneck
        assert len(result["near_bottlenecks"]) == 1
        near_bottleneck = result["near_bottlenecks"][0]
        
        assert near_bottleneck["component_type"] == "datastore"
        assert near_bottleneck["component_name"] == "postgres-db"
        assert near_bottleneck["constraint_type"] == "latency"
        assert near_bottleneck["severity"] == "medium"
        assert near_bottleneck["headroom"] == pytest.approx(110.0 - 105.0, abs=0.1)
        assert "close to limiting" in near_bottleneck["description"]


class TestBottleneckIdentificationRisks:
    """Test identification of potential risks."""
    
    def test_message_queue_risk(self, recommendation_engine):
        """Test identification of message queue as potential risk."""
        infrastructure = {
            "datastores": [],
            "caches": [],
            "message_queues": [
                {
                    "name": "rabbitmq-queue",
                    "type": "rabbitmq"
                }
            ]
        }
        
        recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.identify_infrastructure_bottlenecks(
            service_id="test-service",
            infrastructure_constrained_recommendations=recommendations,
            original_recommendations=recommendations,
            infrastructure=infrastructure
        )
        
        # Should identify message queue as risk
        assert len(result["risks"]) == 1
        risk = result["risks"][0]
        
        assert risk["component_type"] == "message_queue"
        assert risk["component_name"] == "rabbitmq-queue"
        assert risk["severity"] == "low"
        assert "may introduce additional latency" in risk["description"]
    
    def test_multiple_message_queues(self, recommendation_engine):
        """Test identification of multiple message queues as risks."""
        infrastructure = {
            "datastores": [],
            "caches": [],
            "message_queues": [
                {
                    "name": "kafka-queue",
                    "type": "kafka"
                },
                {
                    "name": "rabbitmq-queue",
                    "type": "rabbitmq"
                }
            ]
        }
        
        recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.identify_infrastructure_bottlenecks(
            service_id="test-service",
            infrastructure_constrained_recommendations=recommendations,
            original_recommendations=recommendations,
            infrastructure=infrastructure
        )
        
        # Should identify both queues as risks
        assert len(result["risks"]) == 2
        risk_names = [r["component_name"] for r in result["risks"]]
        assert "kafka-queue" in risk_names
        assert "rabbitmq-queue" in risk_names


class TestBottleneckIdentificationSummary:
    """Test summary generation."""
    
    def test_summary_with_bottlenecks(self, recommendation_engine):
        """Test summary when bottlenecks are identified."""
        infrastructure = {
            "datastores": [
                {
                    "name": "postgres-db",
                    "type": "postgresql",
                    "availability_slo": 99.0,
                    "latency_p95_ms": 100.0
                }
            ],
            "caches": [],
            "message_queues": []
        }
        
        original_recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 50.0,
            "latency_p99_ms": 100.0,
            "error_rate_percent": 1.0
        }
        
        constrained_recommendations = {
            "availability": 98.5,
            "latency_p95_ms": 105.0,
            "latency_p99_ms": 157.5,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.identify_infrastructure_bottlenecks(
            service_id="test-service",
            infrastructure_constrained_recommendations=constrained_recommendations,
            original_recommendations=original_recommendations,
            infrastructure=infrastructure,
            availability_margin=0.5,
            network_overhead_ms=5.0
        )
        
        # Should have a meaningful summary
        assert "active bottleneck" in result["summary"]
        assert "postgres-db" in result["summary"]
        assert result["total_count"] >= 1
    
    def test_summary_with_no_bottlenecks(self, recommendation_engine):
        """Test summary when no bottlenecks are identified."""
        infrastructure = {
            "datastores": [],
            "caches": [],
            "message_queues": []
        }
        
        recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.identify_infrastructure_bottlenecks(
            service_id="test-service",
            infrastructure_constrained_recommendations=recommendations,
            original_recommendations=recommendations,
            infrastructure=infrastructure
        )
        
        # Should have a clear "no bottlenecks" message
        assert result["summary"] == "No infrastructure bottlenecks identified"
        assert result["total_count"] == 0
        assert len(result["bottlenecks"]) == 0
        assert len(result["near_bottlenecks"]) == 0
        assert len(result["risks"]) == 0
    
    def test_summary_with_mixed_components(self, recommendation_engine):
        """Test summary with bottlenecks, near-bottlenecks, and risks."""
        infrastructure = {
            "datastores": [
                {
                    "name": "db1",
                    "type": "postgresql",
                    "availability_slo": 99.0,
                    "latency_p95_ms": 50.0
                },
                {
                    "name": "db2",
                    "type": "mongodb",
                    "availability_slo": 99.5,
                    "latency_p95_ms": 100.0
                }
            ],
            "caches": [],
            "message_queues": [
                {
                    "name": "kafka-queue",
                    "type": "kafka"
                }
            ]
        }
        
        original_recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        # db1 is active bottleneck, db2 is near-bottleneck
        constrained_recommendations = {
            "availability": 98.5,  # Constrained by db1
            "latency_p95_ms": 100.0,  # Not constrained
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.identify_infrastructure_bottlenecks(
            service_id="test-service",
            infrastructure_constrained_recommendations=constrained_recommendations,
            original_recommendations=original_recommendations,
            infrastructure=infrastructure,
            availability_margin=0.5
        )
        
        # Should have comprehensive summary
        summary = result["summary"]
        assert "active bottleneck" in summary or "bottleneck" in summary
        assert "risk" in summary
        assert result["total_count"] >= 2


class TestBottleneckIdentificationEdgeCases:
    """Test edge cases."""
    
    def test_no_infrastructure_components(self, recommendation_engine):
        """Test with no infrastructure components."""
        infrastructure = {
            "datastores": [],
            "caches": [],
            "message_queues": []
        }
        
        recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.identify_infrastructure_bottlenecks(
            service_id="test-service",
            infrastructure_constrained_recommendations=recommendations,
            original_recommendations=recommendations,
            infrastructure=infrastructure
        )
        
        assert len(result["bottlenecks"]) == 0
        assert len(result["near_bottlenecks"]) == 0
        assert len(result["risks"]) == 0
        assert result["summary"] == "No infrastructure bottlenecks identified"
    
    def test_datastore_without_slo_values(self, recommendation_engine):
        """Test datastore without availability or latency values."""
        infrastructure = {
            "datastores": [
                {
                    "name": "unknown-db",
                    "type": "unknown"
                    # No availability_slo or latency_p95_ms
                }
            ],
            "caches": [],
            "message_queues": []
        }
        
        recommendations = {
            "availability": 99.5,
            "latency_p95_ms": 100.0,
            "latency_p99_ms": 200.0,
            "error_rate_percent": 1.0
        }
        
        result = recommendation_engine.identify_infrastructure_bottlenecks(
            service_id="test-service",
            infrastructure_constrained_recommendations=recommendations,
            original_recommendations=recommendations,
            infrastructure=infrastructure
        )
        
        # Should not identify as bottleneck since no SLO values
        assert len(result["bottlenecks"]) == 0
        assert len(result["near_bottlenecks"]) == 0
