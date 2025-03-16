#!/usr/bin/env python3
"""
Global Possibilities - UAE/GCC Business Intelligence Platform
Scheduler Script

This script sets up automated execution of the business intelligence 
platform on a daily schedule (at midnight UAE time).
"""

import os
import sys
import time
import logging
import schedule
import subprocess
from datetime import datetime
from dotenv import load_dotenv
import signal
import threading

# Add the src directory to the path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment variables
load_dotenv()

# Configure logging
log_dir = 'logs'
os.makedirs(log_dir, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(log_dir, f'scheduler_{datetime.now().strftime("%Y%m%d")}.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("scheduler")

# Flag to control the scheduler loop
running = True

def run_job():
    """Run the daily business intelligence process."""
    logger.info("Starting scheduled job")
    try:
        # Get the path to the virtual environment python
        if os.name == 'nt':  # Windows
            python_exec = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'Scripts', 'python.exe')
        else:  # Unix/Linux/Mac
            python_exec = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'venv', 'bin', 'python')
        
        # Check if python executable exists
        if not os.path.exists(python_exec):
            logger.error(f"Python executable not found at {python_exec}")
            python_exec = sys.executable
            logger.info(f"Using system Python: {python_exec}")
        
        # Get the path to the manual_run.py script
        script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'manual_run.py')
        
        # Run the process
        start_time = datetime.now()
        logger.info(f"Running manual_run.py at {start_time}")
        
        result = subprocess.run(
            [python_exec, script_path, '--no-browser'],
            capture_output=True,
            text=True
        )
        
        # Log the output
        if result.stdout:
            logger.info(f"Output: {result.stdout}")
        if result.stderr:
            logger.error(f"Error: {result.stderr}")
        
        end_time = datetime.now()
        duration = end_time - start_time
        
        if result.returncode == 0:
            logger.info(f"Job completed successfully in {duration}")
        else:
            logger.error(f"Job failed with return code {result.returncode} after {duration}")
        
        return result.returncode
    
    except Exception as e:
        logger.error(f"Error running scheduled job: {e}", exc_info=True)
        return 1

def run_test_job():
    """Run a test job to verify scheduler is working."""
    logger.info("Running test job")
    print("\n" + "="*80)
    print(" "*30 + "TEST JOB EXECUTED" + " "*30)
    print("="*80)
    print("\nScheduler is working correctly!")
    print(f"The main job will run daily at the scheduled time: {schedule_time}")
    print("\nYou can keep this script running or set it up as a service.")
    print("="*80 + "\n")
    
    # Remove the test job
    return schedule.CancelJob

def signal_handler(sig, frame):
    """Handle termination signals."""
    global running
    logger.info(f"Received signal {sig}, shutting down...")
    running = False
    sys.exit(0)

def main():
    """Set up and run the scheduler."""
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Print banner
    print("\n" + "="*80)
    print(" "*20 + "Global Possibilities - Business Intelligence Scheduler" + " "*20)
    print("="*80 + "\n")
    
    # Get schedule from environment or use default (midnight UAE time)
    schedule_time = os.getenv('SCHEDULE_TIME', '00:00')  # Default: midnight
    
    logger.info(f"Setting up scheduler to run daily at {schedule_time} (UAE time)")
    
    # Schedule the job to run every day
    schedule.every().day.at(schedule_time).do(run_job)
    
    # Also schedule a test job in 5 seconds for verification
    test_job_time = datetime.now()
    test_job_time = test_job_time.replace(second=test_job_time.second + 5)
    test_job_time_str = test_job_time.strftime("%H:%M:%S")
    
    schedule.every().day.at(test_job_time_str).do(run_test_job)
    
    logger.info(f"Scheduler started. Next job will run at {schedule.next_run()}")
    print(f"Scheduler is running. Next job at {schedule.next_run()}")
    print(f"Running test job in 5 seconds...")
    
    # Loop until interrupted
    while running:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    main() 