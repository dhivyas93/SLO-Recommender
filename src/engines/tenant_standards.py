"""
Tenant-specific SLO standards and configuration.

Implements tenant-specific standards for SLO recommendations,
allowing different organizations to have different baseline expectations.
"""

import logging
from typing import Dict, Any, Optional
from src.storage.file_storage import FileStorage

logger = logging.getLogger(__name__)


class TenantStandardsManager:
    """
    Manages tenant-specific SLO standards and configurations.
    
    Allows different tenants to have different baseline expectations
    for SLOs based on their industry, criticality levels, and other factors.
    """
    
    def __init__(self, storage: Optional[FileStorage] = None):
        """
        Initialize TenantStandardsManager.
        
        Args:
            storage: FileStorage instance for loading standards
        """
        self.storage = storage or FileStorage(base_path="data")
        self._standards_cache: Dict[str, Dict[str, Any]] = {}
        
        # Default industry standards
        self.default_standards = {
            "api_gateway": {
                "availability": 99.99,
                "latency_p95_ms": 100,
                "latency_p99_ms": 500,
                "error_rate_percent": 0.1
            },
            "database": {
                "availability": 99.95,
                "latency_p95_ms": 50,
                "latency_p99_ms": 200,
                "error_rate_percent": 0.05
            },
            "cache": {
                "availability": 99.9,
                "latency_p95_ms": 10,
                "latency_p99_ms": 50,
                "error_rate_percent": 0.1
            },
            "message_queue": {
                "availability": 99.9,
                "latency_p95_ms": 100,
                "latency_p99_ms": 500,
                "error_rate_percent": 0.1
            },
            "background_job": {
                "availability": 99.0,
                "latency_p95_ms": 5000,
                "latency_p99_ms": 30000,
                "error_rate_percent": 1.0
            },
            "batch_process": {
                "availability": 95.0,
                "latency_p95_ms": 60000,
                "latency_p99_ms": 300000,
                "error_rate_percent": 5.0
            }
        }
    
    def get_tenant_standards(self, tenant_id: str) -> Dict[str, Any]:
        """
        Get standards for a specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Dictionary with tenant-specific standards
        """
        # Check cache first
        if tenant_id in self._standards_cache:
            return self._standards_cache[tenant_id]
        
        # Try to load from storage
        try:
            standards = self.storage.read_json(f"tenants/{tenant_id}/standards.json")
            self._standards_cache[tenant_id] = standards
            return standards
        except FileNotFoundError:
            # Return default standards
            logger.info(f"No custom standards found for tenant {tenant_id}, using defaults")
            return self._get_default_standards()
    
    def set_tenant_standards(self, tenant_id: str, standards: Dict[str, Any]) -> None:
        """
        Set standards for a specific tenant.
        
        Args:
            tenant_id: Tenant identifier
            standards: Dictionary with tenant-specific standards
        """
        # Validate standards
        self._validate_standards(standards)
        
        # Store to file
        self.storage.write_json(f"tenants/{tenant_id}/standards.json", standards)
        
        # Update cache
        self._standards_cache[tenant_id] = standards
        logger.info(f"Updated standards for tenant {tenant_id}")
    
    def get_service_type_standard(
        self,
        tenant_id: str,
        service_type: str,
        metric: str
    ) -> Optional[float]:
        """
        Get a specific standard for a service type and metric.
        
        Args:
            tenant_id: Tenant identifier
            service_type: Type of service (e.g., "api_gateway", "database")
            metric: Metric name (e.g., "availability", "latency_p95_ms")
            
        Returns:
            Standard value or None if not found
        """
        standards = self.get_tenant_standards(tenant_id)
        
        if service_type in standards:
            service_standards = standards[service_type]
            if metric in service_standards:
                return service_standards[metric]
        
        # Fall back to default
        if service_type in self.default_standards:
            service_standards = self.default_standards[service_type]
            if metric in service_standards:
                return service_standards[metric]
        
        return None
    
    def get_criticality_adjustments(
        self,
        tenant_id: str,
        criticality: str
    ) -> Dict[str, float]:
        """
        Get SLO adjustments based on service criticality.
        
        Args:
            tenant_id: Tenant identifier
            criticality: Criticality level (e.g., "critical", "high", "medium", "low")
            
        Returns:
            Dictionary with adjustment multipliers for each metric
        """
        standards = self.get_tenant_standards(tenant_id)
        
        # Default criticality adjustments
        default_adjustments = {
            "critical": {
                "availability_multiplier": 1.05,  # 5% stricter
                "latency_multiplier": 0.8,  # 20% faster
                "error_rate_multiplier": 0.5  # 50% lower error rate
            },
            "high": {
                "availability_multiplier": 1.02,  # 2% stricter
                "latency_multiplier": 0.9,  # 10% faster
                "error_rate_multiplier": 0.75  # 25% lower error rate
            },
            "medium": {
                "availability_multiplier": 1.0,  # No change
                "latency_multiplier": 1.0,  # No change
                "error_rate_multiplier": 1.0  # No change
            },
            "low": {
                "availability_multiplier": 0.98,  # 2% more lenient
                "latency_multiplier": 1.1,  # 10% slower acceptable
                "error_rate_multiplier": 1.5  # 50% higher error rate acceptable
            }
        }
        
        # Check for tenant-specific adjustments
        if "criticality_adjustments" in standards:
            tenant_adjustments = standards["criticality_adjustments"]
            if criticality in tenant_adjustments:
                return tenant_adjustments[criticality]
        
        # Return default adjustments
        return default_adjustments.get(criticality, default_adjustments["medium"])
    
    def apply_criticality_adjustment(
        self,
        tenant_id: str,
        criticality: str,
        base_slo: Dict[str, float]
    ) -> Dict[str, float]:
        """
        Apply criticality-based adjustments to a base SLO.
        
        Args:
            tenant_id: Tenant identifier
            criticality: Criticality level
            base_slo: Base SLO values
            
        Returns:
            Adjusted SLO values
        """
        adjustments = self.get_criticality_adjustments(tenant_id, criticality)
        
        adjusted_slo = base_slo.copy()
        
        # Apply availability adjustment
        if "availability" in adjusted_slo:
            multiplier = adjustments.get("availability_multiplier", 1.0)
            # For availability, higher is better, so we adjust towards 100
            current = adjusted_slo["availability"]
            target = 100.0
            adjusted_slo["availability"] = current + (target - current) * (multiplier - 1.0)
            adjusted_slo["availability"] = min(100.0, max(0.0, adjusted_slo["availability"]))
        
        # Apply latency adjustment
        for latency_metric in ["latency_p95_ms", "latency_p99_ms", "latency_p50_ms"]:
            if latency_metric in adjusted_slo:
                multiplier = adjustments.get("latency_multiplier", 1.0)
                adjusted_slo[latency_metric] = adjusted_slo[latency_metric] * multiplier
        
        # Apply error rate adjustment
        if "error_rate_percent" in adjusted_slo:
            multiplier = adjustments.get("error_rate_multiplier", 1.0)
            adjusted_slo["error_rate_percent"] = adjusted_slo["error_rate_percent"] * multiplier
        
        return adjusted_slo
    
    def _get_default_standards(self) -> Dict[str, Any]:
        """Get default standards."""
        return self.default_standards
    
    def _validate_standards(self, standards: Dict[str, Any]) -> None:
        """
        Validate standards format.
        
        Args:
            standards: Standards dictionary to validate
            
        Raises:
            ValueError: If standards are invalid
        """
        if not isinstance(standards, dict):
            raise ValueError("Standards must be a dictionary")
        
        for service_type, service_standards in standards.items():
            if not isinstance(service_standards, dict):
                raise ValueError(f"Standards for {service_type} must be a dictionary")
            
            # Validate metric values
            for metric, value in service_standards.items():
                if not isinstance(value, (int, float)):
                    raise ValueError(f"Standard value for {metric} must be numeric")
                
                # Validate ranges
                if "availability" in metric:
                    if not (0 <= value <= 100):
                        raise ValueError(f"Availability must be between 0 and 100, got {value}")
                elif "latency" in metric:
                    if value < 0:
                        raise ValueError(f"Latency must be non-negative, got {value}")
                elif "error_rate" in metric:
                    if not (0 <= value <= 100):
                        raise ValueError(f"Error rate must be between 0 and 100, got {value}")
