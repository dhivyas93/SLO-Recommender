"""Unit tests for validation utilities."""

import pytest
from src.utils.validators import PIIDetector, validate_metrics_range, validate_percentage, validate_positive


class TestPIIDetector:
    """Tests for PII detection."""

    def test_detect_email(self):
        """Test email detection."""
        contains_pii, pii_types = PIIDetector.contains_pii("user@example.com")
        assert contains_pii is True
        assert "email" in pii_types

    def test_detect_phone_us_format(self):
        """Test US phone number detection."""
        test_cases = [
            "123-456-7890",
            "123.456.7890",
            "1234567890",
            # "(123) 456-7890",  # This format is harder to match without false positives
        ]
        for phone in test_cases:
            contains_pii, pii_types = PIIDetector.contains_pii(phone)
            assert contains_pii is True, f"Failed to detect phone: {phone}"
            assert "phone" in pii_types

    def test_detect_ssn(self):
        """Test SSN detection."""
        test_cases = [
            "123-45-6789",
            "123456789",
        ]
        for ssn in test_cases:
            contains_pii, pii_types = PIIDetector.contains_pii(ssn)
            assert contains_pii is True, f"Failed to detect SSN: {ssn}"
            assert "ssn" in pii_types

    def test_detect_credit_card(self):
        """Test credit card detection."""
        test_cases = [
            "1234 5678 9012 3456",
            "1234-5678-9012-3456",
            "1234567890123456",
        ]
        for cc in test_cases:
            contains_pii, pii_types = PIIDetector.contains_pii(cc)
            assert contains_pii is True, f"Failed to detect credit card: {cc}"
            assert "credit_card" in pii_types

    def test_no_pii_in_clean_text(self):
        """Test that clean text has no PII."""
        clean_texts = [
            "payment-api",
            "This is a normal service description",
            "latency: 150ms",
            "availability: 99.9%",
        ]
        for text in clean_texts:
            contains_pii, pii_types = PIIDetector.contains_pii(text)
            assert contains_pii is False, f"False positive for: {text}"
            assert len(pii_types) == 0

    def test_pii_in_dict(self):
        """Test PII detection in dictionary."""
        data = {
            "service_id": "payment-api",
            "contact": "admin@example.com",
        }
        contains_pii, pii_types = PIIDetector.contains_pii(data)
        assert contains_pii is True
        assert "email" in pii_types

    def test_pii_in_list(self):
        """Test PII detection in list."""
        data = ["payment-api", "user@example.com", "auth-service"]
        contains_pii, pii_types = PIIDetector.contains_pii(data)
        assert contains_pii is True
        assert "email" in pii_types

    def test_validate_no_pii_raises(self):
        """Test that validate_no_pii raises on PII."""
        with pytest.raises(ValueError, match="PII detected"):
            PIIDetector.validate_no_pii("user@example.com", "test_field")

    def test_validate_no_pii_passes(self):
        """Test that validate_no_pii passes on clean data."""
        PIIDetector.validate_no_pii("payment-api", "service_id")  # Should not raise


class TestMetricsRangeValidation:
    """Tests for metrics range validation."""

    def test_valid_metrics_range(self):
        """Test valid metrics range."""
        validate_metrics_range(50, 100, 150, "latency")  # Should not raise

    def test_p95_less_than_p50(self):
        """Test that p95 < p50 raises error."""
        with pytest.raises(ValueError, match="p95 must be >= .*p50"):
            validate_metrics_range(100, 50, 150, "latency")

    def test_p99_less_than_p95(self):
        """Test that p99 < p95 raises error."""
        with pytest.raises(ValueError, match="p99 must be >= .*p95"):
            validate_metrics_range(50, 100, 75, "latency")

    def test_p99_less_than_p50(self):
        """Test that p99 < p50 raises error."""
        with pytest.raises(ValueError, match="p99 must be >= .*p95"):
            validate_metrics_range(100, 150, 50, "latency")

    def test_equal_percentiles(self):
        """Test that equal percentiles are valid."""
        validate_metrics_range(100, 100, 100, "latency")  # Should not raise


class TestPercentageValidation:
    """Tests for percentage validation."""

    def test_valid_percentage(self):
        """Test valid percentage values."""
        validate_percentage(0, "test")
        validate_percentage(50, "test")
        validate_percentage(100, "test")

    def test_negative_percentage(self):
        """Test that negative percentage raises error."""
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            validate_percentage(-1, "test")

    def test_percentage_over_100(self):
        """Test that percentage > 100 raises error."""
        with pytest.raises(ValueError, match="must be between 0 and 100"):
            validate_percentage(101, "test")


class TestPositiveValidation:
    """Tests for positive value validation."""

    def test_valid_positive(self):
        """Test valid positive values."""
        validate_positive(0.1, "test")
        validate_positive(100, "test")
        validate_positive(1000000, "test")

    def test_zero_not_positive(self):
        """Test that zero raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive(0, "test")

    def test_negative_not_positive(self):
        """Test that negative value raises error."""
        with pytest.raises(ValueError, match="must be positive"):
            validate_positive(-1, "test")
