#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Setup Cron Jobs

This script sets up cron jobs for automatic execution of platform tasks,
such as article summarization, report generation, and data crawling.
"""

import argparse
import logging
import os
import subprocess
import sys
from crontab import CronTab
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_project_root():
    """Get the absolute path to the project root directory."""
    # Assuming this script is in src/utils
    current_dir = Path(__file__).parent
    project_root = current_dir.parent.parent.absolute()
    return str(project_root)

def get_python_executable():
    """Get the path to the current Python executable."""
    return sys.executable

def setup_summarize_cron(interval='hourly', limit=20):
    """
    Set up a cron job for automatic article summarization.
    
    Args:
        interval: Frequency of execution (hourly, daily)
        limit: Maximum number of articles to summarize per run
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get project root and Python executable
        project_root = get_project_root()
        python_exe = get_python_executable()
        
        # Create the command
        command = f"cd {project_root} && {python_exe} -m src.main summarize --limit {limit}"
        
        # Get the current user's crontab
        cron = CronTab(user=True)
        
        # Check if the job already exists
        job_exists = False
        for job in cron:
            if "src.main summarize" in str(job):
                job_exists = True
                logger.info("Summarize cron job already exists.")
                break
        
        if not job_exists:
            # Create a new job
            job = cron.new(command=command)
            
            # Set the schedule based on interval
            if interval == 'hourly':
                job.every(1).hours()
            elif interval == 'daily':
                job.hour.on(2)  # Run at 2 AM
            elif interval == 'weekly':
                job.hour.on(3)  # Run at 3 AM
                job.dow.on(0)   # Run on Sunday
            
            # Write the crontab
            cron.write()
            
            logger.info(f"Summarize cron job set up successfully (interval: {interval}, limit: {limit}).")
            logger.info(f"Command: {command}")
            
        return True
    
    except Exception as e:
        logger.error(f"Error setting up summarize cron job: {str(e)}")
        return False

def setup_reports_cron():
    """
    Set up cron jobs for automatic report generation.
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get project root and Python executable
        project_root = get_project_root()
        python_exe = get_python_executable()
        
        # Create the command to list clients
        list_cmd = f"cd {project_root} && {python_exe} -m src.main client --list"
        
        # Get list of clients
        client_list = []
        try:
            result = subprocess.run(list_cmd, shell=True, capture_output=True, text=True)
            
            # Parse client IDs from output (assuming format: "- ID: client-xxx, Name: Client Name")
            for line in result.stdout.splitlines():
                if line.startswith("- ID:"):
                    client_id = line.split(",")[0].replace("- ID:", "").strip()
                    client_list.append(client_id)
        except Exception as e:
            logger.warning(f"Failed to get client list, using generic client IDs: {str(e)}")
            # Use fallback client IDs
            client_list = ["all-clients"]
        
        # Get the current user's crontab
        cron = CronTab(user=True)
        
        # Check if jobs already exist
        jobs_exist = False
        for job in cron:
            if "src.main report" in str(job):
                jobs_exist = True
                logger.info("Report cron jobs already exist.")
                break
        
        if not jobs_exist and client_list:
            # Daily reports
            for client_id in client_list:
                command = f"cd {project_root} && {python_exe} -m src.main report --client-id {client_id} --type daily"
                job = cron.new(command=command)
                job.hour.on(6)  # Run at 6 AM
                
            # Weekly reports (Sunday)
            for client_id in client_list:
                command = f"cd {project_root} && {python_exe} -m src.main report --client-id {client_id} --type weekly"
                job = cron.new(command=command)
                job.hour.on(7)  # Run at 7 AM
                job.dow.on(0)   # Run on Sunday
            
            # Write the crontab
            cron.write()
            
            logger.info(f"Report cron jobs set up successfully for {len(client_list)} clients.")
            
        return True
    
    except Exception as e:
        logger.error(f"Error setting up report cron jobs: {str(e)}")
        return False

def setup_crawl_cron(interval='hourly'):
    """
    Set up a cron job for automatic data crawling.
    
    Args:
        interval: Frequency of execution (hourly, daily)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        # Get project root and Python executable
        project_root = get_project_root()
        python_exe = get_python_executable()
        
        # Create the command
        command = f"cd {project_root} && {python_exe} -m src.main crawl --all"
        
        # Get the current user's crontab
        cron = CronTab(user=True)
        
        # Check if the job already exists
        job_exists = False
        for job in cron:
            if "src.main crawl --all" in str(job):
                job_exists = True
                logger.info("Crawl cron job already exists.")
                break
        
        if not job_exists:
            # Create a new job
            job = cron.new(command=command)
            
            # Set the schedule based on interval
            if interval == 'hourly':
                job.every(1).hours()
            elif interval == 'daily':
                job.hour.on(1)  # Run at 1 AM
            
            # Write the crontab
            cron.write()
            
            logger.info(f"Crawl cron job set up successfully (interval: {interval}).")
            logger.info(f"Command: {command}")
            
        return True
    
    except Exception as e:
        logger.error(f"Error setting up crawl cron job: {str(e)}")
        return False

def parse_arguments():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(description='Set up cron jobs for Market Intelligence Platform')
    
    parser.add_argument('--task', choices=['summarize', 'report', 'crawl', 'all'], 
                        default='all', help='Task to schedule (default: all)')
    parser.add_argument('--interval', choices=['hourly', 'daily', 'weekly'], 
                        default='hourly', help='Job interval (default: hourly)')
    parser.add_argument('--limit', type=int, default=20, 
                        help='Article limit for summarization (default: 20)')
    
    return parser.parse_args()

def main():
    """Main entry point."""
    args = parse_arguments()
    
    task = args.task
    interval = args.interval
    limit = args.limit
    
    success = True
    
    if task in ['summarize', 'all']:
        success = success and setup_summarize_cron(interval, limit)
    
    if task in ['report', 'all']:
        success = success and setup_reports_cron()
    
    if task in ['crawl', 'all']:
        success = success and setup_crawl_cron(interval)
    
    if success:
        logger.info("All cron jobs set up successfully.")
    else:
        logger.error("Failed to set up some cron jobs. Check the logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main() 