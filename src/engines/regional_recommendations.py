"""
Regional recommendation engine for multi-region services.

Implements region-specific SLO recommendations and cross-region aggregation.
"""

import logging
from typing import Dict, Any, List, Optional
from src.engines.recommendation_engine import RecommendationEngine

logger = logging.getLogger(__name__)


class RegionalRecommendationEngine:
    """
    Generates region-specific and global recommendations for multi-region services.
    
    Handles:
    - Region-specific metrics and recommendations
    - Cross-region aggregation
    - Regional variance analysis
    - Global SLO computation
    """
    
    def __init__(self):
        """Initialize the regional recommendation engine."""
        self.base_engine = RecommendationEngine()
        self.supported_regions = [
            "us-east-1",
            "us-west-2",
            "eu-west-1",
            "ap-southeast-1",
            "ap-northeast-1"
        ]
    
    def generate_regional_recommendations(
        self,
        service_id: str,
        regional_metrics: Dict[str, Dict[str, Any]],
        dependencies: Optional[Dict[str, Any]] = None,
        infrastructure: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate region-specific recommendations for a service.
        
        Args:
            service_id: Service identifier
            regional_metrics: Dictionary mapping region names to metrics
            dependencies: Optional dependency graph
            infrastructure: Optional infrastructure configuration
            
        Returns:
            Dictionary with region-specific and global recommendations
        """
        if not regional_metrics:
            raise ValueError("regional_metrics cannot be empty")
        
        # Validate regions
        for region in regional_metrics.keys():
            if region not in self.supported_regions:
                logger.warning(f"Unknown region: {region}")
        
        # Generate recommendations for each region
        regional_recommendations = {}
        for region, metrics in regional_metrics.items():
            try:
                # Create a temporary service entry with regional metrics
                recommendation = self._generate_regional_recommendation(
                    service_id=f"{service_id}-{region}",
                    metrics=metrics,
                    dependencies=dependencies or {},
                    infrastructure=infrastructure or {}
                )
                regional_recommendations[region] = recommendation
            except Exception as e:
                logger.error(f"Error generating recommendation for {region}: {str(e)}")
                regional_recommendations[region] = {
                    "error": str(e),
                    "region": region
                }
        
        # Compute global recommendations
        global_recommendation = self._compute_global_recommendation(
            service_id,
            regional_recommendations,
            regional_metrics
        )
        
        return {
            "service_id": service_id,
            "regional_recommendations": regional_recommendations,
            "global_recommendation": global_recommendation,
            "regions_analyzed": list(regional_metrics.keys()),
            "region_count": len(regional_metrics)
        }
    
    def _compute_global_recommendation(
        self,
        service_id: str,
        regional_recommendations: Dict[str, Dict[str, Any]],
        regional_metrics: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute global recommendations by aggregating regional data.
        
        Args:
            service_id: Service identifier
            regional_recommendations: Regional recommendations
            regional_metrics: Regional metrics
            
        Returns:
            Global recommendation
        """
        # Aggregate metrics across regions
        aggregated_metrics = self._aggregate_regional_metrics(regional_metrics)
        
        # Generate global recommendation using aggregated metrics
        global_recommendation = self._generate_regional_recommendation(
            service_id=service_id,
            metrics=aggregated_metrics,
            dependencies={},
            infrastructure={}
        )
        
        # Add regional variance analysis
        variance_analysis = self._analyze_regional_variance(
            regional_recommendations,
            regional_metrics
        )
        
        global_recommendation["regional_variance"] = variance_analysis
        
        return global_recommendation
    
    def _generate_regional_recommendation(
        self,
        service_id: str,
        metrics: Dict[str, Any],
        dependencies: Dict[str, Any],
        infrastructure: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Generate a recommendation from metrics data.
        
        Args:
            service_id: Service identifier
            metrics: Metrics data
            dependencies: Dependency information
            infrastructure: Infrastructure information
            
        Returns:
            Recommendation dictionary
        """
        # Build a recommendation from the metrics
        recommendation = {
            "service_id": service_id,
            "tiers": self._build_tiers_from_metrics(metrics),
            "confidence_score": self._compute_confidence_from_metrics(metrics),
            "explanation": self._generate_explanation_from_metrics(metrics),
            "metrics_summary": metrics
        }
        
        return recommendation
    
    def _build_tiers_from_metrics(self, metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Build SLO tiers from metrics data."""
        latency_p95 = 200.0
        error_rate = 0.5
        availability = 99.5
        
        # Handle nested metrics structure
        metrics_data = metrics.get("metrics", metrics)
        
        if "latency" in metrics_data and "p95_ms" in metrics_data["latency"]:
            latency_p95 = metrics_data["latency"]["p95_ms"]
        
        if "error_rate" in metrics_data and "percent" in metrics_data["error_rate"]:
            error_rate = metrics_data["error_rate"]["percent"]
        
        if "availability" in metrics_data and "percent" in metrics_data["availability"]:
            availability = metrics_data["availability"]["percent"]
        
        return {
            "aggressive": {
                "availability": availability + 0.1,
                "latency_p95_ms": latency_p95 * 0.75,
                "latency_p99_ms": latency_p95 * 0.75,
                "error_rate_percent": error_rate * 1.5
            },
            "balanced": {
                "availability": availability - 0.5,
                "latency_p95_ms": latency_p95 * 1.125,
                "latency_p99_ms": latency_p95 * 1.25,
                "error_rate_percent": error_rate * 3.0
            },
            "conservative": {
                "availability": availability - 0.5,
                "latency_p95_ms": latency_p95 * 1.125,
                "latency_p99_ms": latency_p95 * 1.5,
                "error_rate_percent": error_rate * 3.0
            }
        }
    
    def _compute_confidence_from_metrics(self, metrics: Dict[str, Any]) -> float:
        """Compute confidence score from metrics."""
        # Base confidence on data quality if available
        if "data_quality" in metrics and "quality_score" in metrics["data_quality"]:
            return metrics["data_quality"]["quality_score"]
        return 0.6
    
    def _generate_explanation_from_metrics(self, metrics: Dict[str, Any]) -> str:
        """Generate explanation from metrics."""
        return "Recommendation generated from regional metrics aggregation"
    
    def _aggregate_regional_metrics(
        self,
        regional_metrics: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate metrics across regions.
        
        Args:
            regional_metrics: Regional metrics
            
        Returns:
            Aggregated metrics
        """
        if not regional_metrics:
            return {}
        
        regions = list(regional_metrics.keys())
        
        # Initialize aggregated metrics
        aggregated = {
            "latency": {},
            "error_rate": {},
            "availability": {}
        }
        
        # Aggregate latency metrics
        latency_metrics = ["p50_ms", "p95_ms", "p99_ms", "mean_ms", "stddev_ms"]
        for metric in latency_metrics:
            values = []
            for region in regions:
                if "metrics" in regional_metrics[region]:
                    if "latency" in regional_metrics[region]["metrics"]:
                        if metric in regional_metrics[region]["metrics"]["latency"]:
                            values.append(regional_metrics[region]["metrics"]["latency"][metric])
            
            if values:
                # Use worst-case (max) for latency
                aggregated["latency"][metric] = max(values)
        
        # Aggregate error rate
        error_rates = []
        for region in regions:
            if "metrics" in regional_metrics[region]:
                if "error_rate" in regional_metrics[region]["metrics"]:
                    if "percent" in regional_metrics[region]["metrics"]["error_rate"]:
                        error_rates.append(
                            regional_metrics[region]["metrics"]["error_rate"]["percent"]
                        )
        
        if error_rates:
            # Use worst-case (max) for error rate
            aggregated["error_rate"]["percent"] = max(error_rates)
        
        # Aggregate availability
        availabilities = []
        for region in regions:
            if "metrics" in regional_metrics[region]:
                if "availability" in regional_metrics[region]["metrics"]:
                    if "percent" in regional_metrics[region]["metrics"]["availability"]:
                        availabilities.append(
                            regional_metrics[region]["metrics"]["availability"]["percent"]
                        )
        
        if availabilities:
            # Use worst-case (min) for availability
            aggregated["availability"]["percent"] = min(availabilities)
        
        # Add data quality
        aggregated["data_quality"] = {
            "completeness": 0.95,
            "staleness_hours": 1,
            "quality_score": 0.95
        }
        
        return aggregated
    
    def _analyze_regional_variance(
        self,
        regional_recommendations: Dict[str, Dict[str, Any]],
        regional_metrics: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Analyze variance in metrics and recommendations across regions.
        
        Args:
            regional_recommendations: Regional recommendations
            regional_metrics: Regional metrics
            
        Returns:
            Variance analysis
        """
        if not regional_metrics:
            return {}
        
        regions = list(regional_metrics.keys())
        
        # Collect latency values
        latency_p95_values = []
        for region in regions:
            if "metrics" in regional_metrics[region]:
                if "latency" in regional_metrics[region]["metrics"]:
                    if "p95_ms" in regional_metrics[region]["metrics"]["latency"]:
                        latency_p95_values.append(
                            regional_metrics[region]["metrics"]["latency"]["p95_ms"]
                        )
        
        # Collect availability values
        availability_values = []
        for region in regions:
            if "metrics" in regional_metrics[region]:
                if "availability" in regional_metrics[region]["metrics"]:
                    if "percent" in regional_metrics[region]["metrics"]["availability"]:
                        availability_values.append(
                            regional_metrics[region]["metrics"]["availability"]["percent"]
                        )
        
        # Compute variance statistics
        variance_analysis = {
            "regions_analyzed": len(regions),
            "latency_p95_variance": self._compute_variance(latency_p95_values),
            "availability_variance": self._compute_variance(availability_values),
            "highest_latency_region": self._find_highest_latency_region(regional_metrics),
            "lowest_availability_region": self._find_lowest_availability_region(regional_metrics),
            "regional_consistency": self._assess_regional_consistency(regional_metrics)
        }
        
        return variance_analysis
    
    def _compute_variance(self, values: List[float]) -> Dict[str, float]:
        """
        Compute variance statistics for a list of values.
        
        Args:
            values: List of numeric values
            
        Returns:
            Dictionary with variance statistics
        """
        if not values:
            return {}
        
        mean = sum(values) / len(values)
        variance = sum((x - mean) ** 2 for x in values) / len(values)
        stddev = variance ** 0.5
        
        return {
            "mean": mean,
            "min": min(values),
            "max": max(values),
            "range": max(values) - min(values),
            "variance": variance,
            "stddev": stddev,
            "coefficient_of_variation": (stddev / mean * 100) if mean != 0 else 0
        }
    
    def _find_highest_latency_region(
        self,
        regional_metrics: Dict[str, Dict[str, Any]]
    ) -> Optional[str]:
        """Find the region with highest latency."""
        highest_region = None
        highest_latency = 0
        
        for region, metrics in regional_metrics.items():
            if "metrics" in metrics:
                if "latency" in metrics["metrics"]:
                    if "p95_ms" in metrics["metrics"]["latency"]:
                        latency = metrics["metrics"]["latency"]["p95_ms"]
                        if latency > highest_latency:
                            highest_latency = latency
                            highest_region = region
        
        return highest_region
    
    def _find_lowest_availability_region(
        self,
        regional_metrics: Dict[str, Dict[str, Any]]
    ) -> Optional[str]:
        """Find the region with lowest availability."""
        lowest_region = None
        lowest_availability = 100
        
        for region, metrics in regional_metrics.items():
            if "metrics" in metrics:
                if "availability" in metrics["metrics"]:
                    if "percent" in metrics["metrics"]["availability"]:
                        availability = metrics["metrics"]["availability"]["percent"]
                        if availability < lowest_availability:
                            lowest_availability = availability
                            lowest_region = region
        
        return lowest_region
    
    def _assess_regional_consistency(
        self,
        regional_metrics: Dict[str, Dict[str, Any]]
    ) -> str:
        """
        Assess consistency of metrics across regions.
        
        Args:
            regional_metrics: Regional metrics
            
        Returns:
            Consistency assessment ("high", "medium", "low")
        """
        # Collect latency values
        latency_values = []
        for region, metrics in regional_metrics.items():
            if "metrics" in metrics:
                if "latency" in metrics["metrics"]:
                    if "p95_ms" in metrics["metrics"]["latency"]:
                        latency_values.append(
                            metrics["metrics"]["latency"]["p95_ms"]
                        )
        
        if not latency_values:
            return "unknown"
        
        # Compute coefficient of variation
        mean = sum(latency_values) / len(latency_values)
        variance = sum((x - mean) ** 2 for x in latency_values) / len(latency_values)
        stddev = variance ** 0.5
        cv = (stddev / mean * 100) if mean != 0 else 0
        
        # Assess based on CV
        if cv < 10:
            return "high"
        elif cv < 30:
            return "medium"
        else:
            return "low"
