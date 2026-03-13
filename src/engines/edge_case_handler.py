"""
Edge case handler for SLO recommendation system.

Handles various edge cases:
- Independent services (no dependencies)
- Circular dependencies
- Metadata conflicts
- Graph versioning
"""

import logging
from typing import Dict, Any, List, Optional, Set, Tuple
from datetime import datetime
from src.algorithms.service_graph import ServiceGraph

logger = logging.getLogger(__name__)


class EdgeCaseHandler:
    """
    Handles edge cases in SLO recommendation generation.
    """
    
    def __init__(self):
        """Initialize the edge case handler."""
        self.conflict_threshold = 0.1  # 10% difference threshold
    
    def handle_independent_service(
        self,
        service_id: str,
        metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Handle services with no dependencies.
        
        Args:
            service_id: Service identifier
            metrics: Service metrics
            
        Returns:
            Recommendation for independent service
        """
        logger.info(f"Handling independent service: {service_id}")
        
        # For independent services, recommendations are based solely on metrics
        # No dependency constraints apply
        
        return {
            "service_id": service_id,
            "is_independent": True,
            "explanation": "Service has no dependencies. Recommendations based solely on metrics.",
            "dependency_constraints": [],
            "notes": "This service operates independently and does not depend on other services."
        }
    
    def handle_circular_dependencies(
        self,
        service_ids: List[str],
        graph: ServiceGraph
    ) -> Dict[str, Any]:
        """
        Handle services in circular dependencies.
        
        Ensures consistent SLOs within the circular dependency group.
        
        Args:
            service_ids: List of service IDs in the cycle
            graph: Service graph
            
        Returns:
            Handling strategy for circular dependencies
        """
        logger.info(f"Handling circular dependency: {' -> '.join(service_ids)}")
        
        return {
            "services_in_cycle": service_ids,
            "cycle_length": len(service_ids),
            "consistency_requirement": {
                "availability_tolerance_percent": 1.0,  # Within 1%
                "latency_tolerance_percent": 10.0,  # Within 10%
                "error_rate_tolerance_percent": 5.0  # Within 5%
            },
            "recommendation": "Apply consistent SLOs to all services in the cycle",
            "notes": "Services in circular dependencies must have compatible SLOs"
        }
    
    def detect_metadata_conflicts(
        self,
        service_id: str,
        declared_metadata: Dict[str, Any],
        observed_metrics: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Detect conflicts between declared metadata and observed behavior.
        
        Args:
            service_id: Service identifier
            declared_metadata: Declared service metadata
            observed_metrics: Observed metrics
            
        Returns:
            Conflict detection results
        """
        conflicts = []
        
        # Check timeout vs observed latency
        if "timeout_ms" in declared_metadata and "latency" in observed_metrics:
            declared_timeout = declared_metadata.get("timeout_ms", 0)
            observed_p99 = observed_metrics.get("latency", {}).get("p99_ms", 0)
            
            if declared_timeout > 0 and observed_p99 > 0:
                ratio = observed_p99 / declared_timeout
                if ratio > 0.8:  # If observed is > 80% of timeout
                    conflicts.append({
                        "type": "timeout_conflict",
                        "declared_timeout_ms": declared_timeout,
                        "observed_p99_ms": observed_p99,
                        "severity": "high" if ratio > 0.95 else "medium",
                        "message": f"Observed latency ({observed_p99}ms) is close to declared timeout ({declared_timeout}ms)"
                    })
        
        # Check availability vs error rate
        if "availability_slo" in declared_metadata and "error_rate" in observed_metrics:
            declared_availability = declared_metadata.get("availability_slo", 100)
            observed_error_rate = observed_metrics.get("error_rate", {}).get("percent", 0)
            
            # Rough conversion: error_rate_percent ≈ (100 - availability)
            implied_availability = 100 - observed_error_rate
            
            if abs(declared_availability - implied_availability) > self.conflict_threshold:
                conflicts.append({
                    "type": "availability_conflict",
                    "declared_availability": declared_availability,
                    "implied_availability": implied_availability,
                    "severity": "medium",
                    "message": f"Declared availability ({declared_availability}%) differs from observed ({implied_availability}%)"
                })
        
        return {
            "service_id": service_id,
            "conflicts_detected": len(conflicts),
            "conflicts": conflicts,
            "resolution_strategy": "Prioritize observed data in recommendations"
        }
    
    def prioritize_observed_data(
        self,
        declared_value: Optional[float],
        observed_value: Optional[float],
        metric_name: str
    ) -> Tuple[float, str]:
        """
        Prioritize observed data over declared metadata.
        
        Args:
            declared_value: Declared value from metadata
            observed_value: Observed value from metrics
            metric_name: Name of the metric
            
        Returns:
            Tuple of (selected_value, source)
        """
        if observed_value is not None:
            logger.info(f"Using observed value for {metric_name}: {observed_value}")
            return observed_value, "observed"
        elif declared_value is not None:
            logger.warning(f"Using declared value for {metric_name}: {declared_value} (no observed data)")
            return declared_value, "declared"
        else:
            logger.warning(f"No value available for {metric_name}")
            return None, "none"
    
    def enforce_consistency(
        self,
        service_ids: List[str],
        recommendations: Dict[str, Dict[str, Any]],
        consistency_requirements: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Enforce consistency constraints on recommendations.
        
        Args:
            service_ids: List of service IDs to enforce consistency on
            recommendations: Dictionary mapping service IDs to recommendations
            consistency_requirements: Tolerance levels for each metric
            
        Returns:
            Consistency enforcement results
        """
        if not service_ids or len(service_ids) < 2:
            return {"enforced": False, "reason": "Need at least 2 services"}
        
        # Extract SLO values for each service
        slo_values = {}
        for service_id in service_ids:
            if service_id in recommendations:
                rec = recommendations[service_id]
                if "recommendations" in rec and "balanced" in rec["recommendations"]:
                    slo_values[service_id] = rec["recommendations"]["balanced"]
        
        if not slo_values:
            return {"enforced": False, "reason": "No recommendations found"}
        
        # Check consistency
        inconsistencies = []
        
        # Get reference values (from first service)
        reference_service = service_ids[0]
        if reference_service not in slo_values:
            return {"enforced": False, "reason": "Reference service not found"}
        
        reference_slos = slo_values[reference_service]
        
        # Compare other services to reference
        for service_id in service_ids[1:]:
            if service_id not in slo_values:
                continue
            
            service_slos = slo_values[service_id]
            
            # Check availability
            if "availability" in reference_slos and "availability" in service_slos:
                ref_avail = reference_slos["availability"]
                service_avail = service_slos["availability"]
                tolerance = consistency_requirements.get("availability_tolerance_percent", 1.0)
                
                if abs(ref_avail - service_avail) > tolerance:
                    inconsistencies.append({
                        "service": service_id,
                        "metric": "availability",
                        "reference_value": ref_avail,
                        "service_value": service_avail,
                        "difference": abs(ref_avail - service_avail),
                        "tolerance": tolerance
                    })
        
        return {
            "enforced": len(inconsistencies) == 0,
            "inconsistencies": inconsistencies,
            "services_checked": len(service_ids),
            "consistency_requirements": consistency_requirements
        }
    
    def implement_graph_versioning(
        self,
        graph_data: Dict[str, Any],
        version: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Implement versioning for dependency graph updates.
        
        Args:
            graph_data: Graph data to version
            version: Optional version string
            
        Returns:
            Versioned graph data
        """
        if version is None:
            # Generate version from timestamp
            version = datetime.utcnow().isoformat() + "Z"
        
        versioned_graph = {
            "version": version,
            "created_at": datetime.utcnow().isoformat() + "Z",
            "graph_data": graph_data,
            "metadata": {
                "services_count": len(graph_data.get("services", [])),
                "edges_count": len(graph_data.get("edges", []))
            }
        }
        
        return versioned_graph
    
    def store_version_history(
        self,
        service_id: str,
        graph_versions: List[Dict[str, Any]],
        new_version: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Store version history for a graph.
        
        Args:
            service_id: Service identifier
            graph_versions: Existing version history
            new_version: New version to add
            
        Returns:
            Updated version history
        """
        # Add new version to history
        updated_history = graph_versions.copy() if graph_versions else []
        updated_history.append(new_version)
        
        # Keep only last 100 versions
        if len(updated_history) > 100:
            updated_history = updated_history[-100:]
        
        return {
            "service_id": service_id,
            "total_versions": len(updated_history),
            "versions": updated_history,
            "latest_version": new_version["version"],
            "oldest_version": updated_history[0]["version"] if updated_history else None
        }
    
    def detect_independent_services(
        self,
        graph: ServiceGraph
    ) -> List[str]:
        """
        Detect services with no dependencies.
        
        Args:
            graph: Service graph
            
        Returns:
            List of independent service IDs
        """
        independent_services = []
        
        for service_id in graph.get_all_nodes():
            upstream = graph.get_upstream_services(service_id)
            downstream = graph.get_downstream_services(service_id)
            
            if len(upstream) == 0 and len(downstream) == 0:
                independent_services.append(service_id)
        
        return independent_services
    
    def detect_circular_dependency_groups(
        self,
        graph: ServiceGraph
    ) -> List[List[str]]:
        """
        Detect all circular dependency groups.
        
        Args:
            graph: Service graph
            
        Returns:
            List of circular dependency groups
        """
        circular_groups = graph.detect_circular_dependencies()
        return circular_groups
