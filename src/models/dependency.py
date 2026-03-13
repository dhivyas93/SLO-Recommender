"""Dependency graph models."""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from pydantic import BaseModel, Field


class WarningType(str, Enum):
    """Types of warnings that can be generated during graph construction."""
    MISSING_DEPENDENCY = "missing_dependency"
    NO_TARGET = "no_target"
    ISOLATED_NODE = "isolated_node"


class GraphWarning(BaseModel):
    """Warning generated during graph construction or analysis."""
    warning_type: WarningType = Field(..., description="Type of warning")
    service_id: str = Field(..., description="Service ID related to the warning")
    message: str = Field(..., description="Human-readable warning message")
    target_id: Optional[str] = Field(None, description="Target service/infrastructure ID if applicable")
    timestamp: datetime = Field(default_factory=datetime.now, description="When the warning was generated")


class DependencyEdge(BaseModel):
    """Dependency edge between services."""
    target_service_id: Optional[str] = Field(None, description="Target service ID")
    target_infrastructure_id: Optional[str] = Field(None, description="Target infrastructure ID")
    infrastructure_type: Optional[str] = Field(None, description="Infrastructure type if applicable")
    dependency_type: str = Field(..., description="Dependency type (synchronous, asynchronous)")
    timeout_ms: Optional[int] = Field(None, gt=0, description="Timeout in milliseconds")
    retry_policy: Optional[str] = Field(None, description="Retry policy")
    criticality: str = Field(..., description="Criticality level (high, medium, low)")


class ServiceDependency(BaseModel):
    """Service with its dependencies."""
    service_id: str = Field(..., description="Service identifier")
    dependencies: List[DependencyEdge] = Field(default_factory=list, description="List of dependencies")


class CircularDependency(BaseModel):
    """Circular dependency detection result."""
    cycle: List[str] = Field(..., description="List of service IDs forming the cycle")
    detected_at: datetime = Field(..., description="Detection timestamp")


class DependencyGraph(BaseModel):
    """Complete dependency graph."""
    version: str = Field(..., description="Graph version")
    updated_at: datetime = Field(..., description="Last update timestamp")
    services: List[ServiceDependency] = Field(..., description="List of services with dependencies")
    circular_dependencies: List[CircularDependency] = Field(
        default_factory=list, description="Detected circular dependencies"
    )


class CriticalPath(BaseModel):
    """Critical path analysis result."""
    path: List[str] = Field(..., description="Service IDs in the critical path")
    total_latency_budget_ms: float = Field(..., gt=0, description="Total latency budget")
    bottleneck_service: str = Field(..., description="Bottleneck service ID")


class AnalyzedService(BaseModel):
    """Analyzed service with computed metrics."""
    service_id: str = Field(..., description="Service identifier")
    upstream_services: List[str] = Field(default_factory=list, description="Upstream service IDs")
    downstream_services: List[str] = Field(default_factory=list, description="Downstream service IDs")
    upstream_count: int = Field(..., ge=0, description="Number of upstream services")
    downstream_count: int = Field(..., ge=0, description="Number of downstream services")
    depth_from_root: int = Field(..., ge=0, description="Depth from root in the graph")
    fanout: int = Field(..., ge=0, description="Fanout (number of direct downstream services)")
    cascading_impact_score: float = Field(..., ge=0, le=1, description="Cascading impact score (0-1)")
    critical_paths: List[CriticalPath] = Field(default_factory=list, description="Critical paths")
    is_in_circular_dependency: bool = Field(..., description="Whether service is in a circular dependency")


class GraphStatistics(BaseModel):
    """Graph-wide statistics."""
    total_services: int = Field(..., ge=0, description="Total number of services")
    total_edges: int = Field(..., ge=0, description="Total number of edges")
    max_depth: int = Field(..., ge=0, description="Maximum depth in the graph")
    circular_dependency_count: int = Field(..., ge=0, description="Number of circular dependencies")


class AnalyzedDependencyGraph(BaseModel):
    """Analyzed dependency graph with computed metrics."""
    version: str = Field(..., description="Graph version")
    analyzed_at: datetime = Field(..., description="Analysis timestamp")
    services: List[AnalyzedService] = Field(..., description="Analyzed services")
    graph_statistics: GraphStatistics = Field(..., description="Graph-wide statistics")
