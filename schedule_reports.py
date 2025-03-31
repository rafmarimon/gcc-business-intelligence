#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Report Scheduler

This script manages automated report scheduling, allowing reports to be generated
on specific dates or recurring intervals for clients.
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timedelta
import time
import threading
import signal
import schedule
from typing import Dict, List, Any, Optional, Callable

# Ensure proper imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import required modules
try:
    from src.models.client_model import ClientModel
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

log_filename = os.path.join(log_dir, f'scheduler_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ReportScheduler:
    """Manages scheduling of automated reports."""
    
    def __init__(self):
        """Initialize the report scheduler."""
        # Initialize Redis cache
        self.redis = RedisCache()
        
        # Initialize client model
        self.client_model = ClientModel()
        
        # Initialize schedule
        self.scheduler = schedule
        
        # Flag to control the scheduler loop
        self.keep_running = True
        
        # Define supported frequencies
        self.frequencies = {
            'daily': self.scheduler.every().day,
            'weekly': self.scheduler.every().week,
            'biweekly': self.scheduler.every(2).weeks,
            'monthly': self.scheduler.every(4).weeks
        }
        
        # Load existing schedules
        self._load_schedules()
        
        logger.info("Report scheduler initialized")
    
    def _load_schedules(self):
        """Load existing schedules from Redis."""
        schedule_keys = self.redis.scan('report_schedule:*')
        
        for key in schedule_keys:
            schedule_data = self.redis.get(key)
            if schedule_data:
                self._schedule_report(schedule_data)
    
    def _schedule_report(self, schedule_data: Dict[str, Any]) -> bool:
        """Schedule a report based on schedule data."""
        client_id = schedule_data.get('client_id')
        frequency = schedule_data.get('frequency')
        
        if not client_id or not frequency:
            logger.error("Missing required fields in schedule data")
            return False
        
        # Check if client exists
        client = self.client_model.get_client_by_id(client_id)
        if not client:
            logger.error(f"Client not found: {client_id}")
            return False
        
        # Create job function that will generate the report
        def job():
            logger.info(f"Generating scheduled report for client {client_id}")
            try:
                # Import here to avoid circular imports
                from generate_client_reports import generate_client_report
                
                output_dir = os.environ.get('REPORTS_DIR', 'reports')
                output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_dir)
                
                # Generate report
                skip_crawling = schedule_data.get('use_cached_data', False)
                report_path = generate_client_report(client_id, output_path, skip_crawling)
                
                # Update last run time
                schedule_data['last_run'] = datetime.now().isoformat()
                self.redis.set(f"report_schedule:{client_id}", schedule_data)
                
                logger.info(f"Scheduled report generated for client {client_id}: {report_path}")
                
                # Record in report history
                self._record_report_generation(client_id, report_path, 'scheduled')
                
                return report_path
            except Exception as e:
                logger.error(f"Error generating scheduled report for client {client_id}: {str(e)}")
                return None
        
        # Schedule based on frequency
        if frequency == 'daily':
            at_time = schedule_data.get('at_time', '00:00')
            self.scheduler.every().day.at(at_time).do(job).tag(f"client_{client_id}")
        
        elif frequency == 'weekly':
            day = schedule_data.get('day', 'monday')
            at_time = schedule_data.get('at_time', '00:00')
            getattr(self.scheduler.every(), day).at(at_time).do(job).tag(f"client_{client_id}")
        
        elif frequency == 'biweekly':
            day = schedule_data.get('day', 'monday')
            at_time = schedule_data.get('at_time', '00:00')
            getattr(self.scheduler.every(2).weeks, day).at(at_time).do(job).tag(f"client_{client_id}")
        
        elif frequency == 'monthly':
            # For monthly, we use the day of month
            day_of_month = schedule_data.get('day_of_month', 1)
            at_time = schedule_data.get('at_time', '00:00')
            
            # Create a custom monthly job
            def monthly_job():
                # Check if today is the day of the month we want
                if datetime.now().day == day_of_month:
                    job()
            
            self.scheduler.every().day.at(at_time).do(monthly_job).tag(f"client_{client_id}")
        
        elif frequency == 'once':
            # One-time schedule
            scheduled_date = schedule_data.get('scheduled_date')
            at_time = schedule_data.get('at_time', '00:00')
            
            if not scheduled_date:
                logger.error("Missing scheduled_date for one-time schedule")
                return False
            
            # Parse date
            try:
                date_obj = datetime.fromisoformat(scheduled_date)
                
                # If date is in the past, don't schedule
                if date_obj < datetime.now():
                    logger.warning(f"Scheduled date is in the past: {scheduled_date}")
                    return False
                
                # Calculate seconds until scheduled time
                now = datetime.now()
                time_parts = at_time.split(':')
                target_time = now.replace(
                    year=date_obj.year,
                    month=date_obj.month,
                    day=date_obj.day,
                    hour=int(time_parts[0]),
                    minute=int(time_parts[1]),
                    second=0
                )
                
                seconds_until = (target_time - now).total_seconds()
                if seconds_until > 0:
                    # Schedule the job to run once after the calculated delay
                    self.scheduler.every(seconds_until).seconds.do(job).tag(f"client_{client_id}_once")
                else:
                    logger.warning(f"Scheduled time is in the past: {scheduled_date} {at_time}")
                    return False
                
            except ValueError as e:
                logger.error(f"Invalid date format: {scheduled_date}")
                return False
        
        else:
            logger.error(f"Unsupported frequency: {frequency}")
            return False
        
        logger.info(f"Scheduled report for client {client_id} with frequency {frequency}")
        return True
    
    def _record_report_generation(self, client_id: str, report_path: str, trigger_type: str):
        """Record a report generation in history."""
        history_key = f"client:{client_id}:report_history"
        history = self.redis.get(history_key) or []
        
        history.append({
            'timestamp': datetime.now().isoformat(),
            'report_path': report_path,
            'trigger_type': trigger_type
        })
        
        # Keep only the last 100 entries
        if len(history) > 100:
            history = history[-100:]
        
        self.redis.set(history_key, history)
    
    def schedule_report(self, client_id: str, frequency: str, **kwargs) -> bool:
        """
        Schedule a report for a client.
        
        Args:
            client_id: Client ID
            frequency: Frequency (daily, weekly, biweekly, monthly, once)
            **kwargs: Additional parameters depending on frequency
                - at_time: Time of day to run (HH:MM)
                - day: Day of week for weekly/biweekly (monday, tuesday, etc.)
                - day_of_month: Day of month for monthly (1-31)
                - scheduled_date: ISO date for one-time schedule (YYYY-MM-DD)
                - use_cached_data: Whether to use cached data instead of crawling
        
        Returns:
            True if scheduled successfully, False otherwise
        """
        # Check if client exists
        client = self.client_model.get_client_by_id(client_id)
        if not client:
            logger.error(f"Client not found: {client_id}")
            return False
        
        # Validate frequency
        valid_frequencies = ['daily', 'weekly', 'biweekly', 'monthly', 'once']
        if frequency not in valid_frequencies:
            logger.error(f"Invalid frequency: {frequency}")
            return False
        
        # Clear existing schedules for this client
        self.clear_schedule(client_id)
        
        # Create schedule data
        schedule_data = {
            'client_id': client_id,
            'frequency': frequency,
            'created_at': datetime.now().isoformat(),
            'created_by': kwargs.get('created_by', 'system')
        }
        
        # Add frequency-specific parameters
        if frequency in ['daily', 'weekly', 'biweekly', 'monthly']:
            schedule_data['at_time'] = kwargs.get('at_time', '00:00')
        
        if frequency in ['weekly', 'biweekly']:
            schedule_data['day'] = kwargs.get('day', 'monday')
        
        if frequency == 'monthly':
            schedule_data['day_of_month'] = kwargs.get('day_of_month', 1)
        
        if frequency == 'once':
            schedule_data['scheduled_date'] = kwargs.get('scheduled_date')
            if not schedule_data['scheduled_date']:
                logger.error("Missing scheduled_date for one-time schedule")
                return False
        
        # Optional parameters
        schedule_data['use_cached_data'] = kwargs.get('use_cached_data', False)
        
        # Save to Redis
        self.redis.set(f"report_schedule:{client_id}", schedule_data)
        
        # Schedule the report
        result = self._schedule_report(schedule_data)
        
        return result
    
    def clear_schedule(self, client_id: str) -> bool:
        """Clear all schedules for a client."""
        # Clear from schedule
        self.scheduler.clear(f"client_{client_id}")
        self.scheduler.clear(f"client_{client_id}_once")
        
        # Clear from Redis
        self.redis.delete(f"report_schedule:{client_id}")
        
        logger.info(f"Cleared schedule for client {client_id}")
        return True
    
    def get_schedule(self, client_id: str) -> Optional[Dict[str, Any]]:
        """Get the schedule for a client."""
        return self.redis.get(f"report_schedule:{client_id}")
    
    def list_schedules(self) -> List[Dict[str, Any]]:
        """List all schedules."""
        schedule_keys = self.redis.scan('report_schedule:*')
        
        schedules = []
        for key in schedule_keys:
            schedule_data = self.redis.get(key)
            if schedule_data:
                # Get client name
                client_id = schedule_data.get('client_id')
                client = self.client_model.get_client_by_id(client_id)
                if client:
                    schedule_data['client_name'] = client.get('name')
                schedules.append(schedule_data)
        
        return schedules
    
    def get_report_history(self, client_id: str) -> List[Dict[str, Any]]:
        """Get report generation history for a client."""
        return self.redis.get(f"client:{client_id}:report_history") or []
    
    def run(self):
        """Run the scheduler loop."""
        logger.info("Starting scheduler loop")
        
        # Set up signal handlers
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)
        
        # Run the scheduler in a separate thread
        scheduler_thread = threading.Thread(target=self._run_scheduler)
        scheduler_thread.daemon = True
        scheduler_thread.start()
        
        try:
            # Keep the main thread alive
            while self.keep_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received, shutting down...")
            self.keep_running = False
        
        logger.info("Scheduler loop stopped")
    
    def _run_scheduler(self):
        """Run the scheduler loop in a separate thread."""
        while self.keep_running:
            self.scheduler.run_pending()
            time.sleep(1)
    
    def _handle_signal(self, signum, frame):
        """Handle signals to gracefully shut down."""
        logger.info(f"Signal {signum} received, shutting down...")
        self.keep_running = False
    
    def generate_report_now(self, client_id: str, use_cached_data: bool = False) -> Optional[str]:
        """Generate a report immediately for a client."""
        # Check if client exists
        client = self.client_model.get_client_by_id(client_id)
        if not client:
            logger.error(f"Client not found: {client_id}")
            return None
        
        logger.info(f"Generating immediate report for client {client_id}")
        try:
            # Import here to avoid circular imports
            from generate_client_reports import generate_client_report
            
            output_dir = os.environ.get('REPORTS_DIR', 'reports')
            output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), output_dir)
            
            # Generate report
            report_path = generate_client_report(client_id, output_path, use_cached_data)
            
            logger.info(f"Immediate report generated for client {client_id}: {report_path}")
            
            # Record in report history
            self._record_report_generation(client_id, report_path, 'manual')
            
            return report_path
        except Exception as e:
            logger.error(f"Error generating immediate report for client {client_id}: {str(e)}")
            return None

def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(description='Report Scheduler')
    
    # Command selection
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Schedule a report
    schedule_parser = subparsers.add_parser('schedule', help='Schedule a report')
    schedule_parser.add_argument('client_id', help='Client ID')
    schedule_parser.add_argument('frequency', choices=['daily', 'weekly', 'biweekly', 'monthly', 'once'], help='Schedule frequency')
    schedule_parser.add_argument('--at-time', help='Time of day to run (HH:MM)')
    schedule_parser.add_argument('--day', choices=['monday', 'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday'], help='Day of week for weekly/biweekly')
    schedule_parser.add_argument('--day-of-month', type=int, help='Day of month for monthly (1-31)')
    schedule_parser.add_argument('--scheduled-date', help='ISO date for one-time schedule (YYYY-MM-DD)')
    schedule_parser.add_argument('--use-cached-data', action='store_true', help='Use cached data instead of crawling')
    schedule_parser.add_argument('--created-by', help='User who created the schedule')
    
    # Clear a schedule
    clear_parser = subparsers.add_parser('clear', help='Clear a schedule')
    clear_parser.add_argument('client_id', help='Client ID')
    
    # Get a schedule
    get_parser = subparsers.add_parser('get', help='Get a schedule')
    get_parser.add_argument('client_id', help='Client ID')
    
    # List all schedules
    list_parser = subparsers.add_parser('list', help='List all schedules')
    
    # Get report history
    history_parser = subparsers.add_parser('history', help='Get report history')
    history_parser.add_argument('client_id', help='Client ID')
    
    # Generate a report now
    generate_parser = subparsers.add_parser('generate', help='Generate a report now')
    generate_parser.add_argument('client_id', help='Client ID')
    generate_parser.add_argument('--use-cached-data', action='store_true', help='Use cached data instead of crawling')
    
    # Run the scheduler loop
    run_parser = subparsers.add_parser('run', help='Run the scheduler loop')
    
    # Output options
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    args = parser.parse_args()
    
    # Initialize scheduler
    scheduler = ReportScheduler()
    
    # Execute command
    result = None
    
    if args.command == 'schedule':
        # Collect kwargs
        kwargs = {
            'at_time': args.at_time,
            'day': args.day,
            'day_of_month': args.day_of_month,
            'scheduled_date': args.scheduled_date,
            'use_cached_data': args.use_cached_data,
            'created_by': args.created_by
        }
        
        # Remove None values
        kwargs = {k: v for k, v in kwargs.items() if v is not None}
        
        success = scheduler.schedule_report(args.client_id, args.frequency, **kwargs)
        if success:
            if args.json:
                result = {'client_id': args.client_id, 'frequency': args.frequency, 'success': True}
            else:
                print(f"Scheduled report for client {args.client_id} with frequency {args.frequency}")
        else:
            print(f"Error scheduling report for client {args.client_id}")
            return 1
    
    elif args.command == 'clear':
        success = scheduler.clear_schedule(args.client_id)
        if success:
            if args.json:
                result = {'client_id': args.client_id, 'success': True}
            else:
                print(f"Cleared schedule for client {args.client_id}")
        else:
            print(f"Error clearing schedule for client {args.client_id}")
            return 1
    
    elif args.command == 'get':
        schedule_data = scheduler.get_schedule(args.client_id)
        if schedule_data:
            if args.json:
                result = schedule_data
            else:
                print(f"Schedule for client {args.client_id}:")
                print(f"  Frequency: {schedule_data.get('frequency')}")
                if schedule_data.get('at_time'):
                    print(f"  Time: {schedule_data.get('at_time')}")
                if schedule_data.get('day'):
                    print(f"  Day: {schedule_data.get('day')}")
                if schedule_data.get('day_of_month'):
                    print(f"  Day of month: {schedule_data.get('day_of_month')}")
                if schedule_data.get('scheduled_date'):
                    print(f"  Scheduled date: {schedule_data.get('scheduled_date')}")
                print(f"  Use cached data: {schedule_data.get('use_cached_data', False)}")
                print(f"  Created at: {schedule_data.get('created_at')}")
                print(f"  Created by: {schedule_data.get('created_by', 'system')}")
                if schedule_data.get('last_run'):
                    print(f"  Last run: {schedule_data.get('last_run')}")
        else:
            print(f"No schedule found for client {args.client_id}")
            if args.json:
                result = {'client_id': args.client_id, 'schedule': None}
    
    elif args.command == 'list':
        schedules = scheduler.list_schedules()
        if args.json:
            result = {'schedules': schedules}
        else:
            print(f"Found {len(schedules)} schedules:")
            for schedule in schedules:
                client_name = schedule.get('client_name', 'Unknown')
                client_id = schedule.get('client_id')
                frequency = schedule.get('frequency')
                
                print(f"  {client_name} ({client_id}): {frequency}")
                if schedule.get('at_time'):
                    print(f"    Time: {schedule.get('at_time')}")
                if schedule.get('day'):
                    print(f"    Day: {schedule.get('day')}")
                if schedule.get('day_of_month'):
                    print(f"    Day of month: {schedule.get('day_of_month')}")
                if schedule.get('scheduled_date'):
                    print(f"    Scheduled date: {schedule.get('scheduled_date')}")
                if schedule.get('last_run'):
                    print(f"    Last run: {schedule.get('last_run')}")
                print()
    
    elif args.command == 'history':
        history = scheduler.get_report_history(args.client_id)
        if args.json:
            result = {'client_id': args.client_id, 'history': history}
        else:
            client = scheduler.client_model.get_client_by_id(args.client_id)
            client_name = client.get('name', 'Unknown') if client else 'Unknown'
            
            print(f"Report history for client {client_name} ({args.client_id}):")
            if history:
                for entry in history:
                    timestamp = entry.get('timestamp', 'Unknown')
                    report_path = entry.get('report_path', 'Unknown')
                    trigger_type = entry.get('trigger_type', 'Unknown')
                    
                    print(f"  {timestamp}: {report_path} ({trigger_type})")
            else:
                print("  No reports generated yet")
    
    elif args.command == 'generate':
        report_path = scheduler.generate_report_now(args.client_id, args.use_cached_data)
        if report_path:
            if args.json:
                result = {'client_id': args.client_id, 'report_path': report_path, 'success': True}
            else:
                print(f"Generated report for client {args.client_id}")
                print(f"Report path: {report_path}")
        else:
            print(f"Error generating report for client {args.client_id}")
            return 1
    
    elif args.command == 'run':
        print("Starting scheduler loop. Press Ctrl+C to stop.")
        scheduler.run()
    
    else:
        parser.print_help()
        return 1
    
    # Output JSON if requested
    if args.json and result:
        print(json.dumps(result, indent=2))
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 