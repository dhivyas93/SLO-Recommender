"""
Unit tests for the Knowledge Layer.

Tests storage and retrieval of recommendation outcomes and feedback.
"""

import pytest
import json
import tempfile
import shutil
from datetime import datetime
from src.engines.knowledge_layer import (
    KnowledgeLayer,
    RecommendationOutcome,
    ServiceOwnerFeedback
)


@pytest.fixture
def temp_data_dir():
    """Create a temporary data directory for testing."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def knowledge_layer(temp_data_dir):
    """Create a KnowledgeLayer instance with temporary storage."""
    return KnowledgeLayer(base_path=temp_data_dir)


class TestRecommendationOutcomeStorage:
    """Test storage and retrieval of recommendation outcomes."""
    
    def test_store_and_retrieve_outcome(self, knowledge_layer):
        """Test storing and retrieving a recommendation outcome."""
        outcome = RecommendationOutcome(
            service_id="payment-api",
            recommendation_version="v1.0.0",
            outcome_type="met",
            timestamp=datetime.utcnow().isoformat() + "Z",
            recommended_availability=99.5,
            recommended_latency_p95_ms=200,
            actual_availability=99.6,
            actual_latency_p95_ms=180
        )
        
        # Store outcome
        knowledge_layer.store_recommendation_outcome(outcome)
        
        # Retrieve outcomes
        outcomes = knowledge_layer.get_recommendation_outcomes("payment-api")
        
        assert len(outcomes) == 1
        assert outcomes[0].service_id == "payment-api"
        assert outcomes[0].outcome_type == "met"
        assert outcomes[0].recommended_availability == 99.5
    
    def test_store_multiple_outcomes(self, knowledge_layer):
        """Test storing multiple outcomes for the same service."""
        outcomes_data = [
            RecommendationOutcome(
                service_id="payment-api",
                recommendation_version="v1.0.0",
                outcome_type="met",
                timestamp=datetime.utcnow().isoformat() + "Z",
                recommended_availability=99.5,
                actual_availability=99.6
            ),
            RecommendationOutcome(
                service_id="payment-api",
                recommendation_version="v1.1.0",
                outcome_type="missed",
                timestamp=datetime.utcnow().isoformat() + "Z",
                recommended_availability=99.7,
                actual_availability=99.2
            )
        ]
        
        for outcome in outcomes_data:
            knowledge_layer.store_recommendation_outcome(outcome)
        
        outcomes = knowledge_layer.get_recommendation_outcomes("payment-api")
        
        assert len(outcomes) == 2
        assert outcomes[0].outcome_type == "met"
        assert outcomes[1].outcome_type == "missed"
    
    def test_retrieve_nonexistent_outcomes(self, knowledge_layer):
        """Test retrieving outcomes for a service with no outcomes."""
        outcomes = knowledge_layer.get_recommendation_outcomes("nonexistent-service")
        
        assert outcomes == []


class TestServiceOwnerFeedbackStorage:
    """Test storage and retrieval of service owner feedback."""
    
    def test_store_and_retrieve_feedback(self, knowledge_layer):
        """Test storing and retrieving feedback."""
        feedback = ServiceOwnerFeedback(
            service_id="payment-api",
            recommendation_version="v1.0.0",
            action="accepted",
            timestamp=datetime.utcnow().isoformat() + "Z",
            service_owner="alice@example.com",
            tier_selected="balanced",
            comments="Looks good"
        )
        
        # Store feedback
        knowledge_layer.store_feedback(feedback)
        
        # Retrieve feedback
        feedback_list = knowledge_layer.get_feedback("payment-api")
        
        assert len(feedback_list) == 1
        assert feedback_list[0].service_id == "payment-api"
        assert feedback_list[0].action == "accepted"
        assert feedback_list[0].service_owner == "alice@example.com"
    
    def test_store_multiple_feedback(self, knowledge_layer):
        """Test storing multiple feedback entries."""
        feedback_data = [
            ServiceOwnerFeedback(
                service_id="payment-api",
                recommendation_version="v1.0.0",
                action="accepted",
                timestamp=datetime.utcnow().isoformat() + "Z",
                service_owner="alice@example.com"
            ),
            ServiceOwnerFeedback(
                service_id="payment-api",
                recommendation_version="v1.1.0",
                action="modified",
                timestamp=datetime.utcnow().isoformat() + "Z",
                service_owner="bob@example.com",
                modifications={"availability": {"recommended": 99.5, "actual": 99.7}}
            )
        ]
        
        for feedback in feedback_data:
            knowledge_layer.store_feedback(feedback)
        
        feedback_list = knowledge_layer.get_feedback("payment-api")
        
        assert len(feedback_list) == 2
        assert feedback_list[0].action == "accepted"
        assert feedback_list[1].action == "modified"
    
    def test_retrieve_nonexistent_feedback(self, knowledge_layer):
        """Test retrieving feedback for a service with no feedback."""
        feedback_list = knowledge_layer.get_feedback("nonexistent-service")
        
        assert feedback_list == []


class TestAcceptanceRateComputation:
    """Test acceptance rate computation."""
    
    def test_compute_acceptance_rate(self, knowledge_layer):
        """Test computing acceptance rate from feedback."""
        feedback_data = [
            ServiceOwnerFeedback(
                service_id="payment-api",
                recommendation_version="v1.0.0",
                action="accepted",
                timestamp=datetime.utcnow().isoformat() + "Z",
                service_owner="alice@example.com"
            ),
            ServiceOwnerFeedback(
                service_id="payment-api",
                recommendation_version="v1.1.0",
                action="accepted",
                timestamp=datetime.utcnow().isoformat() + "Z",
                service_owner="bob@example.com"
            ),
            ServiceOwnerFeedback(
                service_id="payment-api",
                recommendation_version="v1.2.0",
                action="rejected",
                timestamp=datetime.utcnow().isoformat() + "Z",
                service_owner="charlie@example.com"
            )
        ]
        
        for feedback in feedback_data:
            knowledge_layer.store_feedback(feedback)
        
        acceptance_rate = knowledge_layer.compute_acceptance_rate("payment-api")
        
        assert acceptance_rate == pytest.approx(2.0 / 3.0, rel=0.01)
    
    def test_acceptance_rate_no_feedback(self, knowledge_layer):
        """Test acceptance rate when no feedback exists."""
        acceptance_rate = knowledge_layer.compute_acceptance_rate("nonexistent-service")
        
        assert acceptance_rate == 0.0


class TestAccuracyMetricsComputation:
    """Test accuracy metrics computation."""
    
    def test_compute_accuracy_metrics(self, knowledge_layer):
        """Test computing accuracy metrics from outcomes."""
        outcomes_data = [
            RecommendationOutcome(
                service_id="payment-api",
                recommendation_version="v1.0.0",
                outcome_type="met",
                timestamp=datetime.utcnow().isoformat() + "Z"
            ),
            RecommendationOutcome(
                service_id="payment-api",
                recommendation_version="v1.1.0",
                outcome_type="met",
                timestamp=datetime.utcnow().isoformat() + "Z"
            ),
            RecommendationOutcome(
                service_id="payment-api",
                recommendation_version="v1.2.0",
                outcome_type="missed",
                timestamp=datetime.utcnow().isoformat() + "Z"
            ),
            RecommendationOutcome(
                service_id="payment-api",
                recommendation_version="v1.3.0",
                outcome_type="adjusted",
                timestamp=datetime.utcnow().isoformat() + "Z"
            )
        ]
        
        for outcome in outcomes_data:
            knowledge_layer.store_recommendation_outcome(outcome)
        
        metrics = knowledge_layer.compute_accuracy_metrics("payment-api")
        
        assert metrics["total_count"] == 4
        assert metrics["met_count"] == 2
        assert metrics["missed_count"] == 1
        assert metrics["adjusted_count"] == 1
        assert metrics["accuracy"] == pytest.approx(0.5, rel=0.01)
    
    def test_accuracy_metrics_no_outcomes(self, knowledge_layer):
        """Test accuracy metrics when no outcomes exist."""
        metrics = knowledge_layer.compute_accuracy_metrics("nonexistent-service")
        
        assert metrics["total_count"] == 0
        assert metrics["accuracy"] == 0.0
