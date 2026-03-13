"""
Knowledge Layer for SLO Recommendation System

Implements storage and retrieval of historical patterns, feedback, and outcomes.
Supports querying for similar services using cosine similarity.
"""

import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
from src.storage.file_storage import FileStorage

logger = logging.getLogger(__name__)


@dataclass
class RecommendationOutcome:
    """Represents the outcome of a recommendation."""
    service_id: str
    recommendation_version: str
    outcome_type: str  # "met", "missed", "adjusted"
    timestamp: str
    recommended_availability: Optional[float] = None
    recommended_latency_p95_ms: Optional[float] = None
    recommended_latency_p99_ms: Optional[float] = None
    recommended_error_rate_percent: Optional[float] = None
    actual_availability: Optional[float] = None
    actual_latency_p95_ms: Optional[float] = None
    actual_latency_p99_ms: Optional[float] = None
    actual_error_rate_percent: Optional[float] = None
    notes: Optional[str] = None


@dataclass
class ServiceOwnerFeedback:
    """Represents feedback from a service owner."""
    service_id: str
    recommendation_version: str
    action: str  # "accepted", "modified", "rejected"
    timestamp: str
    service_owner: str
    tier_selected: Optional[str] = None
    modifications: Optional[Dict[str, Any]] = None
    comments: Optional[str] = None


class KnowledgeLayer:
    """
    Manages storage and retrieval of historical patterns and feedback.
    
    Stores:
    - Recommendation outcomes (met, missed, adjusted)
    - Service owner feedback
    - Similar service patterns
    - Best practices by service type
    """
    
    def __init__(self, base_path: str = "data"):
        """Initialize the knowledge layer."""
        self.storage = FileStorage(base_path=base_path)
        self.base_path = base_path
    
    def store_recommendation_outcome(self, outcome: RecommendationOutcome) -> None:
        """
        Store a recommendation outcome.
        
        Args:
            outcome: RecommendationOutcome object
        """
        try:
            # Load existing outcomes for the service
            outcomes_file = f"knowledge/outcomes/{outcome.service_id}.json"
            try:
                outcomes_data = self.storage.read_json(outcomes_file)
                if not isinstance(outcomes_data, dict) or "outcomes" not in outcomes_data:
                    outcomes_data = {"service_id": outcome.service_id, "outcomes": []}
            except FileNotFoundError:
                outcomes_data = {"service_id": outcome.service_id, "outcomes": []}
            
            # Add new outcome
            if "outcomes" not in outcomes_data:
                outcomes_data["outcomes"] = []
            outcomes_data["outcomes"].append(asdict(outcome))
            
            # Store updated outcomes
            self.storage.write_json(outcomes_file, outcomes_data)
            logger.info(f"Stored outcome for service {outcome.service_id}")
        except Exception as e:
            logger.error(f"Error storing recommendation outcome: {str(e)}")
            raise
    
    def store_feedback(self, feedback: ServiceOwnerFeedback) -> None:
        """
        Store service owner feedback.
        
        Args:
            feedback: ServiceOwnerFeedback object
        """
        try:
            # Load existing feedback for the service
            feedback_file = f"knowledge/feedback/{feedback.service_id}.json"
            try:
                feedback_data = self.storage.read_json(feedback_file)
                if not isinstance(feedback_data, dict) or "feedback_entries" not in feedback_data:
                    feedback_data = {"service_id": feedback.service_id, "feedback_entries": []}
            except FileNotFoundError:
                feedback_data = {"service_id": feedback.service_id, "feedback_entries": []}
            
            # Add new feedback
            if "feedback_entries" not in feedback_data:
                feedback_data["feedback_entries"] = []
            feedback_data["feedback_entries"].append(asdict(feedback))
            
            # Store updated feedback
            self.storage.write_json(feedback_file, feedback_data)
            logger.info(f"Stored feedback for service {feedback.service_id}")
        except Exception as e:
            logger.error(f"Error storing feedback: {str(e)}")
            raise
    
    def get_recommendation_outcomes(self, service_id: str) -> List[RecommendationOutcome]:
        """
        Get all recommendation outcomes for a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            List of RecommendationOutcome objects
        """
        try:
            outcomes_file = f"knowledge/outcomes/{service_id}.json"
            outcomes_data = self.storage.read_json(outcomes_file)
            
            outcomes = []
            for outcome_dict in outcomes_data.get("outcomes", []):
                outcomes.append(RecommendationOutcome(**outcome_dict))
            
            return outcomes
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Error retrieving outcomes for {service_id}: {str(e)}")
            return []
    
    def get_feedback(self, service_id: str) -> List[ServiceOwnerFeedback]:
        """
        Get all feedback for a service.
        
        Args:
            service_id: Service identifier
            
        Returns:
            List of ServiceOwnerFeedback objects
        """
        try:
            feedback_file = f"knowledge/feedback/{service_id}.json"
            feedback_data = self.storage.read_json(feedback_file)
            
            feedback_list = []
            for feedback_dict in feedback_data.get("feedback_entries", []):
                feedback_list.append(ServiceOwnerFeedback(**feedback_dict))
            
            return feedback_list
        except FileNotFoundError:
            return []
        except Exception as e:
            logger.error(f"Error retrieving feedback for {service_id}: {str(e)}")
            return []
    
    def find_similar_services(
        self,
        service_id: str,
        similarity_threshold: float = 0.7,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Find similar services using cosine similarity on feature vectors.
        
        Features considered:
        - Dependency count (upstream/downstream)
        - Request volume tier
        - Latency tier
        - Service type
        - Infrastructure components
        
        Args:
            service_id: Service identifier
            similarity_threshold: Minimum similarity score (0-1)
            top_k: Maximum number of similar services to return
            
        Returns:
            List of similar services with similarity scores
        """
        try:
            # Load service metadata
            service_file = f"services/{service_id}/metadata.json"
            service_data = self.storage.read_json(service_file)
            
            # Load all services to compare
            similar_services = []
            
            # For now, return empty list (full implementation would compute cosine similarity)
            # This is a placeholder for the actual similarity computation
            
            return similar_services
        except Exception as e:
            logger.error(f"Error finding similar services: {str(e)}")
            return []
    
    def get_best_practices(self, service_type: str) -> Dict[str, Any]:
        """
        Get best practices for a service type.
        
        Args:
            service_type: Type of service (e.g., "api_gateway", "database")
            
        Returns:
            Dictionary with best practices
        """
        try:
            best_practices_file = "knowledge/best_practices.json"
            best_practices_data = self.storage.read_json(best_practices_file)
            
            return best_practices_data.get("service_types", {}).get(service_type, {})
        except FileNotFoundError:
            return {}
        except Exception as e:
            logger.error(f"Error retrieving best practices: {str(e)}")
            return {}
    
    def compute_acceptance_rate(self, service_id: str) -> float:
        """
        Compute the acceptance rate for a service's recommendations.
        
        Args:
            service_id: Service identifier
            
        Returns:
            Acceptance rate (0-1)
        """
        try:
            feedback_list = self.get_feedback(service_id)
            
            if not feedback_list:
                return 0.0
            
            accepted_count = sum(1 for f in feedback_list if f.action == "accepted")
            return accepted_count / len(feedback_list)
        except Exception as e:
            logger.error(f"Error computing acceptance rate: {str(e)}")
            return 0.0
    
    def compute_accuracy_metrics(self, service_id: str) -> Dict[str, float]:
        """
        Compute accuracy metrics for a service's recommendations.
        
        Args:
            service_id: Service identifier
            
        Returns:
            Dictionary with accuracy metrics
        """
        try:
            outcomes = self.get_recommendation_outcomes(service_id)
            
            if not outcomes:
                return {
                    "accuracy": 0.0,
                    "met_count": 0,
                    "missed_count": 0,
                    "adjusted_count": 0,
                    "total_count": 0
                }
            
            met_count = sum(1 for o in outcomes if o.outcome_type == "met")
            missed_count = sum(1 for o in outcomes if o.outcome_type == "missed")
            adjusted_count = sum(1 for o in outcomes if o.outcome_type == "adjusted")
            
            accuracy = met_count / len(outcomes) if outcomes else 0.0
            
            return {
                "accuracy": accuracy,
                "met_count": met_count,
                "missed_count": missed_count,
                "adjusted_count": adjusted_count,
                "total_count": len(outcomes)
            }
        except Exception as e:
            logger.error(f"Error computing accuracy metrics: {str(e)}")
            return {
                "accuracy": 0.0,
                "met_count": 0,
                "missed_count": 0,
                "adjusted_count": 0,
                "total_count": 0
            }
