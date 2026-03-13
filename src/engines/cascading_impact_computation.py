"""Cascading impact computation engine for SLO changes."""

import logging
from typing import Dict, List, Optional, Set, Tuple
from collections import deque
from datetime import datetime
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class SLOChange(BaseModel):
    """Proposed SLO change for a service."""
    service_id: str = Field(..., description="Service ID")
    new_availability: Optional[float] = Field(None, ge=0, le=100, description="New availability percentage")
    new_latency_p95_ms: Optional[float] = Field(None, gt=0, description="New p95 latency in ms")
    new_latency_p99_ms: Optional[float] = Field(None, gt=0, description="New p99 latency in ms")
    new_error_rate_percent: Optional[float] = Field(None, ge=0, le=100, description="New error rate percentage")


class AffectedService(BaseModel):
    """Service affected by cascading impact."""
    service_id: str = Field(..., description="Service ID")
    impact_depth: int = Field(..., ge=1, description="Depth of impact (1 = direct, 2+ = cascading)")
    direct_upstream: Optional[str] = Field(None, description="Direct upstream service causing impact")
    risk_level: str = Field(..., description="Risk level: high, medium, low")
    recommended_adjustments: Dict[str, float] = Field(default_factory=dict, description="Recommended SLO adjustments")


class CriticalPathImpact(BaseModel):
    """Impact on a critical path."""
    source_service: str = Field(..., description="Source service of the change")
    critical_path: List[str] = Field(..., description="Services in the critical path")
    total_latency_budget_ms: float = Field(..., ge=0, description="Total latency budget")
    bottleneck_service: str = Field(..., description="Bottleneck service in the path")
    impact_on_path: str = Field(..., description="Impact level: High, Medium, Low")


class RiskAssessment(BaseModel):
    """Risk assessment of cascading impacts."""
    high_risk_count: int = Field(..., ge=0, description="Number of high-risk affected services")
    medium_risk_count: int = Field(..., ge=0, description="Number of medium-risk affected services")
    low_risk_count: int = Field(..., ge=0, description="Number of low-risk affected services")
    overall_risk: str = Field(..., description="Overall risk level: high, medium, low")


class CascadingImpactResult(BaseModel):
    """Result of cascading impact computation."""
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")
    proposed_changes_count: int = Field(..., ge=1, description="Number of proposed changes")
    analysis_depth: int = Field(..., ge=1, description="Maximum depth of analysis")
    affected_services: List[AffectedService] = Field(default_factory=list, description="Affected services")
    affected_services_count: int = Field(..., ge=0, description="Total number of affected services")
    critical_path_impacts: List[CriticalPathImpact] = Field(default_factory=list, description="Critical path impacts")
    risk_assessment: RiskAssessment = Field(..., description="Risk assessment")


class CascadingImpactComputation:
    """
    Compute cascading impact of SLO changes through the dependency graph.
    
    This engine analyzes how changes to one service's SLOs cascade through
    dependent services, computing direct and indirect impacts, and recommending
    adjustments to maintain consistency across the dependency chain.
    """

    def __init__(self, service_graph):
        """
        Initialize the cascading impact computation engine.
        
        Args:
            service_graph: ServiceGraph instance with the dependency graph
        """
        self.service_graph = service_graph
        self.logger = logging.getLogger(__name__)

    def compute_cascading_impact(
        self,
        proposed_changes: List[SLOChange],
        analysis_depth: int = 3,
        service_latencies: Optional[Dict[str, float]] = None
    ) -> CascadingImpactResult:
        """
        Compute cascading impact of proposed SLO changes.
        
        For each proposed change, this method:
        1. Identifies all downstream services affected
        2. Computes impact depth (distance from source)
        3. Assigns risk levels based on impact depth
        4. Recommends SLO adjustments for affected services
        5. Analyzes critical path impacts
        
        Args:
            proposed_changes: List of proposed SLO changes
            analysis_depth: Maximum depth to traverse (default: 3)
            service_latencies: Optional dict of service latencies for critical path analysis
            
        Returns:
            CascadingImpactResult with affected services and risk assessment
            
        Raises:
            ValueError: If proposed_changes is empty or analysis_depth is invalid
        """
        if not proposed_changes:
            raise ValueError("proposed_changes cannot be empty")
        
        if analysis_depth < 1:
            raise ValueError("analysis_depth must be >= 1")
        
        # Compute affected services through BFS
        affected_services_dict: Dict[str, AffectedService] = {}
        
        for change in proposed_changes:
            self._compute_impact_for_service(
                change,
                analysis_depth,
                affected_services_dict
            )
        
        # Compute recommended adjustments for each affected service
        for affected_id, affected_service in affected_services_dict.items():
            adjustments = self._compute_recommended_adjustments(
                affected_id,
                proposed_changes,
                affected_service.impact_depth
            )
            affected_service.recommended_adjustments = adjustments
        
        # Compute critical path impacts
        critical_path_impacts = self._compute_critical_path_impacts(
            proposed_changes,
            service_latencies
        )
        
        # Compute risk assessment
        risk_assessment = self._compute_risk_assessment(affected_services_dict)
        
        # Build result
        result = CascadingImpactResult(
            proposed_changes_count=len(proposed_changes),
            analysis_depth=analysis_depth,
            affected_services=list(affected_services_dict.values()),
            affected_services_count=len(affected_services_dict),
            critical_path_impacts=critical_path_impacts,
            risk_assessment=risk_assessment
        )
        
        return result

    def _compute_impact_for_service(
        self,
        change: SLOChange,
        analysis_depth: int,
        affected_services_dict: Dict[str, AffectedService]
    ) -> None:
        """
        Compute impact for a single proposed change using BFS.
        
        Args:
            change: Proposed SLO change
            analysis_depth: Maximum depth to traverse
            affected_services_dict: Dictionary to accumulate affected services
        """
        source_service = change.service_id
        
        # BFS to find all downstream services
        queue: deque = deque([(source_service, 0)])
        visited: Set[str] = {source_service}
        
        while queue:
            current_service, depth = queue.popleft()
            
            # Skip the source service itself
            if depth > 0:
                # Update or add affected service
                if current_service not in affected_services_dict:
                    risk_level = self._compute_risk_level(depth)
                    direct_upstream = source_service if depth == 1 else None
                    
                    affected_services_dict[current_service] = AffectedService(
                        service_id=current_service,
                        impact_depth=depth,
                        direct_upstream=direct_upstream,
                        risk_level=risk_level,
                        recommended_adjustments={}
                    )
                else:
                    # Update if this path is shorter (higher impact)
                    if depth < affected_services_dict[current_service].impact_depth:
                        affected_services_dict[current_service].impact_depth = depth
                        affected_services_dict[current_service].risk_level = self._compute_risk_level(depth)
                        if depth == 1:
                            affected_services_dict[current_service].direct_upstream = source_service
            
            # Continue BFS if within depth limit
            if depth < analysis_depth:
                downstream_services = self.service_graph.get_downstream_services(current_service)
                for downstream_service in downstream_services:
                    if downstream_service not in visited:
                        visited.add(downstream_service)
                        queue.append((downstream_service, depth + 1))

    def _compute_risk_level(self, depth: int) -> str:
        """
        Compute risk level based on impact depth.
        
        Args:
            depth: Impact depth (1 = direct, 2+ = cascading)
            
        Returns:
            Risk level: "high" (depth 1), "medium" (depth 2), "low" (depth 3+)
        """
        if depth == 1:
            return "high"
        elif depth == 2:
            return "medium"
        else:
            return "low"

    def _compute_recommended_adjustments(
        self,
        affected_service_id: str,
        proposed_changes: List[SLOChange],
        impact_depth: int
    ) -> Dict[str, float]:
        """
        Compute recommended SLO adjustments for an affected service.
        
        For each proposed change, if the affected service is downstream,
        recommend conservative adjustments to maintain consistency.
        
        Args:
            affected_service_id: Service ID to compute adjustments for
            proposed_changes: List of proposed changes
            impact_depth: Depth of impact for this service
            
        Returns:
            Dictionary of recommended adjustments
        """
        adjustments: Dict[str, float] = {}
        
        for change in proposed_changes:
            # Check if affected_service_id is downstream of change.service_id
            if self._is_downstream(affected_service_id, change.service_id):
                # Recommend conservative adjustments
                if change.new_availability is not None:
                    # Downstream availability should be less than upstream
                    # Apply margin based on impact depth
                    margin = 0.5 * impact_depth  # Larger margin for deeper impacts
                    recommended_availability = max(90.0, change.new_availability - margin)
                    adjustments["recommended_availability"] = round(recommended_availability, 2)
                
                if change.new_latency_p95_ms is not None:
                    # Add buffer for downstream processing
                    # Buffer increases with impact depth
                    buffer = 50 * impact_depth  # 50ms per depth level
                    recommended_latency_p95 = change.new_latency_p95_ms + buffer
                    adjustments["recommended_latency_p95_ms"] = round(recommended_latency_p95, 2)
                
                if change.new_latency_p99_ms is not None:
                    # Add larger buffer for p99
                    buffer = 100 * impact_depth  # 100ms per depth level
                    recommended_latency_p99 = change.new_latency_p99_ms + buffer
                    adjustments["recommended_latency_p99_ms"] = round(recommended_latency_p99, 2)
                
                if change.new_error_rate_percent is not None:
                    # Downstream error rate should be higher (more conservative)
                    # Increase based on impact depth
                    increase = 1.0 * impact_depth  # 1% per depth level
                    recommended_error_rate = min(100.0, change.new_error_rate_percent + increase)
                    adjustments["recommended_error_rate_percent"] = round(recommended_error_rate, 2)
        
        return adjustments

    def _is_downstream(self, service_id: str, upstream_service_id: str) -> bool:
        """
        Check if service_id is downstream of upstream_service_id.
        
        Args:
            service_id: Service to check
            upstream_service_id: Potential upstream service
            
        Returns:
            True if service_id is downstream of upstream_service_id
        """
        # BFS to check if service_id is reachable from upstream_service_id
        visited: Set[str] = set()
        queue: deque = deque([upstream_service_id])
        
        while queue:
            current = queue.popleft()
            
            if current == service_id:
                return True
            
            if current in visited:
                continue
            visited.add(current)
            
            downstream = self.service_graph.get_downstream_services(current)
            for next_service in downstream:
                if next_service not in visited:
                    queue.append(next_service)
        
        return False

    def _compute_critical_path_impacts(
        self,
        proposed_changes: List[SLOChange],
        service_latencies: Optional[Dict[str, float]] = None
    ) -> List[CriticalPathImpact]:
        """
        Compute impacts on critical paths.
        
        Args:
            proposed_changes: List of proposed changes
            service_latencies: Optional dict of service latencies
            
        Returns:
            List of critical path impacts
        """
        impacts: List[CriticalPathImpact] = []
        
        # Build service latencies dictionary
        if service_latencies is None:
            service_latencies = {}
        
        # Add proposed latencies
        for change in proposed_changes:
            if change.new_latency_p95_ms is not None:
                service_latencies[change.service_id] = change.new_latency_p95_ms
        
        # Add default latencies for services not in proposed changes
        for node in self.service_graph.get_all_nodes():
            if node not in service_latencies:
                service_latencies[node] = 100  # Default latency
        
        # Compute critical paths for each proposed change
        for change in proposed_changes:
            try:
                critical_path = self.service_graph.compute_critical_path(
                    change.service_id,
                    service_latencies
                )
                
                if critical_path and critical_path.get("path"):
                    # Determine impact level
                    if change.service_id == critical_path.get("bottleneck_service"):
                        impact_level = "High"
                    elif change.service_id in critical_path.get("path", [])[:2]:
                        impact_level = "Medium"
                    else:
                        impact_level = "Low"
                    
                    impact = CriticalPathImpact(
                        source_service=change.service_id,
                        critical_path=critical_path.get("path", []),
                        total_latency_budget_ms=critical_path.get("total_latency_ms", 0),
                        bottleneck_service=critical_path.get("bottleneck_service", ""),
                        impact_on_path=impact_level
                    )
                    impacts.append(impact)
            except Exception as e:
                self.logger.warning(
                    f"Could not compute critical path for {change.service_id}: {str(e)}"
                )
        
        return impacts

    def _compute_risk_assessment(
        self,
        affected_services_dict: Dict[str, AffectedService]
    ) -> RiskAssessment:
        """
        Compute overall risk assessment.
        
        Args:
            affected_services_dict: Dictionary of affected services
            
        Returns:
            RiskAssessment with counts and overall risk level
        """
        high_risk_count = sum(
            1 for s in affected_services_dict.values() if s.risk_level == "high"
        )
        medium_risk_count = sum(
            1 for s in affected_services_dict.values() if s.risk_level == "medium"
        )
        low_risk_count = sum(
            1 for s in affected_services_dict.values() if s.risk_level == "low"
        )
        
        # Determine overall risk
        if high_risk_count > 0:
            overall_risk = "high"
        elif medium_risk_count > 0:
            overall_risk = "medium"
        else:
            overall_risk = "low"
        
        return RiskAssessment(
            high_risk_count=high_risk_count,
            medium_risk_count=medium_risk_count,
            low_risk_count=low_risk_count,
            overall_risk=overall_risk
        )
