"""Metrics data models."""

from datetime import datetime
from typing import Optional, List, Dict, Union
from pydantic import BaseModel, Field, validator


class LatencyMetrics(BaseModel):
    """Latency metrics."""
    p50_ms: float = Field(..., gt=0, description="p50 latency in milliseconds")
    p95_ms: float = Field(..., gt=0, description="p95 latency in milliseconds")
    p99_ms: float = Field(..., gt=0, description="p99 latency in milliseconds")
    mean_ms: float = Field(..., gt=0, description="Mean latency in milliseconds")
    stddev_ms: float = Field(..., ge=0, description="Standard deviation in milliseconds")

    @validator("p95_ms")
    def validate_p95(cls, v, values):
        """Ensure p95 >= p50."""
        if "p50_ms" in values and v < values["p50_ms"]:
            raise ValueError("p95_ms must be >= p50_ms")
        return v

    @validator("p99_ms")
    def validate_p99(cls, v, values):
        """Ensure p99 >= p95."""
        if "p95_ms" in values and v < values["p95_ms"]:
            raise ValueError("p99_ms must be >= p95_ms")
        return v


class ErrorRateMetrics(BaseModel):
    """Error rate metrics."""
    percent: float = Field(..., ge=0, le=100, description="Error rate percentage")
    total_requests: int = Field(..., ge=0, description="Total number of requests")
    failed_requests: int = Field(..., ge=0, description="Number of failed requests")

    @validator("failed_requests")
    def validate_failed_requests(cls, v, values):
        """Ensure failed_requests <= total_requests."""
        if "total_requests" in values and v > values["total_requests"]:
            raise ValueError("failed_requests cannot exceed total_requests")
        return v


class AvailabilityMetrics(BaseModel):
    """Availability metrics."""
    percent: float = Field(..., ge=0, le=100, description="Availability percentage")
    uptime_seconds: int = Field(..., ge=0, description="Total uptime in seconds")
    downtime_seconds: int = Field(..., ge=0, description="Total downtime in seconds")


class RequestVolumeMetrics(BaseModel):
    """Request volume metrics."""
    requests_per_second: float = Field(..., ge=0, description="Average requests per second")
    peak_rps: float = Field(..., ge=0, description="Peak requests per second")

    @validator("peak_rps")
    def validate_peak_rps(cls, v, values):
        """Ensure peak_rps >= requests_per_second."""
        if "requests_per_second" in values and v < values["requests_per_second"]:
            raise ValueError("peak_rps must be >= requests_per_second")
        return v


class RegionalMetrics(BaseModel):
    """Regional metrics breakdown."""
    latency_p95_ms: float = Field(..., gt=0, description="Regional p95 latency")
    availability: float = Field(..., ge=0, le=100, description="Regional availability")


class OutlierInfo(BaseModel):
    """Information about detected outliers in metrics."""
    metric_name: str = Field(..., description="Name of the metric (e.g., 'latency_p95', 'error_rate')")
    value: float = Field(..., description="The outlier value")
    z_score: float = Field(..., description="Z-score (standard deviations from mean)")
    mean: float = Field(..., description="Historical mean value")
    stddev: float = Field(..., description="Historical standard deviation")


class DataQuality(BaseModel):
    """Data quality indicators."""
    completeness: float = Field(..., ge=0, le=1, description="Data completeness score (0-1)")
    staleness_hours: float = Field(..., ge=0, description="Hours since last metric update")
    outlier_count: int = Field(..., ge=0, description="Number of outliers detected")
    quality_score: float = Field(..., ge=0, le=1, description="Overall quality score (0-1)")
    outliers: Optional[List[OutlierInfo]] = Field(default=None, description="Detailed outlier information")





class MetricsData(BaseModel):
    """Service metrics data."""
    service_id: str = Field(..., description="Service identifier")
    timestamp: datetime = Field(..., description="Metrics collection timestamp")
    time_window: str = Field(..., description="Time window (e.g., 1d, 7d, 30d, 90d)")
    metrics: Dict[str, Union[LatencyMetrics, ErrorRateMetrics, AvailabilityMetrics, RequestVolumeMetrics]] = Field(
        ..., description="Metrics by category"
    )
    regional_breakdown: Optional[Dict[str, RegionalMetrics]] = Field(
        None, description="Regional metrics breakdown"
    )
    data_quality: DataQuality = Field(..., description="Data quality indicators")


class AggregatedLatencyStats(BaseModel):
    """Aggregated latency statistics for a time window."""
    mean_ms: float = Field(..., description="Mean of p50 latencies")
    median_ms: float = Field(..., description="Median of p50 latencies")
    stddev_ms: float = Field(..., description="Standard deviation of p50 latencies")
    p50_ms: float = Field(..., description="50th percentile of p50 latencies")
    p95_ms: float = Field(..., description="95th percentile of p95 latencies")
    p99_ms: float = Field(..., description="99th percentile of p99 latencies")
    min_ms: float = Field(..., description="Minimum latency observed")
    max_ms: float = Field(..., description="Maximum latency observed")
    sample_count: int = Field(..., ge=0, description="Number of data points")


class AggregatedErrorRateStats(BaseModel):
    """Aggregated error rate statistics for a time window."""
    mean_percent: float = Field(..., ge=0, le=100, description="Mean error rate")
    median_percent: float = Field(..., ge=0, le=100, description="Median error rate")
    stddev_percent: float = Field(..., ge=0, description="Standard deviation of error rate")
    p50_percent: float = Field(..., ge=0, le=100, description="50th percentile error rate")
    p95_percent: float = Field(..., ge=0, le=100, description="95th percentile error rate")
    p99_percent: float = Field(..., ge=0, le=100, description="99th percentile error rate")
    min_percent: float = Field(..., ge=0, le=100, description="Minimum error rate")
    max_percent: float = Field(..., ge=0, le=100, description="Maximum error rate")
    total_requests: int = Field(..., ge=0, description="Total requests across all samples")
    total_failed_requests: int = Field(..., ge=0, description="Total failed requests")
    sample_count: int = Field(..., ge=0, description="Number of data points")


class AggregatedAvailabilityStats(BaseModel):
    """Aggregated availability statistics for a time window."""
    mean_percent: float = Field(..., ge=0, le=100, description="Mean availability")
    median_percent: float = Field(..., ge=0, le=100, description="Median availability")
    stddev_percent: float = Field(..., ge=0, description="Standard deviation of availability")
    p50_percent: float = Field(..., ge=0, le=100, description="50th percentile availability")
    p95_percent: float = Field(..., ge=0, le=100, description="95th percentile availability")
    p99_percent: float = Field(..., ge=0, le=100, description="99th percentile availability")
    min_percent: float = Field(..., ge=0, le=100, description="Minimum availability")
    max_percent: float = Field(..., ge=0, le=100, description="Maximum availability")
    total_uptime_seconds: int = Field(..., ge=0, description="Total uptime across all samples")
    total_downtime_seconds: int = Field(..., ge=0, description="Total downtime across all samples")
    sample_count: int = Field(..., ge=0, description="Number of data points")


class TimeWindowQuality(BaseModel):
    """Data quality indicators for a time window."""
    completeness: float = Field(..., ge=0, le=1, description="Data completeness (0-1)")
    staleness_hours: float = Field(..., ge=0, description="Hours since last data point")
    expected_samples: int = Field(..., ge=0, description="Expected number of samples")
    actual_samples: int = Field(..., ge=0, description="Actual number of samples")
    quality_score: float = Field(..., ge=0, le=1, description="Overall quality score (0-1)")


class TimeWindowAggregatedMetrics(BaseModel):
    """Aggregated metrics for a specific time window."""
    time_window: str = Field(..., description="Time window (1d, 7d, 30d, 90d)")
    start_time: datetime = Field(..., description="Start of time window")
    end_time: datetime = Field(..., description="End of time window")
    latency: AggregatedLatencyStats = Field(..., description="Raw aggregated latency statistics (all data)")
    error_rate: AggregatedErrorRateStats = Field(..., description="Raw aggregated error rate statistics (all data)")
    availability: AggregatedAvailabilityStats = Field(..., description="Raw aggregated availability statistics (all data)")
    latency_adjusted: Optional[AggregatedLatencyStats] = Field(None, description="Adjusted latency statistics (outliers excluded)")
    error_rate_adjusted: Optional[AggregatedErrorRateStats] = Field(None, description="Adjusted error rate statistics (outliers excluded)")
    availability_adjusted: Optional[AggregatedAvailabilityStats] = Field(None, description="Adjusted availability statistics (outliers excluded)")
    outlier_indices: Optional[List[int]] = Field(None, description="Indices of metrics identified as outliers")
    data_quality: TimeWindowQuality = Field(..., description="Data quality for this window")


class AggregatedMetrics(BaseModel):
    """Aggregated metrics across all time windows for a service."""
    service_id: str = Field(..., description="Service identifier")
    computed_at: datetime = Field(..., description="When aggregation was computed")
    time_windows: Dict[str, TimeWindowAggregatedMetrics] = Field(
        ..., description="Aggregated metrics by time window (1d, 7d, 30d, 90d)"
    )

