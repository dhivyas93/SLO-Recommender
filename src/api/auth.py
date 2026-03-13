"""
API Authentication and Authorization

Implements API key-based authentication and rate limiting for the SLO
Recommendation System API.

Features:
- API key validation from X-API-Key header
- Tenant mapping and isolation
- Rate limiting (100 requests/minute per API key)
- Request tracking and audit logging
"""

import logging
import time
from typing import Optional, Dict, Any
from pathlib import Path
from fastapi import HTTPException, Request
from src.storage.file_storage import FileStorage

logger = logging.getLogger(__name__)


class APIKeyManager:
    """
    Manages API keys and tenant mapping.
    
    Stores API keys in data/api_keys.json with tenant mapping.
    """
    
    def __init__(self, api_keys_file: str = "api_keys.json"):
        """
        Initialize API key manager.
        
        Args:
            api_keys_file: Path to API keys JSON file (relative to data directory)
        """
        self.api_keys_file = api_keys_file
        self.storage = FileStorage()
        self._api_keys_cache = None
        self._cache_time = 0
        self._cache_ttl = 60  # Cache for 60 seconds
        
        logger.info(f"APIKeyManager initialized with {api_keys_file}")
    
    def load_api_keys(self, force_reload: bool = False) -> Dict[str, Any]:
        """
        Load API keys from file with caching.
        
        Args:
            force_reload: Force reload from file (bypass cache)
            
        Returns:
            Dictionary mapping API key to tenant info
        """
        # Check cache
        if not force_reload and self._api_keys_cache:
            if time.time() - self._cache_time < self._cache_ttl:
                return self._api_keys_cache
        
        try:
            api_keys = self.storage.read_json(self.api_keys_file)
            self._api_keys_cache = api_keys
            self._cache_time = time.time()
            logger.debug(f"Loaded {len(api_keys)} API keys")
            return api_keys
        
        except FileNotFoundError:
            logger.warning(f"API keys file not found: {self.api_keys_file}")
            return {}
        
        except Exception as e:
            logger.error(f"Failed to load API keys: {e}")
            return {}
    
    def validate_api_key(self, api_key: str) -> Optional[Dict[str, Any]]:
        """
        Validate API key and return tenant info.
        
        Args:
            api_key: API key to validate
            
        Returns:
            Tenant info if valid, None otherwise
        """
        if not api_key or not api_key.strip():
            logger.warning("Empty API key provided")
            return None
        
        # Always reload to ensure fresh data (especially for testing)
        api_keys = self.load_api_keys(force_reload=True)
        
        if api_key in api_keys:
            tenant_info = api_keys[api_key]
            logger.debug(f"API key validated for tenant: {tenant_info.get('tenant_id')}")
            return tenant_info
        
        logger.warning(f"Invalid API key: {api_key[:10]}...")
        return None
    
    def create_api_key(
        self,
        tenant_id: str,
        api_key: str,
        description: str = ""
    ) -> bool:
        """
        Create new API key.
        
        Args:
            tenant_id: Tenant identifier
            api_key: API key to create
            description: Optional description
            
        Returns:
            True if created successfully, False otherwise
        """
        try:
            api_keys = self.load_api_keys(force_reload=True)
            
            if api_key in api_keys:
                logger.warning(f"API key already exists: {api_key[:10]}...")
                return False
            
            api_keys[api_key] = {
                "tenant_id": tenant_id,
                "description": description,
                "created_at": time.time(),
                "active": True
            }
            
            self.storage.write_json(self.api_keys_file, api_keys)
            self._api_keys_cache = None  # Invalidate cache
            
            logger.info(f"Created API key for tenant: {tenant_id}")
            return True
        
        except Exception as e:
            logger.error(f"Failed to create API key: {e}")
            return False


class RateLimiter:
    """
    Rate limiter for API requests.
    
    Tracks requests per API key and enforces rate limits.
    """
    
    def __init__(self, requests_per_minute: int = 100):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Maximum requests per minute per API key
        """
        self.requests_per_minute = requests_per_minute
        self.request_history: Dict[str, list] = {}
        
        logger.info(f"RateLimiter initialized: {requests_per_minute} requests/minute")
    
    def is_rate_limited(self, api_key: str) -> bool:
        """
        Check if API key is rate limited.
        
        Args:
            api_key: API key to check
            
        Returns:
            True if rate limited, False otherwise
        """
        current_time = time.time()
        one_minute_ago = current_time - 60
        
        # Get request history for this API key
        if api_key not in self.request_history:
            self.request_history[api_key] = []
        
        # Remove old requests (older than 1 minute)
        self.request_history[api_key] = [
            req_time for req_time in self.request_history[api_key]
            if req_time > one_minute_ago
        ]
        
        # Check if rate limited
        if len(self.request_history[api_key]) >= self.requests_per_minute:
            logger.warning(f"Rate limit exceeded for API key: {api_key[:10]}...")
            return True
        
        # Record this request
        self.request_history[api_key].append(current_time)
        return False
    
    def get_remaining_requests(self, api_key: str) -> int:
        """
        Get remaining requests for API key.
        
        Args:
            api_key: API key to check
            
        Returns:
            Number of remaining requests
        """
        current_time = time.time()
        one_minute_ago = current_time - 60
        
        if api_key not in self.request_history:
            return self.requests_per_minute
        
        # Count requests in last minute
        recent_requests = [
            req_time for req_time in self.request_history[api_key]
            if req_time > one_minute_ago
        ]
        
        return max(0, self.requests_per_minute - len(recent_requests))
    
    def get_reset_time(self, api_key: str) -> int:
        """
        Get time until rate limit resets (in seconds).
        
        Args:
            api_key: API key to check
            
        Returns:
            Seconds until rate limit resets
        """
        if api_key not in self.request_history or not self.request_history[api_key]:
            return 0
        
        oldest_request = min(self.request_history[api_key])
        reset_time = oldest_request + 60
        current_time = time.time()
        
        return max(0, int(reset_time - current_time))


class AuthMiddleware:
    """
    FastAPI middleware for API authentication and rate limiting.
    """
    
    def __init__(
        self,
        api_key_manager: Optional[APIKeyManager] = None,
        rate_limiter: Optional[RateLimiter] = None
    ):
        """
        Initialize auth middleware.
        
        Args:
            api_key_manager: API key manager instance
            rate_limiter: Rate limiter instance
        """
        self.api_key_manager = api_key_manager or APIKeyManager()
        self.rate_limiter = rate_limiter or RateLimiter()
        
        logger.info("AuthMiddleware initialized")
    
    async def authenticate_request(self, request: Request) -> Dict[str, Any]:
        """
        Authenticate API request.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Tenant info if authenticated
            
        Raises:
            HTTPException: If authentication fails
        """
        # Get API key from header
        api_key = request.headers.get("X-API-Key")
        
        if not api_key:
            logger.warning("Missing X-API-Key header")
            raise HTTPException(
                status_code=401,
                detail="Missing X-API-Key header"
            )
        
        # Validate API key
        tenant_info = self.api_key_manager.validate_api_key(api_key)
        
        if not tenant_info:
            logger.warning(f"Invalid API key: {api_key[:10]}...")
            raise HTTPException(
                status_code=401,
                detail="Invalid API key"
            )
        
        # Check rate limit
        if self.rate_limiter.is_rate_limited(api_key):
            reset_time = self.rate_limiter.get_reset_time(api_key)
            logger.warning(f"Rate limit exceeded for tenant: {tenant_info['tenant_id']}")
            raise HTTPException(
                status_code=429,
                detail="Rate limit exceeded",
                headers={"Retry-After": str(reset_time)}
            )
        
        # Add rate limit headers
        remaining = self.rate_limiter.get_remaining_requests(api_key)
        request.state.tenant_id = tenant_info['tenant_id']
        request.state.api_key = api_key
        request.state.rate_limit_remaining = remaining
        
        return tenant_info
    
    def get_rate_limit_headers(self, request: Request) -> Dict[str, str]:
        """
        Get rate limit headers for response.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Dictionary of rate limit headers
        """
        api_key = request.state.api_key if hasattr(request.state, 'api_key') else None
        
        if not api_key:
            return {}
        
        remaining = self.rate_limiter.get_remaining_requests(api_key)
        reset_time = self.rate_limiter.get_reset_time(api_key)
        
        return {
            "X-RateLimit-Limit": str(self.rate_limiter.requests_per_minute),
            "X-RateLimit-Remaining": str(remaining),
            "X-RateLimit-Reset": str(int(time.time()) + reset_time)
        }


# Global instances
api_key_manager = APIKeyManager()
rate_limiter = RateLimiter()
auth_middleware = AuthMiddleware(api_key_manager, rate_limiter)
