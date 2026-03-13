"""Validation utilities for data models."""

import re
from typing import Any, Tuple, List


class PIIDetector:
    """Detect Personally Identifiable Information (PII) in data."""

    # Email pattern
    EMAIL_PATTERN = re.compile(
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    )

    # Phone patterns (US and international formats)
    PHONE_PATTERNS = [
        re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),  # US: 123-456-7890, 123.456.7890, 1234567890
        re.compile(r'\b\(\d{3}\)\s*\d{3}[-.]?\d{4}\b'),  # US: (123) 456-7890
        re.compile(r'\b\+\d{1,3}[-.\s]?\(?\d{1,4}\)?[-.\s]?\d{1,4}[-.\s]?\d{1,9}\b'),  # International
    ]

    # SSN pattern (US Social Security Number)
    SSN_PATTERN = re.compile(
        r'\b\d{3}[-]?\d{2}[-]?\d{4}\b'
    )

    # Credit card pattern (basic check for 13-19 digit sequences)
    CREDIT_CARD_PATTERN = re.compile(
        r'\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4,7}\b'
    )

    @classmethod
    def contains_pii(cls, value: Any) -> Tuple[bool, List[str]]:
        """
        Check if value contains PII.

        Args:
            value: Value to check (string, dict, list, or other)

        Returns:
            Tuple of (contains_pii, list_of_pii_types_found)
        """
        pii_types = []

        if isinstance(value, str):
            pii_types.extend(cls._check_string_for_pii(value))
        elif isinstance(value, dict):
            for v in value.values():
                found_pii, found_types = cls.contains_pii(v)
                if found_pii:
                    pii_types.extend(found_types)
        elif isinstance(value, (list, tuple)):
            for item in value:
                found_pii, found_types = cls.contains_pii(item)
                if found_pii:
                    pii_types.extend(found_types)

        # Remove duplicates while preserving order
        pii_types = list(dict.fromkeys(pii_types))
        return len(pii_types) > 0, pii_types

    @classmethod
    def _check_string_for_pii(cls, text: str) -> List[str]:
        """Check a string for PII patterns."""
        found_types = []

        if cls.EMAIL_PATTERN.search(text):
            found_types.append("email")

        for pattern in cls.PHONE_PATTERNS:
            if pattern.search(text):
                found_types.append("phone")
                break

        if cls.SSN_PATTERN.search(text):
            found_types.append("ssn")

        if cls.CREDIT_CARD_PATTERN.search(text):
            found_types.append("credit_card")

        return found_types

    @classmethod
    def validate_no_pii(cls, value: Any, field_name: str = "field") -> None:
        """
        Validate that value contains no PII.

        Args:
            value: Value to validate
            field_name: Name of the field for error message

        Raises:
            ValueError: If PII is detected
        """
        contains_pii, pii_types = cls.contains_pii(value)
        if contains_pii:
            pii_list = ", ".join(pii_types)
            raise ValueError(
                f"PII detected in {field_name}: {pii_list}. "
                f"Please remove personally identifiable information."
            )


def validate_metrics_range(
    p50: float,
    p95: float,
    p99: float,
    field_prefix: str = "latency"
) -> None:
    """
    Validate that percentile metrics are in correct order.

    Args:
        p50: 50th percentile value
        p95: 95th percentile value
        p99: 99th percentile value
        field_prefix: Prefix for field names in error messages

    Raises:
        ValueError: If metrics are not in correct order
    """
    if p95 < p50:
        raise ValueError(f"{field_prefix}_p95 must be >= {field_prefix}_p50")
    if p99 < p95:
        raise ValueError(f"{field_prefix}_p99 must be >= {field_prefix}_p95")
    if p99 < p50:
        raise ValueError(f"{field_prefix}_p99 must be >= {field_prefix}_p50")


def validate_percentage(value: float, field_name: str) -> None:
    """
    Validate that value is a valid percentage (0-100).

    Args:
        value: Value to validate
        field_name: Name of the field for error message

    Raises:
        ValueError: If value is not in range [0, 100]
    """
    if not 0 <= value <= 100:
        raise ValueError(f"{field_name} must be between 0 and 100, got {value}")


def validate_positive(value: float, field_name: str) -> None:
    """
    Validate that value is positive.

    Args:
        value: Value to validate
        field_name: Name of the field for error message

    Raises:
        ValueError: If value is not positive
    """
    if value <= 0:
        raise ValueError(f"{field_name} must be positive, got {value}")


def validate_no_pii(value: Any, field_name: str = "field") -> None:
    """
    Validate that value contains no PII.
    
    Convenience function that delegates to PIIDetector.validate_no_pii.

    Args:
        value: Value to validate
        field_name: Name of the field for error message

    Raises:
        ValueError: If PII is detected
    """
    PIIDetector.validate_no_pii(value, field_name)
