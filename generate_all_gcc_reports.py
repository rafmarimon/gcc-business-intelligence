#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Script to automatically generate GCC-focused market intelligence reports
for all clients. This script is designed to be run from a cron job.
"""

import os
import sys
import logging
import argparse
import time
from datetime import datetime
from typing import Dict, List, Any, Optional

# Ensure src directory is in the path for imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import required modules
try:
    from generate_client_reports import ClientReportGenerator
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

log_filename = os.path.join(log_dir, f'gcc_reports_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def generate_reports_for_all_clients(output_dir: str, skip_crawling: bool = False) -> Dict[str, Any]:
    """
    Generate GCC-focused reports for all clients.
    
    Args:
        output_dir: Directory to save reports
        skip_crawling: Whether to skip crawling and use cached data
        
    Returns:
        Dictionary with results for each client
    """
    logger.info("Starting GCC report generation for all clients")
    
    # Initialize Redis and client model
    redis_cache = RedisCache()
    client_model = ClientModel()
    
    # Get all clients
    clients = client_model.get_all_clients()
    logger.info(f"Found {len(clients)} clients")
    
    results = {}
    
    # Process each client
    for client in clients:
        client_name = client.get('name')
        client_id = client.get('id')
        
        if not client_name:
            logger.warning(f"Skipping client with ID {client_id} - no name found")
            continue
            
        logger.info(f"Generating GCC report for {client_name} (ID: {client_id})")
        
        try:
            # Create client-specific output directory
            client_output_dir = os.path.join(output_dir, client_name.lower().replace(' ', '_'))
            os.makedirs(client_output_dir, exist_ok=True)
            
            # Initialize report generator
            generator = ClientReportGenerator(
                reports_dir=client_output_dir,
                lookback_days=7,
                simulate_crawling=skip_crawling
            )
            
            # Generate the report
            start_time = time.time()
            md_path = generator.generate_client_report(client_name, output_format='both')
            end_time = time.time()
            
            if md_path and os.path.exists(md_path):
                # Check for PDF
                pdf_path = md_path.replace('.md', '.pdf')
                has_pdf = os.path.exists(pdf_path)
                
                results[client_id] = {
                    'client_name': client_name,
                    'success': True,
                    'md_path': md_path,
                    'pdf_path': pdf_path if has_pdf else None,
                    'generation_time': end_time - start_time,
                    'timestamp': datetime.now().isoformat()
                }
                
                logger.info(f"Successfully generated report for {client_name}")
                logger.info(f"  - Markdown: {md_path}")
                if has_pdf:
                    logger.info(f"  - PDF: {pdf_path}")
                logger.info(f"  - Time taken: {end_time - start_time:.2f} seconds")
            else:
                results[client_id] = {
                    'client_name': client_name,
                    'success': False,
                    'error': 'Failed to generate report file',
                    'timestamp': datetime.now().isoformat()
                }
                logger.error(f"Failed to generate report for {client_name}")
        
        except Exception as e:
            results[client_id] = {
                'client_name': client_name,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            logger.error(f"Error generating report for {client_name}: {str(e)}")
    
    # Summarize results
    success_count = sum(1 for r in results.values() if r.get('success', False))
    logger.info(f"Completed GCC report generation for all clients")
    logger.info(f"Successfully generated {success_count} out of {len(clients)} reports")
    
    return results

def main():
    """Run the report generation process."""
    parser = argparse.ArgumentParser(description='Generate GCC reports for all clients')
    parser.add_argument('--output-dir', type=str, default='reports/gcc', help='Directory to save reports')
    parser.add_argument('--skip-crawling', action='store_true', help='Skip crawling and use cached data')
    args = parser.parse_args()
    
    # Ensure output directory exists
    output_dir = os.path.abspath(args.output_dir)
    os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Starting automatic report generation")
    logger.info(f"Reports will be saved to: {output_dir}")
    
    try:
        # Generate reports for all clients
        results = generate_reports_for_all_clients(output_dir, args.skip_crawling)
        
        # Log summary
        success_count = sum(1 for r in results.values() if r.get('success', False))
        logger.info(f"Report generation complete: {success_count} successes, {len(results) - success_count} failures")
        
        # Return success if all reports were generated successfully
        return 0 if success_count == len(results) else 1
        
    except Exception as e:
        logger.error(f"Error during report generation: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 