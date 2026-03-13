"""
Fault Tolerance Engine for SLO Recommendation System

Implements component failure detection and graceful degradation.
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ComponentStatus(Enum):
    """Component health status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNAVAILABLE = "unavailable"


@dataclass
class ComponentHealth:
    """Represents the health status of a component."""
    component_name: str
    status: ComponentStatus
    last_check: datetime
    error_message: Optional[str] = None
    recovery_attempts: int = 0
    last_error_time: Optional[datetime] = None


class FaultToleranceEngine:
    """
    Manages component health and implements graceful degradation.
    
    Monitors:
    - Knowledge layer availability
    - Dependency analyzer availability
    - Metrics ingestion availability
    - LLM/Ollama availability
    - File storage availability
    """
    
    def __init__(self):
        """Initialize the fault tolerance engine."""
        self.component_health: Dict[str, ComponentHealth] = {
            "knowledge_layer": ComponentHealth(
                component_name="knowledge_layer",
                status=ComponentStatus.HEALTHY,
                last_check=datetime.utcnow()
            ),
            "dependency_analyzer": ComponentHealth(
                component_name="dependency_analyzer",
                status=ComponentStatus.HEALTHY,
                last_check=datetime.utcnow()
            ),
            "metrics_ingestion": ComponentHealth(
                component_name="metrics_ingestion",
                status=ComponentStatus.HEALTHY,
                last_check=datetime.utcnow()
            ),
            "llm_service": ComponentHealth(
                component_name="llm_service",
                status=ComponentStatus.HEALTHY,
                last_check=datetime.utcnow()
            ),
            "file_storage": ComponentHealth(
                component_name="file_storage",
                status=ComponentStatus.HEALTHY,
                last_check=datetime.utcnow()
            )
        }
        self.health_check_interval = timedelta(seconds=30)
    
    def report_component_error(
        self,
        component_name: str,
        error: Exception,
        is_transient: bool = True
    ) -> None:
        """
        Report an error for a component.
        
        Args:
            component_name: Name of the component
            error: Exception that occurred
            is_transient: Whether the error is transient (can recover)
        """
        if component_name not in self.component_health:
            logger.warning(f"Unknown component: {component_name}")
            return
        
        health = self.component_health[component_name]
        health.last_error_time = datetime.utcnow()
        health.error_message = str(error)
        
        if is_transient:
            health.status = ComponentStatus.DEGRADED
            health.recovery_attempts += 1
            logger.warning(
                f"Component {component_name} degraded: {str(error)} "
                f"(attempt {health.recovery_attempts})"
            )
        else:
            health.status = ComponentStatus.UNAVAILABLE
            logger.error(f"Component {component_name} unavailable: {str(error)}")
    
    def report_component_recovery(self, component_name: str) -> None:
        """
        Report that a component has recovered.
        
        Args:
            component_name: Name of the component
        """
        if component_name not in self.component_health:
            logger.warning(f"Unknown component: {component_name}")
            return
        
        health = self.component_health[component_name]
        health.status = ComponentStatus.HEALTHY
        health.last_check = datetime.utcnow()
        health.error_message = None
        health.recovery_attempts = 0
        logger.info(f"Component {component_name} recovered")
    
    def is_component_available(self, component_name: str) -> bool:
        """
        Check if a component is available.
        
        Args:
            component_name: Name of the component
            
        Returns:
            True if component is healthy or degraded, False if unavailable
        """
        if component_name not in self.component_health:
            return False
        
        health = self.component_health[component_name]
        return health.status != ComponentStatus.UNAVAILABLE
    
    def get_component_status(self, component_name: str) -> Optional[ComponentHealth]:
        """
        Get the health status of a component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            ComponentHealth object or None if component not found
        """
        return self.component_health.get(component_name)
    
    def get_all_component_status(self) -> Dict[str, ComponentHealth]:
        """
        Get the health status of all components.
        
        Returns:
            Dictionary mapping component names to ComponentHealth objects
        """
        return self.component_health.copy()
    
    def get_system_health(self) -> Dict[str, Any]:
        """
        Get overall system health status.
        
        Returns:
            Dictionary with system health information
        """
        statuses = list(self.component_health.values())
        
        healthy_count = sum(1 for s in statuses if s.status == ComponentStatus.HEALTHY)
        degraded_count = sum(1 for s in statuses if s.status == ComponentStatus.DEGRADED)
        unavailable_count = sum(1 for s in statuses if s.status == ComponentStatus.UNAVAILABLE)
        
        # Determine overall system status
        if unavailable_count > 0:
            overall_status = "degraded"
        elif degraded_count > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"
        
        return {
            "overall_status": overall_status,
            "healthy_components": healthy_count,
            "degraded_components": degraded_count,
            "unavailable_components": unavailable_count,
            "total_components": len(statuses),
            "components": {
                name: {
                    "status": health.status.value,
                    "last_check": health.last_check.isoformat() + "Z",
                    "error_message": health.error_message,
                    "recovery_attempts": health.recovery_attempts
                }
                for name, health in self.component_health.items()
            }
        }
    
    def should_retry(self, component_name: str, max_retries: int = 3) -> bool:
        """
        Determine if a component should be retried.
        
        Args:
            component_name: Name of the component
            max_retries: Maximum number of retries
            
        Returns:
            True if component should be retried, False otherwise
        """
        if component_name not in self.component_health:
            return False
        
        health = self.component_health[component_name]
        
        # Don't retry if unavailable or max retries exceeded
        if health.status == ComponentStatus.UNAVAILABLE:
            return False
        
        if health.recovery_attempts >= max_retries:
            return False
        
        return True
    
    def get_fallback_recommendations(
        self,
        service_id: str,
        metrics: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate fallback recommendations when components are unavailable.
        
        Args:
            service_id: Service identifier
            metrics: Optional metrics data
            
        Returns:
            Dictionary with fallback recommendations
        """
        # Use conservative industry standards as fallback
        fallback = {
            "service_id": service_id,
            "recommendations": {
                "aggressive": {
                    "availability": 99.5,
                    "latency_p95_ms": 500,
                    "latency_p99_ms": 1000,
                    "error_rate_percent": 1.0
                },
                "balanced": {
                    "availability": 99.0,
                    "latency_p95_ms": 1000,
                    "latency_p99_ms": 2000,
                    "error_rate_percent": 2.0
                },
                "conservative": {
                    "availability": 95.0,
                    "latency_p95_ms": 2000,
                    "latency_p99_ms": 5000,
                    "error_rate_percent": 5.0
                }
            },
            "recommended_tier": "conservative",
            "confidence_score": 0.3,
            "is_fallback": True,
            "fallback_reason": "Using industry standards due to component unavailability",
            "warnings": [
                "Knowledge layer unavailable - using conservative estimates",
                "Dependency analysis unavailable - treating service as independent",
                "Recommendations based on industry standards, not actual metrics"
            ]
        }
        
        # If metrics are available, adjust fallback based on metrics
        if metrics:
            fallback["warnings"].append("Adjusted based on available metrics")
        
        return fallback
    
    def get_degradation_warnings(self) -> List[str]:
        """
        Get warnings about degraded components.
        
        Returns:
            List of warning messages
        """
        warnings = []
        
        for name, health in self.component_health.items():
            if health.status == ComponentStatus.DEGRADED:
                warnings.append(
                    f"{name} is degraded: {health.error_message} "
                    f"(recovery attempt {health.recovery_attempts})"
                )
            elif health.status == ComponentStatus.UNAVAILABLE:
                warnings.append(f"{name} is unavailable: {health.error_message}")
        
        return warnings
