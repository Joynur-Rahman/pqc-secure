"""Rate limiting middleware for FastAPI"""
import time
import logging
from typing import Optional, Dict
from collections import defaultdict
from fastapi import Request, HTTPException, status
from pqc_secure.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """Simple in-memory rate limiter using token bucket algorithm"""
    
    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.
        
        Args:
            requests_per_minute: Number of requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_minute / 60.0
        # Store request timestamps by client identifier
        self.request_history: Dict[str, list] = defaultdict(list)
    
    def is_rate_limited(self, client_id: str) -> bool:
        """
        Check if a client is rate limited.
        
        Args:
            client_id: Unique identifier for the client (e.g., IP address or email)
            
        Returns:
            True if rate limited, False otherwise
        """
        current_time = time.time()
        one_minute_ago = current_time - 60
        
        # Remove requests older than 1 minute
        self.request_history[client_id] = [
            req_time for req_time in self.request_history[client_id]
            if req_time > one_minute_ago
        ]
        
        # Check if we've exceeded the limit
        if len(self.request_history[client_id]) >= self.requests_per_minute:
            return True
        
        # Record this request
        self.request_history[client_id].append(current_time)
        return False
    
    def cleanup_old_entries(self):
        """Clean up old client entries to prevent memory buildup"""
        current_time = time.time()
        one_hour_ago = current_time - 3600
        
        # Remove entries with no requests in the last hour
        clients_to_remove = []
        for client_id, requests in self.request_history.items():
            if requests and requests[-1] < one_hour_ago:
                clients_to_remove.append(client_id)
        
        for client_id in clients_to_remove:
            del self.request_history[client_id]


class EndpointRateLimiter:
    """Rate limiter for specific endpoints"""
    
    def __init__(self):
        """Initialize endpoint-specific rate limiters"""
        self.auth_limiter = RateLimiter(
            requests_per_minute=settings.rate_limit_auth_requests_per_minute
        )
        self.general_limiter = RateLimiter(
            requests_per_minute=settings.rate_limit_requests_per_minute
        )
    
    def get_client_identifier(self, request: Request) -> str:
        """
        Extract client identifier from request.
        Prioritizes X-Forwarded-For header for proxied requests.
        
        Args:
            request: FastAPI request object
            
        Returns:
            Client identifier (IP address)
        """
        # Check for forwarded IP (behind proxy)
        if request.headers.get("x-forwarded-for"):
            return request.headers["x-forwarded-for"].split(",")[0].strip()
        
        # Fall back to direct client IP
        if request.client:
            return request.client.host
        
        return "unknown"
    
    def check_auth_rate_limit(self, request: Request) -> bool:
        """
        Check if auth endpoint request is rate limited.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if rate limited, False otherwise
        """
        if not settings.rate_limit_enabled:
            return False
        
        client_id = self.get_client_identifier(request)
        is_limited = self.auth_limiter.is_rate_limited(client_id)
        
        if is_limited:
            logger.warning(f"Auth endpoint rate limit exceeded for client: {client_id}")
        
        return is_limited
    
    def check_general_rate_limit(self, request: Request) -> bool:
        """
        Check if general endpoint request is rate limited.
        
        Args:
            request: FastAPI request object
            
        Returns:
            True if rate limited, False otherwise
        """
        if not settings.rate_limit_enabled:
            return False
        
        client_id = self.get_client_identifier(request)
        is_limited = self.general_limiter.is_rate_limited(client_id)
        
        if is_limited:
            logger.warning(f"General endpoint rate limit exceeded for client: {client_id}")
        
        return is_limited


# Global rate limiter instance
rate_limiter = EndpointRateLimiter()
