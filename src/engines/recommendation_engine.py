"""
Recommendation Engine.

This module provides the RecommendationEngine class that generates SLO
recommendations using hybrid rule-based + statistical approach.
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path

from src.models.recommendation import (
    Recommendation,
    SLOTier,
    RecommendationExplanation,
    ConfidenceScore,
    DataQualityInfo
)
from src.engines.metrics_ingestion import MetricsIngestionEngine
from src.storage.file_storage import FileStorage


class RecommendationEngine:
    """
    Recommendation Engine for generating SLO recommendations.
    
    Responsibilities:
    - Generate SLO recommendations using statistical baseline
    - Apply dependency constraints
    - Apply infrastructure constraints
    - Generate three recommendation tiers (aggressive, balanced, conservative)
    - Compute confidence scores
    - Generate human-readable explanations
    - Validate recommendations for achievability
    
    Attributes:
        storage: FileStorage instance for persisting recommendations
        metrics_engine: MetricsIngestionEngine for retrieving metrics
    """
    
    def __init__(
        self,
        storage: Optional[FileStorage] = None,
        metrics_engine: Optional[MetricsIngestionEngine] = None
    ):
        """
        Initialize RecommendationEngine.
        
        Args:
            storage: FileStorage instance (creates default if None)
            metrics_engine: MetricsIngestionEngine instance (creates default if None)
        """
        self.storage = storage or FileStorage(base_path="data")
        self.metrics_engine = metrics_engine or MetricsIngestionEngine(storage=self.storage)
    
    def compute_base_recommendations(
        self,
        service_id: str,
        time_window: str = "30d",
        availability_buffer: float = 0.5,
        error_rate_buffer: float = 0.5
    ) -> Dict[str, Any]:
        """
        Compute base statistical baseline recommendations from historical metrics.
        
        This method implements the core statistical formulas:
        - Base availability: p95 of historical - buffer (e.g., 0.5%)
        - Base latency p95: mean + 1.5 * stddev
        - Base latency p99: mean + 2 * stddev
        - Base error rate: p95 + buffer (e.g., 0.5%)
        
        Args:
            service_id: Service identifier
            time_window: Time window to use for historical data (default: "30d")
            availability_buffer: Buffer to subtract from availability p95 (default: 0.5%)
            error_rate_buffer: Buffer to add to error rate p95 (default: 0.5%)
        
        Returns:
            Dict with base recommendations and metadata
        
        Raises:
            ValueError: If service has no aggregated metrics or insufficient data
        """
        # Retrieve aggregated metrics for the service
        aggregated_metrics = self.metrics_engine.get_aggregated_metrics(service_id)
        
        if not aggregated_metrics:
            raise ValueError(
                f"No aggregated metrics found for service: {service_id}. "
                "Please ingest metrics and compute aggregations first."
            )
        
        # Get the specified time window
        time_windows = aggregated_metrics.get("time_windows", {})
        if time_window not in time_windows:
            raise ValueError(
                f"Time window '{time_window}' not found in aggregated metrics. "
                f"Available windows: {list(time_windows.keys())}"
            )
        
        window_data = time_windows[time_window]
        
        # Check data quality
        data_quality = window_data.get("data_quality", {})
        if data_quality.get("actual_samples", 0) == 0:
            raise ValueError(
                f"Insufficient data for time window '{time_window}'. "
                "No samples available."
            )
        
        # Extract aggregated statistics
        # Use adjusted stats if available (outliers excluded), otherwise use raw stats
        latency_stats = window_data.get("latency_adjusted") or window_data.get("latency")
        error_rate_stats = window_data.get("error_rate_adjusted") or window_data.get("error_rate")
        availability_stats = window_data.get("availability_adjusted") or window_data.get("availability")
        
        if not all([latency_stats, error_rate_stats, availability_stats]):
            raise ValueError(
                f"Incomplete metrics data for service: {service_id}. "
                "Missing latency, error_rate, or availability statistics."
            )
        
        # Compute base availability recommendation
        # Formula: p95 of historical - buffer
        base_availability = availability_stats["p95_percent"] - availability_buffer
        
        # Ensure availability is within valid range [0, 100]
        base_availability = max(0.0, min(100.0, base_availability))
        
        # Compute base latency p95 recommendation
        # Formula: mean + 1.5 * stddev
        latency_mean = latency_stats["mean_ms"]
        latency_stddev = latency_stats["stddev_ms"]
        base_latency_p95 = latency_mean + (1.5 * latency_stddev)
        
        # Ensure latency is positive
        base_latency_p95 = max(1.0, base_latency_p95)
        
        # Compute base latency p99 recommendation
        # Formula: mean + 2 * stddev
        base_latency_p99 = latency_mean + (2.0 * latency_stddev)
        
        # Ensure latency is positive and p99 >= p95
        base_latency_p99 = max(base_latency_p95, base_latency_p99)
        
        # Compute base error rate recommendation
        # Formula: p95 + buffer
        base_error_rate = error_rate_stats["p95_percent"] + error_rate_buffer
        
        # Ensure error rate is within valid range [0, 100]
        base_error_rate = max(0.0, min(100.0, base_error_rate))
        
        # Build base recommendations
        base_recommendations = {
            "availability": round(base_availability, 2),
            "latency_p95_ms": round(base_latency_p95, 2),
            "latency_p99_ms": round(base_latency_p99, 2),
            "error_rate_percent": round(base_error_rate, 2)
        }
        
        # Compute metadata about the computation
        computation_metadata = {
            "service_id": service_id,
            "time_window": time_window,
            "computed_at": datetime.utcnow().isoformat(),
            "data_quality": {
                "completeness": data_quality.get("completeness", 0.0),
                "staleness_hours": data_quality.get("staleness_hours", 0),
                "sample_count": data_quality.get("sample_count", 0),
                "quality_score": data_quality.get("quality_score", 0.0)
            },
            "historical_metrics": {
                "availability": {
                    "mean": availability_stats["mean_percent"],
                    "p95": availability_stats["p95_percent"],
                    "stddev": availability_stats["stddev_percent"]
                },
                "latency": {
                    "mean_ms": latency_mean,
                    "stddev_ms": latency_stddev,
                    "p95_ms": latency_stats["p95_ms"],
                    "p99_ms": latency_stats["p99_ms"]
                },
                "error_rate": {
                    "mean": error_rate_stats["mean_percent"],
                    "p95": error_rate_stats["p95_percent"],
                    "stddev": error_rate_stats["stddev_percent"]
                }
            },
            "formulas_applied": {
                "availability": f"p95 ({availability_stats['p95_percent']}%) - buffer ({availability_buffer}%)",
                "latency_p95": f"mean ({latency_mean:.2f}ms) + 1.5 * stddev ({latency_stddev:.2f}ms)",
                "latency_p99": f"mean ({latency_mean:.2f}ms) + 2.0 * stddev ({latency_stddev:.2f}ms)",
                "error_rate": f"p95 ({error_rate_stats['p95_percent']}%) + buffer ({error_rate_buffer}%)"
            },
            "buffers": {
                "availability_buffer": availability_buffer,
                "error_rate_buffer": error_rate_buffer
            },
            "outliers_excluded": bool(window_data.get("latency_adjusted"))
        }
        
        return {
            "base_recommendations": base_recommendations,
            "metadata": computation_metadata
        }
    def apply_dependency_constraints(
        self,
        service_id: str,
        base_recommendations: Dict[str, float],
        availability_margin: float = 0.5,
        latency_margin_percent: float = 0.1
    ) -> Dict[str, Any]:
        """
        Apply dependency constraints to adjust recommendations based on upstream services.

        A service cannot be more available than its dependencies, and latency must fit
        within the critical path budget.

        Args:
            service_id: Service identifier
            base_recommendations: Base recommendations dict with keys:
                - availability: float (percentage)
                - latency_p95_ms: float (milliseconds)
                - latency_p99_ms: float (milliseconds)
                - error_rate_percent: float (percentage)
            availability_margin: Margin to subtract from upstream availability (default: 0.5%)
            latency_margin_percent: Percentage margin for latency budget (default: 0.1 = 10%)

        Returns:
            Dict with:
                - constrained_recommendations: Dict with adjusted SLO values
                - constraints_applied: List of constraint descriptions
                - metadata: Dict with constraint details

        Raises:
            ValueError: If base_recommendations is missing required keys
        """
        # Validate input
        required_keys = ["availability", "latency_p95_ms", "latency_p99_ms", "error_rate_percent"]
        missing_keys = [key for key in required_keys if key not in base_recommendations]
        if missing_keys:
            raise ValueError(
                f"base_recommendations missing required keys: {missing_keys}. "
                f"Required keys: {required_keys}"
            )

        # Start with a copy of base recommendations
        constrained = base_recommendations.copy()
        constraints_applied = []
        constraint_metadata = {
            "availability_constraints": [],
            "latency_constraints": [],
            "upstream_services_checked": [],
            "critical_path_analyzed": False
        }

        # Load analyzed dependency graph
        analyzed_graph_path = "dependencies/analyzed_graph.json"
        analyzed_graph_data = self.storage.read_json(analyzed_graph_path)

        # If no analyzed graph exists, return base recommendations unchanged
        if not analyzed_graph_data or "services" not in analyzed_graph_data:
            return {
                "constrained_recommendations": constrained,
                "constraints_applied": ["No dependency graph available - using base recommendations"],
                "metadata": {
                    **constraint_metadata,
                    "note": "No analyzed dependency graph found"
                }
            }

        # Find the service in the analyzed graph
        service_analysis = None
        for svc in analyzed_graph_data["services"]:
            if svc["service_id"] == service_id:
                service_analysis = svc
                break

        # If service not found in graph, return base recommendations
        if not service_analysis:
            return {
                "constrained_recommendations": constrained,
                "constraints_applied": ["Service not found in dependency graph - using base recommendations"],
                "metadata": {
                    **constraint_metadata,
                    "note": f"Service {service_id} not found in analyzed graph"
                }
            }

        # Get upstream services
        upstream_services = service_analysis.get("upstream_services", [])
        constraint_metadata["upstream_services_checked"] = upstream_services

        # Apply availability constraints based on upstream services
        if upstream_services:
            for upstream_id in upstream_services:
                # Try to load upstream service's latest recommendation
                upstream_rec_path = f"recommendations/{upstream_id}/latest.json"
                upstream_rec = self.storage.read_json(upstream_rec_path)

                if upstream_rec and "recommendations" in upstream_rec:
                    # Use the balanced tier as the reference
                    upstream_slo = upstream_rec["recommendations"].get("balanced", {})
                    upstream_availability = upstream_slo.get("availability")

                    if upstream_availability is not None:
                        # Apply constraint: service availability <= upstream availability - margin
                        max_availability = upstream_availability - availability_margin

                        if constrained["availability"] > max_availability:
                            original_availability = constrained["availability"]
                            constrained["availability"] = max_availability

                            constraint_desc = (
                                f"Availability constrained by upstream service '{upstream_id}': "
                                f"{original_availability:.2f}% → {max_availability:.2f}% "
                                f"(upstream: {upstream_availability:.2f}%, margin: {availability_margin}%)"
                            )
                            constraints_applied.append(constraint_desc)
                            constraint_metadata["availability_constraints"].append({
                                "upstream_service": upstream_id,
                                "upstream_availability": upstream_availability,
                                "margin": availability_margin,
                                "original_value": original_availability,
                                "constrained_value": max_availability
                            })
                else:
                    # Upstream service has no SLO - note this as uncertainty
                    constraint_desc = (
                        f"Upstream service '{upstream_id}' has no SLO defined - "
                        "using conservative base recommendation"
                    )
                    constraints_applied.append(constraint_desc)
                    constraint_metadata["availability_constraints"].append({
                        "upstream_service": upstream_id,
                        "upstream_availability": None,
                        "note": "No SLO defined for upstream service"
                    })

        # Apply latency constraints based on critical path
        critical_paths = service_analysis.get("critical_paths", [])

        if critical_paths:
            constraint_metadata["critical_path_analyzed"] = True

            # Use the first critical path (typically the longest/most critical)
            critical_path = critical_paths[0]
            path_services = critical_path.get("path", [])
            total_budget = critical_path.get("total_latency_budget_ms")

            if total_budget and len(path_services) > 0:
                # Calculate per-service budget with margin
                path_length = len(path_services)
                per_service_budget = (total_budget / path_length) * (1 - latency_margin_percent)

                # Check if current latency recommendations exceed budget
                if constrained["latency_p95_ms"] > per_service_budget:
                    original_latency_p95 = constrained["latency_p95_ms"]
                    constrained["latency_p95_ms"] = per_service_budget

                    constraint_desc = (
                        f"Latency p95 constrained by critical path budget: "
                        f"{original_latency_p95:.2f}ms → {per_service_budget:.2f}ms "
                        f"(total budget: {total_budget:.2f}ms, path length: {path_length}, "
                        f"margin: {latency_margin_percent*100:.0f}%)"
                    )
                    constraints_applied.append(constraint_desc)
                    constraint_metadata["latency_constraints"].append({
                        "constraint_type": "critical_path_budget",
                        "critical_path": path_services,
                        "total_budget_ms": total_budget,
                        "path_length": path_length,
                        "per_service_budget_ms": per_service_budget,
                        "margin_percent": latency_margin_percent,
                        "original_value_ms": original_latency_p95,
                        "constrained_value_ms": per_service_budget
                    })

                # Also adjust p99 if needed (should be >= p95)
                if constrained["latency_p99_ms"] < constrained["latency_p95_ms"]:
                    # Maintain a reasonable p99/p95 ratio (e.g., 1.5x)
                    constrained["latency_p99_ms"] = constrained["latency_p95_ms"] * 1.5

        # Handle circular dependencies
        if service_analysis.get("is_in_circular_dependency", False):
            constraint_desc = (
                f"Service is part of a circular dependency - "
                "recommendations should be consistent across the cycle"
            )
            constraints_applied.append(constraint_desc)
            constraint_metadata["circular_dependency_detected"] = True

        # If no constraints were applied, note that
        if not constraints_applied:
            constraints_applied.append("No dependency constraints applied - service operates independently")

        return {
            "constrained_recommendations": constrained,
            "constraints_applied": constraints_applied,
            "metadata": constraint_metadata
        }

    def apply_infrastructure_constraints(
        self,
        service_id: str,
        constrained_recommendations: Dict[str, float],
        network_overhead_ms: float = 5.0,
        availability_margin: float = 0.5,
        cache_hit_rate_threshold: float = 0.8,
        cache_latency_reduction_factor: float = 0.3
    ) -> Dict[str, Any]:
        """
        Apply infrastructure constraints to adjust recommendations based on datastores and caches.

        Infrastructure constraints include:
        - Datastore latency constraint: service latency >= datastore latency + network overhead
        - Datastore availability constraint: service availability <= datastore availability - margin
        - Cache benefit: adjust latency for high cache hit rates
        - Identify infrastructure bottlenecks

        Args:
            service_id: Service identifier
            constrained_recommendations: Recommendations after dependency constraints, with keys:
                - availability: float (percentage)
                - latency_p95_ms: float (milliseconds)
                - latency_p99_ms: float (milliseconds)
                - error_rate_percent: float (percentage)
            network_overhead_ms: Network overhead to add to datastore latency (default: 5.0ms)
            availability_margin: Margin to subtract from datastore availability (default: 0.5%)
            cache_hit_rate_threshold: Cache hit rate threshold for applying latency reduction (default: 0.8)
            cache_latency_reduction_factor: Factor to reduce latency for cache hits (default: 0.3 = 30%)

        Returns:
            Dict with:
                - infrastructure_constrained_recommendations: Dict with adjusted SLO values
                - constraints_applied: List of constraint descriptions
                - bottlenecks_identified: List of bottleneck descriptions
                - metadata: Dict with constraint details

        Raises:
            ValueError: If constrained_recommendations is missing required keys
        """
        # Validate input
        required_keys = ["availability", "latency_p95_ms", "latency_p99_ms", "error_rate_percent"]
        missing_keys = [key for key in required_keys if key not in constrained_recommendations]
        if missing_keys:
            raise ValueError(
                f"constrained_recommendations missing required keys: {missing_keys}. "
                f"Required keys: {required_keys}"
            )

        # Start with a copy of constrained recommendations
        infrastructure_constrained = constrained_recommendations.copy()
        constraints_applied = []
        bottlenecks_identified = []
        constraint_metadata = {
            "datastore_constraints": [],
            "cache_benefits": [],
            "infrastructure_components": {
                "datastores": [],
                "caches": [],
                "message_queues": []
            },
            "network_overhead_ms": network_overhead_ms,
            "availability_margin": availability_margin,
            "cache_hit_rate_threshold": cache_hit_rate_threshold,
            "cache_latency_reduction_factor": cache_latency_reduction_factor
        }

        # Load service metadata to get infrastructure information
        service_metadata_path = f"services/{service_id}/metadata.json"
        service_metadata = self.storage.read_json(service_metadata_path)

        # If no service metadata exists, return recommendations unchanged
        if not service_metadata:
            return {
                "infrastructure_constrained_recommendations": infrastructure_constrained,
                "constraints_applied": ["No service metadata available - using constrained recommendations"],
                "bottlenecks_identified": [],
                "metadata": {
                    **constraint_metadata,
                    "note": f"No service metadata found for {service_id}"
                }
            }

        # Extract infrastructure components
        infrastructure = service_metadata.get("infrastructure", {})
        datastores = infrastructure.get("datastores", [])
        caches = infrastructure.get("caches", [])
        message_queues = infrastructure.get("message_queues", [])

        # Update metadata with infrastructure components
        constraint_metadata["infrastructure_components"]["datastores"] = datastores
        constraint_metadata["infrastructure_components"]["caches"] = caches
        constraint_metadata["infrastructure_components"]["message_queues"] = message_queues

        # Apply datastore constraints
        if datastores:
            for datastore in datastores:
                datastore_name = datastore.get("name", "unknown")
                datastore_type = datastore.get("type", "unknown")
                datastore_availability = datastore.get("availability_slo")
                datastore_latency = datastore.get("latency_p95_ms")

                # Track datastore in metadata
                datastore_info = {
                    "name": datastore_name,
                    "type": datastore_type,
                    "availability_slo": datastore_availability,
                    "latency_p95_ms": datastore_latency
                }

                # Apply availability constraint if datastore has availability SLO
                if datastore_availability is not None:
                    # Constraint: service availability <= datastore availability - margin
                    max_availability = datastore_availability - availability_margin

                    if infrastructure_constrained["availability"] > max_availability:
                        original_availability = infrastructure_constrained["availability"]
                        infrastructure_constrained["availability"] = max_availability

                        constraint_desc = (
                            f"Availability constrained by datastore '{datastore_name}' ({datastore_type}): "
                            f"{original_availability:.2f}% → {max_availability:.2f}% "
                            f"(datastore: {datastore_availability:.2f}%, margin: {availability_margin}%)"
                        )
                        constraints_applied.append(constraint_desc)

                        constraint_metadata["datastore_constraints"].append({
                            "datastore": datastore_name,
                            "type": datastore_type,
                            "constraint_type": "availability",
                            "datastore_availability": datastore_availability,
                            "margin": availability_margin,
                            "original_value": original_availability,
                            "constrained_value": max_availability,
                            "is_bottleneck": True
                        })
                    else:
                        constraint_metadata["datastore_constraints"].append({
                            **datastore_info,
                            "constraint_type": "availability",
                            "applied": False,
                            "reason": f"Service availability ({infrastructure_constrained['availability']:.2f}%) already ≤ datastore availability ({max_availability:.2f}%)"
                        })
                else:
                    constraint_metadata["datastore_constraints"].append({
                        **datastore_info,
                        "constraint_type": "availability",
                        "applied": False,
                        "reason": "No availability SLO defined for datastore"
                    })

                # Apply latency constraint if datastore has latency
                if datastore_latency is not None:
                    # Constraint: service latency >= datastore latency + network overhead
                    min_latency = datastore_latency + network_overhead_ms

                    if infrastructure_constrained["latency_p95_ms"] < min_latency:
                        original_latency_p95 = infrastructure_constrained["latency_p95_ms"]
                        infrastructure_constrained["latency_p95_ms"] = min_latency

                        # Also adjust p99 to maintain ratio
                        if infrastructure_constrained["latency_p99_ms"] < infrastructure_constrained["latency_p95_ms"]:
                            infrastructure_constrained["latency_p99_ms"] = infrastructure_constrained["latency_p95_ms"] * 1.5

                        constraint_desc = (
                            f"Latency p95 constrained by datastore '{datastore_name}' ({datastore_type}): "
                            f"{original_latency_p95:.2f}ms → {min_latency:.2f}ms "
                            f"(datastore: {datastore_latency:.2f}ms, network overhead: {network_overhead_ms}ms)"
                        )
                        constraints_applied.append(constraint_desc)

                        constraint_metadata["datastore_constraints"].append({
                            "datastore": datastore_name,
                            "type": datastore_type,
                            "constraint_type": "latency",
                            "datastore_latency": datastore_latency,
                            "network_overhead": network_overhead_ms,
                            "original_value_ms": original_latency_p95,
                            "constrained_value_ms": min_latency,
                            "is_bottleneck": True
                        })
                    else:
                        constraint_metadata["datastore_constraints"].append({
                            **datastore_info,
                            "constraint_type": "latency",
                            "applied": False,
                            "reason": f"Service latency ({infrastructure_constrained['latency_p95_ms']:.2f}ms) already ≥ datastore latency ({min_latency:.2f}ms)"
                        })
                else:
                    constraint_metadata["datastore_constraints"].append({
                        **datastore_info,
                        "constraint_type": "latency",
                        "applied": False,
                        "reason": "No latency defined for datastore"
                    })

        # Apply cache benefits
        if caches:
            for cache in caches:
                cache_name = cache.get("name", "unknown")
                cache_type = cache.get("type", "unknown")
                cache_hit_rate = cache.get("hit_rate")

                # Track cache in metadata
                cache_info = {
                    "name": cache_name,
                    "type": cache_type,
                    "hit_rate": cache_hit_rate
                }

                if cache_hit_rate is not None and cache_hit_rate >= cache_hit_rate_threshold:
                    # Apply latency reduction for high cache hit rates
                    # Formula: adjusted_latency = original_latency * (1 - cache_hit_rate * reduction_factor)
                    latency_reduction = cache_hit_rate * cache_latency_reduction_factor
                    
                    original_latency_p95 = infrastructure_constrained["latency_p95_ms"]
                    original_latency_p99 = infrastructure_constrained["latency_p99_ms"]
                    
                    # Reduce latency for cache hits
                    infrastructure_constrained["latency_p95_ms"] = original_latency_p95 * (1 - latency_reduction)
                    infrastructure_constrained["latency_p99_ms"] = original_latency_p99 * (1 - latency_reduction)
                    
                    # Ensure latencies are positive
                    infrastructure_constrained["latency_p95_ms"] = max(1.0, infrastructure_constrained["latency_p95_ms"])
                    infrastructure_constrained["latency_p99_ms"] = max(
                        infrastructure_constrained["latency_p95_ms"],
                        infrastructure_constrained["latency_p99_ms"]
                    )

                    constraint_desc = (
                        f"Latency reduced by cache '{cache_name}' ({cache_type}): "
                        f"p95: {original_latency_p95:.2f}ms → {infrastructure_constrained['latency_p95_ms']:.2f}ms, "
                        f"p99: {original_latency_p99:.2f}ms → {infrastructure_constrained['latency_p99_ms']:.2f}ms "
                        f"(hit rate: {cache_hit_rate:.2%}, reduction factor: {cache_latency_reduction_factor:.1%})"
                    )
                    constraints_applied.append(constraint_desc)

                    constraint_metadata["cache_benefits"].append({
                        **cache_info,
                        "applied": True,
                        "latency_reduction_factor": latency_reduction,
                        "original_latency_p95_ms": original_latency_p95,
                        "adjusted_latency_p95_ms": infrastructure_constrained["latency_p95_ms"],
                        "original_latency_p99_ms": original_latency_p99,
                        "adjusted_latency_p99_ms": infrastructure_constrained["latency_p99_ms"]
                    })
                else:
                    # Format cache hit rate for display
                    cache_hit_rate_display = f"{cache_hit_rate:.2%}" if cache_hit_rate is not None else "N/A"
                    
                    constraint_metadata["cache_benefits"].append({
                        **cache_info,
                        "applied": False,
                        "reason": (
                            f"Cache hit rate ({cache_hit_rate_display}) "
                            f"below threshold ({cache_hit_rate_threshold:.0%})"
                        )
                    })

        # Use the dedicated bottleneck identification method
        bottleneck_analysis = self.identify_infrastructure_bottlenecks(
            service_id=service_id,
            infrastructure_constrained_recommendations=infrastructure_constrained,
            original_recommendations=constrained_recommendations,
            infrastructure=infrastructure,
            network_overhead_ms=network_overhead_ms,
            availability_margin=availability_margin
        )
        
        # Extract bottleneck descriptions for backward compatibility
        for bottleneck in bottleneck_analysis["bottlenecks"]:
            bottlenecks_identified.append(bottleneck["description"])
        
        for near_bottleneck in bottleneck_analysis["near_bottlenecks"]:
            bottlenecks_identified.append(near_bottleneck["description"])
        
        for risk in bottleneck_analysis["risks"]:
            bottlenecks_identified.append(risk["description"])
        
        # Add detailed bottleneck analysis to metadata
        constraint_metadata["bottleneck_analysis"] = bottleneck_analysis

        # If no constraints were applied, note that
        if not constraints_applied:
            if datastores or caches or message_queues:
                constraints_applied.append(
                    "No infrastructure constraints applied - recommendations already satisfy infrastructure capabilities"
                )
            else:
                constraints_applied.append(
                    "No infrastructure components defined - using constrained recommendations"
                )

        return {
            "infrastructure_constrained_recommendations": infrastructure_constrained,
            "constraints_applied": constraints_applied,
            "bottlenecks_identified": bottlenecks_identified,
            "metadata": constraint_metadata
        }
    
    def identify_infrastructure_bottlenecks(
        self,
        service_id: str,
        infrastructure_constrained_recommendations: Dict[str, float],
        original_recommendations: Dict[str, float],
        infrastructure: Dict[str, Any],
        network_overhead_ms: float = 5.0,
        availability_margin: float = 0.5
    ) -> Dict[str, Any]:
        """
        Identify infrastructure components that are bottlenecks or near-bottlenecks.

        A bottleneck is an infrastructure component that:
        1. Actively constrains the service's SLO recommendations (limiting factor)
        2. Is close to becoming a constraint (near-bottleneck)
        3. Introduces additional latency or availability risks

        Args:
            service_id: Service identifier
            infrastructure_constrained_recommendations: Recommendations after infrastructure constraints
            original_recommendations: Recommendations before infrastructure constraints
            infrastructure: Infrastructure components dict with datastores, caches, message_queues
            network_overhead_ms: Network overhead for datastore calls (default: 5.0ms)
            availability_margin: Margin for availability constraints (default: 0.5%)

        Returns:
            Dict with:
                - bottlenecks: List of active bottleneck dicts with details
                - near_bottlenecks: List of near-bottleneck dicts
                - risks: List of potential risk dicts
                - summary: Human-readable summary
        """
        bottlenecks = []
        near_bottlenecks = []
        risks = []

        # Extract infrastructure components
        datastores = infrastructure.get("datastores", [])
        caches = infrastructure.get("caches", [])
        message_queues = infrastructure.get("message_queues", [])

        # Check datastores for bottlenecks
        for datastore in datastores:
            datastore_name = datastore.get("name", "unknown")
            datastore_type = datastore.get("type", "unknown")
            datastore_availability = datastore.get("availability_slo")
            datastore_latency = datastore.get("latency_p95_ms")

            # Check availability bottleneck
            if datastore_availability is not None:
                max_service_availability = datastore_availability - availability_margin
                current_availability = infrastructure_constrained_recommendations["availability"]
                original_availability = original_recommendations["availability"]

                # Active bottleneck: datastore actively constrained the recommendation
                if original_availability > max_service_availability and current_availability == max_service_availability:
                    bottlenecks.append({
                        "component_type": "datastore",
                        "component_name": datastore_name,
                        "component_subtype": datastore_type,
                        "constraint_type": "availability",
                        "severity": "high",
                        "impact": {
                            "metric": "availability",
                            "original_value": original_availability,
                            "constrained_value": current_availability,
                            "reduction": original_availability - current_availability
                        },
                        "details": {
                            "datastore_slo": datastore_availability,
                            "margin": availability_margin,
                            "max_service_availability": max_service_availability
                        },
                        "description": (
                            f"Datastore '{datastore_name}' ({datastore_type}) limits service availability "
                            f"to {current_availability:.2f}% (datastore SLO: {datastore_availability:.2f}%)"
                        )
                    })
                # Near-bottleneck: close to becoming a constraint (within 1% headroom)
                elif current_availability <= max_service_availability:
                    availability_headroom = max_service_availability - current_availability
                    if 0 <= availability_headroom <= 1.0:
                        near_bottlenecks.append({
                            "component_type": "datastore",
                            "component_name": datastore_name,
                            "component_subtype": datastore_type,
                            "constraint_type": "availability",
                            "severity": "medium",
                            "headroom": availability_headroom,
                            "details": {
                                "datastore_slo": datastore_availability,
                                "current_service_availability": current_availability,
                                "max_service_availability": max_service_availability
                            },
                            "description": (
                                f"Datastore '{datastore_name}' ({datastore_type}) availability "
                                f"({datastore_availability:.2f}%) is close to limiting service availability "
                                f"({current_availability:.2f}%, headroom: {availability_headroom:.2f}%)"
                            )
                        })

            # Check latency bottleneck
            if datastore_latency is not None:
                min_service_latency = datastore_latency + network_overhead_ms
                current_latency = infrastructure_constrained_recommendations["latency_p95_ms"]
                original_latency = original_recommendations["latency_p95_ms"]

                # Active bottleneck: datastore actively constrained the recommendation
                if original_latency < min_service_latency and current_latency == min_service_latency:
                    bottlenecks.append({
                        "component_type": "datastore",
                        "component_name": datastore_name,
                        "component_subtype": datastore_type,
                        "constraint_type": "latency",
                        "severity": "high",
                        "impact": {
                            "metric": "latency_p95_ms",
                            "original_value": original_latency,
                            "constrained_value": current_latency,
                            "increase": current_latency - original_latency
                        },
                        "details": {
                            "datastore_latency": datastore_latency,
                            "network_overhead": network_overhead_ms,
                            "min_service_latency": min_service_latency
                        },
                        "description": (
                            f"Datastore '{datastore_name}' ({datastore_type}) sets minimum service latency "
                            f"to {current_latency:.2f}ms (datastore: {datastore_latency:.2f}ms + "
                            f"network: {network_overhead_ms:.2f}ms)"
                        )
                    })
                # Near-bottleneck: close to becoming a constraint (within 10ms headroom)
                elif current_latency >= min_service_latency:
                    latency_headroom = current_latency - min_service_latency
                    if 0 <= latency_headroom <= 10.0:
                        near_bottlenecks.append({
                            "component_type": "datastore",
                            "component_name": datastore_name,
                            "component_subtype": datastore_type,
                            "constraint_type": "latency",
                            "severity": "medium",
                            "headroom": latency_headroom,
                            "details": {
                                "datastore_latency": datastore_latency,
                                "current_service_latency": current_latency,
                                "min_service_latency": min_service_latency
                            },
                            "description": (
                                f"Datastore '{datastore_name}' ({datastore_type}) latency "
                                f"({datastore_latency:.2f}ms) is close to limiting service latency "
                                f"({current_latency:.2f}ms, headroom: {latency_headroom:.2f}ms)"
                            )
                        })

        # Check message queues as potential risks
        for queue in message_queues:
            queue_name = queue.get("name", "unknown")
            queue_type = queue.get("type", "unknown")

            risks.append({
                "component_type": "message_queue",
                "component_name": queue_name,
                "component_subtype": queue_type,
                "severity": "low",
                "description": (
                    f"Message queue '{queue_name}' ({queue_type}) may introduce additional latency "
                    "and affect availability during queue processing or failures"
                )
            })

        # Generate summary
        summary_parts = []
        if bottlenecks:
            bottleneck_names = [b["component_name"] for b in bottlenecks]
            summary_parts.append(
                f"{len(bottlenecks)} active bottleneck(s): {', '.join(bottleneck_names)}"
            )
        if near_bottlenecks:
            near_bottleneck_names = [nb["component_name"] for nb in near_bottlenecks]
            summary_parts.append(
                f"{len(near_bottlenecks)} near-bottleneck(s): {', '.join(near_bottleneck_names)}"
            )
        if risks:
            risk_names = [r["component_name"] for r in risks]
            summary_parts.append(
                f"{len(risks)} potential risk(s): {', '.join(risk_names)}"
            )

        if not summary_parts:
            summary = "No infrastructure bottlenecks identified"
        else:
            summary = "; ".join(summary_parts)

        return {
            "bottlenecks": bottlenecks,
            "near_bottlenecks": near_bottlenecks,
            "risks": risks,
            "summary": summary,
            "total_count": len(bottlenecks) + len(near_bottlenecks) + len(risks)
        }


    def generate_tiers(
        self,
        service_id: str,
        constrained_recommendations: Dict[str, float],
        time_window: str = "30d"
    ) -> Dict[str, Any]:
        """
        Generate three recommendation tiers (aggressive, balanced, conservative).

        Tier definitions:
        - Aggressive tier: p75 historical performance (more ambitious)
        - Balanced tier: constrained recommendations (default, after dependency/infrastructure constraints)
        - Conservative tier: p95 historical performance (safer)

        Tier ordering:
        - Availability: aggressive >= balanced >= conservative (higher is better)
        - Latency: aggressive <= balanced <= conservative (lower is better)
        - Error rate: aggressive <= balanced <= conservative (lower is better)

        Args:
            service_id: Service identifier
            constrained_recommendations: Recommendations after all constraints applied
            time_window: Time window to use for historical data (default: "30d")

        Returns:
            Dict with:
                - tiers: Dict with aggressive, balanced, conservative tiers
                - metadata: Dict with tier generation details

        Raises:
            ValueError: If service has no aggregated metrics or insufficient data
        """
        # Retrieve aggregated metrics for the service
        aggregated_metrics = self.metrics_engine.get_aggregated_metrics(service_id)

        if not aggregated_metrics:
            raise ValueError(
                f"No aggregated metrics found for service: {service_id}. "
                "Please ingest metrics and compute aggregations first."
            )

        # Get the specified time window
        time_windows = aggregated_metrics.get("time_windows", {})
        if time_window not in time_windows:
            raise ValueError(
                f"Time window '{time_window}' not found in aggregated metrics. "
                f"Available windows: {list(time_windows.keys())}"
            )

        window_data = time_windows[time_window]

        # Check data quality
        data_quality = window_data.get("data_quality", {})
        if data_quality.get("actual_samples", 0) == 0:
            raise ValueError(
                f"Insufficient data for time window '{time_window}'. "
                "No samples available."
            )

        # Extract aggregated statistics (use adjusted if available)
        latency_stats = window_data.get("latency_adjusted") or window_data.get("latency")
        error_rate_stats = window_data.get("error_rate_adjusted") or window_data.get("error_rate")
        availability_stats = window_data.get("availability_adjusted") or window_data.get("availability")

        if not all([latency_stats, error_rate_stats, availability_stats]):
            raise ValueError(
                f"Incomplete metrics data for service: {service_id}. "
                "Missing latency, error_rate, or availability statistics."
            )

        # Balanced tier: Use constrained recommendations (default)
        balanced = {
            "availability": constrained_recommendations["availability"],
            "latency_p95_ms": constrained_recommendations["latency_p95_ms"],
            "latency_p99_ms": constrained_recommendations["latency_p99_ms"],
            "error_rate_percent": constrained_recommendations["error_rate_percent"]
        }

        # Aggressive tier: Use p75 historical performance (more ambitious)
        aggressive = {
            "availability": availability_stats.get("p75_percent", availability_stats["p95_percent"]),
            "latency_p95_ms": latency_stats.get("p75_ms", latency_stats["p95_ms"]),
            "latency_p99_ms": latency_stats.get("p75_ms", latency_stats["p99_ms"]),
            "error_rate_percent": error_rate_stats.get("p75_percent", error_rate_stats["p95_percent"])
        }

        # Conservative tier: Use p95 historical performance (safer)
        conservative = {
            "availability": availability_stats["p95_percent"],
            "latency_p95_ms": latency_stats["p95_ms"],
            "latency_p99_ms": latency_stats["p99_ms"],
            "error_rate_percent": error_rate_stats["p95_percent"]
        }

        # Ensure tier ordering is correct
        # Availability: aggressive >= balanced >= conservative (higher is better)
        aggressive["availability"] = max(aggressive["availability"], balanced["availability"])
        conservative["availability"] = min(conservative["availability"], balanced["availability"])

        # Latency: aggressive <= balanced <= conservative (lower is better)
        aggressive["latency_p95_ms"] = min(aggressive["latency_p95_ms"], balanced["latency_p95_ms"])
        aggressive["latency_p99_ms"] = min(aggressive["latency_p99_ms"], balanced["latency_p99_ms"])
        conservative["latency_p95_ms"] = max(conservative["latency_p95_ms"], balanced["latency_p95_ms"])
        conservative["latency_p99_ms"] = max(conservative["latency_p99_ms"], balanced["latency_p99_ms"])

        # Error rate: aggressive <= balanced <= conservative (lower is better)
        aggressive["error_rate_percent"] = min(aggressive["error_rate_percent"], balanced["error_rate_percent"])
        conservative["error_rate_percent"] = max(conservative["error_rate_percent"], balanced["error_rate_percent"])

        # Round all values for cleaner output
        for tier in [aggressive, balanced, conservative]:
            tier["availability"] = round(tier["availability"], 2)
            tier["latency_p95_ms"] = round(tier["latency_p95_ms"], 2)
            tier["latency_p99_ms"] = round(tier["latency_p99_ms"], 2)
            tier["error_rate_percent"] = round(tier["error_rate_percent"], 2)

        # Build metadata
        metadata = {
            "service_id": service_id,
            "time_window": time_window,
            "generated_at": datetime.utcnow().isoformat(),
            "tier_definitions": {
                "aggressive": "p75 historical performance (more ambitious)",
                "balanced": "constrained recommendations after dependency/infrastructure constraints (default)",
                "conservative": "p95 historical performance (safer)"
            },
            "historical_percentiles": {
                "availability": {
                    "p75": availability_stats.get("p75_percent"),
                    "p95": availability_stats["p95_percent"]
                },
                "latency_p95": {
                    "p75": latency_stats.get("p75_ms"),
                    "p95": latency_stats["p95_ms"]
                },
                "latency_p99": {
                    "p75": latency_stats.get("p75_ms"),
                    "p99": latency_stats["p99_ms"]
                },
                "error_rate": {
                    "p75": error_rate_stats.get("p75_percent"),
                    "p95": error_rate_stats["p95_percent"]
                }
            },
            "ordering_enforced": {
                "availability": "aggressive >= balanced >= conservative",
                "latency": "aggressive <= balanced <= conservative",
                "error_rate": "aggressive <= balanced <= conservative"
            },
            "data_quality": {
                "completeness": data_quality.get("completeness", 0.0),
                "staleness_hours": data_quality.get("staleness_hours", 0),
                "sample_count": data_quality.get("sample_count", 0),
                "quality_score": data_quality.get("quality_score", 0.0)
            }
        }

        return {
            "tiers": {
                "aggressive": aggressive,
                "balanced": balanced,
                "conservative": conservative
            },
            "metadata": metadata
        }

    def compute_confidence_score(
        self,
        service_id: str,
        time_window: str = "30d"
    ) -> Dict[str, Any]:
        """
        Compute confidence score for recommendations.

        The confidence score is computed based on four components:
        1. Data completeness (0-0.3): Based on metrics data quality
        2. Historical stability (0-0.3): Based on coefficient of variation (lower CV = more stable)
        3. Dependency clarity (0-0.2): Ratio of upstream services with known SLOs
        4. Knowledge base match (0-0.2): Placeholder for now (0.5 * 0.2 = 0.1)

        Formula:
        confidence = (
            0.3 * data_completeness +
            0.3 * (1 - coefficient_of_variation) +
            0.2 * dependency_completeness +
            0.2 * knowledge_base_match_score
        )

        Args:
            service_id: Service identifier
            time_window: Time window to use for historical data (default: "30d")

        Returns:
            Dict with:
                - confidence_score: float in [0, 1]
                - components: Dict with individual component scores
                - metadata: Dict with computation details

        Raises:
            ValueError: If service has no aggregated metrics or insufficient data
        """
        # Retrieve aggregated metrics for the service
        aggregated_metrics = self.metrics_engine.get_aggregated_metrics(service_id)

        if not aggregated_metrics:
            raise ValueError(
                f"No aggregated metrics found for service: {service_id}. "
                "Please ingest metrics and compute aggregations first."
            )

        # Get the specified time window
        time_windows = aggregated_metrics.get("time_windows", {})
        if time_window not in time_windows:
            raise ValueError(
                f"Time window '{time_window}' not found in aggregated metrics. "
                f"Available windows: {list(time_windows.keys())}"
            )

        window_data = time_windows[time_window]

        # Check data quality
        data_quality = window_data.get("data_quality", {})
        if data_quality.get("actual_samples", 0) == 0:
            raise ValueError(
                f"Insufficient data for time window '{time_window}'. "
                "No samples available."
            )

        # Extract aggregated statistics
        latency_stats = window_data.get("latency_adjusted") or window_data.get("latency")
        error_rate_stats = window_data.get("error_rate_adjusted") or window_data.get("error_rate")
        availability_stats = window_data.get("availability_adjusted") or window_data.get("availability")

        if not all([latency_stats, error_rate_stats, availability_stats]):
            raise ValueError(
                f"Incomplete metrics data for service: {service_id}. "
                "Missing latency, error_rate, or availability statistics."
            )

        # Component 1: Data completeness (0-0.3)
        # Use the completeness field from data quality, but also consider sample count
        completeness = data_quality.get("completeness", 0.0)
        actual_samples = data_quality.get("actual_samples", 0)
        expected_samples = data_quality.get("expected_samples", 1)
        
        # Boost completeness if we have good sample count
        if actual_samples > 0 and expected_samples > 0:
            sample_ratio = min(1.0, actual_samples / expected_samples)
            completeness = max(completeness, sample_ratio * 0.8)  # Cap at 0.8 if only using samples
        
        data_completeness_component = 0.3 * completeness

        # Component 2: Historical stability (0-0.3)
        # Based on coefficient of variation (CV = stddev / mean)
        # Lower CV = more stable = higher confidence
        # Formula: 0.3 * (1 - CV), clamped to [0, 0.3]

        # Calculate CV for latency (primary stability metric)
        latency_mean = latency_stats.get("mean_ms", 0)
        latency_stddev = latency_stats.get("stddev_ms", 0)

        if latency_mean > 0:
            coefficient_of_variation = latency_stddev / latency_mean
        else:
            coefficient_of_variation = 1.0  # Worst case if no data

        # Clamp CV to [0, 1] for stability calculation
        coefficient_of_variation = max(0.0, min(1.0, coefficient_of_variation))

        # Calculate stability component: 0.3 * (1 - CV)
        historical_stability_component = 0.3 * (1 - coefficient_of_variation)

        # Component 3: Dependency clarity (0-0.2)
        # Ratio of upstream services with known SLOs
        dependency_clarity_component = 0.0
        dependency_metadata = {
            "upstream_services_count": 0,
            "upstream_with_slos_count": 0,
            "dependency_completeness": 0.0
        }

        # Load analyzed dependency graph
        analyzed_graph_path = "dependencies/analyzed_graph.json"
        analyzed_graph_data = self.storage.read_json(analyzed_graph_path)

        if analyzed_graph_data and "services" in analyzed_graph_data:
            # Find the service in the analyzed graph
            service_analysis = None
            for svc in analyzed_graph_data["services"]:
                if svc["service_id"] == service_id:
                    service_analysis = svc
                    break

            if service_analysis:
                upstream_services = service_analysis.get("upstream_services", [])
                dependency_metadata["upstream_services_count"] = len(upstream_services)

                if upstream_services:
                    # Count how many upstream services have SLOs
                    upstream_with_slos = 0
                    for upstream_id in upstream_services:
                        upstream_rec_path = f"recommendations/{upstream_id}/latest.json"
                        upstream_rec = self.storage.read_json(upstream_rec_path)
                        if upstream_rec and "recommendations" in upstream_rec:
                            upstream_with_slos += 1

                    dependency_metadata["upstream_with_slos_count"] = upstream_with_slos

                    # Calculate dependency completeness ratio
                    dependency_completeness = upstream_with_slos / len(upstream_services)
                    dependency_metadata["dependency_completeness"] = dependency_completeness

                    # Calculate component: 0.2 * dependency_completeness
                    dependency_clarity_component = 0.2 * dependency_completeness
                else:
                    # No upstream dependencies = full clarity (1.0)
                    dependency_metadata["dependency_completeness"] = 1.0
                    dependency_clarity_component = 0.2 * 1.0
        else:
            # No dependency graph = assume full clarity (conservative)
            dependency_metadata["dependency_completeness"] = 1.0
            dependency_clarity_component = 0.2 * 1.0

        # Component 4: Knowledge base match (0-0.2)
        # Use data quality score as a proxy for knowledge base match
        # If we have good data quality, we have better knowledge
        knowledge_base_match_score = data_quality.get("quality_score", 0.5)
        knowledge_base_match_component = 0.2 * knowledge_base_match_score

        knowledge_metadata = {
            "match_score": knowledge_base_match_score,
            "note": "Based on data quality score"
        }

        # Calculate total confidence score
        total_confidence = (
            data_completeness_component +
            historical_stability_component +
            dependency_clarity_component +
            knowledge_base_match_component
        )

        # Ensure total is in [0, 1]
        total_confidence = max(0.0, min(1.0, total_confidence))

        # Round components for cleaner output
        components = {
            "data_completeness": round(data_completeness_component, 4),
            "historical_stability": round(historical_stability_component, 4),
            "dependency_clarity": round(dependency_clarity_component, 4),
            "knowledge_base_match": round(knowledge_base_match_component, 4),
            "total": round(total_confidence, 4)
        }

        # Build metadata
        metadata = {
            "service_id": service_id,
            "time_window": time_window,
            "computed_at": datetime.utcnow().isoformat(),
            "formula": "0.3 * data_completeness + 0.3 * (1 - CV) + 0.2 * dependency_completeness + 0.2 * knowledge_match",
            "data_quality": {
                "completeness": completeness,
                "staleness_hours": data_quality.get("staleness_hours", 0),
                "quality_score": data_quality.get("quality_score", 0.0)
            },
            "stability_metrics": {
                "latency_mean_ms": latency_mean,
                "latency_stddev_ms": latency_stddev,
                "coefficient_of_variation": round(coefficient_of_variation, 4),
                "stability_score": round(1 - coefficient_of_variation, 4)
            },
            "dependency_metrics": dependency_metadata,
            "knowledge_base_metrics": knowledge_metadata,
            "component_weights": {
                "data_completeness": 0.3,
                "historical_stability": 0.3,
                "dependency_clarity": 0.2,
                "knowledge_base_match": 0.2
            }
        }

        return {
            "confidence_score": round(total_confidence, 4),
            "components": components,
            "metadata": metadata
        }



    def generate_explanation(
        self,
        service_id: str,
        base_recommendations: Dict[str, float],
        constrained_recommendations: Dict[str, float],
        infrastructure_constrained_recommendations: Dict[str, float],
        dependency_metadata: Dict[str, Any],
        infrastructure_metadata: Dict[str, Any],
        confidence_score: float,
        time_window: str = "30d"
    ) -> Dict[str, Any]:
        """
        Generate human-readable explanation for recommendations.
        
        The explanation includes:
        1. Summary: One sentence describing the recommendation rationale
        2. Top factors: Top 3 influencing factors (from historical metrics, dependencies, infrastructure)
        3. Dependency constraints: List of dependency constraints applied
        4. Infrastructure bottlenecks: List of infrastructure bottlenecks identified
        5. Similar services: References to similar services (placeholder for now)
        
        Args:
            service_id: Service identifier
            base_recommendations: Base statistical recommendations
            constrained_recommendations: Recommendations after dependency constraints
            infrastructure_constrained_recommendations: Final recommendations after infrastructure constraints
            dependency_metadata: Metadata from apply_dependency_constraints
            infrastructure_metadata: Metadata from apply_infrastructure_constraints
            confidence_score: Overall confidence score
            time_window: Time window used for historical data (default: "30d")
        
        Returns:
            Dict with:
                - summary: str (one sentence summary)
                - top_factors: List[str] (top 3 influencing factors)
                - dependency_constraints: List[str]
                - infrastructure_bottlenecks: List[str]
                - similar_services: List[str] (placeholder)
        
        Raises:
            ValueError: If service has no aggregated metrics
        """
        # Retrieve aggregated metrics for the service
        aggregated_metrics = self.metrics_engine.get_aggregated_metrics(service_id)
        
        if not aggregated_metrics:
            raise ValueError(
                f"No aggregated metrics found for service: {service_id}. "
                "Please ingest metrics and compute aggregations first."
            )
        
        # Get the specified time window
        time_windows = aggregated_metrics.get("time_windows", {})
        if time_window not in time_windows:
            raise ValueError(
                f"Time window '{time_window}' not found in aggregated metrics. "
                f"Available windows: {list(time_windows.keys())}"
            )
        
        window_data = time_windows[time_window]
        
        # Extract aggregated statistics
        latency_stats = window_data.get("latency_adjusted") or window_data.get("latency")
        error_rate_stats = window_data.get("error_rate_adjusted") or window_data.get("error_rate")
        availability_stats = window_data.get("availability_adjusted") or window_data.get("availability")
        
        # Build top factors list
        top_factors = []
        
        # Factor 1: Historical metrics (always include)
        historical_factor = (
            f"Historical p95 latency: {latency_stats['p95_ms']:.2f}ms, "
            f"availability: {availability_stats['p95_percent']:.2f}% "
            f"({time_window} window)"
        )
        top_factors.append(historical_factor)
        
        # Factor 2: Dependency constraints (if any were applied)
        dependency_constraints_applied = dependency_metadata.get("availability_constraints", []) or \
                                        dependency_metadata.get("latency_constraints", [])
        
        if dependency_constraints_applied:
            # Find the most significant dependency constraint
            upstream_services = dependency_metadata.get("upstream_services_checked", [])
            if upstream_services:
                # Check if availability was constrained
                avail_constraints = dependency_metadata.get("availability_constraints", [])
                if avail_constraints:
                    # Find the constraint that was actually applied
                    applied_constraint = None
                    for constraint in avail_constraints:
                        if constraint.get("constrained_value") is not None:
                            applied_constraint = constraint
                            break
                    
                    if applied_constraint:
                        upstream_service = applied_constraint.get("upstream_service", "unknown")
                        upstream_avail = applied_constraint.get("upstream_availability", 0)
                        dependency_factor = (
                            f"Downstream of '{upstream_service}' "
                            f"({upstream_avail:.2f}% availability) requires margin"
                        )
                        top_factors.append(dependency_factor)
                    else:
                        # No constraint was applied, but dependencies exist
                        dependency_factor = f"Depends on {len(upstream_services)} upstream service(s)"
                        top_factors.append(dependency_factor)
                else:
                    dependency_factor = f"Depends on {len(upstream_services)} upstream service(s)"
                    top_factors.append(dependency_factor)
        
        # Factor 3: Infrastructure constraints (if any were applied)
        datastore_constraints = infrastructure_metadata.get("datastore_constraints", [])
        if datastore_constraints:
            # Find the most significant infrastructure constraint
            applied_constraint = None
            for constraint in datastore_constraints:
                if constraint.get("is_bottleneck", False):
                    applied_constraint = constraint
                    break
            
            if applied_constraint:
                datastore_name = applied_constraint.get("datastore", "unknown")
                datastore_type = applied_constraint.get("type", "unknown")
                constraint_type = applied_constraint.get("constraint_type", "unknown")
                
                if constraint_type == "latency":
                    datastore_latency = applied_constraint.get("datastore_latency", 0)
                    infrastructure_factor = (
                        f"{datastore_type.capitalize()} datastore '{datastore_name}' "
                        f"adds {datastore_latency:.2f}ms baseline latency"
                    )
                elif constraint_type == "availability":
                    datastore_avail = applied_constraint.get("datastore_slo", 0)
                    infrastructure_factor = (
                        f"{datastore_type.capitalize()} datastore '{datastore_name}' "
                        f"limits availability to {datastore_avail:.2f}%"
                    )
                else:
                    infrastructure_factor = (
                        f"{datastore_type.capitalize()} datastore '{datastore_name}' "
                        f"constrains {constraint_type}"
                    )
                
                top_factors.append(infrastructure_factor)
            else:
                # Check if there are any datastores even if not bottlenecks
                datastores = infrastructure_metadata.get("infrastructure_components", {}).get("datastores", [])
                if datastores:
                    datastore = datastores[0]
                    datastore_name = datastore.get("name", "unknown")
                    datastore_type = datastore.get("type", "unknown")
                    infrastructure_factor = f"Uses {datastore_type} datastore '{datastore_name}'"
                    top_factors.append(infrastructure_factor)
        
        # Ensure we have exactly 3 factors (pad with generic info if needed)
        if len(top_factors) < 3:
            # Add data quality as a factor
            data_quality = window_data.get("data_quality", {})
            quality_score = data_quality.get("quality_score", 0.0)
            completeness = data_quality.get("completeness", 0.0)
            
            quality_factor = (
                f"Data quality: {quality_score:.1%} "
                f"(completeness: {completeness:.1%})"
            )
            top_factors.append(quality_factor)
        
        # Trim to exactly 3 factors
        top_factors = top_factors[:3]
        
        # Build dependency constraints list
        dependency_constraints_list = []
        
        # Add availability constraints
        avail_constraints = dependency_metadata.get("availability_constraints", [])
        for constraint in avail_constraints:
            if constraint.get("constrained_value") is not None:
                upstream_service = constraint.get("upstream_service", "unknown")
                upstream_avail = constraint.get("upstream_availability", 0)
                margin = constraint.get("margin", 0)
                constrained_value = constraint.get("constrained_value", 0)
                
                constraint_desc = (
                    f"'{upstream_service}' availability ({upstream_avail:.2f}%) "
                    f"limits this service to {constrained_value:.2f}%"
                )
                dependency_constraints_list.append(constraint_desc)
        
        # Add latency constraints
        latency_constraints = dependency_metadata.get("latency_constraints", [])
        for constraint in latency_constraints:
            if constraint.get("constraint_type") == "critical_path_budget":
                total_budget = constraint.get("total_budget_ms", 0)
                path_length = constraint.get("path_length", 0)
                
                constraint_desc = (
                    f"Critical path budget: {total_budget:.2f}ms "
                    f"across {path_length} service(s)"
                )
                dependency_constraints_list.append(constraint_desc)
        
        # Build infrastructure bottlenecks list
        infrastructure_bottlenecks_list = []
        
        # Get bottleneck analysis from metadata
        bottleneck_analysis = infrastructure_metadata.get("bottleneck_analysis", {})
        bottlenecks = bottleneck_analysis.get("bottlenecks", [])
        
        for bottleneck in bottlenecks:
            description = bottleneck.get("description", "Unknown bottleneck")
            infrastructure_bottlenecks_list.append(description)
        
        # If no bottlenecks, check for near-bottlenecks
        if not infrastructure_bottlenecks_list:
            near_bottlenecks = bottleneck_analysis.get("near_bottlenecks", [])
            for near_bottleneck in near_bottlenecks:
                description = near_bottleneck.get("description", "Unknown near-bottleneck")
                infrastructure_bottlenecks_list.append(description)
        
        # Build similar services list (placeholder for now)
        similar_services_list = []
        # TODO: Implement knowledge layer integration to find similar services
        # For now, return empty list as per task requirements
        
        # Generate summary sentence
        # Determine the tier based on confidence and constraints
        if confidence_score >= 0.8:
            confidence_level = "high confidence"
        elif confidence_score >= 0.6:
            confidence_level = "moderate confidence"
        else:
            confidence_level = "low confidence"
        
        # Determine complexity based on constraints
        has_dependency_constraints = len(dependency_constraints_list) > 0
        has_infrastructure_constraints = len(infrastructure_bottlenecks_list) > 0
        
        if has_dependency_constraints and has_infrastructure_constraints:
            complexity = "complex dependency and infrastructure constraints"
        elif has_dependency_constraints:
            complexity = "dependency constraints"
        elif has_infrastructure_constraints:
            complexity = "infrastructure constraints"
        else:
            complexity = "stable historical performance"
        
        # Build summary
        summary = (
            f"Balanced tier recommended with {confidence_level} "
            f"based on {complexity}"
        )
        
        return {
            "summary": summary,
            "top_factors": top_factors,
            "dependency_constraints": dependency_constraints_list,
            "infrastructure_bottlenecks": infrastructure_bottlenecks_list,
            "similar_services": similar_services_list
        }
    def validate_achievability(
        self,
        service_id: str,
        recommendations: Dict[str, float],
        time_window: str = "30d",
        availability_max_increase: float = 1.0,
        latency_max_decrease_percent: float = 0.2,
        error_rate_max_decrease_percent: float = 0.2
    ) -> Dict[str, Any]:
        """
        Validate that recommendations are achievable based on historical performance.

        This method implements safety guardrails to ensure recommendations don't exceed
        historical performance by unrealistic margins:
        - Availability: recommended <= historical p99 + max_increase (default: +1%)
        - Latency: recommended >= historical p50 - max_decrease_percent (default: -20%)
        - Error Rate: recommended >= historical p50 - max_decrease_percent (default: -20%)

        If recommendations exceed these thresholds, they are adjusted to be more realistic.

        Args:
            service_id: Service identifier
            recommendations: Dict with recommended SLO values:
                - availability: float (percentage)
                - latency_p95_ms: float (milliseconds)
                - latency_p99_ms: float (milliseconds)
                - error_rate_percent: float (percentage)
            time_window: Time window to use for historical data (default: "30d")
            availability_max_increase: Max increase above historical p99 availability (default: 1.0%)
            latency_max_decrease_percent: Max decrease below historical p50 latency (default: 0.2 = 20%)
            error_rate_max_decrease_percent: Max decrease below historical p50 error rate (default: 0.2 = 20%)

        Returns:
            Dict with:
                - validated_recommendations: Dict with adjusted SLO values
                - adjustments_made: List of adjustment descriptions
                - warnings: List of warning messages
                - metadata: Dict with validation details

        Raises:
            ValueError: If service has no aggregated metrics or recommendations missing required keys
        """
        # Validate input
        required_keys = ["availability", "latency_p95_ms", "latency_p99_ms", "error_rate_percent"]
        missing_keys = [key for key in required_keys if key not in recommendations]
        if missing_keys:
            raise ValueError(
                f"recommendations missing required keys: {missing_keys}. "
                f"Required keys: {required_keys}"
            )

        # Retrieve aggregated metrics for the service
        aggregated_metrics = self.metrics_engine.get_aggregated_metrics(service_id)

        if not aggregated_metrics:
            raise ValueError(
                f"No aggregated metrics found for service: {service_id}. "
                "Please ingest metrics and compute aggregations first."
            )

        # Get the specified time window
        time_windows = aggregated_metrics.get("time_windows", {})
        if time_window not in time_windows:
            raise ValueError(
                f"Time window '{time_window}' not found in aggregated metrics. "
                f"Available windows: {list(time_windows.keys())}"
            )

        window_data = time_windows[time_window]

        # Check data quality
        data_quality = window_data.get("data_quality", {})
        if data_quality.get("actual_samples", 0) == 0:
            raise ValueError(
                f"Insufficient data for time window '{time_window}'. "
                "No samples available."
            )

        # Extract aggregated statistics (use adjusted if available)
        latency_stats = window_data.get("latency_adjusted") or window_data.get("latency")
        error_rate_stats = window_data.get("error_rate_adjusted") or window_data.get("error_rate")
        availability_stats = window_data.get("availability_adjusted") or window_data.get("availability")

        if not all([latency_stats, error_rate_stats, availability_stats]):
            raise ValueError(
                f"Incomplete metrics data for service: {service_id}. "
                "Missing latency, error_rate, or availability statistics."
            )

        # Start with a copy of recommendations
        validated = recommendations.copy()
        adjustments_made = []
        warnings = []
        validation_details = {
            "availability_validation": {},
            "latency_validation": {},
            "error_rate_validation": {},
            "thresholds": {
                "availability_max_increase": availability_max_increase,
                "latency_max_decrease_percent": latency_max_decrease_percent,
                "error_rate_max_decrease_percent": error_rate_max_decrease_percent
            }
        }

        # Validate Availability
        # Rule: recommended availability <= historical p99 availability + max_increase
        historical_p99_availability = availability_stats.get("p99_percent", availability_stats["p95_percent"])
        max_achievable_availability = historical_p99_availability + availability_max_increase

        # Ensure max_achievable_availability doesn't exceed 100%
        max_achievable_availability = min(100.0, max_achievable_availability)

        validation_details["availability_validation"] = {
            "historical_p99": historical_p99_availability,
            "max_achievable": max_achievable_availability,
            "recommended": recommendations["availability"],
            "threshold_exceeded": recommendations["availability"] > max_achievable_availability
        }

        if recommendations["availability"] > max_achievable_availability:
            original_availability = recommendations["availability"]
            validated["availability"] = max_achievable_availability

            adjustment_desc = (
                f"Availability adjusted for achievability: "
                f"{original_availability:.2f}% → {max_achievable_availability:.2f}% "
                f"(historical p99: {historical_p99_availability:.2f}%, "
                f"max increase: {availability_max_increase:.2f}%)"
            )
            adjustments_made.append(adjustment_desc)

            warning_msg = (
                f"Recommended availability ({original_availability:.2f}%) exceeds "
                f"historical p99 ({historical_p99_availability:.2f}%) by more than "
                f"{availability_max_increase:.2f}% - adjusted to {max_achievable_availability:.2f}%"
            )
            warnings.append(warning_msg)

            validation_details["availability_validation"]["adjusted_value"] = max_achievable_availability
            validation_details["availability_validation"]["adjustment_reason"] = "Exceeded historical p99 + max_increase"

        # Validate Latency p95
        # Rule: recommended latency >= historical p50 latency - max_decrease_percent
        historical_p50_latency = latency_stats.get("p50_ms", latency_stats.get("mean_ms", latency_stats["p95_ms"]))
        min_achievable_latency_p95 = historical_p50_latency * (1 - latency_max_decrease_percent)

        # Ensure min_achievable_latency is positive
        min_achievable_latency_p95 = max(1.0, min_achievable_latency_p95)

        validation_details["latency_validation"] = {
            "p95": {
                "historical_p50": historical_p50_latency,
                "min_achievable": min_achievable_latency_p95,
                "recommended": recommendations["latency_p95_ms"],
                "threshold_exceeded": recommendations["latency_p95_ms"] < min_achievable_latency_p95
            }
        }

        if recommendations["latency_p95_ms"] < min_achievable_latency_p95:
            original_latency_p95 = recommendations["latency_p95_ms"]
            validated["latency_p95_ms"] = min_achievable_latency_p95

            adjustment_desc = (
                f"Latency p95 adjusted for achievability: "
                f"{original_latency_p95:.2f}ms → {min_achievable_latency_p95:.2f}ms "
                f"(historical p50: {historical_p50_latency:.2f}ms, "
                f"max decrease: {latency_max_decrease_percent:.1%})"
            )
            adjustments_made.append(adjustment_desc)

            warning_msg = (
                f"Recommended latency p95 ({original_latency_p95:.2f}ms) is more than "
                f"{latency_max_decrease_percent:.1%} below historical p50 "
                f"({historical_p50_latency:.2f}ms) - adjusted to {min_achievable_latency_p95:.2f}ms"
            )
            warnings.append(warning_msg)

            validation_details["latency_validation"]["p95"]["adjusted_value"] = min_achievable_latency_p95
            validation_details["latency_validation"]["p95"]["adjustment_reason"] = "Below historical p50 - max_decrease_percent"

        # Validate Latency p99
        # Rule: recommended latency >= historical p50 latency - max_decrease_percent
        # Also ensure p99 >= p95
        min_achievable_latency_p99 = historical_p50_latency * (1 - latency_max_decrease_percent)
        min_achievable_latency_p99 = max(1.0, min_achievable_latency_p99)

        # Ensure p99 >= p95 (use the validated p95 value)
        min_achievable_latency_p99 = max(min_achievable_latency_p99, validated["latency_p95_ms"])

        validation_details["latency_validation"]["p99"] = {
            "historical_p50": historical_p50_latency,
            "min_achievable": min_achievable_latency_p99,
            "recommended": recommendations["latency_p99_ms"],
            "threshold_exceeded": recommendations["latency_p99_ms"] < min_achievable_latency_p99
        }

        if recommendations["latency_p99_ms"] < min_achievable_latency_p99:
            original_latency_p99 = recommendations["latency_p99_ms"]
            validated["latency_p99_ms"] = min_achievable_latency_p99

            adjustment_desc = (
                f"Latency p99 adjusted for achievability: "
                f"{original_latency_p99:.2f}ms → {min_achievable_latency_p99:.2f}ms "
                f"(historical p50: {historical_p50_latency:.2f}ms, "
                f"max decrease: {latency_max_decrease_percent:.1%})"
            )
            adjustments_made.append(adjustment_desc)

            warning_msg = (
                f"Recommended latency p99 ({original_latency_p99:.2f}ms) is more than "
                f"{latency_max_decrease_percent:.1%} below historical p50 "
                f"({historical_p50_latency:.2f}ms) - adjusted to {min_achievable_latency_p99:.2f}ms"
            )
            warnings.append(warning_msg)

            validation_details["latency_validation"]["p99"]["adjusted_value"] = min_achievable_latency_p99
            validation_details["latency_validation"]["p99"]["adjustment_reason"] = "Below historical p50 - max_decrease_percent or below p95"

        # Validate Error Rate
        # Rule: recommended error rate >= historical p50 error rate - max_decrease_percent
        historical_p50_error_rate = error_rate_stats.get("p50_percent", error_rate_stats.get("mean_percent", error_rate_stats["p95_percent"]))
        min_achievable_error_rate = historical_p50_error_rate * (1 - error_rate_max_decrease_percent)

        # Ensure min_achievable_error_rate is non-negative and within [0, 100]
        min_achievable_error_rate = max(0.0, min(100.0, min_achievable_error_rate))

        validation_details["error_rate_validation"] = {
            "historical_p50": historical_p50_error_rate,
            "min_achievable": min_achievable_error_rate,
            "recommended": recommendations["error_rate_percent"],
            "threshold_exceeded": recommendations["error_rate_percent"] < min_achievable_error_rate
        }

        if recommendations["error_rate_percent"] < min_achievable_error_rate:
            original_error_rate = recommendations["error_rate_percent"]
            validated["error_rate_percent"] = min_achievable_error_rate

            adjustment_desc = (
                f"Error rate adjusted for achievability: "
                f"{original_error_rate:.2f}% → {min_achievable_error_rate:.2f}% "
                f"(historical p50: {historical_p50_error_rate:.2f}%, "
                f"max decrease: {error_rate_max_decrease_percent:.1%})"
            )
            adjustments_made.append(adjustment_desc)

            warning_msg = (
                f"Recommended error rate ({original_error_rate:.2f}%) is more than "
                f"{error_rate_max_decrease_percent:.1%} below historical p50 "
                f"({historical_p50_error_rate:.2f}%) - adjusted to {min_achievable_error_rate:.2f}%"
            )
            warnings.append(warning_msg)

            validation_details["error_rate_validation"]["adjusted_value"] = min_achievable_error_rate
            validation_details["error_rate_validation"]["adjustment_reason"] = "Below historical p50 - max_decrease_percent"

        # Round validated values for cleaner output
        validated["availability"] = round(validated["availability"], 2)
        validated["latency_p95_ms"] = round(validated["latency_p95_ms"], 2)
        validated["latency_p99_ms"] = round(validated["latency_p99_ms"], 2)
        validated["error_rate_percent"] = round(validated["error_rate_percent"], 2)

        # If no adjustments were made, note that
        if not adjustments_made:
            adjustments_made.append("No adjustments needed - all recommendations are achievable")

        # Build metadata
        metadata = {
            "service_id": service_id,
            "time_window": time_window,
            "validated_at": datetime.utcnow().isoformat(),
            "validation_details": validation_details,
            "historical_metrics": {
                "availability_p99": historical_p99_availability,
                "latency_p50": historical_p50_latency,
                "error_rate_p50": historical_p50_error_rate
            },
            "data_quality": {
                "completeness": data_quality.get("completeness", 0.0),
                "staleness_hours": data_quality.get("staleness_hours", 0),
                "sample_count": data_quality.get("sample_count", 0),
                "quality_score": data_quality.get("quality_score", 0.0)
            }
        }

        return {
            "validated_recommendations": validated,
            "adjustments_made": adjustments_made,
            "warnings": warnings,
            "metadata": metadata
        }

    def validate_minimum_thresholds(
        self,
        recommendations: Dict[str, float],
        min_availability: float = 90.0,
        min_latency_ms: float = 1.0,
        min_error_rate: float = 0.0,
        max_error_rate: float = 100.0
    ) -> Dict[str, Any]:
        """
        Validate that recommendations meet minimum threshold requirements.

        This method implements safety guardrails to ensure recommendations meet basic
        quality standards:
        - Availability: >= min_availability (default: 90%)
        - Latency p95: > min_latency_ms (default: 1.0ms, must be positive)
        - Latency p99: > min_latency_ms (default: 1.0ms, must be positive)
        - Error rate: within [min_error_rate, max_error_rate] (default: [0, 100])

        If recommendations fall below minimum thresholds, they are adjusted to meet
        the minimum requirements.

        Args:
            recommendations: Dict with recommended SLO values:
                - availability: float (percentage)
                - latency_p95_ms: float (milliseconds)
                - latency_p99_ms: float (milliseconds)
                - error_rate_percent: float (percentage)
            min_availability: Minimum acceptable availability (default: 90.0%)
            min_latency_ms: Minimum acceptable latency (default: 1.0ms, must be positive)
            min_error_rate: Minimum acceptable error rate (default: 0.0%)
            max_error_rate: Maximum acceptable error rate (default: 100.0%)

        Returns:
            Dict with:
                - validated_recommendations: Dict with adjusted SLO values
                - adjustments_made: List of adjustment descriptions
                - warnings: List of warning messages
                - metadata: Dict with validation details

        Raises:
            ValueError: If recommendations is missing required keys or thresholds are invalid
        """
        # Validate input
        required_keys = ["availability", "latency_p95_ms", "latency_p99_ms", "error_rate_percent"]
        missing_keys = [key for key in required_keys if key not in recommendations]
        if missing_keys:
            raise ValueError(
                f"recommendations missing required keys: {missing_keys}. "
                f"Required keys: {required_keys}"
            )

        # Validate threshold parameters
        if min_availability < 0 or min_availability > 100:
            raise ValueError(
                f"min_availability must be in range [0, 100], got: {min_availability}"
            )

        if min_latency_ms <= 0:
            raise ValueError(
                f"min_latency_ms must be positive, got: {min_latency_ms}"
            )

        if min_error_rate < 0 or min_error_rate > 100:
            raise ValueError(
                f"min_error_rate must be in range [0, 100], got: {min_error_rate}"
            )

        if max_error_rate < 0 or max_error_rate > 100:
            raise ValueError(
                f"max_error_rate must be in range [0, 100], got: {max_error_rate}"
            )

        if min_error_rate > max_error_rate:
            raise ValueError(
                f"min_error_rate ({min_error_rate}) cannot be greater than "
                f"max_error_rate ({max_error_rate})"
            )

        # Start with a copy of recommendations
        validated = recommendations.copy()
        adjustments_made = []
        warnings = []
        validation_details = {
            "availability_validation": {},
            "latency_p95_validation": {},
            "latency_p99_validation": {},
            "error_rate_validation": {},
            "thresholds": {
                "min_availability": min_availability,
                "min_latency_ms": min_latency_ms,
                "min_error_rate": min_error_rate,
                "max_error_rate": max_error_rate
            }
        }

        # Validate Availability
        # Rule: availability >= min_availability
        validation_details["availability_validation"] = {
            "original_value": recommendations["availability"],
            "min_threshold": min_availability,
            "threshold_violated": recommendations["availability"] < min_availability
        }

        if recommendations["availability"] < min_availability:
            original_availability = recommendations["availability"]
            validated["availability"] = min_availability

            adjustment_desc = (
                f"Availability adjusted to meet minimum threshold: "
                f"{original_availability:.2f}% → {min_availability:.2f}% "
                f"(minimum: {min_availability:.2f}%)"
            )
            adjustments_made.append(adjustment_desc)

            warning_msg = (
                f"Recommended availability ({original_availability:.2f}%) is below "
                f"minimum acceptable threshold ({min_availability:.2f}%) - "
                f"adjusted to {min_availability:.2f}%"
            )
            warnings.append(warning_msg)

            validation_details["availability_validation"]["adjusted_value"] = min_availability
            validation_details["availability_validation"]["adjustment_reason"] = "Below minimum threshold"

        # Validate Latency p95
        # Rule: latency_p95_ms > min_latency_ms (must be positive)
        validation_details["latency_p95_validation"] = {
            "original_value": recommendations["latency_p95_ms"],
            "min_threshold": min_latency_ms,
            "threshold_violated": recommendations["latency_p95_ms"] <= min_latency_ms
        }

        if recommendations["latency_p95_ms"] <= min_latency_ms:
            original_latency_p95 = recommendations["latency_p95_ms"]
            validated["latency_p95_ms"] = min_latency_ms

            adjustment_desc = (
                f"Latency p95 adjusted to meet minimum threshold: "
                f"{original_latency_p95:.2f}ms → {min_latency_ms:.2f}ms "
                f"(minimum: {min_latency_ms:.2f}ms)"
            )
            adjustments_made.append(adjustment_desc)

            warning_msg = (
                f"Recommended latency p95 ({original_latency_p95:.2f}ms) is at or below "
                f"minimum acceptable threshold ({min_latency_ms:.2f}ms) - "
                f"adjusted to {min_latency_ms:.2f}ms"
            )
            warnings.append(warning_msg)

            validation_details["latency_p95_validation"]["adjusted_value"] = min_latency_ms
            validation_details["latency_p95_validation"]["adjustment_reason"] = "At or below minimum threshold"

        # Validate Latency p99
        # Rule: latency_p99_ms > min_latency_ms (must be positive)
        # Also ensure p99 >= p95
        min_latency_p99 = max(min_latency_ms, validated["latency_p95_ms"])

        validation_details["latency_p99_validation"] = {
            "original_value": recommendations["latency_p99_ms"],
            "min_threshold": min_latency_ms,
            "effective_min_threshold": min_latency_p99,
            "threshold_violated": recommendations["latency_p99_ms"] < min_latency_p99
        }

        if recommendations["latency_p99_ms"] < min_latency_p99:
            original_latency_p99 = recommendations["latency_p99_ms"]
            validated["latency_p99_ms"] = min_latency_p99

            if min_latency_p99 > min_latency_ms:
                # Adjusted because p99 must be >= p95
                adjustment_desc = (
                    f"Latency p99 adjusted to maintain p99 >= p95: "
                    f"{original_latency_p99:.2f}ms → {min_latency_p99:.2f}ms "
                    f"(p95: {validated['latency_p95_ms']:.2f}ms)"
                )
                adjustment_reason = "Below p95 threshold"
            else:
                # Adjusted because below minimum threshold
                adjustment_desc = (
                    f"Latency p99 adjusted to meet minimum threshold: "
                    f"{original_latency_p99:.2f}ms → {min_latency_p99:.2f}ms "
                    f"(minimum: {min_latency_ms:.2f}ms)"
                )
                adjustment_reason = "Below minimum threshold"

            adjustments_made.append(adjustment_desc)

            warning_msg = (
                f"Recommended latency p99 ({original_latency_p99:.2f}ms) is below "
                f"acceptable threshold ({min_latency_p99:.2f}ms) - "
                f"adjusted to {min_latency_p99:.2f}ms"
            )
            warnings.append(warning_msg)

            validation_details["latency_p99_validation"]["adjusted_value"] = min_latency_p99
            validation_details["latency_p99_validation"]["adjustment_reason"] = adjustment_reason

        # Validate Error Rate
        # Rule: error_rate_percent must be within [min_error_rate, max_error_rate]
        validation_details["error_rate_validation"] = {
            "original_value": recommendations["error_rate_percent"],
            "min_threshold": min_error_rate,
            "max_threshold": max_error_rate,
            "threshold_violated": (
                recommendations["error_rate_percent"] < min_error_rate or
                recommendations["error_rate_percent"] > max_error_rate
            )
        }

        if recommendations["error_rate_percent"] < min_error_rate:
            original_error_rate = recommendations["error_rate_percent"]
            validated["error_rate_percent"] = min_error_rate

            adjustment_desc = (
                f"Error rate adjusted to meet minimum threshold: "
                f"{original_error_rate:.2f}% → {min_error_rate:.2f}% "
                f"(minimum: {min_error_rate:.2f}%)"
            )
            adjustments_made.append(adjustment_desc)

            warning_msg = (
                f"Recommended error rate ({original_error_rate:.2f}%) is below "
                f"minimum acceptable threshold ({min_error_rate:.2f}%) - "
                f"adjusted to {min_error_rate:.2f}%"
            )
            warnings.append(warning_msg)

            validation_details["error_rate_validation"]["adjusted_value"] = min_error_rate
            validation_details["error_rate_validation"]["adjustment_reason"] = "Below minimum threshold"

        elif recommendations["error_rate_percent"] > max_error_rate:
            original_error_rate = recommendations["error_rate_percent"]
            validated["error_rate_percent"] = max_error_rate

            adjustment_desc = (
                f"Error rate adjusted to meet maximum threshold: "
                f"{original_error_rate:.2f}% → {max_error_rate:.2f}% "
                f"(maximum: {max_error_rate:.2f}%)"
            )
            adjustments_made.append(adjustment_desc)

            warning_msg = (
                f"Recommended error rate ({original_error_rate:.2f}%) exceeds "
                f"maximum acceptable threshold ({max_error_rate:.2f}%) - "
                f"adjusted to {max_error_rate:.2f}%"
            )
            warnings.append(warning_msg)

            validation_details["error_rate_validation"]["adjusted_value"] = max_error_rate
            validation_details["error_rate_validation"]["adjustment_reason"] = "Above maximum threshold"

        # Round validated values for cleaner output
        validated["availability"] = round(validated["availability"], 2)
        validated["latency_p95_ms"] = round(validated["latency_p95_ms"], 2)
        validated["latency_p99_ms"] = round(validated["latency_p99_ms"], 2)
        validated["error_rate_percent"] = round(validated["error_rate_percent"], 2)

        # If no adjustments were made, note that
        if not adjustments_made:
            adjustments_made.append("No adjustments needed - all recommendations meet minimum thresholds")

        # Build metadata
        metadata = {
            "validated_at": datetime.utcnow().isoformat(),
            "validation_details": validation_details,
            "thresholds_applied": {
                "min_availability": min_availability,
                "min_latency_ms": min_latency_ms,
                "min_error_rate": min_error_rate,
                "max_error_rate": max_error_rate
            },
            "validation_summary": {
                "total_adjustments": len([adj for adj in adjustments_made if adj != "No adjustments needed - all recommendations meet minimum thresholds"]),
                "availability_adjusted": validation_details["availability_validation"].get("threshold_violated", False),
                "latency_p95_adjusted": validation_details["latency_p95_validation"].get("threshold_violated", False),
                "latency_p99_adjusted": validation_details["latency_p99_validation"].get("threshold_violated", False),
                "error_rate_adjusted": validation_details["error_rate_validation"].get("threshold_violated", False)
            }
        }

        return {
            "validated_recommendations": validated,
            "adjustments_made": adjustments_made,
            "warnings": warnings,
            "metadata": metadata
        }

    def validate_dependency_chain_consistency(
        self,
        service_id: str,
        recommendations: Dict[str, float]
    ) -> Dict[str, Any]:
        """
        Validate that recommendations are consistent with dependency chain constraints.

        This method ensures that:
        1. Downstream services don't have higher availability than upstream services
        2. Latency budgets are consistent across critical paths
        3. Recommendations don't create impossible dependency chains

        Args:
            service_id: Service identifier
            recommendations: Dict with recommended SLO values:
                - availability: float (percentage)
                - latency_p95_ms: float (milliseconds)
                - latency_p99_ms: float (milliseconds)
                - error_rate_percent: float (percentage)

        Returns:
            Dict with:
                - is_consistent: bool (True if all validations pass)
                - inconsistencies: List of inconsistency descriptions
                - warnings: List of warning messages
                - metadata: Dict with validation details

        Raises:
            ValueError: If recommendations is missing required keys
        """
        # Validate input
        required_keys = ["availability", "latency_p95_ms", "latency_p99_ms", "error_rate_percent"]
        missing_keys = [key for key in required_keys if key not in recommendations]
        if missing_keys:
            raise ValueError(
                f"recommendations missing required keys: {missing_keys}. "
                f"Required keys: {required_keys}"
            )

        inconsistencies = []
        warnings = []
        metadata = {
            "service_id": service_id,
            "validated_at": datetime.utcnow().isoformat(),
            "upstream_checks": [],
            "downstream_checks": [],
            "critical_path_checks": [],
            "recommendations_checked": recommendations
        }

        # Load analyzed dependency graph
        analyzed_graph_path = "dependencies/analyzed_graph.json"
        analyzed_graph_data = self.storage.read_json(analyzed_graph_path)

        # If no analyzed graph exists, return consistent (no dependencies to check)
        if not analyzed_graph_data or "services" not in analyzed_graph_data:
            metadata["note"] = "No dependency graph available - skipping consistency checks"
            return {
                "is_consistent": True,
                "inconsistencies": [],
                "warnings": ["No dependency graph available - consistency checks skipped"],
                "metadata": metadata
            }

        # Find the service in the analyzed graph
        service_analysis = None
        for svc in analyzed_graph_data["services"]:
            if svc["service_id"] == service_id:
                service_analysis = svc
                break

        # If service not found in graph, return consistent (no dependencies to check)
        if not service_analysis:
            metadata["note"] = f"Service {service_id} not found in dependency graph"
            return {
                "is_consistent": True,
                "inconsistencies": [],
                "warnings": [f"Service {service_id} not found in dependency graph - consistency checks skipped"],
                "metadata": metadata
            }

        # Check 1: Validate availability against upstream services
        # Rule: Service availability should be <= upstream availability
        upstream_services = service_analysis.get("upstream_services", [])
        metadata["upstream_services_count"] = len(upstream_services)

        for upstream_id in upstream_services:
            # Try to load upstream service's latest recommendation
            upstream_rec_path = f"recommendations/{upstream_id}/latest.json"
            upstream_rec = self.storage.read_json(upstream_rec_path)

            upstream_check = {
                "upstream_service": upstream_id,
                "has_recommendation": False,
                "availability_consistent": None,
                "details": {}
            }

            if upstream_rec and "recommendations" in upstream_rec:
                # Use the balanced tier as the reference
                upstream_slo = upstream_rec["recommendations"].get("balanced", {})
                upstream_availability = upstream_slo.get("availability")

                if upstream_availability is not None:
                    upstream_check["has_recommendation"] = True
                    upstream_check["upstream_availability"] = upstream_availability
                    upstream_check["service_availability"] = recommendations["availability"]

                    # Check if service availability exceeds upstream availability
                    if recommendations["availability"] > upstream_availability:
                        inconsistency_desc = (
                            f"Availability inconsistency: Service '{service_id}' has "
                            f"{recommendations['availability']:.2f}% availability, which exceeds "
                            f"upstream service '{upstream_id}' availability of {upstream_availability:.2f}%. "
                            f"A downstream service cannot be more available than its upstream dependencies."
                        )
                        inconsistencies.append(inconsistency_desc)
                        upstream_check["availability_consistent"] = False
                        upstream_check["details"]["inconsistency"] = inconsistency_desc
                    else:
                        upstream_check["availability_consistent"] = True
                        upstream_check["details"]["note"] = "Availability is consistent with upstream service"
                else:
                    # Upstream has recommendation but no availability value
                    warning_msg = (
                        f"Upstream service '{upstream_id}' has a recommendation but no availability value - "
                        "cannot validate consistency"
                    )
                    warnings.append(warning_msg)
                    upstream_check["details"]["warning"] = warning_msg
            else:
                # Upstream service has no SLO - note this as a warning
                warning_msg = (
                    f"Upstream service '{upstream_id}' has no SLO recommendation - "
                    "cannot validate availability consistency"
                )
                warnings.append(warning_msg)
                upstream_check["details"]["warning"] = warning_msg

            metadata["upstream_checks"].append(upstream_check)

        # Check 2: Validate availability against downstream services
        # Rule: Downstream services should have <= availability than this service
        downstream_services = service_analysis.get("downstream_services", [])
        metadata["downstream_services_count"] = len(downstream_services)

        for downstream_id in downstream_services:
            # Try to load downstream service's latest recommendation
            downstream_rec_path = f"recommendations/{downstream_id}/latest.json"
            downstream_rec = self.storage.read_json(downstream_rec_path)

            downstream_check = {
                "downstream_service": downstream_id,
                "has_recommendation": False,
                "availability_consistent": None,
                "details": {}
            }

            if downstream_rec and "recommendations" in downstream_rec:
                # Use the balanced tier as the reference
                downstream_slo = downstream_rec["recommendations"].get("balanced", {})
                downstream_availability = downstream_slo.get("availability")

                if downstream_availability is not None:
                    downstream_check["has_recommendation"] = True
                    downstream_check["downstream_availability"] = downstream_availability
                    downstream_check["service_availability"] = recommendations["availability"]

                    # Check if downstream availability exceeds this service's availability
                    if downstream_availability > recommendations["availability"]:
                        inconsistency_desc = (
                            f"Availability inconsistency: Downstream service '{downstream_id}' has "
                            f"{downstream_availability:.2f}% availability, which exceeds "
                            f"this service '{service_id}' availability of {recommendations['availability']:.2f}%. "
                            f"A downstream service cannot be more available than its upstream dependencies."
                        )
                        inconsistencies.append(inconsistency_desc)
                        downstream_check["availability_consistent"] = False
                        downstream_check["details"]["inconsistency"] = inconsistency_desc
                    else:
                        downstream_check["availability_consistent"] = True
                        downstream_check["details"]["note"] = "Downstream availability is consistent"
                else:
                    # Downstream has recommendation but no availability value
                    warning_msg = (
                        f"Downstream service '{downstream_id}' has a recommendation but no availability value - "
                        "cannot validate consistency"
                    )
                    warnings.append(warning_msg)
                    downstream_check["details"]["warning"] = warning_msg
            else:
                # Downstream service has no SLO - this is OK, just note it
                downstream_check["details"]["note"] = f"Downstream service '{downstream_id}' has no SLO recommendation yet"

            metadata["downstream_checks"].append(downstream_check)

        # Check 3: Validate latency consistency across critical paths
        # Rule: Total latency across critical path should be consistent with individual service latencies
        critical_paths = service_analysis.get("critical_paths", [])
        metadata["critical_paths_count"] = len(critical_paths)

        for path_idx, critical_path in enumerate(critical_paths):
            path_services = critical_path.get("path", [])
            total_budget = critical_path.get("total_latency_budget_ms")

            path_check = {
                "path_index": path_idx,
                "path_services": path_services,
                "total_budget_ms": total_budget,
                "is_consistent": None,
                "details": {}
            }

            if total_budget and len(path_services) > 0:
                # Calculate sum of individual service latencies in the path
                path_latency_sum = 0.0
                services_with_slos = []
                services_without_slos = []

                for path_service_id in path_services:
                    if path_service_id == service_id:
                        # Use the current recommendations for this service
                        path_latency_sum += recommendations["latency_p95_ms"]
                        services_with_slos.append({
                            "service_id": path_service_id,
                            "latency_p95_ms": recommendations["latency_p95_ms"]
                        })
                    else:
                        # Try to load the service's recommendation
                        path_service_rec_path = f"recommendations/{path_service_id}/latest.json"
                        path_service_rec = self.storage.read_json(path_service_rec_path)

                        if path_service_rec and "recommendations" in path_service_rec:
                            path_service_slo = path_service_rec["recommendations"].get("balanced", {})
                            path_service_latency = path_service_slo.get("latency_p95_ms")

                            if path_service_latency is not None:
                                path_latency_sum += path_service_latency
                                services_with_slos.append({
                                    "service_id": path_service_id,
                                    "latency_p95_ms": path_service_latency
                                })
                            else:
                                services_without_slos.append(path_service_id)
                        else:
                            services_without_slos.append(path_service_id)

                path_check["services_with_slos"] = services_with_slos
                path_check["services_without_slos"] = services_without_slos
                path_check["calculated_path_latency_ms"] = path_latency_sum

                # Only validate if we have SLOs for all services in the path
                if not services_without_slos:
                    # Check if sum of latencies exceeds the budget
                    if path_latency_sum > total_budget:
                        inconsistency_desc = (
                            f"Latency budget inconsistency: Critical path {path_services} has "
                            f"total budget of {total_budget:.2f}ms, but sum of individual service "
                            f"latencies is {path_latency_sum:.2f}ms (exceeds budget by "
                            f"{path_latency_sum - total_budget:.2f}ms). "
                            f"Individual service latencies must fit within the critical path budget."
                        )
                        inconsistencies.append(inconsistency_desc)
                        path_check["is_consistent"] = False
                        path_check["details"]["inconsistency"] = inconsistency_desc
                        path_check["details"]["budget_exceeded_by_ms"] = path_latency_sum - total_budget
                    else:
                        path_check["is_consistent"] = True
                        path_check["details"]["note"] = "Latency budget is consistent"
                        path_check["details"]["budget_headroom_ms"] = total_budget - path_latency_sum

                        # Add a warning if headroom is very small (< 10ms)
                        headroom = total_budget - path_latency_sum
                        if headroom < 10.0:
                            warning_msg = (
                                f"Critical path {path_services} has only {headroom:.2f}ms headroom "
                                f"in latency budget ({path_latency_sum:.2f}ms / {total_budget:.2f}ms used). "
                                f"Consider increasing budget or reducing service latencies."
                            )
                            warnings.append(warning_msg)
                            path_check["details"]["warning"] = warning_msg
                else:
                    # Cannot fully validate - some services don't have SLOs
                    warning_msg = (
                        f"Critical path {path_services} cannot be fully validated - "
                        f"{len(services_without_slos)} service(s) have no SLO recommendations: "
                        f"{', '.join(services_without_slos)}"
                    )
                    warnings.append(warning_msg)
                    path_check["details"]["warning"] = warning_msg
            else:
                path_check["details"]["note"] = "No latency budget defined for this critical path"

            metadata["critical_path_checks"].append(path_check)

        # Determine overall consistency
        is_consistent = len(inconsistencies) == 0

        # Add summary to metadata
        metadata["validation_summary"] = {
            "is_consistent": is_consistent,
            "total_inconsistencies": len(inconsistencies),
            "total_warnings": len(warnings),
            "upstream_services_checked": len(upstream_services),
            "downstream_services_checked": len(downstream_services),
            "critical_paths_checked": len(critical_paths)
        }

        return {
            "is_consistent": is_consistent,
            "inconsistencies": inconsistencies,
            "warnings": warnings,
            "metadata": metadata
        }


    def get_industry_standard_recommendations(
        self,
        service_type: str = "generic"
    ) -> Dict[str, float]:
        """
        Get industry standard SLO recommendations for a service type.

        This method provides fallback recommendations based on industry standards
        when confidence is low or data is insufficient. The standards are based
        on common SRE practices and typical service performance expectations.

        Industry Standards by Service Type:
        - API Gateway: 99.9% availability, 100ms p95 latency, 0.5% error rate
        - Database: 99.95% availability, 50ms p95 latency
        - Message Queue: 99.9% availability, 200ms p95 latency
        - Generic Service: 99.5% availability, 200ms p95 latency, 1.0% error rate

        Args:
            service_type: Type of service (default: "generic")
                Valid types: "api_gateway", "database", "message_queue", "generic"

        Returns:
            Dict with standard SLO values:
                - availability: float (percentage)
                - latency_p95_ms: float (milliseconds)
                - latency_p99_ms: float (milliseconds, typically 2x p95)
                - error_rate_percent: float (percentage)

        Example:
            >>> engine = RecommendationEngine()
            >>> standards = engine.get_industry_standard_recommendations("api_gateway")
            >>> print(standards)
            {
                "availability": 99.9,
                "latency_p95_ms": 100.0,
                "latency_p99_ms": 200.0,
                "error_rate_percent": 0.5
            }
        """
        # Normalize service type to lowercase and replace hyphens with underscores
        normalized_type = service_type.lower().replace("-", "_").replace(" ", "_")

        # Define industry standards for different service types
        industry_standards = {
            "api_gateway": {
                "availability": 99.9,
                "latency_p95_ms": 100.0,
                "latency_p99_ms": 200.0,  # Typically 2x p95
                "error_rate_percent": 0.5
            },
            "database": {
                "availability": 99.95,
                "latency_p95_ms": 50.0,
                "latency_p99_ms": 100.0,  # Typically 2x p95
                "error_rate_percent": 0.1  # Databases typically have very low error rates
            },
            "message_queue": {
                "availability": 99.9,
                "latency_p95_ms": 200.0,
                "latency_p99_ms": 400.0,  # Typically 2x p95
                "error_rate_percent": 0.5
            },
            "generic": {
                "availability": 99.5,
                "latency_p95_ms": 200.0,
                "latency_p99_ms": 400.0,  # Typically 2x p95
                "error_rate_percent": 1.0
            }
        }

        # Get the standard for the specified service type, default to generic
        standard = industry_standards.get(normalized_type, industry_standards["generic"])

        # Return a copy to prevent external modification
        return standard.copy()


