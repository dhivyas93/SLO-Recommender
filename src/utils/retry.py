"""
Retry logic with exponential backoff and jitter for fault tolerance.
"""

import time
import random
import functools
import logging
from typing import Callable, Any, TypeVar, Optional

logger = logging.getLogger(__name__)

F = TypeVar('F', bound=Callable[..., Any])


def retry_with_backoff(
    max_retries: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    jitter: bool = False
) -> Callable[[F], F]:
    """
    Decorator for retrying functions with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff calculation
        jitter: Whether to add random jitter to delays
    
    Returns:
        Decorated function that retries on exception
    
    Example:
        @retry_with_backoff(max_retries=3, initial_delay=1.0)
        def flaky_operation():
            # This will be retried up to 3 times with exponential backoff
            pass
    """
    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        # Calculate delay with exponential backoff
                        delay = min(
                            initial_delay * (exponential_base ** attempt),
                            max_delay
                        )
                        
                        # Add jitter if enabled
                        if jitter:
                            delay = delay * (0.5 + random.random())
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed for {func.__name__}: {e}. "
                            f"Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"All {max_retries + 1} attempts failed for {func.__name__}: {e}"
                        )
            
            # If we get here, all retries failed
            raise last_exception
        
        return wrapper  # type: ignore
    
    return decorator


def retry_file_lock(
    max_retries: int = 5,
    initial_delay: float = 0.01,
    max_delay: float = 1.0,
    jitter: bool = True
) -> Callable[[F], F]:
    """
    Decorator for retrying file operations with lock contention.
    
    Specialized for file lock scenarios with shorter delays and jitter.
    
    Args:
        max_retries: Maximum number of retry attempts
        initial_delay: Initial delay in seconds (shorter for file locks)
        max_delay: Maximum delay in seconds
        jitter: Whether to add random jitter (enabled by default for file locks)
    
    Returns:
        Decorated function that retries on exception
    
    Example:
        @retry_file_lock(max_retries=5)
        def write_to_file():
            # This will be retried up to 5 times with jitter
            pass
    """
    return retry_with_backoff(
        max_retries=max_retries,
        initial_delay=initial_delay,
        max_delay=max_delay,
        exponential_base=2.0,
        jitter=jitter
    )


class RetryConfig:
    """Configuration for retry behavior."""
    
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = False
    ):
        """
        Initialize retry configuration.
        
        Args:
            max_retries: Maximum number of retry attempts
            initial_delay: Initial delay in seconds
            max_delay: Maximum delay in seconds
            exponential_base: Base for exponential backoff calculation
            jitter: Whether to add random jitter to delays
        """
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """
        Calculate delay for a given attempt number.
        
        Args:
            attempt: Attempt number (0-indexed)
        
        Returns:
            Delay in seconds
        """
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            delay = delay * (0.5 + random.random())
        
        return delay


def retry_with_config(config: RetryConfig) -> Callable[[F], F]:
    """
    Decorator for retrying functions with a RetryConfig.
    
    Args:
        config: RetryConfig instance
    
    Returns:
        Decorated function that retries on exception
    
    Example:
        config = RetryConfig(max_retries=3, initial_delay=1.0, jitter=True)
        
        @retry_with_config(config)
        def operation():
            pass
    """
    return retry_with_backoff(
        max_retries=config.max_retries,
        initial_delay=config.initial_delay,
        max_delay=config.max_delay,
        exponential_base=config.exponential_base,
        jitter=config.jitter
    )
