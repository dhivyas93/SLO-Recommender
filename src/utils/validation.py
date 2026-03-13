"""Comprehensive validation module for all data inputs."""

from typing import Any, Dict
from src.utils.validators import PIIDetector, validate_metrics_range, validate_percentage, validate_positive


class MetricsValidator:
    """Validator for metrics data."""

    @staticmethod
    def validate_latency_metrics(p50: float, p95: float, p99: float) -> None:
        """
        Validate latency metrics are in correct order and positive.

        Args:
            p50: 50th percentile latency
            p95: 95th percentile latency
            p99: 99th percentile latency

        Raises:
            ValueError: If validation fails
        """
        validate_positive(p50, "latency_p50")
        validate_positive(p95, "latency_p95")
        validate_positive(p99, "latency_p99")
        validate_metrics_range(p50, p95, p99, "latency")

    @staticmethod
    def validate_availability(availability: float) -> None:
        """
        Validate availability percentage.

        Args:
            availability: Availability percentage

        Raises:
            ValueError: If validation fails
        """
        validate_percentage(availability, "availability")

    @staticmethod
    def validate_error_rate(error_rate: float) -> None:
        """
        Validate error rate percentage.

        Args:
            error_rate: Error rate percentage

        Raises:
            ValueError: If validation fails
        """
        validate_percentage(error_rate, "error_rate")

    @staticmethod
    def validate_request_counts(total: int, failed: int) -> None:
        """
        Validate request counts.

        Args:
            total: Total requests
            failed: Failed requests

        Raises:
            ValueError: If validation fails
        """
        if total < 0:
            raise ValueError(f"total_requests must be non-negative, got {total}")
        if failed < 0:
            raise ValueError(f"failed_requests must be non-negative, got {failed}")
        if failed > total:
            raise ValueError(
                f"failed_requests ({failed}) cannot exceed total_requests ({total})"
            )


class SLOValidator:
    """Validator for SLO recommendations."""

    @staticmethod
    def validate_slo_tier(
        availability: float,
        latency_p95: float,
        latency_p99: float,
        error_rate: float
    ) -> None:
        """
        Validate SLO tier values.

        Args:
            availability: Availability percentage
            latency_p95: p95 latency
            latency_p99: p99 latency
            error_rate: Error rate percentage

        Raises:
            ValueError: If validation fails
        """
        validate_percentage(availability, "availability")
        validate_positive(latency_p95, "latency_p95")
        validate_positive(latency_p99, "latency_p99")
        validate_percentage(error_rate, "error_rate")

        if latency_p99 < latency_p95:
            raise ValueError("latency_p99 must be >= latency_p95")

    @staticmethod
    def validate_tier_ordering(
        aggressive: Dict[str, float],
        balanced: Dict[str, float],
        conservative: Dict[str, float]
    ) -> None:
        """
        Validate that SLO tiers are properly ordered.

        For availability: aggressive >= balanced >= conservative
        For latency: aggressive <= balanced <= conservative
        For error_rate: aggressive <= balanced <= conservative

        Args:
            aggressive: Aggressive tier SLOs
            balanced: Balanced tier SLOs
            conservative: Conservative tier SLOs

        Raises:
            ValueError: If tier ordering is incorrect
        """
        # Availability should decrease from aggressive to conservative
        if not (aggressive["availability"] >= balanced["availability"] >= conservative["availability"]):
            raise ValueError(
                "Availability tier ordering incorrect: "
                f"aggressive ({aggressive['availability']}) >= "
                f"balanced ({balanced['availability']}) >= "
                f"conservative ({conservative['availability']})"
            )

        # Latency should increase from aggressive to conservative
        if not (aggressive["latency_p95_ms"] <= balanced["latency_p95_ms"] <= conservative["latency_p95_ms"]):
            raise ValueError(
                "Latency p95 tier ordering incorrect: "
                f"aggressive ({aggressive['latency_p95_ms']}) <= "
                f"balanced ({balanced['latency_p95_ms']}) <= "
                f"conservative ({conservative['latency_p95_ms']})"
            )

        if not (aggressive["latency_p99_ms"] <= balanced["latency_p99_ms"] <= conservative["latency_p99_ms"]):
            raise ValueError(
                "Latency p99 tier ordering incorrect: "
                f"aggressive ({aggressive['latency_p99_ms']}) <= "
                f"balanced ({balanced['latency_p99_ms']}) <= "
                f"conservative ({conservative['latency_p99_ms']})"
            )

        # Error rate should increase from aggressive to conservative
        if not (aggressive["error_rate_percent"] <= balanced["error_rate_percent"] <= conservative["error_rate_percent"]):
            raise ValueError(
                "Error rate tier ordering incorrect: "
                f"aggressive ({aggressive['error_rate_percent']}) <= "
                f"balanced ({balanced['error_rate_percent']}) <= "
                f"conservative ({conservative['error_rate_percent']})"
            )


class InputValidator:
    """Validator for all input data."""

    @staticmethod
    def validate_no_pii(data: Any, field_name: str = "input") -> None:
        """
        Validate that input contains no PII.

        Args:
            data: Data to validate
            field_name: Field name for error messages

        Raises:
            ValueError: If PII is detected
        """
        PIIDetector.validate_no_pii(data, field_name)

    @staticmethod
    def validate_service_id(service_id: str) -> None:
        """
        Validate service ID format.

        Args:
            service_id: Service identifier

        Raises:
            ValueError: If service ID is invalid
        """
        if not service_id or not service_id.strip():
            raise ValueError("service_id cannot be empty")

        # Check for PII in service ID
        PIIDetector.validate_no_pii(service_id, "service_id")

    @staticmethod
    def validate_time_window(time_window: str) -> None:
        """
        Validate time window format.

        Args:
            time_window: Time window string (e.g., "1d", "7d", "30d", "90d")

        Raises:
            ValueError: If time window is invalid
        """
        valid_windows = ["1d", "7d", "30d", "90d"]
        if time_window not in valid_windows:
            raise ValueError(
                f"Invalid time_window '{time_window}'. "
                f"Must be one of: {', '.join(valid_windows)}"
            )
