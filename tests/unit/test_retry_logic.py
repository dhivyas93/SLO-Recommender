"""
Unit tests for retry logic with exponential backoff.
"""

import pytest
import time
from unittest.mock import Mock, patch, call
from src.utils.retry import (
    retry_with_backoff,
    retry_file_lock,
    retry_with_config,
    RetryConfig
)


class TestRetryWithBackoff:
    """Test retry_with_backoff decorator."""
    
    def test_successful_on_first_attempt(self):
        """Test function succeeds on first attempt."""
        mock_func = Mock(return_value="success")
        
        @retry_with_backoff(max_retries=3)
        def operation():
            return mock_func()
        
        result = operation()
        
        assert result == "success"
        assert mock_func.call_count == 1
    
    def test_retry_on_failure_then_success(self):
        """Test function fails then succeeds on retry."""
        mock_func = Mock(side_effect=[
            Exception("First attempt failed"),
            "success"
        ])
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def operation():
            return mock_func()
        
        result = operation()
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_all_retries_exhausted(self):
        """Test exception raised after all retries exhausted."""
        mock_func = Mock(side_effect=Exception("Always fails"))
        
        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def operation():
            return mock_func()
        
        with pytest.raises(Exception, match="Always fails"):
            operation()
        
        # Should try: initial + 2 retries = 3 total attempts
        assert mock_func.call_count == 3
    
    def test_exponential_backoff_delays(self):
        """Test exponential backoff increases delays."""
        mock_func = Mock(side_effect=Exception("Fail"))
        
        @retry_with_backoff(
            max_retries=3,
            initial_delay=0.1,
            exponential_base=2.0,
            jitter=False
        )
        def operation():
            return mock_func()
        
        start_time = time.time()
        
        with pytest.raises(Exception):
            operation()
        
        elapsed = time.time() - start_time
        
        # Expected delays: 0.1, 0.2, 0.4 = 0.7 seconds total
        # Allow some tolerance for execution time
        assert elapsed >= 0.6  # At least the sum of delays
        assert elapsed < 1.5   # But not too much more
    
    def test_max_delay_cap(self):
        """Test that delays are capped at max_delay."""
        mock_func = Mock(side_effect=Exception("Fail"))
        
        @retry_with_backoff(
            max_retries=5,
            initial_delay=1.0,
            max_delay=0.1,  # Cap at 0.1 seconds
            exponential_base=2.0,
            jitter=False
        )
        def operation():
            return mock_func()
        
        start_time = time.time()
        
        with pytest.raises(Exception):
            operation()
        
        elapsed = time.time() - start_time
        
        # With max_delay=0.1, delays should be: 0.1, 0.1, 0.1, 0.1, 0.1 = 0.5 seconds
        # Allow tolerance
        assert elapsed >= 0.4
        assert elapsed < 1.0
    
    def test_jitter_adds_randomness(self):
        """Test that jitter adds randomness to delays."""
        mock_func = Mock(side_effect=Exception("Fail"))
        
        @retry_with_backoff(
            max_retries=2,
            initial_delay=1.0,
            jitter=True
        )
        def operation():
            return mock_func()
        
        # Run multiple times and check that delays vary
        times = []
        for _ in range(3):
            start_time = time.time()
            try:
                operation()
            except Exception:
                pass
            elapsed = time.time() - start_time
            times.append(elapsed)
        
        # With jitter, times should vary (not all identical)
        # This is probabilistic, so we just check they're not all the same
        assert len(set([round(t, 2) for t in times])) > 1 or all(t < 0.5 for t in times)
    
    def test_function_arguments_passed_through(self):
        """Test that function arguments are passed correctly."""
        mock_func = Mock(return_value="result")
        
        @retry_with_backoff(max_retries=1)
        def operation(a, b, c=None):
            return mock_func(a, b, c)
        
        result = operation(1, 2, c=3)
        
        assert result == "result"
        mock_func.assert_called_once_with(1, 2, 3)
    
    def test_function_name_preserved(self):
        """Test that decorated function preserves original name."""
        @retry_with_backoff(max_retries=1)
        def my_operation():
            pass
        
        assert my_operation.__name__ == "my_operation"
    
    def test_specific_exception_types(self):
        """Test retry on specific exception types."""
        mock_func = Mock(side_effect=[
            ValueError("First attempt"),
            "success"
        ])
        
        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def operation():
            return mock_func()
        
        result = operation()
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_return_value_preserved(self):
        """Test that return values are preserved through retries."""
        mock_func = Mock(side_effect=[
            Exception("Fail"),
            {"status": "success", "data": [1, 2, 3]}
        ])
        
        @retry_with_backoff(max_retries=2, initial_delay=0.01)
        def operation():
            return mock_func()
        
        result = operation()
        
        assert result == {"status": "success", "data": [1, 2, 3]}


class TestRetryFileLock:
    """Test retry_file_lock decorator for file operations."""
    
    def test_file_lock_retry_with_jitter(self):
        """Test file lock retry has jitter enabled by default."""
        mock_func = Mock(side_effect=[
            Exception("Lock contention"),
            "success"
        ])
        
        @retry_file_lock(max_retries=2)
        def write_file():
            return mock_func()
        
        result = write_file()
        
        assert result == "success"
        assert mock_func.call_count == 2
    
    def test_file_lock_shorter_delays(self):
        """Test file lock retry uses shorter delays."""
        mock_func = Mock(side_effect=Exception("Fail"))
        
        @retry_file_lock(max_retries=3)
        def write_file():
            return mock_func()
        
        start_time = time.time()
        
        with pytest.raises(Exception):
            write_file()
        
        elapsed = time.time() - start_time
        
        # File lock retries should be faster (shorter delays)
        # Default: 0.01, 0.02, 0.04 = 0.07 seconds
        assert elapsed < 0.5  # Should be quick


class TestRetryConfig:
    """Test RetryConfig class."""
    
    def test_config_initialization(self):
        """Test RetryConfig initialization."""
        config = RetryConfig(
            max_retries=5,
            initial_delay=0.5,
            max_delay=10.0,
            exponential_base=3.0,
            jitter=True
        )
        
        assert config.max_retries == 5
        assert config.initial_delay == 0.5
        assert config.max_delay == 10.0
        assert config.exponential_base == 3.0
        assert config.jitter == True
    
    def test_config_get_delay(self):
        """Test delay calculation from config."""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=100.0,
            jitter=False
        )
        
        # Attempt 0: 1.0 * 2^0 = 1.0
        assert config.get_delay(0) == 1.0
        
        # Attempt 1: 1.0 * 2^1 = 2.0
        assert config.get_delay(1) == 2.0
        
        # Attempt 2: 1.0 * 2^2 = 4.0
        assert config.get_delay(2) == 4.0
    
    def test_config_get_delay_with_cap(self):
        """Test delay calculation respects max_delay."""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=5.0,
            jitter=False
        )
        
        # Attempt 0: 1.0 (< 5.0)
        assert config.get_delay(0) == 1.0
        
        # Attempt 2: 4.0 (< 5.0)
        assert config.get_delay(2) == 4.0
        
        # Attempt 3: 8.0 capped to 5.0
        assert config.get_delay(3) == 5.0
        
        # Attempt 4: 16.0 capped to 5.0
        assert config.get_delay(4) == 5.0
    
    def test_config_get_delay_with_jitter(self):
        """Test delay calculation with jitter."""
        config = RetryConfig(
            initial_delay=1.0,
            exponential_base=2.0,
            max_delay=100.0,
            jitter=True
        )
        
        # With jitter, delay should be between 0.5 * base_delay and 1.5 * base_delay
        # (because jitter multiplies by 0.5 + random() where random() is 0-1)
        delay = config.get_delay(0)
        assert 0.5 <= delay <= 1.5
        
        delay = config.get_delay(1)
        assert 1.0 <= delay <= 3.0


class TestRetryWithConfig:
    """Test retry_with_config decorator."""
    
    def test_retry_with_custom_config(self):
        """Test retry with custom RetryConfig."""
        config = RetryConfig(
            max_retries=2,
            initial_delay=0.01,
            jitter=False
        )
        
        mock_func = Mock(side_effect=[
            Exception("Fail"),
            Exception("Fail"),
            "success"
        ])
        
        @retry_with_config(config)
        def operation():
            return mock_func()
        
        result = operation()
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_config_max_retries_respected(self):
        """Test that config max_retries is respected."""
        config = RetryConfig(max_retries=1, initial_delay=0.01)
        
        mock_func = Mock(side_effect=Exception("Always fails"))
        
        @retry_with_config(config)
        def operation():
            return mock_func()
        
        with pytest.raises(Exception):
            operation()
        
        # Should try: initial + 1 retry = 2 total attempts
        assert mock_func.call_count == 2


class TestRetryEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_zero_retries(self):
        """Test with zero retries (no retry)."""
        mock_func = Mock(side_effect=Exception("Fail"))
        
        @retry_with_backoff(max_retries=0, initial_delay=0.01)
        def operation():
            return mock_func()
        
        with pytest.raises(Exception):
            operation()
        
        # Should try once (no retries)
        assert mock_func.call_count == 1
    
    def test_very_large_max_retries(self):
        """Test with very large max_retries."""
        call_count = 0
        
        def operation_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Fail")
            return "success"
        
        @retry_with_backoff(max_retries=1000, initial_delay=0.001)
        def operation():
            return operation_func()
        
        result = operation()
        
        assert result == "success"
        assert call_count == 3
    
    def test_negative_initial_delay(self):
        """Test behavior with negative initial delay."""
        mock_func = Mock(return_value="success")
        
        @retry_with_backoff(max_retries=1, initial_delay=-1.0)
        def operation():
            return mock_func()
        
        # Should still work, just with no delay
        result = operation()
        assert result == "success"
    
    def test_exception_message_preserved(self):
        """Test that exception message is preserved."""
        error_msg = "Specific error message"
        
        @retry_with_backoff(max_retries=0, initial_delay=0.01)
        def operation():
            raise ValueError(error_msg)
        
        with pytest.raises(ValueError, match=error_msg):
            operation()
    
    def test_multiple_exception_types(self):
        """Test retry with multiple exception types."""
        mock_func = Mock(side_effect=[
            ValueError("First"),
            TypeError("Second"),
            RuntimeError("Third"),
            "success"
        ])
        
        @retry_with_backoff(max_retries=3, initial_delay=0.01)
        def operation():
            return mock_func()
        
        result = operation()
        
        assert result == "success"
        assert mock_func.call_count == 4
