#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Redis Cache Utility Module - Provides Redis-based caching for:
- API responses
- Expensive database queries
- Generated reports and analytics data
- Session management
"""

import os
import json
import time
import logging
from typing import Any, Optional, Union, Dict
import hashlib
import pickle
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

try:
    import redis
    from redis.exceptions import RedisError
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis package not installed. Using fallback in-memory cache.")
    REDIS_AVAILABLE = False

# Fallback in-memory cache for when Redis is not available
class InMemoryCache:
    """Simple in-memory cache as fallback when Redis is unavailable"""
    
    def __init__(self):
        self.cache = {}
        self.expires = {}
        self.cache_dir = os.path.join(os.getcwd(), 'data', 'cache')
        
        # Ensure cache directory exists
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
            
        # Load cache from disk if it exists
        self._load_from_disk()
        
        logger.info(f"Initialized InMemoryCache with persistence at {self.cache_dir}")
    
    def _load_from_disk(self):
        """Load cache data from disk"""
        cache_file = os.path.join(self.cache_dir, 'cache.json')
        expires_file = os.path.join(self.cache_dir, 'expires.json')
        
        try:
            if os.path.exists(cache_file):
                with open(cache_file, 'r') as f:
                    self.cache = json.load(f)
                logger.info(f"Loaded {len(self.cache)} keys from disk cache")
            
            if os.path.exists(expires_file):
                with open(expires_file, 'r') as f:
                    # Convert string keys back to numbers
                    expires_data = json.load(f)
                    self.expires = {k: float(v) for k, v in expires_data.items()}
        except Exception as e:
            logger.error(f"Error loading cache from disk: {str(e)}")
    
    def _save_to_disk(self):
        """Save cache data to disk"""
        cache_file = os.path.join(self.cache_dir, 'cache.json')
        expires_file = os.path.join(self.cache_dir, 'expires.json')
        
        try:
            with open(cache_file, 'w') as f:
                json.dump(self.cache, f)
            
            with open(expires_file, 'w') as f:
                json.dump(self.expires, f)
        except Exception as e:
            logger.error(f"Error saving cache to disk: {str(e)}")
    
    def set(self, key: str, value: Any, expire: Optional[int] = None) -> bool:
        """Set a value in the cache with optional expiration time"""
        self.cache[key] = value
        
        if expire:
            self.expires[key] = time.time() + expire
        
        # Save to disk after update
        self._save_to_disk()
        
        return True
    
    def get(self, key: str) -> Any:
        """Get a value from the cache if it exists and is not expired"""
        if key in self.cache:
            # Check if expired
            if key in self.expires and time.time() > self.expires[key]:
                # Expired, remove and return None
                del self.cache[key]
                del self.expires[key]
                return None
            
            return self.cache[key]
        
        return None
    
    def delete(self, key: str) -> bool:
        """Delete a key from the cache"""
        if key in self.cache:
            del self.cache[key]
            if key in self.expires:
                del self.expires[key]
            
            # Save changes to disk
            self._save_to_disk()
            
            return True
        
        return False
    
    def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired"""
        if key in self.cache:
            if key in self.expires and time.time() > self.expires[key]:
                # Expired, remove and return False
                del self.cache[key]
                del self.expires[key]
                return False
            
            return True
        
        return False
    
    def flush(self) -> bool:
        """Clear the entire cache"""
        self.cache = {}
        self.expires = {}
        
        # Save empty cache to disk
        self._save_to_disk()
        
        return True
    
    def scan(self, cursor: int, match_pattern: str, count: int) -> tuple:
        """
        Scan for keys matching a pattern.
        
        Args:
            cursor: Scan cursor (ignored in this implementation)
            match_pattern: Pattern to match
            count: Maximum number of keys to return (ignored in this implementation)
            
        Returns:
            Tuple of (next_cursor, list_of_keys)
        """
        import fnmatch
        
        # Filter keys based on pattern
        matched_keys = []
        for key in self.cache.keys():
            if fnmatch.fnmatch(key, match_pattern):
                matched_keys.append(key)
                
        # This is a simple implementation that returns all matches at once
        return (0, matched_keys)

class RedisCache:
    """Redis-based caching utility for the GCC Business Intelligence platform.
    
    This class provides caching functionality for API responses, 
    generated content, and other data that benefits from caching.
    """
    
    def __init__(self):
        """Initialize Redis connection from environment variables.
        
        Falls back to in-memory cache if Redis connection fails.
        """
        self.redis_enabled = True
        self.connected = False
        self.in_memory_cache = None
        
        try:
            # Get Redis connection parameters from environment variables
            redis_host = os.getenv('REDIS_HOST')
            redis_port = int(os.getenv('REDIS_PORT', '6379'))
            redis_user = os.getenv('REDIS_USERNAME')
            redis_password = os.getenv('REDIS_PASSWORD')
            redis_db = int(os.getenv('REDIS_DB', '0'))
            
            # Try to connect to Redis Cloud
            try:
                # Only include username and password if they are provided
                connection_params = {
                    "host": redis_host,
                    "port": redis_port,
                    "decode_responses": True,
                    "db": redis_db,
                    "socket_timeout": 5.0,
                    "socket_connect_timeout": 5.0,
                }
                
                # Add credentials only if both username and password are provided
                if redis_user and redis_password:
                    connection_params["username"] = redis_user
                    connection_params["password"] = redis_password
                
                self.redis = redis.Redis(**connection_params)
                
                # Test connection
                self.redis.ping()
                self.connected = True
                logger.info(f"Connected to Redis at {redis_host}:{redis_port}")
            except Exception as cloud_error:
                # If Redis Cloud connection fails, try connecting to localhost without authentication
                logger.warning(f"Redis connection failed: {str(cloud_error)}. Using in-memory cache.")
                self.redis_enabled = False
                self.in_memory_cache = InMemoryCache()
            
        except Exception as e:
            logger.error(f"Redis connection initialization error: {str(e)}. Using in-memory cache.")
            self.redis_enabled = False
            self.in_memory_cache = InMemoryCache()
    
    def set(self, key, value, expiry=86400):
        """Set a value in the cache with an optional expiry (default 24 hours).
        
        Args:
            key: The cache key
            value: The value to cache (will be JSON serialized if not a string)
            expiry: Time in seconds until the key expires (default: 24 hours)
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Convert non-string values to JSON
            if not isinstance(value, str):
                value = json.dumps(value)
                
            if self.redis_enabled and self.connected:
                return self.redis.setex(key, expiry, value)
            else:
                self.in_memory_cache.cache[key] = {
                    'value': value,
                    'expiry': time.time() + expiry
                }
                return True
        except Exception as e:
            logger.error(f"Error setting cache key '{key}': {str(e)}")
            return False
    
    def get(self, key):
        """Get a value from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            The cached value or None if not found or expired
        """
        try:
            if self.redis_enabled and self.connected:
                value = self.redis.get(key)
                if not value:
                    return None
            else:
                # Check in-memory cache
                if key not in self.in_memory_cache.cache:
                    return None
                    
                # Check if expired
                if time.time() > self.in_memory_cache.cache[key]['expiry']:
                    del self.in_memory_cache.cache[key]
                    return None
                    
                value = self.in_memory_cache.cache[key]['value']
            
            # Try to parse as JSON
            try:
                return json.loads(value)
            except:
                # Return as is if not valid JSON
                return value
                
        except Exception as e:
            logger.error(f"Error getting cache key '{key}': {str(e)}")
            return None
    
    def delete(self, key):
        """Delete a key from the cache.
        
        Args:
            key: The cache key
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.redis_enabled and self.connected:
                return bool(self.redis.delete(key))
            else:
                if key in self.in_memory_cache.cache:
                    del self.in_memory_cache.cache[key]
                    return True
                return False
        except Exception as e:
            logger.error(f"Error deleting cache key '{key}': {str(e)}")
            return False
    
    def exists(self, key):
        """Check if a key exists in the cache.
        
        Args:
            key: The cache key
            
        Returns:
            bool: True if the key exists, False otherwise
        """
        try:
            if self.redis_enabled and self.connected:
                return bool(self.redis.exists(key))
            else:
                if key not in self.in_memory_cache.cache:
                    return False
                    
                # Check if expired
                if time.time() > self.in_memory_cache.cache[key]['expiry']:
                    del self.in_memory_cache.cache[key]
                    return False
                    
                return True
        except Exception as e:
            logger.error(f"Error checking if cache key '{key}' exists: {str(e)}")
            return False
    
    def flush(self):
        """Clear the entire cache.
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            if self.redis_enabled and self.connected:
                self.redis.flushdb()
            else:
                self.in_memory_cache.cache = {}
            return True
        except Exception as e:
            logger.error(f"Error flushing cache: {str(e)}")
            return False
    
    def increment(self, key, amount=1):
        """Increment a counter in the cache.
        
        Args:
            key: The cache key
            amount: The amount to increment by (default: 1)
            
        Returns:
            int: The new value or None if failed
        """
        try:
            if self.redis_enabled and self.connected:
                return self.redis.incrby(key, amount)
            else:
                # Check if key exists and is a number
                if key in self.in_memory_cache.cache and self.in_memory_cache.cache[key]['value'].isdigit():
                    value = int(self.in_memory_cache.cache[key]['value']) + amount
                    self.in_memory_cache.cache[key]['value'] = str(value)
                    return value
                else:
                    # Initialize with amount
                    self.in_memory_cache.cache[key] = {
                        'value': str(amount),
                        'expiry': time.time() + 86400  # Default 24 hour expiry
                    }
                    return amount
        except Exception as e:
            logger.error(f"Error incrementing cache key '{key}': {str(e)}")
            return None

# Singleton instance for use throughout the application
cache = RedisCache()

# Create a singleton instance for global usage
_cache_instance = None

def get_cache(cache_prefix: str = "gcc_bi", 
             redis_url: Optional[str] = None,
             reset: bool = False) -> RedisCache:
    """
    Get the global cache instance
    
    Args:
        cache_prefix: Prefix for all keys to avoid collisions
        redis_url: Redis connection URL (defaults to REDIS_URL env var)
        reset: Whether to reset the cache instance
        
    Returns:
        RedisCache instance
    """
    global _cache_instance
    
    if _cache_instance is None or reset:
        _cache_instance = RedisCache()
    
    return _cache_instance


def cache_key_from_args(*args, **kwargs) -> str:
    """
    Generate a cache key based on function arguments
    
    Args:
        *args: Positional arguments
        **kwargs: Keyword arguments
        
    Returns:
        str: Cache key
    """
    # Create a deterministic string representation of args and kwargs
    key_parts = [str(arg) for arg in args]
    key_parts.extend([f"{k}:{v}" for k, v in sorted(kwargs.items())])
    
    # Join all parts with a separator
    key_str = ":".join(key_parts)
    
    # Hash for shorter keys
    return hashlib.md5(key_str.encode()).hexdigest()


def cached(expire: int = 3600, prefix: str = ""):
    """
    Decorator to cache function results
    
    Args:
        expire: Expiration time in seconds
        prefix: Optional prefix for the cache key
        
    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # Get function name for the cache key
            func_name = func.__name__
            
            # Generate cache key
            if prefix:
                key = f"{prefix}:{func_name}:{cache_key_from_args(*args, **kwargs)}"
            else:
                key = f"{func_name}:{cache_key_from_args(*args, **kwargs)}"
            
            # Get global cache instance
            cache = get_cache()
            
            # Try to get from cache
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result
            
            # Call the function and cache the result
            result = func(*args, **kwargs)
            cache.set(key, result, expire)
            
            return result
        
        return wrapper
    
    return decorator 

def get_redis_cache():
    """Get the Redis cache singleton instance.
    
    Returns:
        RedisCache: A Redis cache instance
    """
    return get_cache() 