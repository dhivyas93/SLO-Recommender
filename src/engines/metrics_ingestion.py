"""
Metrics Ingestion Engine.

This module provides the MetricsIngestionEngine class that accepts, validates,
and processes operational metrics for services. It handles validation, outlier
detection, statistical aggregation, and data quality assessment.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import statistics

from src.models.metrics import (
    MetricsData,
    LatencyMetrics,
    ErrorRateMetrics,
    AvailabilityMetrics,
    RequestVolumeMetrics,
    RegionalMetrics,
    DataQuality,
    AggregatedMetrics,
    TimeWindowAggregatedMetrics,
    AggregatedLatencyStats,
    AggregatedErrorRateStats,
    AggregatedAvailabilityStats,
    TimeWindowQuality
)
from src.storage.file_storage import FileStorage
from src.utils.validators import validate_no_pii


class MetricsIngestionEngine:
    """
    Metrics Ingestion Engine for accepting and processing service metrics.
    
    Responsibilities:
    - Accept metrics via API (latency, error rate, availability)
    - Validate metric ranges and relationships
    - Store raw metrics with timestamp
    - Return data quality assessment
    - Compute aggregated statistics across time windows
    
    Attributes:
        storage: FileStorage instance for persisting metrics
    """
    
    def __init__(self, storage: Optional[FileStorage] = None):
        """
        Initialize MetricsIngestionEngine.
        
        Args:
            storage: FileStorage instance (creates default if None)
        """
        self.storage = storage or FileStorage(base_path="data")
    
    def ingest_metrics(
        self,
        service_id: str,
        time_window: str,
        latency: Dict[str, float],
        error_rate: Dict[str, Any],
        availability: Dict[str, Any],
        request_volume: Optional[Dict[str, float]] = None,
        regional_breakdown: Optional[Dict[str, Dict[str, float]]] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Ingest and validate metrics for a service.

        Args:
            service_id: Service identifier
            time_window: Time window (e.g., "1d", "7d", "30d", "90d")
            latency: Latency metrics dict with p50_ms, p95_ms, p99_ms, mean_ms, stddev_ms
            error_rate: Error rate metrics dict with percent, total_requests, failed_requests
            availability: Availability metrics dict with percent, uptime_seconds, downtime_seconds
            request_volume: Optional request volume metrics with requests_per_second, peak_rps
            regional_breakdown: Optional regional metrics by region name
            timestamp: Optional timestamp (defaults to now)

        Returns:
            Dict with status, timestamp, data_quality, and validation_results

        Raises:
            ValueError: If validation fails (PII detected, invalid ranges, etc.)
        """
        # Use current time if not provided
        if timestamp is None:
            timestamp = datetime.utcnow()

        # Validate service_id for PII
        validate_no_pii(service_id, field_name="service_id")

        # Validate time_window format
        if time_window not in ["1d", "7d", "30d", "90d"]:
            raise ValueError(f"Invalid time_window: {time_window}. Must be one of: 1d, 7d, 30d, 90d")

        # Build and validate metrics models
        try:
            latency_metrics = LatencyMetrics(**latency)
            error_rate_metrics = ErrorRateMetrics(**error_rate)
            availability_metrics = AvailabilityMetrics(**availability)

            # Collect validation warnings
            warnings = []

            # Validate error rate consistency
            error_rate_warnings = self._validate_error_rate_consistency(error_rate_metrics)
            warnings.extend(error_rate_warnings)

            # Validate availability consistency
            availability_warnings = self._validate_availability_consistency(availability_metrics)
            warnings.extend(availability_warnings)

            # Validate metrics quality
            quality_warnings = self._validate_metrics_quality(error_rate_metrics, availability_metrics)
            warnings.extend(quality_warnings)

            # Build metrics dict
            metrics_dict = {
                "latency": latency_metrics,
                "error_rate": error_rate_metrics,
                "availability": availability_metrics
            }

            # Add request volume if provided
            if request_volume:
                request_volume_metrics = RequestVolumeMetrics(**request_volume)
                metrics_dict["request_volume"] = request_volume_metrics

            # Build regional breakdown if provided
            regional_data = None
            if regional_breakdown:
                regional_data = {}
                for region, metrics in regional_breakdown.items():
                    validate_no_pii(region, field_name=f"region_{region}")
                    regional_data[region] = RegionalMetrics(**metrics)

            # Compute data quality
            data_quality = self._compute_data_quality(
                service_id,
                latency_metrics,
                error_rate_metrics,
                availability_metrics,
                request_volume_metrics if request_volume else None,
                timestamp
            )

            # Create MetricsData model
            metrics_data = MetricsData(
                service_id=service_id,
                timestamp=timestamp,
                time_window=time_window,
                metrics=metrics_dict,
                regional_breakdown=regional_data,
                data_quality=data_quality
            )

            # Store metrics
            self._store_metrics(metrics_data)

            # Return success response
            return {
                "status": "ingested",
                "service_id": service_id,
                "timestamp": timestamp.isoformat(),
                "data_quality": {
                    "completeness": data_quality.completeness,
                    "staleness_hours": data_quality.staleness_hours,
                    "outlier_count": data_quality.outlier_count,
                    "quality_score": data_quality.quality_score
                },
                "validation_results": {
                    "warnings": warnings,
                    "errors": []
                }
            }

        except ValueError as e:
            # Validation error
            return {
                "status": "rejected",
                "service_id": service_id,
                "timestamp": timestamp.isoformat(),
                "validation_results": {
                    "warnings": [],
                    "errors": [str(e)]
                }
            }
    
    def _compute_data_quality(
        self,
        service_id: str,
        latency: LatencyMetrics,
        error_rate: ErrorRateMetrics,
        availability: AvailabilityMetrics,
        request_volume: Optional[RequestVolumeMetrics],
        current_timestamp: datetime
    ) -> DataQuality:
        """
        Compute data quality indicators.
        
        Computes:
        - Completeness score (0-1): ratio of available data points to expected
        - Staleness indicator: hours since last data point
        - Outlier count: number of data points beyond 3 standard deviations
        - Overall quality score (0-1): weighted combination of factors
        
        Args:
            service_id: Service identifier
            latency: Latency metrics
            error_rate: Error rate metrics
            availability: Availability metrics
            request_volume: Optional request volume metrics
            current_timestamp: Current timestamp for staleness calculation
        
        Returns:
            DataQuality object with completeness, staleness, outlier count, and quality score
        """
        # Compute completeness (all required fields present)
        required_fields = 3  # latency, error_rate, availability
        provided_fields = 3
        if request_volume:
            required_fields = 4
            provided_fields = 4
        
        completeness = provided_fields / required_fields
        
        # Compute staleness (hours since last metric update)
        staleness_hours = 0.0
        latest_metrics = self.get_latest_metrics(service_id)
        if latest_metrics:
            time_diff = current_timestamp - latest_metrics.timestamp
            staleness_hours = max(0.0, time_diff.total_seconds() / 3600)
        
        # Detect outliers by comparing current metrics against historical data
        outlier_count, outlier_details = self._detect_outliers(
            service_id=service_id,
            current_latency=latency,
            current_error_rate=error_rate,
            current_availability=availability
        )
        
        # Compute quality score using weighted combination of factors
        # Formula: quality_score = w1*completeness + w2*staleness_factor + w3*outlier_factor
        # Weights: completeness (0.4), staleness (0.3), outliers (0.3)
        
        # Completeness component (0-0.4)
        completeness_component = completeness * 0.4
        
        # Staleness component (0-0.3)
        # Fresh data (< 1 hour): full score (0.3)
        # Moderate staleness (1-24 hours): reduced score
        # High staleness (> 24 hours): minimal score
        if staleness_hours <= 1:
            staleness_component = 0.3
        elif staleness_hours <= 24:
            staleness_component = 0.3 * (1 - (staleness_hours - 1) / 23 * 0.5)
        elif staleness_hours <= 72:
            staleness_component = 0.15 * (1 - (staleness_hours - 24) / 48)
        else:
            staleness_component = 0.05
        
        # Outlier component (0-0.3)
        # No outliers: full score (0.3)
        # 1-2 outliers: reduced score
        # 3+ outliers: minimal score
        if outlier_count == 0:
            outlier_component = 0.3
        elif outlier_count <= 2:
            outlier_component = 0.3 * (1 - outlier_count * 0.2)
        else:
            outlier_component = 0.3 * 0.5 * (1 / outlier_count)
        
        # Combine components
        quality_score = completeness_component + staleness_component + outlier_component
        
        # Additional penalties for severe issues
        # Reduce quality if error rate is very high (>10%)
        if error_rate.percent > 10:
            quality_score *= 0.9
        
        # Reduce quality if availability is very low (<90%)
        if availability.percent < 90:
            quality_score *= 0.9
        
        # Ensure quality score is within valid range [0, 1]
        quality_score = max(0.0, min(1.0, quality_score))
        
        return DataQuality(
            completeness=round(completeness, 2),
            staleness_hours=round(staleness_hours, 2),
            outlier_count=outlier_count,
            quality_score=round(quality_score, 2),
            outliers=outlier_details if outlier_details else None
        )
    
    def _detect_outliers(
        self,
        service_id: str,
        current_latency: LatencyMetrics,
        current_error_rate: ErrorRateMetrics,
        current_availability: AvailabilityMetrics
    ) -> Tuple[int, List]:
        """
        Detect outliers by comparing current metrics against historical data.

        An outlier is defined as a data point that is more than 3 standard deviations
        away from the mean of historical data.

        Args:
            service_id: Service identifier
            current_latency: Current latency metrics
            current_error_rate: Current error rate metrics
            current_availability: Current availability metrics

        Returns:
            Tuple of (outlier_count, list of OutlierInfo objects)
        """
        from src.models.metrics import OutlierInfo

        outlier_count = 0
        outlier_details = []

        # Get historical metrics for comparison (all available metrics)
        try:
            historical_metrics = self.get_metrics(
                service_id=service_id
            )
        except Exception:
            # If no historical data available, cannot detect outliers
            return 0, []

        if not historical_metrics or len(historical_metrics) < 3:
            # Need at least 3 data points to compute meaningful statistics
            return 0, []

        # Extract historical values for each metric
        historical_latency_p95 = []
        historical_latency_p99 = []
        historical_error_rate = []
        historical_availability = []

        for m in historical_metrics:
            if "latency" in m.metrics:
                latency = m.metrics["latency"]
                historical_latency_p95.append(latency.p95_ms)
                historical_latency_p99.append(latency.p99_ms)
            if "error_rate" in m.metrics:
                error_rate = m.metrics["error_rate"]
                historical_error_rate.append(error_rate.percent)
            if "availability" in m.metrics:
                availability = m.metrics["availability"]
                historical_availability.append(availability.percent)

        # Check latency p95 for outliers
        if len(historical_latency_p95) >= 3:
            mean_p95 = statistics.mean(historical_latency_p95)
            stddev_p95 = statistics.stdev(historical_latency_p95)
            if stddev_p95 > 0:
                z_score = abs(current_latency.p95_ms - mean_p95) / stddev_p95
                if z_score > 3:
                    outlier_count += 1
                    outlier_details.append(OutlierInfo(
                        metric_name="latency_p95_ms",
                        value=current_latency.p95_ms,
                        z_score=z_score,
                        mean=mean_p95,
                        stddev=stddev_p95
                    ))

        # Check latency p99 for outliers
        if len(historical_latency_p99) >= 3:
            mean_p99 = statistics.mean(historical_latency_p99)
            stddev_p99 = statistics.stdev(historical_latency_p99)
            if stddev_p99 > 0:
                z_score = abs(current_latency.p99_ms - mean_p99) / stddev_p99
                if z_score > 3:
                    outlier_count += 1
                    outlier_details.append(OutlierInfo(
                        metric_name="latency_p99_ms",
                        value=current_latency.p99_ms,
                        z_score=z_score,
                        mean=mean_p99,
                        stddev=stddev_p99
                    ))

        # Check error rate for outliers
        if len(historical_error_rate) >= 3:
            mean_error = statistics.mean(historical_error_rate)
            stddev_error = statistics.stdev(historical_error_rate)
            if stddev_error > 0:
                z_score = abs(current_error_rate.percent - mean_error) / stddev_error
                if z_score > 3:
                    outlier_count += 1
                    outlier_details.append(OutlierInfo(
                        metric_name="error_rate_percent",
                        value=current_error_rate.percent,
                        z_score=z_score,
                        mean=mean_error,
                        stddev=stddev_error
                    ))

        # Check availability for outliers
        if len(historical_availability) >= 3:
            mean_avail = statistics.mean(historical_availability)
            stddev_avail = statistics.stdev(historical_availability)
            if stddev_avail > 0:
                z_score = abs(current_availability.percent - mean_avail) / stddev_avail
                if z_score > 3:
                    outlier_count += 1
                    outlier_details.append(OutlierInfo(
                        metric_name="availability_percent",
                        value=current_availability.percent,
                        z_score=z_score,
                        mean=mean_avail,
                        stddev=stddev_avail
                    ))

        return outlier_count, outlier_details
    
    def _store_metrics(self, metrics_data: MetricsData):
        """
        Store metrics to file system.
        
        Args:
            metrics_data: MetricsData object to store
        """
        # Store raw metrics with timestamp (including microseconds for uniqueness)
        timestamp_str = metrics_data.timestamp.strftime("%Y%m%d_%H%M%S_%f")
        metrics_path = f"services/{metrics_data.service_id}/metrics/{timestamp_str}.json"
        
        # Convert to dict for storage
        metrics_dict = metrics_data.dict()
        
        # Convert datetime objects to ISO format strings
        metrics_dict["timestamp"] = metrics_data.timestamp.isoformat()
        
        # Store metrics
        self.storage.write_json(metrics_path, metrics_dict)
        
        # Update latest metrics pointer
        latest_path = f"services/{metrics_data.service_id}/metrics/latest.json"
        self.storage.write_json(latest_path, metrics_dict)
    
    def get_metrics(
        self,
        service_id: str,
        time_window: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[MetricsData]:
        """
        Retrieve stored metrics for a service.
        
        Args:
            service_id: Service identifier
            time_window: Optional filter by time window
            limit: Optional limit on number of results
        
        Returns:
            List of MetricsData objects
        """
        metrics_dir = self.storage.base_path / "services" / service_id / "metrics"
        
        if not metrics_dir.exists():
            return []
        
        metrics_list = []
        
        # Read all metric files (excluding latest.json and lock files)
        for metrics_file in sorted(metrics_dir.glob("*.json"), reverse=True):
            if metrics_file.name in ["latest.json"] or metrics_file.suffix == ".lock":
                continue
            
            metrics_dict = self.storage.read_json(
                f"services/{service_id}/metrics/{metrics_file.name}"
            )
            
            if not metrics_dict:
                continue
            
            # Filter by time window if specified
            if time_window and metrics_dict.get("time_window") != time_window:
                continue
            
            # Convert ISO strings back to datetime (Python 3.6 compatible)
            if "timestamp" in metrics_dict:
                from dateutil.parser import parse
                metrics_dict["timestamp"] = parse(metrics_dict["timestamp"])
            
            metrics_list.append(MetricsData(**metrics_dict))
            
            # Apply limit if specified
            if limit and len(metrics_list) >= limit:
                break
        
        return metrics_list
    
    def get_latest_metrics(self, service_id: str) -> Optional[MetricsData]:
        """
        Get the most recent metrics for a service.
        
        Args:
            service_id: Service identifier
        
        Returns:
            MetricsData object or None if no metrics exist
        """
        latest_path = f"services/{service_id}/metrics/latest.json"
        metrics_dict = self.storage.read_json(latest_path)
        
        if not metrics_dict:
            return None
        
        # Convert ISO strings back to datetime (Python 3.6 compatible)
        if "timestamp" in metrics_dict:
            from dateutil.parser import parse
            metrics_dict["timestamp"] = parse(metrics_dict["timestamp"])
        
        return MetricsData(**metrics_dict)

    def _validate_error_rate_consistency(
        self,
        error_rate: ErrorRateMetrics,
        tolerance: float = 1.0
    ) -> List[str]:
        """
        Validate error rate calculation consistency.

        Args:
            error_rate: ErrorRateMetrics object
            tolerance: Tolerance percentage for comparison (default 1%)

        Returns:
            List of warning messages (empty if consistent)
        """
        warnings = []

        # Avoid division by zero
        if error_rate.total_requests == 0:
            if error_rate.failed_requests > 0:
                warnings.append(
                    "Error rate has failed_requests > 0 but total_requests = 0"
                )
            if error_rate.percent > 0:
                warnings.append(
                    "Error rate percent > 0 but total_requests = 0"
                )
            return warnings

        # Calculate expected error rate
        calculated_percent = (error_rate.failed_requests / error_rate.total_requests) * 100

        # Check if provided percent matches calculated percent within tolerance
        diff = abs(calculated_percent - error_rate.percent)
        if diff > tolerance:
            warnings.append(
                f"Error rate inconsistency: provided percent={error_rate.percent:.2f}%, "
                f"but calculated from failed_requests/total_requests={calculated_percent:.2f}% "
                f"(difference: {diff:.2f}%)"
            )

        return warnings

    def _validate_availability_consistency(
        self,
        availability: AvailabilityMetrics,
        tolerance: float = 1.0
    ) -> List[str]:
        """
        Validate availability calculation consistency.

        Args:
            availability: AvailabilityMetrics object
            tolerance: Tolerance percentage for comparison (default 1%)

        Returns:
            List of warning messages (empty if consistent)
        """
        warnings = []

        total_time = availability.uptime_seconds + availability.downtime_seconds

        # Check for suspicious values
        if total_time == 0:
            if availability.percent > 0:
                warnings.append(
                    "Availability percent > 0 but both uptime_seconds and downtime_seconds = 0"
                )
            return warnings

        # Calculate expected availability
        calculated_percent = (availability.uptime_seconds / total_time) * 100

        # Check if provided percent matches calculated percent within tolerance
        diff = abs(calculated_percent - availability.percent)
        if diff > tolerance:
            warnings.append(
                f"Availability inconsistency: provided percent={availability.percent:.2f}%, "
                f"but calculated from uptime_seconds/(uptime_seconds+downtime_seconds)={calculated_percent:.2f}% "
                f"(difference: {diff:.2f}%)"
            )

        # Warn about suspicious combinations
        if availability.percent == 100.0 and availability.downtime_seconds > 0:
            warnings.append(
                f"Suspicious: availability is 100% but downtime_seconds={availability.downtime_seconds}"
            )

        return warnings

    def _validate_metrics_quality(
        self,
        error_rate: ErrorRateMetrics,
        availability: AvailabilityMetrics
    ) -> List[str]:
        """
        Validate metrics quality and generate warnings for suspicious values.

        Args:
            error_rate: ErrorRateMetrics object
            availability: AvailabilityMetrics object

        Returns:
            List of warning messages
        """
        warnings = []

        # Warn about very high error rates
        if error_rate.percent > 10:
            warnings.append(
                f"High error rate detected: {error_rate.percent:.2f}% (>10%)"
            )

        # Warn about very low availability
        if availability.percent < 90:
            warnings.append(
                f"Low availability detected: {availability.percent:.2f}% (<90%)"
            )

        return warnings

    def compute_aggregated_metrics(
        self,
        service_id: str,
        time_windows: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compute aggregated statistics across multiple time windows.

        This method retrieves all raw metrics for a service and computes
        aggregated statistics (mean, median, stddev, percentiles) for each
        time window (1d, 7d, 30d, 90d).

        Args:
            service_id: Service identifier
            time_windows: Optional list of time windows to compute (defaults to all)

        Returns:
            Dict with aggregated metrics for each time window

        Raises:
            ValueError: If service has no metrics data or invalid time window
        """
        # Default to all time windows
        if time_windows is None:
            time_windows = ["1d", "7d", "30d", "90d"]

        # Validate time windows
        valid_windows = ["1d", "7d", "30d", "90d"]
        for window in time_windows:
            if window not in valid_windows:
                raise ValueError(f"Invalid time_window: {window}. Must be one of: {valid_windows}")

        # Get current time
        now = datetime.utcnow()

        # Retrieve all raw metrics for the service
        all_metrics = self.get_metrics(service_id)

        if not all_metrics:
            raise ValueError(f"No metrics found for service: {service_id}")

        # Compute aggregated metrics for each time window
        aggregated_windows = {}

        for window in time_windows:
            # Determine time window boundaries
            window_days = self._parse_time_window(window)
            start_time = now - timedelta(days=window_days)
            end_time = now

            # Filter metrics within this time window
            window_metrics = [
                m for m in all_metrics
                if start_time <= m.timestamp <= end_time
            ]

            if not window_metrics:
                # No data for this window - create empty stats with low quality
                aggregated_windows[window] = self._create_empty_window_stats(
                    window, start_time, end_time
                )
                continue

            # Compute aggregated statistics (raw - all data)
            latency_stats = self._aggregate_latency_stats(window_metrics)
            error_rate_stats = self._aggregate_error_rate_stats(window_metrics)
            availability_stats = self._aggregate_availability_stats(window_metrics)

            # Identify outliers in the window
            outlier_indices = self._identify_outlier_indices(window_metrics)

            # Compute adjusted statistics (excluding outliers)
            latency_stats_adjusted = None
            error_rate_stats_adjusted = None
            availability_stats_adjusted = None
            
            if outlier_indices:
                # Filter out outliers
                non_outlier_metrics = [
                    m for i, m in enumerate(window_metrics) 
                    if i not in outlier_indices
                ]
                
                if non_outlier_metrics:
                    latency_stats_adjusted = self._aggregate_latency_stats(non_outlier_metrics)
                    error_rate_stats_adjusted = self._aggregate_error_rate_stats(non_outlier_metrics)
                    availability_stats_adjusted = self._aggregate_availability_stats(non_outlier_metrics)

            # Compute data quality for this window
            data_quality = self._compute_window_quality(
                window, window_metrics, start_time, end_time
            )

            # Create TimeWindowAggregatedMetrics
            aggregated_windows[window] = TimeWindowAggregatedMetrics(
                time_window=window,
                start_time=start_time,
                end_time=end_time,
                latency=latency_stats,
                error_rate=error_rate_stats,
                availability=availability_stats,
                latency_adjusted=latency_stats_adjusted,
                error_rate_adjusted=error_rate_stats_adjusted,
                availability_adjusted=availability_stats_adjusted,
                outlier_indices=outlier_indices if outlier_indices else None,
                data_quality=data_quality
            )

        # Create AggregatedMetrics object
        aggregated_metrics = AggregatedMetrics(
            service_id=service_id,
            computed_at=now,
            time_windows=aggregated_windows
        )

        # Store aggregated metrics
        self._store_aggregated_metrics(aggregated_metrics)

        # Return as dict
        return aggregated_metrics.dict()
    def compute_regional_aggregated_metrics(
        self,
        service_id: str,
        time_windows: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compute per-region aggregated statistics across multiple time windows.

        This method retrieves all raw metrics for a service and computes
        aggregated statistics (mean, median, percentiles) for each region
        separately for each time window (1d, 7d, 30d, 90d).

        Args:
            service_id: Service identifier
            time_windows: Optional list of time windows to compute (defaults to all)

        Returns:
            Dict with per-region aggregated metrics for each time window

        Raises:
            ValueError: If service has no metrics data or invalid time window
        """
        # Default to all time windows
        if time_windows is None:
            time_windows = ["1d", "7d", "30d", "90d"]

        # Validate time windows
        valid_windows = ["1d", "7d", "30d", "90d"]
        for window in time_windows:
            if window not in valid_windows:
                raise ValueError(f"Invalid time_window: {window}. Must be one of: {valid_windows}")

        # Get current time
        now = datetime.utcnow()

        # Retrieve all raw metrics for the service
        all_metrics = self.get_metrics(service_id)

        if not all_metrics:
            raise ValueError(f"No metrics found for service: {service_id}")

        # Check if any metrics have regional data
        has_regional_data = any(m.regional_breakdown for m in all_metrics)
        if not has_regional_data:
            return {
                "service_id": service_id,
                "computed_at": now.isoformat(),
                "has_regional_data": False,
                "regions": {},
                "message": "No regional data available for this service"
            }

        # Collect all unique regions across all metrics
        all_regions = set()
        for m in all_metrics:
            if m.regional_breakdown:
                all_regions.update(m.regional_breakdown.keys())

        # Compute aggregated metrics for each region and time window
        regional_aggregated = {}

        for region in sorted(all_regions):
            regional_aggregated[region] = {}

            for window in time_windows:
                # Determine time window boundaries
                window_days = self._parse_time_window(window)
                start_time = now - timedelta(days=window_days)
                end_time = now

                # Filter metrics within this time window that have data for this region
                window_metrics_for_region = []
                for m in all_metrics:
                    if start_time <= m.timestamp <= end_time:
                        if m.regional_breakdown and region in m.regional_breakdown:
                            window_metrics_for_region.append(m)

                if not window_metrics_for_region:
                    # No data for this region in this window
                    regional_aggregated[region][window] = {
                        "time_window": window,
                        "start_time": start_time.isoformat(),
                        "end_time": end_time.isoformat(),
                        "sample_count": 0,
                        "data_available": False,
                        "latency_p95_ms": None,
                        "availability": None
                    }
                    continue

                # Extract regional metric values for this region
                latency_p95_values = []
                availability_values = []

                for m in window_metrics_for_region:
                    regional_metrics = m.regional_breakdown[region]
                    latency_p95_values.append(regional_metrics.latency_p95_ms)
                    availability_values.append(regional_metrics.availability)

                # Compute statistics for latency_p95_ms
                latency_stats = {
                    "mean": round(statistics.mean(latency_p95_values), 2),
                    "median": round(statistics.median(latency_p95_values), 2),
                    "stddev": round(statistics.stdev(latency_p95_values) if len(latency_p95_values) > 1 else 0, 2),
                    "p50": round(self._percentile(latency_p95_values, 50), 2),
                    "p95": round(self._percentile(latency_p95_values, 95), 2),
                    "p99": round(self._percentile(latency_p95_values, 99), 2),
                    "min": round(min(latency_p95_values), 2),
                    "max": round(max(latency_p95_values), 2)
                }

                # Compute statistics for availability
                availability_stats = {
                    "mean": round(statistics.mean(availability_values), 2),
                    "median": round(statistics.median(availability_values), 2),
                    "stddev": round(statistics.stdev(availability_values) if len(availability_values) > 1 else 0, 2),
                    "p50": round(self._percentile(availability_values, 50), 2),
                    "p95": round(self._percentile(availability_values, 95), 2),
                    "p99": round(self._percentile(availability_values, 99), 2),
                    "min": round(min(availability_values), 2),
                    "max": round(max(availability_values), 2)
                }

                # Store aggregated stats for this region and window
                regional_aggregated[region][window] = {
                    "time_window": window,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "sample_count": len(window_metrics_for_region),
                    "data_available": True,
                    "latency_p95_ms": latency_stats,
                    "availability": availability_stats
                }

        # Build result
        result = {
            "service_id": service_id,
            "computed_at": now.isoformat(),
            "has_regional_data": True,
            "regions": regional_aggregated
        }

        # Store regional aggregated metrics
        self._store_regional_aggregated_metrics(service_id, result)

        return result

    def _store_regional_aggregated_metrics(self, service_id: str, regional_data: Dict[str, Any]):
        """
        Store regional aggregated metrics to file system.

        Args:
            service_id: Service identifier
            regional_data: Regional aggregated metrics data
        """
        # Store to regional_metrics_aggregated.json
        regional_path = f"services/{service_id}/regional_metrics_aggregated.json"
        self.storage.write_json(regional_path, regional_data)

    def get_regional_aggregated_metrics(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve regional aggregated metrics for a service.

        Args:
            service_id: Service identifier

        Returns:
            Dict with regional aggregated metrics or None if not found
        """
        regional_path = f"services/{service_id}/regional_metrics_aggregated.json"
        return self.storage.read_json(regional_path)

    def compute_global_aggregated_metrics(
        self,
        service_id: str,
        time_windows: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Compute global aggregated statistics across all regions.

        This method takes per-region statistics and aggregates them into
        global statistics. It computes weighted averages when possible,
        or simple averages when weights are not available.

        Args:
            service_id: Service identifier
            time_windows: Optional list of time windows to compute (defaults to all)

        Returns:
            Dict with global aggregated metrics for each time window

        Raises:
            ValueError: If service has no regional metrics data
        """
        # Default to all time windows
        if time_windows is None:
            time_windows = ["1d", "7d", "30d", "90d"]

        # Validate time windows
        valid_windows = ["1d", "7d", "30d", "90d"]
        for window in time_windows:
            if window not in valid_windows:
                raise ValueError(f"Invalid time_window: {window}. Must be one of: {valid_windows}")

        # Get current time
        now = datetime.utcnow()

        # Retrieve all raw metrics for the service
        all_metrics = self.get_metrics(service_id)

        if not all_metrics:
            raise ValueError(f"No metrics found for service: {service_id}")

        # Check if any metrics have regional data
        has_regional_data = any(m.regional_breakdown for m in all_metrics)
        if not has_regional_data:
            return {
                "service_id": service_id,
                "computed_at": now.isoformat(),
                "has_regional_data": False,
                "global_stats": {},
                "message": "No regional data available for this service"
            }

        # Compute global aggregated metrics for each time window
        global_aggregated = {}

        for window in time_windows:
            # Determine time window boundaries
            window_days = self._parse_time_window(window)
            start_time = now - timedelta(days=window_days)
            end_time = now

            # Filter metrics within this time window that have regional data
            window_metrics = [
                m for m in all_metrics
                if start_time <= m.timestamp <= end_time and m.regional_breakdown
            ]

            if not window_metrics:
                # No regional data for this window
                global_aggregated[window] = {
                    "time_window": window,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "sample_count": 0,
                    "data_available": False,
                    "latency_p95_ms": None,
                    "availability": None
                }
                continue

            # Aggregate across all regions for each metric point
            # For each timestamp, compute the average across all regions
            aggregated_latency_values = []
            aggregated_availability_values = []

            for m in window_metrics:
                # Get all regional values for this timestamp
                regional_latencies = [
                    regional_metrics.latency_p95_ms
                    for regional_metrics in m.regional_breakdown.values()
                ]
                regional_availabilities = [
                    regional_metrics.availability
                    for regional_metrics in m.regional_breakdown.values()
                ]

                # Compute average across regions for this timestamp
                # (simple average - could be weighted by traffic in future)
                avg_latency = statistics.mean(regional_latencies)
                avg_availability = statistics.mean(regional_availabilities)

                aggregated_latency_values.append(avg_latency)
                aggregated_availability_values.append(avg_availability)

            # Compute statistics for the aggregated values
            latency_stats = {
                "mean": round(statistics.mean(aggregated_latency_values), 2),
                "median": round(statistics.median(aggregated_latency_values), 2),
                "stddev": round(
                    statistics.stdev(aggregated_latency_values) if len(aggregated_latency_values) > 1 else 0,
                    2
                ),
                "p50": round(self._percentile(aggregated_latency_values, 50), 2),
                "p95": round(self._percentile(aggregated_latency_values, 95), 2),
                "p99": round(self._percentile(aggregated_latency_values, 99), 2),
                "min": round(min(aggregated_latency_values), 2),
                "max": round(max(aggregated_latency_values), 2)
            }

            availability_stats = {
                "mean": round(statistics.mean(aggregated_availability_values), 2),
                "median": round(statistics.median(aggregated_availability_values), 2),
                "stddev": round(
                    statistics.stdev(aggregated_availability_values) if len(aggregated_availability_values) > 1 else 0,
                    2
                ),
                "p50": round(self._percentile(aggregated_availability_values, 50), 2),
                "p95": round(self._percentile(aggregated_availability_values, 95), 2),
                "p99": round(self._percentile(aggregated_availability_values, 99), 2),
                "min": round(min(aggregated_availability_values), 2),
                "max": round(max(aggregated_availability_values), 2)
            }

            # Store aggregated stats for this window
            global_aggregated[window] = {
                "time_window": window,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "sample_count": len(window_metrics),
                "data_available": True,
                "latency_p95_ms": latency_stats,
                "availability": availability_stats
            }

        # Build result
        result = {
            "service_id": service_id,
            "computed_at": now.isoformat(),
            "has_regional_data": True,
            "global_stats": global_aggregated
        }

        # Store global aggregated metrics
        self._store_global_aggregated_metrics(service_id, result)

        return result

    def _store_global_aggregated_metrics(self, service_id: str, global_data: Dict[str, Any]):
        """
        Store global aggregated metrics to file system.

        Args:
            service_id: Service identifier
            global_data: Global aggregated metrics data
        """
        # Store to global_metrics_aggregated.json
        global_path = f"services/{service_id}/global_metrics_aggregated.json"
        self.storage.write_json(global_path, global_data)

    def get_global_aggregated_metrics(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve global aggregated metrics for a service.

        Args:
            service_id: Service identifier

        Returns:
            Dict with global aggregated metrics or None if not found
        """
        global_path = f"services/{service_id}/global_metrics_aggregated.json"
        return self.storage.read_json(global_path)

    
    def _parse_time_window(self, window: str) -> int:
        """
        Parse time window string to number of days.

        Args:
            window: Time window string (e.g., "1d", "7d", "30d", "90d")

        Returns:
            Number of days
        """
        window_map = {
            "1d": 1,
            "7d": 7,
            "30d": 30,
            "90d": 90
        }
        return window_map[window]
    
    def _aggregate_latency_stats(self, metrics_list: List[MetricsData]) -> AggregatedLatencyStats:
        """
        Aggregate latency statistics from multiple metrics.

        Args:
            metrics_list: List of MetricsData objects

        Returns:
            AggregatedLatencyStats object
        """
        # Extract latency values
        p50_values = []
        p95_values = []
        p99_values = []
        mean_values = []

        for metrics in metrics_list:
            latency = metrics.metrics.get("latency")
            if latency:
                p50_values.append(latency.p50_ms)
                p95_values.append(latency.p95_ms)
                p99_values.append(latency.p99_ms)
                mean_values.append(latency.mean_ms)

        # Compute statistics
        return AggregatedLatencyStats(
            mean_ms=round(statistics.mean(mean_values), 2),
            median_ms=round(statistics.median(p50_values), 2),
            stddev_ms=round(statistics.stdev(mean_values) if len(mean_values) > 1 else 0, 2),
            p50_ms=round(self._percentile(p50_values, 50), 2),
            p95_ms=round(self._percentile(p95_values, 95), 2),
            p99_ms=round(self._percentile(p99_values, 99), 2),
            min_ms=round(min(p50_values), 2),
            max_ms=round(max(p99_values), 2),
            sample_count=len(metrics_list)
        )
    
    def _aggregate_error_rate_stats(self, metrics_list: List[MetricsData]) -> AggregatedErrorRateStats:
        """
        Aggregate error rate statistics from multiple metrics.

        Args:
            metrics_list: List of MetricsData objects

        Returns:
            AggregatedErrorRateStats object
        """
        # Extract error rate values
        error_rate_values = []
        total_requests = 0
        total_failed = 0

        for metrics in metrics_list:
            error_rate = metrics.metrics.get("error_rate")
            if error_rate:
                error_rate_values.append(error_rate.percent)
                total_requests += error_rate.total_requests
                total_failed += error_rate.failed_requests

        # Compute statistics
        return AggregatedErrorRateStats(
            mean_percent=round(statistics.mean(error_rate_values), 2),
            median_percent=round(statistics.median(error_rate_values), 2),
            stddev_percent=round(statistics.stdev(error_rate_values) if len(error_rate_values) > 1 else 0, 2),
            p50_percent=round(self._percentile(error_rate_values, 50), 2),
            p95_percent=round(self._percentile(error_rate_values, 95), 2),
            p99_percent=round(self._percentile(error_rate_values, 99), 2),
            min_percent=round(min(error_rate_values), 2),
            max_percent=round(max(error_rate_values), 2),
            total_requests=total_requests,
            total_failed_requests=total_failed,
            sample_count=len(metrics_list)
        )
    
    def _aggregate_availability_stats(self, metrics_list: List[MetricsData]) -> AggregatedAvailabilityStats:
        """
        Aggregate availability statistics from multiple metrics.

        Args:
            metrics_list: List of MetricsData objects

        Returns:
            AggregatedAvailabilityStats object
        """
        # Extract availability values
        availability_values = []
        total_uptime = 0
        total_downtime = 0

        for metrics in metrics_list:
            availability = metrics.metrics.get("availability")
            if availability:
                availability_values.append(availability.percent)
                total_uptime += availability.uptime_seconds
                total_downtime += availability.downtime_seconds

        # Compute statistics
        return AggregatedAvailabilityStats(
            mean_percent=round(statistics.mean(availability_values), 2),
            median_percent=round(statistics.median(availability_values), 2),
            stddev_percent=round(statistics.stdev(availability_values) if len(availability_values) > 1 else 0, 2),
            p50_percent=round(self._percentile(availability_values, 50), 2),
            p95_percent=round(self._percentile(availability_values, 95), 2),
            p99_percent=round(self._percentile(availability_values, 99), 2),
            min_percent=round(min(availability_values), 2),
            max_percent=round(max(availability_values), 2),
            total_uptime_seconds=total_uptime,
            total_downtime_seconds=total_downtime,
            sample_count=len(metrics_list)
        )
    
    def _percentile(self, values: List[float], percentile: float) -> float:
        """
        Compute percentile of a list of values.

        Args:
            values: List of numeric values
            percentile: Percentile to compute (0-100)

        Returns:
            Percentile value
        """
        if not values:
            return 0.0

        sorted_values = sorted(values)
        index = (percentile / 100) * (len(sorted_values) - 1)

        if index.is_integer():
            return sorted_values[int(index)]
        else:
            lower = sorted_values[int(index)]
            upper = sorted_values[int(index) + 1]
            fraction = index - int(index)
            return lower + (upper - lower) * fraction
    
    def _compute_window_quality(
        self,
        window: str,
        metrics_list: List[MetricsData],
        start_time: datetime,
        end_time: datetime
    ) -> TimeWindowQuality:
        """
        Compute data quality indicators for a time window.
        
        Computes:
        - Completeness: ratio of actual samples to expected samples
        - Staleness: hours since last data point
        - Outlier count: number of data points beyond 3 standard deviations
        - Quality score: weighted combination of factors

        Args:
            window: Time window string
            metrics_list: List of MetricsData objects in this window
            start_time: Start of time window
            end_time: End of time window

        Returns:
            TimeWindowQuality object
        """
        # Determine expected number of samples
        # Assume we expect one sample per day for POC
        window_days = self._parse_time_window(window)
        expected_samples = window_days
        actual_samples = len(metrics_list)

        # Compute completeness
        completeness = min(actual_samples / expected_samples, 1.0) if expected_samples > 0 else 0.0

        # Compute staleness (hours since last data point)
        if metrics_list:
            latest_timestamp = max(m.timestamp for m in metrics_list)
            staleness_hours = (end_time - latest_timestamp).total_seconds() / 3600
        else:
            staleness_hours = (end_time - start_time).total_seconds() / 3600

        # Detect outliers in the time window
        outlier_count = self._detect_window_outliers(metrics_list)

        # Compute quality score using weighted combination
        # Weights: completeness (0.4), staleness (0.3), outliers (0.3)
        
        # Completeness component (0-0.4)
        completeness_component = completeness * 0.4
        
        # Staleness component (0-0.3)
        if staleness_hours <= 1:
            staleness_component = 0.3
        elif staleness_hours <= 24:
            staleness_component = 0.3 * (1 - (staleness_hours - 1) / 23 * 0.5)
        elif staleness_hours <= 72:
            staleness_component = 0.15 * (1 - (staleness_hours - 24) / 48)
        else:
            staleness_component = 0.05
        
        # Outlier component (0-0.3)
        if outlier_count == 0:
            outlier_component = 0.3
        elif outlier_count <= 2:
            outlier_component = 0.3 * (1 - outlier_count * 0.2)
        else:
            outlier_component = 0.3 * 0.5 * (1 / outlier_count)
        
        # Combine components
        quality_score = completeness_component + staleness_component + outlier_component
        
        # Ensure quality score is within valid range [0, 1]
        quality_score = max(0.0, min(1.0, quality_score))

        return TimeWindowQuality(
            completeness=round(completeness, 2),
            staleness_hours=round(staleness_hours, 2),
            expected_samples=expected_samples,
            actual_samples=actual_samples,
            quality_score=round(quality_score, 2)
        )
    
    def _detect_window_outliers(self, metrics_list: List[MetricsData]) -> int:
        """
        Detect outliers within a time window of metrics.
        
        An outlier is defined as a data point that is more than 3 standard deviations
        away from the mean of the metrics in the window.
        
        Args:
            metrics_list: List of MetricsData objects in the window
        
        Returns:
            Number of outliers detected across all metrics
        """
        outlier_indices = self._identify_outlier_indices(metrics_list)
        return len(outlier_indices) if outlier_indices else 0
    
    def _identify_outlier_indices(self, metrics_list: List[MetricsData]) -> List[int]:
        """
        Identify indices of metrics that are outliers within a time window.
        
        A metric is considered an outlier if any of its values (latency p95, p99,
        error rate, or availability) is more than 3 standard deviations away from
        the mean of that metric across the window.
        
        Args:
            metrics_list: List of MetricsData objects in the window
        
        Returns:
            List of indices of metrics that are outliers
        """
        if len(metrics_list) < 3:
            # Need at least 3 data points to compute meaningful statistics
            return []
        
        outlier_indices_set = set()
        
        # Extract metric values from the list
        latency_p95_values = []
        latency_p99_values = []
        error_rate_values = []
        availability_values = []
        
        for m in metrics_list:
            latency = m.metrics.get("latency")
            if latency:
                # Handle both dict and Pydantic model
                if isinstance(latency, dict):
                    latency_p95_values.append(latency.get("p95_ms", 0))
                    latency_p99_values.append(latency.get("p99_ms", 0))
                else:
                    latency_p95_values.append(latency.p95_ms)
                    latency_p99_values.append(latency.p99_ms)
            else:
                latency_p95_values.append(0)
                latency_p99_values.append(0)
                
            error_rate = m.metrics.get("error_rate")
            if error_rate:
                # Handle both dict and Pydantic model
                if isinstance(error_rate, dict):
                    error_rate_values.append(error_rate.get("percent", 0))
                else:
                    error_rate_values.append(error_rate.percent)
            else:
                error_rate_values.append(0)
                
            availability = m.metrics.get("availability")
            if availability:
                # Handle both dict and Pydantic model
                if isinstance(availability, dict):
                    availability_values.append(availability.get("percent", 0))
                else:
                    availability_values.append(availability.percent)
            else:
                availability_values.append(0)
        
        # Check each metric series for outliers and collect indices
        outlier_indices_set.update(self._find_outlier_indices_in_series(latency_p95_values))
        outlier_indices_set.update(self._find_outlier_indices_in_series(latency_p99_values))
        outlier_indices_set.update(self._find_outlier_indices_in_series(error_rate_values))
        outlier_indices_set.update(self._find_outlier_indices_in_series(availability_values))
        
        return sorted(list(outlier_indices_set))
    
    def _find_outlier_indices_in_series(self, values: List[float]) -> List[int]:
        """
        Find indices of outliers in a series of values using 3-sigma rule.
        
        Args:
            values: List of numeric values
        
        Returns:
            List of indices where values are beyond 3 standard deviations from mean
        """
        if len(values) < 3:
            return []
        
        try:
            mean = statistics.mean(values)
            stddev = statistics.stdev(values)
            
            if stddev == 0:
                # No variation, no outliers
                return []
            
            # Find indices of values beyond 3 standard deviations
            outlier_indices = []
            for i, value in enumerate(values):
                z_score = abs(value - mean) / stddev
                if z_score > 3:
                    outlier_indices.append(i)
            
            return outlier_indices
        except Exception:
            # If any error occurs, return empty list
            return []
    
    def _count_outliers_in_series(self, values: List[float]) -> int:
        """
        Count outliers in a series of values using 3-sigma rule.
        
        Args:
            values: List of numeric values
        
        Returns:
            Number of outliers (values beyond 3 standard deviations from mean)
        """
        if len(values) < 3:
            return 0
        
        try:
            mean = statistics.mean(values)
            stddev = statistics.stdev(values)
            
            if stddev == 0:
                # No variation, no outliers
                return 0
            
            # Count values beyond 3 standard deviations
            outliers = 0
            for value in values:
                z_score = abs(value - mean) / stddev
                if z_score > 3:
                    outliers += 1
            
            return outliers
        except Exception:
            # If any error occurs, return 0
            return 0
    
    def _create_empty_window_stats(
        self,
        window: str,
        start_time: datetime,
        end_time: datetime
    ) -> TimeWindowAggregatedMetrics:
        """
        Create empty aggregated stats for a window with no data.

        Args:
            window: Time window string
            start_time: Start of time window
            end_time: End of time window

        Returns:
            TimeWindowAggregatedMetrics with zero values
        """
        return TimeWindowAggregatedMetrics(
            time_window=window,
            start_time=start_time,
            end_time=end_time,
            latency=AggregatedLatencyStats(
                mean_ms=0, median_ms=0, stddev_ms=0,
                p50_ms=0, p95_ms=0, p99_ms=0,
                min_ms=0, max_ms=0, sample_count=0
            ),
            error_rate=AggregatedErrorRateStats(
                mean_percent=0, median_percent=0, stddev_percent=0,
                p50_percent=0, p95_percent=0, p99_percent=0,
                min_percent=0, max_percent=0,
                total_requests=0, total_failed_requests=0, sample_count=0
            ),
            availability=AggregatedAvailabilityStats(
                mean_percent=0, median_percent=0, stddev_percent=0,
                p50_percent=0, p95_percent=0, p99_percent=0,
                min_percent=0, max_percent=0,
                total_uptime_seconds=0, total_downtime_seconds=0, sample_count=0
            ),
            data_quality=TimeWindowQuality(
                completeness=0.0,
                staleness_hours=(end_time - start_time).total_seconds() / 3600,
                expected_samples=self._parse_time_window(window),
                actual_samples=0,
                quality_score=0.0
            )
        )
    
    def _store_aggregated_metrics(self, aggregated_metrics: AggregatedMetrics):
        """
        Store aggregated metrics to file system.

        Args:
            aggregated_metrics: AggregatedMetrics object to store
        """
        # Store to metrics_aggregated.json
        aggregated_path = f"services/{aggregated_metrics.service_id}/metrics_aggregated.json"

        # Convert to dict for storage
        aggregated_dict = aggregated_metrics.dict()

        # Convert datetime objects to ISO format strings
        aggregated_dict["computed_at"] = aggregated_metrics.computed_at.isoformat()

        for window, window_data in aggregated_dict["time_windows"].items():
            window_data["start_time"] = aggregated_metrics.time_windows[window].start_time.isoformat()
            window_data["end_time"] = aggregated_metrics.time_windows[window].end_time.isoformat()

        # Store aggregated metrics
        self.storage.write_json(aggregated_path, aggregated_dict)
    
    def get_aggregated_metrics(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve aggregated metrics for a service.

        Args:
            service_id: Service identifier

        Returns:
            Dict with aggregated metrics or None if not found
        """
        aggregated_path = f"services/{service_id}/metrics_aggregated.json"
        aggregated_dict = self.storage.read_json(aggregated_path)

        if not aggregated_dict:
            return None

        # Convert ISO strings back to datetime (Python 3.6 compatible)
        if "computed_at" in aggregated_dict:
            from dateutil.parser import parse
            aggregated_dict["computed_at"] = parse(aggregated_dict["computed_at"])

        if "time_windows" in aggregated_dict:
            for window, window_data in aggregated_dict["time_windows"].items():
                if "start_time" in window_data:
                    from dateutil.parser import parse
                    window_data["start_time"] = parse(window_data["start_time"])
                if "end_time" in window_data:
                    from dateutil.parser import parse
                    window_data["end_time"] = parse(window_data["end_time"])

        return aggregated_dict
