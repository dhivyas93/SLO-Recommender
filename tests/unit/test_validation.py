"""Unit tests for comprehensive validation module."""

import pytest
from src.utils.validation import MetricsValidator, SLOValidator, InputValidator


class TestMetricsValidator:
    """Tests for MetricsValidator."""

    def test_valid_latency_metrics(self):
        """Test valid latency metrics."""
        MetricsValidator.validate_latency_metrics(50, 100, 150)

    def test_invalid_latency_ordering(self):
        """Test invalid latency ordering."""
        with pytest.raises(ValueError):
            MetricsValidator.validate_latency_metrics(100, 50, 150)

    def test_negative_latency(self):
        """Test negative latency values."""
        with pytest.raises(ValueError, match="must be positive"):
            MetricsValidator.validate_latency_metrics(-10, 100, 150)

    def test_valid_availability(self):
        """Test valid availability values."""
        MetricsValidator.validate_availability(99.9)
        MetricsValidator.validate_availability(0)
        MetricsValidator.validate_availability(100)

    def test_invalid_availability(self):
        """Test invalid availability values."""
        with pytest.raises(ValueError):
            MetricsValidator.validate_availability(-1)
        with pytest.raises(ValueError):
            MetricsValidator.validate_availability(101)

    def test_valid_error_rate(self):
        """Test valid error rate values."""
        MetricsValidator.validate_error_rate(0.5)
        MetricsValidator.validate_error_rate(0)
        MetricsValidator.validate_error_rate(100)

    def test_invalid_error_rate(self):
        """Test invalid error rate values."""
        with pytest.raises(ValueError):
            MetricsValidator.validate_error_rate(-1)
        with pytest.raises(ValueError):
            MetricsValidator.validate_error_rate(101)

    def test_valid_request_counts(self):
        """Test valid request counts."""
        MetricsValidator.validate_request_counts(1000, 10)
        MetricsValidator.validate_request_counts(1000, 0)
        MetricsValidator.validate_request_counts(1000, 1000)

    def test_failed_exceeds_total(self):
        """Test failed requests exceeding total."""
        with pytest.raises(ValueError, match="cannot exceed total_requests"):
            MetricsValidator.validate_request_counts(1000, 1001)

    def test_negative_request_counts(self):
        """Test negative request counts."""
        with pytest.raises(ValueError, match="must be non-negative"):
            MetricsValidator.validate_request_counts(-1, 0)
        with pytest.raises(ValueError, match="must be non-negative"):
            MetricsValidator.validate_request_counts(1000, -1)


class TestSLOValidator:
    """Tests for SLOValidator."""

    def test_valid_slo_tier(self):
        """Test valid SLO tier."""
        SLOValidator.validate_slo_tier(99.9, 100, 200, 0.5)

    def test_invalid_slo_tier_latency_ordering(self):
        """Test invalid latency ordering in SLO tier."""
        with pytest.raises(ValueError, match="p99 must be >= .*p95"):
            SLOValidator.validate_slo_tier(99.9, 200, 100, 0.5)

    def test_invalid_slo_tier_availability(self):
        """Test invalid availability in SLO tier."""
        with pytest.raises(ValueError):
            SLOValidator.validate_slo_tier(101, 100, 200, 0.5)

    def test_valid_tier_ordering(self):
        """Test valid tier ordering."""
        aggressive = {
            "availability": 99.99,
            "latency_p95_ms": 50,
            "latency_p99_ms": 100,
            "error_rate_percent": 0.1,
        }
        balanced = {
            "availability": 99.9,
            "latency_p95_ms": 100,
            "latency_p99_ms": 200,
            "error_rate_percent": 0.5,
        }
        conservative = {
            "availability": 99.5,
            "latency_p95_ms": 200,
            "latency_p99_ms": 400,
            "error_rate_percent": 1.0,
        }
        SLOValidator.validate_tier_ordering(aggressive, balanced, conservative)

    def test_invalid_availability_tier_ordering(self):
        """Test invalid availability tier ordering."""
        aggressive = {"availability": 99.5, "latency_p95_ms": 50, "latency_p99_ms": 100, "error_rate_percent": 0.1}
        balanced = {"availability": 99.9, "latency_p95_ms": 100, "latency_p99_ms": 200, "error_rate_percent": 0.5}
        conservative = {"availability": 99.99, "latency_p95_ms": 200, "latency_p99_ms": 400, "error_rate_percent": 1.0}

        with pytest.raises(ValueError, match="Availability tier ordering incorrect"):
            SLOValidator.validate_tier_ordering(aggressive, balanced, conservative)

    def test_invalid_latency_tier_ordering(self):
        """Test invalid latency tier ordering."""
        aggressive = {"availability": 99.99, "latency_p95_ms": 200, "latency_p99_ms": 400, "error_rate_percent": 0.1}
        balanced = {"availability": 99.9, "latency_p95_ms": 100, "latency_p99_ms": 200, "error_rate_percent": 0.5}
        conservative = {"availability": 99.5, "latency_p95_ms": 50, "latency_p99_ms": 100, "error_rate_percent": 1.0}

        with pytest.raises(ValueError, match="Latency .* tier ordering incorrect"):
            SLOValidator.validate_tier_ordering(aggressive, balanced, conservative)

    def test_invalid_error_rate_tier_ordering(self):
        """Test invalid error rate tier ordering."""
        aggressive = {"availability": 99.99, "latency_p95_ms": 50, "latency_p99_ms": 100, "error_rate_percent": 1.0}
        balanced = {"availability": 99.9, "latency_p95_ms": 100, "latency_p99_ms": 200, "error_rate_percent": 0.5}
        conservative = {"availability": 99.5, "latency_p95_ms": 200, "latency_p99_ms": 400, "error_rate_percent": 0.1}

        with pytest.raises(ValueError, match="Error rate tier ordering incorrect"):
            SLOValidator.validate_tier_ordering(aggressive, balanced, conservative)


class TestInputValidator:
    """Tests for InputValidator."""

    def test_validate_no_pii_clean_data(self):
        """Test validation passes for clean data."""
        InputValidator.validate_no_pii("payment-api", "service_id")
        InputValidator.validate_no_pii({"key": "value"}, "metadata")

    def test_validate_no_pii_with_pii(self):
        """Test validation fails for data with PII."""
        with pytest.raises(ValueError, match="PII detected"):
            InputValidator.validate_no_pii("user@example.com", "email_field")

    def test_valid_service_id(self):
        """Test valid service IDs."""
        InputValidator.validate_service_id("payment-api")
        InputValidator.validate_service_id("auth-service-v2")

    def test_empty_service_id(self):
        """Test empty service ID."""
        with pytest.raises(ValueError, match="cannot be empty"):
            InputValidator.validate_service_id("")
        with pytest.raises(ValueError, match="cannot be empty"):
            InputValidator.validate_service_id("   ")

    def test_service_id_with_pii(self):
        """Test service ID containing PII."""
        with pytest.raises(ValueError, match="PII detected"):
            InputValidator.validate_service_id("service-user@example.com")

    def test_valid_time_window(self):
        """Test valid time windows."""
        for window in ["1d", "7d", "30d", "90d"]:
            InputValidator.validate_time_window(window)

    def test_invalid_time_window(self):
        """Test invalid time windows."""
        with pytest.raises(ValueError, match="Invalid time_window"):
            InputValidator.validate_time_window("5d")
        with pytest.raises(ValueError, match="Invalid time_window"):
            InputValidator.validate_time_window("1h")
        with pytest.raises(ValueError, match="Invalid time_window"):
            InputValidator.validate_time_window("invalid")
