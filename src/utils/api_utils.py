#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Utility Module - Provides robust API request capabilities with:
- Automatic retries with exponential backoff
- Response caching
- Rate limiting
- Comprehensive error handling
- Circuit breaker pattern to prevent repeated failures
"""

import os
import time
import json
import random
import logging
import hashlib
import requests
import threading
from datetime import datetime, timedelta
from functools import wraps

# Configure logging
logger = logging.getLogger(__name__)

class RateLimiter:
    """
    Rate limiter that ensures API requests don't exceed specified limits
    """
    def __init__(self, calls_per_minute=60):
        self.calls_per_minute = calls_per_minute
        self.call_timestamps = []
        self.lock = threading.Lock()
    
    def wait_if_needed(self):
        """Wait if we've exceeded the rate limit"""
        with self.lock:
            now = time.time()
            
            # Clean old timestamps
            min_timestamp = now - 60  # 1 minute rolling window
            self.call_timestamps = [ts for ts in self.call_timestamps if ts > min_timestamp]
            
            # Check if we need to wait
            if len(self.call_timestamps) >= self.calls_per_minute:
                # Calculate wait time (time to wait until the oldest timestamp is 1 minute old)
                wait_time = self.call_timestamps[0] + 60 - now
                if wait_time > 0:
                    logger.info(f"Rate limit reached. Waiting {wait_time:.2f} seconds")
                    time.sleep(wait_time)
                    now = time.time()  # Update current time
            
            # Record this call
            self.call_timestamps.append(now)

class CircuitBreaker:
    """
    Circuit breaker pattern to prevent repeated API failures
    """
    # Shared circuit breaker state across all instances
    _breakers = {}
    _lock = threading.Lock()
    
    def __init__(self, service_name, failure_threshold=5, reset_timeout=300):
        self.service_name = service_name
        self.failure_threshold = failure_threshold
        self.reset_timeout = reset_timeout
        
        # Initialize breaker state if not already done
        with self._lock:
            if service_name not in self._breakers:
                self._breakers[service_name] = {
                    'failures': 0,
                    'open_until': None,
                    'half_open': False
                }
    
    @property
    def state(self):
        """Get current state of the circuit breaker"""
        return self._breakers[self.service_name]
    
    def is_open(self):
        """Check if circuit breaker is open (meaning API calls should not be attempted)"""
        with self._lock:
            if self.state['open_until'] is not None:
                # If we're in open state, check if reset timeout has elapsed
                if time.time() > self.state['open_until']:
                    # Reset to half-open state to allow a test request
                    self.state['open_until'] = None
                    self.state['half_open'] = True
                    logger.info(f"Circuit for {self.service_name} reset to half-open state")
                    return False
                return True
            return False
    
    def record_success(self):
        """Record a successful API call"""
        with self._lock:
            # If successful in half-open state, reset the circuit
            if self.state['half_open']:
                self.reset()
            else:
                # Reset failure count on success
                self.state['failures'] = 0
    
    def record_failure(self):
        """Record a failed API call"""
        with self._lock:
            self.state['failures'] += 1
            
            # If in half-open state, any failure reopens the circuit
            if self.state['half_open']:
                self.trip_breaker()
            # If we've reached the failure threshold, open the circuit
            elif self.state['failures'] >= self.failure_threshold:
                self.trip_breaker()
    
    def trip_breaker(self):
        """Open the circuit breaker"""
        with self._lock:
            self.state['open_until'] = time.time() + self.reset_timeout
            self.state['half_open'] = False
            logger.warning(f"Circuit breaker for {self.service_name} tripped. "
                          f"Open until {datetime.fromtimestamp(self.state['open_until'])}")
    
    def reset(self):
        """Reset the circuit breaker to closed state"""
        with self._lock:
            self.state['failures'] = 0
            self.state['open_until'] = None
            self.state['half_open'] = False
            logger.info(f"Circuit breaker for {self.service_name} reset to closed state")

class APICache:
    """
    Cache for API responses
    """
    def __init__(self, max_size=100):
        self.cache = {}
        self.timestamps = {}
        self.max_size = max_size
        self.lock = threading.Lock()
    
    def get(self, key, ttl=600):
        """Get value from cache if it exists and is not expired"""
        with self.lock:
            if key in self.cache:
                timestamp = self.timestamps.get(key, 0)
                if time.time() - timestamp <= ttl:
                    return self.cache[key]
        return None
    
    def set(self, key, value, ttl=600):
        """Set value in cache"""
        with self.lock:
            # If cache is full, remove oldest item
            if len(self.cache) >= self.max_size:
                oldest_key = min(self.timestamps.items(), key=lambda x: x[1])[0]
                del self.cache[oldest_key]
                del self.timestamps[oldest_key]
            
            self.cache[key] = value
            self.timestamps[key] = time.time()
    
    def invalidate(self, key):
        """Remove key from cache"""
        with self.lock:
            if key in self.cache:
                del self.cache[key]
                del self.timestamps[key]
    
    def prune(self, ttl=600):
        """Remove expired items from cache"""
        with self.lock:
            now = time.time()
            expired_keys = [k for k, t in self.timestamps.items() if now - t > ttl]
            
            for key in expired_keys:
                del self.cache[key]
                del self.timestamps[key]
            
            return len(expired_keys)

# Create global instances
global_cache = APICache()
global_rate_limiter = RateLimiter()

def robust_api_request(service_name, max_retries=3, cache_ttl=600, rate_limit=True):
    """
    Decorator to make an API request function more robust with retries, caching, and rate limiting
    
    Args:
        service_name (str): Name of the API service (used for circuit breaker)
        max_retries (int): Maximum number of retry attempts
        cache_ttl (int): Cache time-to-live in seconds (0 to disable caching)
        rate_limit (bool): Whether to apply rate limiting
    
    Returns:
        Decorated function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get cache_key from kwargs or use default
            provided_cache_key = kwargs.pop('cache_key', None) 
            
            # If no cache_key provided, generate one based on args and kwargs
            if provided_cache_key is None and cache_ttl > 0:
                # Create a deterministic string representation of args and kwargs
                cache_parts = [str(arg) for arg in args]
                cache_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
                cache_str = f"{func.__name__}:{':'.join(cache_parts)}"
                cache_key = hashlib.md5(cache_str.encode()).hexdigest()
            else:
                cache_key = provided_cache_key
            
            # Try cache first
            if cache_ttl > 0 and cache_key:
                cached_response = global_cache.get(cache_key, cache_ttl)
                if cached_response is not None:
                    logger.debug(f"Cache hit for {service_name} request: {func.__name__}")
                    return cached_response
            
            # Check circuit breaker
            circuit_breaker = CircuitBreaker(service_name)
            if circuit_breaker.is_open():
                logger.warning(f"Circuit breaker open for {service_name}. Request blocked.")
                return {
                    "error": "Service temporarily unavailable due to repeated failures",
                    "circuit_open": True,
                    "data": {}
                }
            
            # Apply rate limiting if enabled
            if rate_limit:
                global_rate_limiter.wait_if_needed()
            
            # Implement retry logic
            retry_count = 0
            last_exception = None
            
            while retry_count <= max_retries:
                try:
                    if retry_count > 0:
                        # Calculate exponential backoff with jitter
                        backoff = (2 ** retry_count) + random.uniform(0, 1)
                        logger.info(f"Retrying {service_name} request in {backoff:.2f} seconds "
                                   f"(attempt {retry_count}/{max_retries})")
                        time.sleep(backoff)
                    
                    # Make the actual API request
                    response = func(*args, **kwargs)
                    
                    # Cache successful response
                    if cache_ttl > 0 and cache_key and 'error' not in response:
                        global_cache.set(cache_key, response, cache_ttl)
                    
                    # Record success in circuit breaker
                    circuit_breaker.record_success()
                    
                    return response
                    
                except requests.exceptions.Timeout:
                    logger.warning(f"Timeout error for {service_name} (attempt {retry_count+1}/{max_retries+1})")
                    last_exception = "Request timed out"
                    retry_count += 1
                    
                except requests.exceptions.ConnectionError:
                    logger.warning(f"Connection error for {service_name} (attempt {retry_count+1}/{max_retries+1})")
                    last_exception = "Connection error"
                    retry_count += 1
                    
                except requests.exceptions.HTTPError as e:
                    status_code = e.response.status_code if hasattr(e, 'response') else "unknown"
                    logger.warning(f"HTTP error {status_code} for {service_name} "
                                  f"(attempt {retry_count+1}/{max_retries+1})")
                    
                    # Don't retry client errors (4xx) except for 429 (Too Many Requests)
                    if hasattr(e, 'response') and 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                        circuit_breaker.record_failure()
                        return {
                            "error": f"Client error: {status_code}",
                            "status_code": status_code,
                            "data": {}
                        }
                    
                    # For 429 or 5xx errors, retry
                    last_exception = f"HTTP error: {status_code}"
                    retry_count += 1
                    
                except Exception as e:
                    logger.error(f"Unexpected error for {service_name}: {str(e)}")
                    last_exception = str(e)
                    retry_count += 1
            
            # All retries failed - record failure and return error
            circuit_breaker.record_failure()
            
            logger.error(f"Request to {service_name} failed after {max_retries + 1} attempts: {last_exception}")
            return {
                "error": last_exception,
                "max_retries_exceeded": True,
                "data": {}
            }
        
        return wrapper
    
    return decorator

def make_api_request(url, method='post', data=None, headers=None, timeout=30, **kwargs):
    """
    General purpose API request function with robust error handling
    
    Args:
        url (str): URL to request
        method (str): HTTP method (get, post, put, delete)
        data (dict): Request data/payload
        headers (dict): Request headers
        timeout (int): Request timeout in seconds
        **kwargs: Additional arguments to pass to requests
    
    Returns:
        dict: Response data or error information
    """
    try:
        # Default headers
        if headers is None:
            headers = {'Content-Type': 'application/json'}
        
        # Convert data to JSON if it's a dict
        json_data = None
        if data is not None and isinstance(data, dict):
            json_data = data
            data = None
        
        # Make the request
        method_func = getattr(requests, method.lower())
        response = method_func(
            url, 
            headers=headers,
            json=json_data,
            data=data,
            timeout=timeout,
            **kwargs
        )
        
        # Raise for status
        response.raise_for_status()
        
        # Parse response
        try:
            return response.json()
        except ValueError:
            # Not JSON - return text
            return {
                "text": response.text,
                "status_code": response.status_code
            }
            
    except requests.exceptions.RequestException as e:
        error_info = {
            "error": str(e),
            "url": url,
            "method": method,
        }
        
        # Add response info if available
        if hasattr(e, 'response') and e.response is not None:
            error_info["status_code"] = e.response.status_code
            try:
                error_info["response"] = e.response.json()
            except ValueError:
                error_info["response_text"] = e.response.text[:500]
        
        return error_info 