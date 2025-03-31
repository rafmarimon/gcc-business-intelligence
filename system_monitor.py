#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
System Health and Error Monitoring Tool

This script provides monitoring capabilities for the GCC Reports platform,
including error log analysis, system health checks, and alerts.
"""

import os
import sys
import json
import argparse
import logging
import time
import glob
import re
import smtplib
import socket
import platform
import subprocess
import psutil
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Any, Optional, Tuple, Set

# Ensure proper imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import required modules
try:
    from src.utils.redis_cache import RedisCache
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Error importing required modules: {str(e)}")
    print("Make sure you're running from the project root.")
    sys.exit(1)

# Load environment variables
load_dotenv()

# Configure logging
log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
os.makedirs(log_dir, exist_ok=True)

log_filename = os.path.join(log_dir, f'system_monitor_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class SystemMonitor:
    """Monitors system health and error logs."""
    
    def __init__(self):
        """Initialize the system monitor."""
        # Initialize Redis cache
        self.redis = RedisCache()
        
        # Set up logs directory
        self.logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs')
        
        # Email settings from environment variables
        self.email_enabled = os.environ.get('EMAIL_ALERTS_ENABLED', 'false').lower() == 'true'
        self.email_from = os.environ.get('EMAIL_FROM', '')
        self.email_to = os.environ.get('EMAIL_TO', '').split(',')
        self.email_server = os.environ.get('EMAIL_SERVER', 'localhost')
        self.email_port = int(os.environ.get('EMAIL_PORT', '25'))
        self.email_user = os.environ.get('EMAIL_USER', '')
        self.email_password = os.environ.get('EMAIL_PASSWORD', '')
        
        logger.info("System monitor initialized")
    
    def check_system_health(self) -> Dict[str, Any]:
        """
        Check overall system health.
        
        Returns:
            Dictionary with system health data
        """
        health_data = {
            'timestamp': datetime.now().isoformat(),
            'host': socket.gethostname(),
            'platform': platform.platform(),
            'cpu': {},
            'memory': {},
            'disk': {},
            'python': {},
            'redis': {},
            'processes': {},
            'services': {}
        }
        
        # CPU info
        cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
        health_data['cpu'] = {
            'usage_percent': psutil.cpu_percent(interval=1),
            'per_cpu_percent': cpu_percent,
            'count': psutil.cpu_count(),
            'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else None
        }
        
        # Memory info
        mem = psutil.virtual_memory()
        health_data['memory'] = {
            'total': mem.total,
            'available': mem.available,
            'used': mem.used,
            'percent': mem.percent
        }
        
        # Disk info
        disk = psutil.disk_usage('/')
        health_data['disk'] = {
            'total': disk.total,
            'used': disk.used,
            'free': disk.free,
            'percent': disk.percent
        }
        
        # Python info
        health_data['python'] = {
            'version': sys.version,
            'path': sys.executable,
            'is_64bit': sys.maxsize > 2**32
        }
        
        # Redis info
        try:
            redis_info = self.redis.info()
            health_data['redis'] = {
                'connected': True,
                'version': redis_info.get('redis_version', 'unknown'),
                'used_memory': redis_info.get('used_memory', 0),
                'used_memory_peak': redis_info.get('used_memory_peak', 0),
                'clients': redis_info.get('connected_clients', 0)
            }
        except Exception as e:
            health_data['redis'] = {
                'connected': False,
                'error': str(e)
            }
        
        # Process info - check for key processes
        report_processes = [p for p in psutil.process_iter(['pid', 'name', 'cmdline']) 
                          if any('report' in cmd.lower() for cmd in p.info['cmdline'] if cmd)]
        
        health_data['processes'] = {
            'report_processes': len(report_processes),
            'total_processes': len(list(psutil.process_iter()))
        }
        
        # Check key services
        services_to_check = ['redis', 'nginx', 'uwsgi']
        health_data['services'] = {}
        
        for service in services_to_check:
            try:
                # Check if service is running
                if platform.system() == 'Linux':
                    result = subprocess.run(['systemctl', 'is-active', service], 
                                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    health_data['services'][service] = result.stdout.decode().strip() == 'active'
                else:
                    # For non-Linux systems, check processes
                    health_data['services'][service] = any(service in p.name().lower() 
                                                         for p in psutil.process_iter(['name']))
            except Exception as e:
                health_data['services'][service] = False
        
        # Save health data to Redis
        key = f"system:health:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.redis.set(key, health_data, expire=86400*7)  # Keep for 7 days
        
        # Generate status summary
        status = 'healthy'
        warnings = []
        
        # Check for concerning values
        if health_data['cpu']['usage_percent'] > 90:
            status = 'warning'
            warnings.append(f"High CPU usage: {health_data['cpu']['usage_percent']}%")
        
        if health_data['memory']['percent'] > 90:
            status = 'warning'
            warnings.append(f"High memory usage: {health_data['memory']['percent']}%")
        
        if health_data['disk']['percent'] > 90:
            status = 'warning'
            warnings.append(f"Low disk space: {health_data['disk']['percent']}% used")
        
        if not health_data['redis']['connected']:
            status = 'critical'
            warnings.append(f"Redis connection error: {health_data['redis'].get('error', 'Unknown error')}")
        
        # Add status summary
        health_data['status'] = {
            'overall': status,
            'warnings': warnings
        }
        
        # Send alert if status is warning or critical
        if status in ['warning', 'critical'] and self.email_enabled:
            self._send_alert("System Health Warning", 
                          f"System health status: {status}\n\nWarnings:\n" + 
                          "\n".join(warnings))
        
        return health_data
    
    def analyze_logs(self, days: int = 1, error_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Analyze logs for errors.
        
        Args:
            days: Number of days back to analyze
            error_types: Optional list of error types to filter by
            
        Returns:
            Dictionary with log analysis data
        """
        # Calculate cutoff date
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Find log files
        log_files = glob.glob(os.path.join(self.logs_dir, '*.log'))
        
        # Filter out old files based on modification time
        recent_logs = [f for f in log_files 
                     if datetime.fromtimestamp(os.path.getmtime(f)) >= cutoff_date]
        
        # Default error types to look for
        if not error_types:
            error_types = ['ERROR', 'CRITICAL', 'EXCEPTION', 'FAIL', 'TIMEOUT']
        
        # Compile regex patterns
        patterns = [re.compile(rf'{error_type}', re.IGNORECASE) for error_type in error_types]
        
        # Store error information
        errors = []
        error_count = 0
        error_by_type = {}
        error_by_file = {}
        
        # Scan log files
        for log_file in recent_logs:
            file_errors = 0
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line_num, line in enumerate(f, 1):
                        for pattern in patterns:
                            if pattern.search(line):
                                # Extract timestamp if present
                                timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', line)
                                timestamp = timestamp_match.group(1) if timestamp_match else None
                                
                                # Determine error type
                                error_type = None
                                for et in error_types:
                                    if re.search(rf'{et}', line, re.IGNORECASE):
                                        error_type = et
                                        break
                                
                                # Create error record
                                error_record = {
                                    'file': os.path.basename(log_file),
                                    'line': line_num,
                                    'timestamp': timestamp,
                                    'type': error_type,
                                    'message': line.strip()
                                }
                                
                                errors.append(error_record)
                                error_count += 1
                                file_errors += 1
                                
                                # Update counts by type
                                if error_type:
                                    error_by_type[error_type] = error_by_type.get(error_type, 0) + 1
                                
                                # Only count first occurrence of each error
                                break
            
            except Exception as e:
                logger.error(f"Error analyzing log file {log_file}: {str(e)}")
            
            # Update counts by file
            if file_errors > 0:
                error_by_file[os.path.basename(log_file)] = file_errors
        
        # Prepare analysis results
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'days_analyzed': days,
            'logs_analyzed': len(recent_logs),
            'error_count': error_count,
            'error_by_type': error_by_type,
            'error_by_file': error_by_file,
            'errors': errors[:100]  # Limit to most recent 100 errors
        }
        
        # Save analysis to Redis
        key = f"logs:analysis:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.redis.set(key, analysis, expire=86400*7)  # Keep for 7 days
        
        # Send alert if there are many errors and alerts are enabled
        if error_count > 10 and self.email_enabled:
            self._send_alert(
                f"Log Analysis - {error_count} errors detected",
                f"Log analysis detected {error_count} errors in the past {days} days.\n\n" +
                f"Errors by type:\n" + 
                "\n".join([f"{t}: {c}" for t, c in error_by_type.items()]) +
                f"\n\nSee attached for details."
            )
        
        return analysis
    
    def monitor_report_generation(self) -> Dict[str, Any]:
        """
        Monitor report generation activity and success/failure rates.
        
        Returns:
            Dictionary with report generation statistics
        """
        # Look for generation logs
        generation_logs = glob.glob(os.path.join(self.logs_dir, '*generation*.log'))
        
        # Sort by modification time (newest first)
        generation_logs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Stats to collect
        stats = {
            'timestamp': datetime.now().isoformat(),
            'total_reports_found': 0,
            'successful_reports': 0,
            'failed_reports': 0,
            'reports_by_client': {},
            'recent_failures': [],
            'average_generation_time': 0,
            'generation_times': []
        }
        
        # Patterns to match
        success_pattern = re.compile(r'successfully generated', re.IGNORECASE)
        failure_pattern = re.compile(r'failed|error|exception', re.IGNORECASE)
        client_pattern = re.compile(r'client[: ]+([a-zA-Z0-9_]+)', re.IGNORECASE)
        time_pattern = re.compile(r'completed in (\d+\.?\d*) seconds', re.IGNORECASE)
        
        # Analyze logs
        total_time = 0
        times_count = 0
        
        for log_file in generation_logs[:10]:  # Limit to 10 most recent logs
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Find all successful generations
                    for match in success_pattern.finditer(content):
                        stats['total_reports_found'] += 1
                        stats['successful_reports'] += 1
                        
                        # Get client if mentioned
                        client_match = client_pattern.search(content[:match.start()])
                        if client_match:
                            client = client_match.group(1)
                            if client not in stats['reports_by_client']:
                                stats['reports_by_client'][client] = {'success': 0, 'failure': 0}
                            stats['reports_by_client'][client]['success'] += 1
                        
                        # Get generation time if mentioned
                        time_match = time_pattern.search(content[match.start():match.start()+200])
                        if time_match:
                            gen_time = float(time_match.group(1))
                            total_time += gen_time
                            times_count += 1
                            stats['generation_times'].append(gen_time)
                    
                    # Find all failed generations
                    for match in failure_pattern.finditer(content):
                        # Check if it's actually a failure message
                        line_start = content.rfind('\n', 0, match.start()) + 1
                        line_end = content.find('\n', match.start())
                        line = content[line_start:line_end]
                        
                        if 'error' in line.lower() or 'fail' in line.lower() or 'exception' in line.lower():
                            stats['total_reports_found'] += 1
                            stats['failed_reports'] += 1
                            
                            # Get client if mentioned
                            client_match = client_pattern.search(content[:match.start()])
                            if client_match:
                                client = client_match.group(1)
                                if client not in stats['reports_by_client']:
                                    stats['reports_by_client'][client] = {'success': 0, 'failure': 0}
                                stats['reports_by_client'][client]['failure'] += 1
                            
                            # Add to recent failures
                            context_start = max(0, line_start - 200)
                            context_end = min(len(content), line_end + 200)
                            context = content[context_start:context_end]
                            
                            stats['recent_failures'].append({
                                'timestamp': self._extract_timestamp(line),
                                'client': client_match.group(1) if client_match else 'unknown',
                                'message': line.strip(),
                                'context': context
                            })
                            
                            # Limit to 10 recent failures
                            if len(stats['recent_failures']) >= 10:
                                break
            
            except Exception as e:
                logger.error(f"Error analyzing generation log {log_file}: {str(e)}")
        
        # Calculate average generation time
        if times_count > 0:
            stats['average_generation_time'] = total_time / times_count
        
        # Save stats to Redis
        key = f"reports:generation:stats:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.redis.set(key, stats, expire=86400*7)  # Keep for 7 days
        
        # Send alert if failure rate is high
        if stats['total_reports_found'] > 0:
            failure_rate = stats['failed_reports'] / stats['total_reports_found']
            if failure_rate > 0.2 and self.email_enabled:  # Alert if more than 20% failures
                self._send_alert(
                    f"High Report Failure Rate: {failure_rate:.1%}",
                    f"Report generation is experiencing a high failure rate of {failure_rate:.1%}\n\n" +
                    f"Total reports: {stats['total_reports_found']}\n" +
                    f"Failed: {stats['failed_reports']}\n" +
                    f"Successful: {stats['successful_reports']}\n\n" +
                    "Recent failures:\n" +
                    "\n".join([f"- {f['client']}: {f['message']}" for f in stats['recent_failures']])
                )
        
        return stats
    
    def _extract_timestamp(self, text: str) -> Optional[str]:
        """Extract timestamp from log line."""
        timestamp_match = re.search(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})', text)
        if timestamp_match:
            return timestamp_match.group(1)
        return None
    
    def _send_alert(self, subject: str, message: str) -> bool:
        """Send email alert."""
        if not self.email_enabled or not self.email_from or not self.email_to:
            logger.warning("Email alerts disabled or not configured")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_from
            msg['To'] = ', '.join(self.email_to)
            msg['Subject'] = f"[GCC Reports Alert] {subject}"
            
            # Add timestamp to message
            full_message = f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            full_message += f"Server: {socket.gethostname()}\n\n"
            full_message += message
            
            msg.attach(MIMEText(full_message, 'plain'))
            
            # Connect to server
            if self.email_user and self.email_password:
                server = smtplib.SMTP(self.email_server, self.email_port)
                server.starttls()
                server.login(self.email_user, self.email_password)
            else:
                server = smtplib.SMTP(self.email_server, self.email_port)
            
            # Send email
            server.send_message(msg)
            server.quit()
            
            logger.info(f"Sent alert email: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending alert email: {str(e)}")
            return False
    
    def monitor_api_requests(self) -> Dict[str, Any]:
        """
        Monitor API request logs to track usage and errors.
        
        Returns:
            Dictionary with API request statistics
        """
        # Look for API logs
        api_logs = glob.glob(os.path.join(self.logs_dir, '*api*.log'))
        
        # Sort by modification time (newest first)
        api_logs.sort(key=lambda x: os.path.getmtime(x), reverse=True)
        
        # Stats to collect
        stats = {
            'timestamp': datetime.now().isoformat(),
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'requests_by_endpoint': {},
            'requests_by_status': {},
            'recent_errors': [],
            'recent_requests': []
        }
        
        # Patterns to match
        request_pattern = re.compile(r'(GET|POST|PUT|DELETE) ([^\s]+) .* status=(\d+) .*')
        
        # Analyze logs
        for log_file in api_logs[:5]:  # Limit to 5 most recent logs
            try:
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        # Look for API request lines
                        match = request_pattern.search(line)
                        if match:
                            method, endpoint, status = match.groups()
                            stats['total_requests'] += 1
                            
                            # Track by endpoint
                            endpoint_key = f"{method} {endpoint}"
                            if endpoint_key not in stats['requests_by_endpoint']:
                                stats['requests_by_endpoint'][endpoint_key] = {'count': 0, 'success': 0, 'failure': 0}
                            stats['requests_by_endpoint'][endpoint_key]['count'] += 1
                            
                            # Track by status code
                            if status not in stats['requests_by_status']:
                                stats['requests_by_status'][status] = 0
                            stats['requests_by_status'][status] += 1
                            
                            # Categorize as success or failure
                            if status.startswith('2'):  # 2xx status codes
                                stats['successful_requests'] += 1
                                stats['requests_by_endpoint'][endpoint_key]['success'] += 1
                            else:
                                stats['failed_requests'] += 1
                                stats['requests_by_endpoint'][endpoint_key]['failure'] += 1
                                
                                # Add to recent errors if it's an error
                                if status.startswith(('4', '5')):
                                    stats['recent_errors'].append({
                                        'timestamp': self._extract_timestamp(line),
                                        'method': method,
                                        'endpoint': endpoint,
                                        'status': status,
                                        'message': line.strip()
                                    })
                            
                            # Add to recent requests
                            stats['recent_requests'].append({
                                'timestamp': self._extract_timestamp(line),
                                'method': method,
                                'endpoint': endpoint,
                                'status': status
                            })
                            
                            # Limit collections
                            if len(stats['recent_errors']) > 10:
                                stats['recent_errors'] = stats['recent_errors'][-10:]
                            if len(stats['recent_requests']) > 20:
                                stats['recent_requests'] = stats['recent_requests'][-20:]
            
            except Exception as e:
                logger.error(f"Error analyzing API log {log_file}: {str(e)}")
        
        # Save stats to Redis
        key = f"api:request:stats:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.redis.set(key, stats, expire=86400*7)  # Keep for 7 days
        
        # Send alert if error rate is high
        if stats['total_requests'] > 10:  # Only if we have enough data
            error_rate = stats['failed_requests'] / stats['total_requests']
            if error_rate > 0.1 and self.email_enabled:  # Alert if more than 10% errors
                self._send_alert(
                    f"High API Error Rate: {error_rate:.1%}",
                    f"API is experiencing a high error rate of {error_rate:.1%}\n\n" +
                    f"Total requests: {stats['total_requests']}\n" +
                    f"Failed: {stats['failed_requests']}\n" +
                    f"Successful: {stats['successful_requests']}\n\n" +
                    "Recent errors:\n" +
                    "\n".join([f"- {e['method']} {e['endpoint']} ({e['status']})" for e in stats['recent_errors']])
                )
        
        return stats
    
    def run_full_check(self) -> Dict[str, Any]:
        """
        Run all monitoring checks and return combined results.
        
        Returns:
            Dictionary with all monitoring data
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'system_health': self.check_system_health(),
            'log_analysis': self.analyze_logs(days=1),
            'report_generation': self.monitor_report_generation(),
            'api_requests': self.monitor_api_requests()
        }
        
        # Determine overall status
        status = 'healthy'
        warnings = []
        
        # Check system health
        if results['system_health']['status']['overall'] in ['warning', 'critical']:
            status = results['system_health']['status']['overall']
            warnings.extend(results['system_health']['status']['warnings'])
        
        # Check log errors
        if results['log_analysis']['error_count'] > 10:
            if status != 'critical':
                status = 'warning'
            warnings.append(f"High error count in logs: {results['log_analysis']['error_count']}")
        
        # Check report generation
        if results['report_generation']['total_reports_found'] > 0:
            failure_rate = results['report_generation']['failed_reports'] / results['report_generation']['total_reports_found']
            if failure_rate > 0.2:
                if status != 'critical':
                    status = 'warning'
                warnings.append(f"High report failure rate: {failure_rate:.1%}")
        
        # Check API errors
        if results['api_requests']['total_requests'] > 10:
            error_rate = results['api_requests']['failed_requests'] / results['api_requests']['total_requests']
            if error_rate > 0.1:
                if status != 'critical':
                    status = 'warning'
                warnings.append(f"High API error rate: {error_rate:.1%}")
        
        # Add status summary
        results['status'] = {
            'overall': status,
            'warnings': warnings
        }
        
        # Save to Redis
        key = f"system:full_check:{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.redis.set(key, results, expire=86400*30)  # Keep for 30 days
        
        return results

def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(description='System Health and Error Monitoring Tool')
    
    # Command selection
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Check system health
    health_parser = subparsers.add_parser('health', help='Check system health')
    
    # Analyze logs
    logs_parser = subparsers.add_parser('logs', help='Analyze error logs')
    logs_parser.add_argument('--days', type=int, default=1, help='Number of days back to analyze')
    logs_parser.add_argument('--errors', help='Comma-separated list of error types to look for')
    
    # Monitor report generation
    reports_parser = subparsers.add_parser('reports', help='Monitor report generation')
    
    # Monitor API requests
    api_parser = subparsers.add_parser('api', help='Monitor API requests')
    
    # Run full check
    full_parser = subparsers.add_parser('full', help='Run full system check')
    
    # Daemon mode
    daemon_parser = subparsers.add_parser('daemon', help='Run in daemon mode with periodic checks')
    daemon_parser.add_argument('--interval', type=int, default=3600, help='Check interval in seconds')
    
    # Output options
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    args = parser.parse_args()
    
    # Initialize monitor
    monitor = SystemMonitor()
    
    # Execute command
    result = None
    
    if args.command == 'health':
        health_data = monitor.check_system_health()
        if args.json:
            result = health_data
        else:
            print(f"System Health Check - Status: {health_data['status']['overall']}")
            if health_data['status']['warnings']:
                print("\nWarnings:")
                for warning in health_data['status']['warnings']:
                    print(f"- {warning}")
            
            print("\nSystem Info:")
            print(f"Host: {health_data['host']}")
            print(f"Platform: {health_data['platform']}")
            
            print("\nResource Usage:")
            print(f"CPU: {health_data['cpu']['usage_percent']}%")
            print(f"Memory: {health_data['memory']['percent']}% ({health_data['memory']['used'] / (1024**3):.1f} GB / {health_data['memory']['total'] / (1024**3):.1f} GB)")
            print(f"Disk: {health_data['disk']['percent']}% ({health_data['disk']['used'] / (1024**3):.1f} GB / {health_data['disk']['total'] / (1024**3):.1f} GB)")
            
            print("\nServices:")
            for service, status in health_data['services'].items():
                print(f"{service}: {'Running' if status else 'Stopped'}")
    
    elif args.command == 'logs':
        error_types = args.errors.split(',') if args.errors else None
        log_data = monitor.analyze_logs(days=args.days, error_types=error_types)
        
        if args.json:
            result = log_data
        else:
            print(f"Log Analysis - {log_data['error_count']} errors found in {log_data['logs_analyzed']} log files")
            
            if log_data['error_by_type']:
                print("\nErrors by Type:")
                for error_type, count in log_data['error_by_type'].items():
                    print(f"- {error_type}: {count}")
            
            if log_data['error_by_file']:
                print("\nErrors by File:")
                for file, count in log_data['error_by_file'].items():
                    print(f"- {file}: {count}")
            
            if log_data['errors']:
                print("\nRecent Errors:")
                for i, error in enumerate(log_data['errors'][:10]):
                    print(f"{i+1}. {error['file']} (line {error['line']})")
                    print(f"   {error['message']}")
                    print()
    
    elif args.command == 'reports':
        report_data = monitor.monitor_report_generation()
        
        if args.json:
            result = report_data
        else:
            print(f"Report Generation Statistics")
            print(f"Total Reports: {report_data['total_reports_found']}")
            print(f"Successful: {report_data['successful_reports']}")
            print(f"Failed: {report_data['failed_reports']}")
            
            if report_data['total_reports_found'] > 0:
                success_rate = report_data['successful_reports'] / report_data['total_reports_found'] * 100
                print(f"Success Rate: {success_rate:.1f}%")
            
            if report_data['generation_times']:
                print(f"Average Generation Time: {report_data['average_generation_time']:.2f} seconds")
            
            if report_data['reports_by_client']:
                print("\nReports by Client:")
                for client, stats in report_data['reports_by_client'].items():
                    print(f"- {client}: {stats['success']} successful, {stats['failure']} failed")
            
            if report_data['recent_failures']:
                print("\nRecent Failures:")
                for i, failure in enumerate(report_data['recent_failures']):
                    print(f"{i+1}. Client: {failure['client']}")
                    print(f"   Message: {failure['message']}")
                    print()
    
    elif args.command == 'api':
        api_data = monitor.monitor_api_requests()
        
        if args.json:
            result = api_data
        else:
            print(f"API Request Statistics")
            print(f"Total Requests: {api_data['total_requests']}")
            print(f"Successful: {api_data['successful_requests']}")
            print(f"Failed: {api_data['failed_requests']}")
            
            if api_data['total_requests'] > 0:
                success_rate = api_data['successful_requests'] / api_data['total_requests'] * 100
                print(f"Success Rate: {success_rate:.1f}%")
            
            if api_data['requests_by_status']:
                print("\nRequests by Status:")
                for status, count in api_data['requests_by_status'].items():
                    print(f"- {status}: {count}")
            
            if api_data['requests_by_endpoint']:
                print("\nTop Endpoints:")
                sorted_endpoints = sorted(api_data['requests_by_endpoint'].items(), 
                                         key=lambda x: x[1]['count'], reverse=True)
                for endpoint, stats in sorted_endpoints[:5]:
                    print(f"- {endpoint}: {stats['count']} requests ({stats['success']} successful, {stats['failure']} failed)")
            
            if api_data['recent_errors']:
                print("\nRecent Errors:")
                for i, error in enumerate(api_data['recent_errors']):
                    print(f"{i+1}. {error['method']} {error['endpoint']} (Status {error['status']})")
                    if error['timestamp']:
                        print(f"   Time: {error['timestamp']}")
                    print()
    
    elif args.command == 'full':
        full_data = monitor.run_full_check()
        
        if args.json:
            result = full_data
        else:
            print(f"Full System Check - Status: {full_data['status']['overall']}")
            
            if full_data['status']['warnings']:
                print("\nWarnings:")
                for warning in full_data['status']['warnings']:
                    print(f"- {warning}")
            
            # System health summary
            health = full_data['system_health']
            print("\nSystem Health:")
            print(f"CPU: {health['cpu']['usage_percent']}%")
            print(f"Memory: {health['memory']['percent']}%")
            print(f"Disk: {health['disk']['percent']}%")
            
            # Log analysis summary
            logs = full_data['log_analysis']
            print("\nLog Analysis:")
            print(f"Errors: {logs['error_count']} in {logs['logs_analyzed']} log files")
            
            # Report generation summary
            reports = full_data['report_generation']
            print("\nReport Generation:")
            print(f"Total: {reports['total_reports_found']}")
            print(f"Success/Failure: {reports['successful_reports']}/{reports['failed_reports']}")
            
            # API requests summary
            api = full_data['api_requests']
            print("\nAPI Requests:")
            print(f"Total: {api['total_requests']}")
            print(f"Success/Failure: {api['successful_requests']}/{api['failed_requests']}")
    
    elif args.command == 'daemon':
        print(f"Starting system monitor daemon with {args.interval} second interval")
        print("Press Ctrl+C to stop")
        
        try:
            while True:
                print(f"\n[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Running system check...")
                full_data = monitor.run_full_check()
                
                print(f"Status: {full_data['status']['overall']}")
                if full_data['status']['warnings']:
                    print("Warnings:")
                    for warning in full_data['status']['warnings']:
                        print(f"- {warning}")
                
                # Sleep until next check
                print(f"Next check in {args.interval} seconds")
                time.sleep(args.interval)
        
        except KeyboardInterrupt:
            print("\nStopping daemon")
    
    else:
        parser.print_help()
        return 1
    
    # Output JSON if requested
    if args.json and result:
        print(json.dumps(result, indent=2))
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 