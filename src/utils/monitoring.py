#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
API Monitoring and Metrics

This module provides utilities for monitoring API performance and health
using Prometheus metrics.
"""

import time
import logging
import functools
import threading
import os
from typing import Dict, Callable, Any, Optional, List

# Use Prometheus client if available, otherwise create stubs
try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False
    logging.warning("Prometheus client not available. Using stub metrics.")
    
    # Create stub classes for metrics
    class Counter:
        def __init__(self, name, documentation, labelnames=None):
            self.name = name
            self.documentation = documentation
            self.labelnames = labelnames or []
            self._values = {}
        
        def inc(self, amount=1, **labels):
            key = tuple(sorted(labels.items()))
            if key not in self._values:
                self._values[key] = 0
            self._values[key] += amount
            
        def labels(self, **kwargs):
            return self
    
    class Histogram:
        def __init__(self, name, documentation, buckets=None, labelnames=None):
            self.name = name
            self.documentation = documentation
            self.buckets = buckets or [0.1, 0.5, 1.0, 5.0]
            self.labelnames = labelnames or []
            self._values = {}
        
        def observe(self, amount, **labels):
            key = tuple(sorted(labels.items()))
            if key not in self._values:
                self._values[key] = []
            self._values[key].append(amount)
            
        def labels(self, **kwargs):
            return self
            
        def time(self):
            start = time.time()
            def observer():
                self.observe(time.time() - start)
            return observer
    
    class Gauge:
        def __init__(self, name, documentation, labelnames=None):
            self.name = name
            self.documentation = documentation
            self.labelnames = labelnames or []
            self._values = {}
        
        def set(self, value, **labels):
            key = tuple(sorted(labels.items()))
            self._values[key] = value
            
        def inc(self, amount=1, **labels):
            key = tuple(sorted(labels.items()))
            if key not in self._values:
                self._values[key] = 0
            self._values[key] += amount
            
        def dec(self, amount=1, **labels):
            key = tuple(sorted(labels.items()))
            if key not in self._values:
                self._values[key] = 0
            self._values[key] -= amount
            
        def labels(self, **kwargs):
            return self
    
    def start_http_server(port):
        logging.info(f"Stub Prometheus server would start on port {port}")

# Configure logging
logger = logging.getLogger(__name__)

# Define metrics
API_REQUESTS = Counter(
    'api_requests_total',
    'Total count of API requests',
    ['method', 'endpoint', 'status']
)

API_REQUEST_DURATION = Histogram(
    'api_request_duration_seconds',
    'Duration of API requests in seconds',
    buckets=[0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    labelnames=['method', 'endpoint']
)

API_ERRORS = Counter(
    'api_errors_total',
    'Total count of API errors',
    ['method', 'endpoint', 'error_type']
)

CACHE_HITS = Counter(
    'cache_hits_total',
    'Total count of cache hits',
    ['cache_name']
)

CACHE_MISSES = Counter(
    'cache_misses_total',
    'Total count of cache misses',
    ['cache_name']
)

ACTIVE_REQUESTS = Gauge(
    'api_active_requests',
    'Number of active API requests',
    ['method']
)

API_RATE_LIMIT_REACHED = Counter(
    'api_rate_limit_reached_total',
    'Total count of API rate limit reached',
    ['endpoint']
)

API_CIRCUIT_BREAKER_TRIPS = Counter(
    'api_circuit_breaker_trips_total',
    'Total count of API circuit breaker trips',
    ['endpoint']
)

class ApiMetrics:
    """
    API metrics collection and monitoring
    """
    
    def __init__(self, app_name: str = "gcc_business_intelligence"):
        """
        Initialize API metrics
        
        Args:
            app_name: Name of the application
        """
        self.app_name = app_name
        self._started = False
        self._lock = threading.Lock()
        
        # Start metrics server if configured
        metrics_port = int(os.environ.get('METRICS_PORT', 9090))
        if PROMETHEUS_AVAILABLE and os.environ.get('ENABLE_METRICS', 'true').lower() == 'true':
            self.start_metrics_server(metrics_port)
    
    def start_metrics_server(self, port: int = 9090) -> bool:
        """
        Start Prometheus metrics server
        
        Args:
            port: Port to expose metrics on
            
        Returns:
            Success status
        """
        with self._lock:
            if self._started:
                return True
                
            try:
                start_http_server(port)
                self._started = True
                logger.info(f"Started Prometheus metrics server on port {port}")
                return True
            except Exception as e:
                logger.error(f"Failed to start Prometheus metrics server: {e}")
                return False
    
    def track_request(self, method: str, endpoint: str, status_code: int, duration: float):
        """
        Track an API request
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            status_code: HTTP status code
            duration: Request duration in seconds
        """
        API_REQUESTS.labels(method=method, endpoint=endpoint, status=str(status_code)).inc()
        API_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)
        
        if status_code >= 400:
            error_type = 'client_error' if status_code < 500 else 'server_error'
            API_ERRORS.labels(method=method, endpoint=endpoint, error_type=error_type).inc()
    
    def track_error(self, method: str, endpoint: str, error_type: str):
        """
        Track an API error
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            error_type: Type of error
        """
        API_ERRORS.labels(method=method, endpoint=endpoint, error_type=error_type).inc()
    
    def track_cache(self, cache_name: str, hit: bool):
        """
        Track a cache hit or miss
        
        Args:
            cache_name: Name of the cache
            hit: Whether it was a hit or miss
        """
        if hit:
            CACHE_HITS.labels(cache_name=cache_name).inc()
        else:
            CACHE_MISSES.labels(cache_name=cache_name).inc()
    
    def track_rate_limit(self, endpoint: str):
        """
        Track a rate limit being reached
        
        Args:
            endpoint: API endpoint
        """
        API_RATE_LIMIT_REACHED.labels(endpoint=endpoint).inc()
    
    def track_circuit_breaker(self, endpoint: str):
        """
        Track a circuit breaker trip
        
        Args:
            endpoint: API endpoint
        """
        API_CIRCUIT_BREAKER_TRIPS.labels(endpoint=endpoint).inc()
    
    def measure_request(self, method: str, endpoint: str) -> Callable:
        """
        Create a context manager to measure request duration
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            
        Returns:
            Context manager
        """
        class RequestMetrics:
            def __init__(self, metrics, method, endpoint):
                self.metrics = metrics
                self.method = method
                self.endpoint = endpoint
                self.start_time = None
            
            def __enter__(self):
                self.start_time = time.time()
                ACTIVE_REQUESTS.labels(method=self.method).inc()
                return self
            
            def __exit__(self, exc_type, exc_val, exc_tb):
                duration = time.time() - self.start_time
                ACTIVE_REQUESTS.labels(method=self.method).dec()
                
                if exc_type is not None:
                    # There was an exception
                    self.metrics.track_error(self.method, self.endpoint, exc_type.__name__)
                    return False
                
                # Success case will be tracked separately with status code
                return True
        
        return RequestMetrics(self, method, endpoint)


# Create a default instance
metrics = ApiMetrics()


def monitor_api_call(endpoint: Optional[str] = None):
    """
    Decorator for monitoring API calls
    
    Args:
        endpoint: API endpoint (optional, will use function name if not provided)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            method = kwargs.get('method', 'GET')
            actual_endpoint = endpoint or func.__name__
            
            with metrics.measure_request(method, actual_endpoint):
                try:
                    result = func(*args, **kwargs)
                    
                    # Extract status code from response if available
                    status_code = 200
                    if hasattr(result, 'status_code'):
                        status_code = result.status_code
                    elif isinstance(result, dict) and 'status_code' in result:
                        status_code = result['status_code']
                    
                    duration = time.time() - wrapper.start_time
                    metrics.track_request(method, actual_endpoint, status_code, duration)
                    
                    return result
                    
                except Exception as e:
                    metrics.track_error(method, actual_endpoint, type(e).__name__)
                    raise
                    
            return result
            
        wrapper.start_time = time.time()
        return wrapper
        
    return decorator


def monitor_flask_app(app):
    """
    Setup monitoring for a Flask application
    
    Args:
        app: Flask application
        
    Returns:
        The app with monitoring enabled
    """
    if not hasattr(app, 'before_request'):
        logger.warning("Not a Flask app, monitoring not enabled")
        return app
        
    @app.before_request
    def before_request():
        from flask import request, g
        g.start_time = time.time()
        ACTIVE_REQUESTS.labels(method=request.method).inc()
        
    @app.after_request
    def after_request(response):
        from flask import request, g
        duration = time.time() - g.start_time
        ACTIVE_REQUESTS.labels(method=request.method).dec()
        
        # Skip metrics endpoints and static files
        if not request.path.startswith('/metrics') and not request.path.startswith('/static'):
            endpoint = request.endpoint or request.path
            metrics.track_request(request.method, endpoint, response.status_code, duration)
            
        return response
        
    return app


def health_check() -> Dict[str, Any]:
    """
    Perform a health check
    
    Returns:
        Health status
    """
    import psutil
    
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        'status': 'ok',
        'timestamp': time.time(),
        'memory': {
            'total': memory.total,
            'available': memory.available,
            'percent': memory.percent
        },
        'disk': {
            'total': disk.total,
            'free': disk.free,
            'percent': disk.percent
        },
        'metrics_enabled': PROMETHEUS_AVAILABLE
    } 