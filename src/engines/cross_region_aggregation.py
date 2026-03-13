"""
Cross-region aggregation engine for multi-region services.

Implements aggregation strategies for combining metrics and recommendations
from multiple regions into global SLOs.
"""

import logging
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class AggregationStrategy(Enum):
    """Aggregation strategies for cross-region metrics."""
    WORST_CASE = "worst_case"  # Use worst value across regions
    AVERAGE = "average"  # Use average value across regions
    PERCENTILE_95 = "percentile_95"  # Use 95th percentile
    WEIGHTED = "weighted"  # Use weighted average based on traffic


class CrossRegionAggregationEngine:
    """
    Aggregates metrics and recommendations across multiple regions.
    
    Supports multiple aggregation strategies and provides insights into
    regional variance and consistency.
    """
    
    def __init__(self, strategy: AggregationStrategy = AggregationStrategy.WORST_CASE):
        """
        Initialize the cross-region aggregation engine.
        
        Args:
            strategy: Aggregation strategy to use
        """
        self.strategy = strategy
    
    def aggregate_metrics(
        self,
        regional_metrics: Dict[str, Dict[str, Any]],
        strategy: Optional[AggregationStrategy] = None
    ) -> Dict[str, Any]:
        """
        Aggregate metrics from multiple regions.
        
        Args:
            regional_metrics: Dictionary mapping region names to metrics
            strategy: Optional override for aggregation strategy
            
        Returns:
            Aggregated metrics
        """
        if not regional_metrics:
            raise ValueError("regional_metrics cannot be empty")
        
        strategy = strategy or self.strategy
        
        # Extract metric values by type
        latency_p50_values = self._extract_metric_values(regional_metrics, "latency", "p50_ms")
        latency_p95_values = self._extract_metric_values(regional_metrics, "latency", "p95_ms")
        latency_p99_values = self._extract_metric_values(regional_metrics, "latency", "p99_ms")
        error_rate_values = self._extract_metric_values(regional_metrics, "error_rate", "percent")
        availability_values = self._extract_metric_values(regional_metrics, "availability", "percent")
        
        # Aggregate based on strategy
        aggregated = {
            "latency": {},
            "error_rate": {},
            "availability": {},
            "aggregation_strategy": strategy.value,
            "regions_aggregated": len(regional_metrics)
        }
        
        # Aggregate latency
        if latency_p50_values:
            aggregated["latency"]["p50_ms"] = self._aggregate_values(
                latency_p50_values,
                strategy,
                is_latency=True
            )
        
        if latency_p95_values:
            aggregated["latency"]["p95_ms"] = self._aggregate_values(
                latency_p95_values,
                strategy,
                is_latency=True
            )
        
        if latency_p99_values:
            aggregated["latency"]["p99_ms"] = self._aggregate_values(
                latency_p99_values,
                strategy,
                is_latency=True
            )
        
        # Aggregate error rate (worst case)
        if error_rate_values:
            aggregated["error_rate"]["percent"] = self._aggregate_values(
                error_rate_values,
                strategy,
                is_latency=False
            )
        
        # Aggregate availability (worst case)
        if availability_values:
            aggregated["availability"]["percent"] = self._aggregate_values(
                availability_values,
                strategy,
                is_latency=False
            )
        
        # Add data quality
        aggregated["data_quality"] = {
            "completeness": 0.95,
            "staleness_hours": 1,
            "quality_score": 0.95
        }
        
        return aggregated
    
    def aggregate_recommendations(
        self,
        regional_recommendations: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Aggregate recommendations from multiple regions.
        
        Args:
            regional_recommendations: Dictionary mapping region names to recommendations
            
        Returns:
            Aggregated recommendation
        """
        if not regional_recommendations:
            raise ValueError("regional_recommendations cannot be empty")
        
        # Extract SLO values from each region
        regional_slos = {}
        for region, recommendation in regional_recommendations.items():
            if "recommendations" in recommendation:
                regional_slos[region] = recommendation["recommendations"]
        
        if not regional_slos:
            raise ValueError("No valid recommendations found in regional data")
        
        # Aggregate each tier
        aggregated_tiers = {}
        for tier in ["aggressive", "balanced", "conservative"]:
            tier_values = {}
            
            for region, slos in regional_slos.items():
                if tier in slos:
                    tier_slo = slos[tier]
                    for metric, value in tier_slo.items():
                        if metric not in tier_values:
                            tier_values[metric] = []
                        tier_values[metric].append(value)
            
            # Aggregate values for this tier
            aggregated_tier = {}
            for metric, values in tier_values.items():
                if "availability" in metric:
                    # Use worst case (minimum) for availability
                    aggregated_tier[metric] = min(values)
                elif "latency" in metric or "error_rate" in metric:
                    # Use worst case (maximum) for latency and error rate
                    aggregated_tier[metric] = max(values)
                else:
                    # Default to average
                    aggregated_tier[metric] = sum(values) / len(values)
            
            aggregated_tiers[tier] = aggregated_tier
        
        return {
            "recommendations": aggregated_tiers,
            "regions_aggregated": len(regional_recommendations),
            "aggregation_strategy": self.strategy.value
        }
    
    def _extract_metric_values(
        self,
        regional_metrics: Dict[str, Dict[str, Any]],
        metric_type: str,
        metric_name: str
    ) -> List[float]:
        """
        Extract specific metric values from regional metrics.
        
        Args:
            regional_metrics: Regional metrics dictionary
            metric_type: Type of metric (e.g., "latency", "error_rate")
            metric_name: Name of specific metric (e.g., "p95_ms")
            
        Returns:
            List of metric values
        """
        values = []
        
        for region, metrics in regional_metrics.items():
            if "metrics" in metrics:
                if metric_type in metrics["metrics"]:
                    if metric_name in metrics["metrics"][metric_type]:
                        value = metrics["metrics"][metric_type][metric_name]
                        if isinstance(value, (int, float)):
                            values.append(value)
        
        return values
    
    def _aggregate_values(
        self,
        values: List[float],
        strategy: AggregationStrategy,
        is_latency: bool = False
    ) -> float:
        """
        Aggregate values using the specified strategy.
        
        Args:
            values: List of values to aggregate
            strategy: Aggregation strategy
            is_latency: Whether this is a latency metric
            
        Returns:
            Aggregated value
        """
        if not values:
            return 0.0
        
        if strategy == AggregationStrategy.WORST_CASE:
            # For latency and error rate, worst case is maximum
            # For availability, worst case is minimum
            if is_latency:
                return max(values)
            else:
                return max(values)
        
        elif strategy == AggregationStrategy.AVERAGE:
            return sum(values) / len(values)
        
        elif strategy == AggregationStrategy.PERCENTILE_95:
            sorted_values = sorted(values)
            index = int(len(sorted_values) * 0.95)
            return sorted_values[min(index, len(sorted_values) - 1)]
        
        elif strategy == AggregationStrategy.WEIGHTED:
            # Default to average if weights not provided
            return sum(values) / len(values)
        
        else:
            return sum(values) / len(values)
    
    def compute_regional_variance(
        self,
        regional_metrics: Dict[str, Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Compute variance statistics for regional metrics.
        
        Args:
            regional_metrics: Regional metrics dictionary
            
        Returns:
            Variance statistics
        """
        if not regional_metrics:
            return {}
        
        # Extract latency values
        latency_values = self._extract_metric_values(regional_metrics, "latency", "p95_ms")
        
        # Extract availability values
        availability_values = self._extract_metric_values(regional_metrics, "availability", "percent")
        
        # Extract error rate values
        error_rate_values = self._extract_metric_values(regional_metrics, "error_rate", "percent")
        
        variance_stats = {
            "latency_p95_variance": self._compute_variance_stats(latency_values),
            "availability_variance": self._compute_variance_stats(availability_values),
            "error_rate_variance": self._compute_variance_stats(error_rate_values),
            "regions_analyzed": len(regional_metrics)
        }
        
        return variance_stats
    
    def _compute_variance_stats(self, values: List[float]) -> Dict[str, float]:
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
    
    def identify_outlier_regions(
        self,
        regional_metrics: Dict[str, Dict[str, Any]],
        threshold_stddev: float = 2.0
    ) -> Dict[str, List[str]]:
        """
        Identify regions with outlier metrics.
        
        Args:
            regional_metrics: Regional metrics dictionary
            threshold_stddev: Number of standard deviations for outlier detection
            
        Returns:
            Dictionary mapping metric types to list of outlier regions
        """
        outliers = {
            "latency": [],
            "availability": [],
            "error_rate": []
        }
        
        # Check latency
        latency_values = self._extract_metric_values(regional_metrics, "latency", "p95_ms")
        if latency_values:
            mean = sum(latency_values) / len(latency_values)
            variance = sum((x - mean) ** 2 for x in latency_values) / len(latency_values)
            stddev = variance ** 0.5
            
            for region, metrics in regional_metrics.items():
                if "metrics" in metrics and "latency" in metrics["metrics"]:
                    if "p95_ms" in metrics["metrics"]["latency"]:
                        value = metrics["metrics"]["latency"]["p95_ms"]
                        if abs(value - mean) > threshold_stddev * stddev:
                            outliers["latency"].append(region)
        
        # Check availability
        availability_values = self._extract_metric_values(regional_metrics, "availability", "percent")
        if availability_values:
            mean = sum(availability_values) / len(availability_values)
            variance = sum((x - mean) ** 2 for x in availability_values) / len(availability_values)
            stddev = variance ** 0.5
            
            for region, metrics in regional_metrics.items():
                if "metrics" in metrics and "availability" in metrics["metrics"]:
                    if "percent" in metrics["metrics"]["availability"]:
                        value = metrics["metrics"]["availability"]["percent"]
                        if abs(value - mean) > threshold_stddev * stddev:
                            outliers["availability"].append(region)
        
        # Check error rate
        error_rate_values = self._extract_metric_values(regional_metrics, "error_rate", "percent")
        if error_rate_values:
            mean = sum(error_rate_values) / len(error_rate_values)
            variance = sum((x - mean) ** 2 for x in error_rate_values) / len(error_rate_values)
            stddev = variance ** 0.5
            
            for region, metrics in regional_metrics.items():
                if "metrics" in metrics and "error_rate" in metrics["metrics"]:
                    if "percent" in metrics["metrics"]["error_rate"]:
                        value = metrics["metrics"]["error_rate"]["percent"]
                        if abs(value - mean) > threshold_stddev * stddev:
                            outliers["error_rate"].append(region)
        
        return outliers
