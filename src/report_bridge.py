#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Report Bridge - Connects the simplified report generator with the API server and dashboard.
This allows the dashboard to use the simple, direct report generation approach while maintaining
access to old reports.
"""

import os
import sys
import json
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('report_bridge')

class ReportBridge:
    """
    Bridge between the simplified report generator and the API dashboard.
    """
    
    def __init__(self):
        """Initialize the bridge with paths to the simple generator and report directories."""
        # Get script directory
        self.base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # Define paths
        self.simple_generator_path = os.path.join(self.base_dir, 'generate_report.py')
        self.reports_dir = os.path.join(self.base_dir, 'reports')
        
        # Ensure the simple generator exists
        if not os.path.exists(self.simple_generator_path):
            logger.error(f"Simple report generator not found at {self.simple_generator_path}")
            raise FileNotFoundError(f"Simple report generator not found at {self.simple_generator_path}")
        
        # Ensure reports directory exists
        os.makedirs(self.reports_dir, exist_ok=True)
        
        logger.info(f"Report Bridge initialized. Simple generator: {self.simple_generator_path}")
        logger.info(f"Reports directory: {self.reports_dir}")
    
    def generate_report(self, client="general", frequency="weekly", skip_collection=False):
        """
        Generate a report using the simple generator.
        
        Args:
            client (str): Client name or ID
            frequency (str): Report frequency (daily, weekly, monthly)
            skip_collection (bool): If True, use existing data
        
        Returns:
            dict: Paths to the generated report files
        """
        logger.info(f"Generating report for client '{client}', frequency: {frequency}")
        
        # Build command to run simple generator
        cmd = [
            sys.executable,
            self.simple_generator_path,
            "--client", client,
            "--frequency", frequency
        ]
        
        # Execute the simple report generator
        try:
            logger.info(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd=self.base_dir
            )
            
            if result.returncode == 0:
                logger.info("Report generation completed successfully")
                
                # Parse the output to get report paths
                output = result.stdout
                
                # Extract paths from output
                md_path = None
                html_path = None
                pdf_path = None
                
                for line in output.splitlines():
                    if "Markdown:" in line:
                        md_path = line.split("Markdown:")[1].strip()
                    elif "HTML:" in line:
                        html_path = line.split("HTML:")[1].strip()
                    elif "PDF:" in line:
                        pdf_path = line.split("PDF:")[1].strip()
                
                # Verify the paths exist
                report_paths = {}
                if md_path and os.path.exists(md_path):
                    report_paths["markdown"] = md_path
                if html_path and os.path.exists(html_path):
                    report_paths["html"] = html_path
                if pdf_path and os.path.exists(pdf_path):
                    report_paths["pdf"] = pdf_path
                
                # Rename files to conform to expected dashboard naming conventions
                renamed_paths = self._rename_for_dashboard(report_paths, client, frequency)
                
                return {
                    "success": True,
                    "message": "Report generated successfully",
                    "paths": renamed_paths
                }
            else:
                logger.error(f"Report generation failed: {result.stderr}")
                return {
                    "success": False,
                    "message": f"Report generation failed: {result.stderr}",
                    "paths": {}
                }
                
        except Exception as e:
            logger.error(f"Error generating report: {e}")
            return {
                "success": False,
                "message": f"Error generating report: {str(e)}",
                "paths": {}
            }
    
    def _rename_for_dashboard(self, report_paths, client, frequency):
        """
        Rename report files to match dashboard expectations.
        
        Args:
            report_paths (dict): Original report paths
            client (str): Client name or ID
            frequency (str): Report frequency
        
        Returns:
            dict: Updated paths
        """
        renamed_paths = {}
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        try:
            client_dir = os.path.join(self.reports_dir, client.lower().replace(" ", "_"), frequency)
            os.makedirs(client_dir, exist_ok=True)
            
            # Process each report type
            for report_type, original_path in report_paths.items():
                if not original_path or not os.path.exists(original_path):
                    continue
                
                # Define new filename with consolidated_ prefix
                extension = os.path.splitext(original_path)[1]
                new_filename = f"consolidated_report_{timestamp}{extension}"
                new_path = os.path.join(client_dir, new_filename)
                
                # Copy the file to the new location
                import shutil
                shutil.copy2(original_path, new_path)
                logger.info(f"Copied {original_path} to {new_path}")
                
                # Store the new path
                renamed_paths[report_type] = new_path
            
            return renamed_paths
            
        except Exception as e:
            logger.error(f"Error renaming files: {e}")
            return report_paths  # Return original paths on error
    
    def list_available_reports(self, client="general", frequency="weekly", limit=10):
        """
        List available reports for a specific client and frequency.
        
        Args:
            client (str): Client name or ID
            frequency (str): Report frequency
            limit (int): Maximum number of reports to return
        
        Returns:
            list: List of report information
        """
        try:
            client_dir = os.path.join(self.reports_dir, client.lower().replace(" ", "_"), frequency)
            
            if not os.path.exists(client_dir):
                logger.warning(f"No reports found for client '{client}' with frequency '{frequency}'")
                return []
            
            # Find all report files
            report_files = []
            for file in os.listdir(client_dir):
                if file.startswith("consolidated_report_") and (file.endswith(".md") or file.endswith(".html")):
                    report_path = os.path.join(client_dir, file)
                    report_files.append((report_path, os.path.getmtime(report_path)))
            
            # Sort by modification time (newest first)
            report_files.sort(key=lambda x: x[1], reverse=True)
            
            # Limit number of reports
            report_files = report_files[:limit]
            
            # Build report info
            reports = []
            for report_path, mtime in report_files:
                if report_path.endswith('.md'):
                    # Extract timestamp from filename
                    filename = os.path.basename(report_path)
                    timestamp = filename.replace("consolidated_report_", "").replace(".md", "")
                    
                    # Parse timestamp
                    try:
                        date_obj = datetime.strptime(timestamp, '%Y%m%d_%H%M%S')
                        formatted_date = date_obj.strftime('%B %d, %Y')
                        formatted_time = date_obj.strftime('%I:%M %p')
                    except:
                        formatted_date = "Unknown Date"
                        formatted_time = "Unknown Time"
                        date_obj = datetime.fromtimestamp(mtime)
                    
                    # Get HTML and PDF paths
                    html_path = report_path.replace('.md', '.html')
                    pdf_path = report_path.replace('.md', '.pdf')
                    
                    # Get relative paths for URLs
                    relative_dir = os.path.relpath(os.path.dirname(report_path), self.reports_dir)
                    
                    # Read the first 200 characters for description
                    description = ""
                    try:
                        with open(report_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            # Skip headers and get content
                            parts = content.split('---', 2)
                            if len(parts) > 2:
                                actual_content = parts[2]
                            else:
                                actual_content = content
                            description = actual_content.strip()[:200] + "..."
                    except:
                        description = f"{frequency.capitalize()} business intelligence report for {client}"
                    
                    # Create report info
                    report_info = {
                        "title": f"Business Intelligence Report - {formatted_date}",
                        "client": client,
                        "frequency": frequency,
                        "date": date_obj.isoformat(),
                        "formatted_date": formatted_date,
                        "formatted_time": formatted_time,
                        "timestamp": timestamp,
                        "description": description,
                        "md_url": f"/reports/{relative_dir}/{os.path.basename(report_path)}",
                        "html_url": f"/reports/{relative_dir}/{os.path.basename(html_path)}",
                        "pdf_url": f"/reports/{relative_dir}/{os.path.basename(pdf_path)}"
                    }
                    
                    reports.append(report_info)
            
            return reports
            
        except Exception as e:
            logger.error(f"Error listing reports: {e}")
            return []

# Create a singleton instance for the API to use
report_bridge = ReportBridge()

def generate_report(client="general", frequency="weekly", skip_collection=False):
    """Wrapper function for the API server to use."""
    return report_bridge.generate_report(client, frequency, skip_collection)

def list_reports(client="general", frequency="weekly", limit=10):
    """Wrapper function for the API server to use."""
    return report_bridge.list_available_reports(client, frequency, limit)

if __name__ == "__main__":
    # Simple test
    bridge = ReportBridge()
    result = bridge.generate_report()
    print(f"Generation result: {result['success']}")
    if result['success']:
        print(f"Report paths: {result['paths']}")
    
    # List reports
    reports = bridge.list_available_reports()
    print(f"Found {len(reports)} reports") 