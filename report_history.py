#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Report History Manager

This script provides functionality to access, search, and download historical
reports. It allows users to view a complete archive of reports by client,
date, or content, and to compare reports over time.
"""

import os
import sys
import json
import argparse
import logging
import shutil
from datetime import datetime, timedelta
import re
import glob
from typing import Dict, List, Any, Optional, Tuple
import difflib

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

log_filename = os.path.join(log_dir, f'report_history_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ReportHistoryManager:
    """Manages access to historical reports."""
    
    def __init__(self):
        """Initialize the report history manager."""
        # Initialize Redis cache
        self.redis = RedisCache()
        
        # Initialize client model
        self.client_model = ClientModel()
        
        # Set up reports directory
        reports_dir = os.environ.get('REPORTS_DIR', 'reports')
        self.reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), reports_dir))
        
        # Set up archive directory
        archive_dir = os.environ.get('ARCHIVE_DIR', 'archive')
        self.archive_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), archive_dir))
        
        # Create directories if they don't exist
        os.makedirs(self.reports_dir, exist_ok=True)
        os.makedirs(self.archive_dir, exist_ok=True)
        
        logger.info("Report history manager initialized")
    
    def _get_report_metadata(self, report_path: str) -> Dict[str, Any]:
        """Extract metadata from a report file path."""
        # Extract client ID, timestamp, and format from file path
        try:
            # Expected format: reports/client_id/YYYYMMDD_HHMMSS_report.html
            parts = os.path.normpath(report_path).split(os.path.sep)
            
            # Get filename and client ID
            filename = os.path.basename(report_path)
            client_id = parts[-2] if len(parts) >= 2 else "unknown"
            
            # Parse timestamp from filename
            timestamp_match = re.search(r'(\d{8}_\d{6})', filename)
            timestamp = timestamp_match.group(1) if timestamp_match else None
            
            # Parse format from filename extension
            _, ext = os.path.splitext(filename)
            report_format = ext[1:] if ext else "unknown"
            
            # If it's a markdown file, check for YAML front matter
            metadata = {}
            if report_format == 'md':
                try:
                    with open(report_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                        # Check for YAML front matter
                        if content.startswith('---'):
                            end_marker = content.find('---', 3)
                            if end_marker > 0:
                                front_matter = content[3:end_marker].strip()
                                
                                # Parse simple key-value pairs
                                for line in front_matter.split('\n'):
                                    if ':' in line:
                                        key, value = line.split(':', 1)
                                        metadata[key.strip()] = value.strip()
                except Exception as e:
                    logger.warning(f"Error parsing front matter from {report_path}: {str(e)}")
            
            # Try to get client name
            client = self.client_model.get_client_by_id(client_id)
            client_name = client.get('name') if client else "Unknown Client"
            
            # Create metadata
            result = {
                'client_id': client_id,
                'client_name': client_name,
                'timestamp': timestamp,
                'format': report_format,
                'file_path': report_path,
                'file_size': os.path.getsize(report_path),
                'last_modified': datetime.fromtimestamp(os.path.getmtime(report_path)).isoformat()
            }
            
            # Add any additional metadata from front matter
            result.update(metadata)
            
            return result
        
        except Exception as e:
            logger.error(f"Error extracting metadata from {report_path}: {str(e)}")
            return {
                'file_path': report_path,
                'error': str(e)
            }
    
    def _search_report_content(self, report_path: str, search_term: str) -> Tuple[bool, List[str]]:
        """Search for content within a report file."""
        try:
            # Get file extension
            _, ext = os.path.splitext(report_path)
            ext = ext[1:].lower()
            
            # Only search text-based formats
            if ext in ['html', 'md', 'txt', 'json']:
                with open(report_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                    # Check if search term is in content
                    if search_term.lower() in content.lower():
                        # Find matching lines
                        matches = []
                        lines = content.split('\n')
                        for i, line in enumerate(lines):
                            if search_term.lower() in line.lower():
                                # Add line number and content
                                context_start = max(0, i - 1)
                                context_end = min(len(lines), i + 2)
                                
                                # Create context snippet
                                snippet = '\n'.join([
                                    f"{j+1}: {lines[j]}" 
                                    for j in range(context_start, context_end)
                                ])
                                
                                matches.append(snippet)
                                
                                # Limit to 5 matches to avoid overwhelming output
                                if len(matches) >= 5:
                                    break
                        
                        return True, matches
            
            return False, []
        
        except Exception as e:
            logger.error(f"Error searching content in {report_path}: {str(e)}")
            return False, []
    
    def list_reports(self, client_id: Optional[str] = None, days: Optional[int] = None, 
                     start_date: Optional[str] = None, end_date: Optional[str] = None,
                     format_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List reports with optional filtering.
        
        Args:
            client_id: Optional client ID to filter by
            days: Optional number of days back to include
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            format_type: Optional format type (html, md, pdf, etc.)
            
        Returns:
            List of report metadata
        """
        reports = []
        
        # Define search pattern
        if client_id:
            search_pattern = os.path.join(self.reports_dir, client_id, '*')
        else:
            search_pattern = os.path.join(self.reports_dir, '*', '*')
        
        # Get all report files
        report_files = glob.glob(search_pattern)
        
        # Add archived reports if they exist
        if client_id:
            archive_pattern = os.path.join(self.archive_dir, client_id, '*')
        else:
            archive_pattern = os.path.join(self.archive_dir, '*', '*')
        
        archived_files = glob.glob(archive_pattern)
        all_files = report_files + archived_files
        
        # Process each file
        for file_path in all_files:
            # Skip directories
            if os.path.isdir(file_path):
                continue
            
            # Get metadata
            metadata = self._get_report_metadata(file_path)
            
            # Skip if metadata extraction failed
            if 'error' in metadata:
                continue
            
            # Apply filters
            
            # Format filter
            if format_type and metadata.get('format') != format_type:
                continue
            
            # Date filters
            if days or start_date or end_date:
                # Convert timestamp to datetime
                if metadata.get('timestamp'):
                    try:
                        timestamp_str = metadata.get('timestamp')
                        file_date = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    except (ValueError, TypeError):
                        # If timestamp parsing fails, use last modified date
                        file_date = datetime.fromisoformat(metadata.get('last_modified'))
                else:
                    # Use last modified date if no timestamp
                    file_date = datetime.fromisoformat(metadata.get('last_modified'))
                
                # Check days filter
                if days:
                    cutoff_date = datetime.now() - timedelta(days=days)
                    if file_date < cutoff_date:
                        continue
                
                # Check start date filter
                if start_date:
                    try:
                        start = datetime.strptime(start_date, '%Y-%m-%d')
                        if file_date < start:
                            continue
                    except ValueError:
                        logger.warning(f"Invalid start_date format: {start_date}")
                
                # Check end date filter
                if end_date:
                    try:
                        end = datetime.strptime(end_date, '%Y-%m-%d')
                        end = end.replace(hour=23, minute=59, second=59)  # End of day
                        if file_date > end:
                            continue
                    except ValueError:
                        logger.warning(f"Invalid end_date format: {end_date}")
            
            # Add to results
            reports.append(metadata)
        
        # Sort by timestamp (newest first)
        reports.sort(key=lambda x: x.get('last_modified', ''), reverse=True)
        
        return reports
    
    def search_reports(self, search_term: str, client_id: Optional[str] = None, 
                       days: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Search for reports containing a specific term.
        
        Args:
            search_term: Term to search for
            client_id: Optional client ID to filter by
            days: Optional number of days back to include
            
        Returns:
            List of matching report metadata with context
        """
        # First get reports matching the filter criteria
        reports = self.list_reports(client_id=client_id, days=days)
        
        results = []
        for report in reports:
            file_path = report.get('file_path')
            
            # Search content
            matches_found, context_snippets = self._search_report_content(file_path, search_term)
            
            if matches_found:
                # Add search results to metadata
                report['search_matches'] = context_snippets
                results.append(report)
        
        return results
    
    def get_report_content(self, report_path: str) -> Optional[str]:
        """Get the content of a report."""
        try:
            with open(report_path, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            logger.error(f"Error reading report content from {report_path}: {str(e)}")
            return None
    
    def archive_report(self, report_path: str) -> bool:
        """
        Move a report from the reports directory to the archive directory.
        
        Args:
            report_path: Path to the report file
            
        Returns:
            True if archived successfully, False otherwise
        """
        try:
            # Get metadata to extract client ID
            metadata = self._get_report_metadata(report_path)
            client_id = metadata.get('client_id', 'unknown')
            
            # Create archive directory for client if it doesn't exist
            client_archive_dir = os.path.join(self.archive_dir, client_id)
            os.makedirs(client_archive_dir, exist_ok=True)
            
            # Get filename
            filename = os.path.basename(report_path)
            
            # Create destination path
            dest_path = os.path.join(client_archive_dir, filename)
            
            # Move file to archive
            shutil.move(report_path, dest_path)
            
            logger.info(f"Archived report {report_path} to {dest_path}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error archiving report {report_path}: {str(e)}")
            return False
    
    def restore_report(self, archive_path: str) -> bool:
        """
        Restore a report from the archive directory to the reports directory.
        
        Args:
            archive_path: Path to the archived report file
            
        Returns:
            True if restored successfully, False otherwise
        """
        try:
            # Get metadata to extract client ID
            metadata = self._get_report_metadata(archive_path)
            client_id = metadata.get('client_id', 'unknown')
            
            # Create reports directory for client if it doesn't exist
            client_reports_dir = os.path.join(self.reports_dir, client_id)
            os.makedirs(client_reports_dir, exist_ok=True)
            
            # Get filename
            filename = os.path.basename(archive_path)
            
            # Create destination path
            dest_path = os.path.join(client_reports_dir, filename)
            
            # Move file to reports
            shutil.move(archive_path, dest_path)
            
            logger.info(f"Restored report {archive_path} to {dest_path}")
            
            return True
        
        except Exception as e:
            logger.error(f"Error restoring report {archive_path}: {str(e)}")
            return False
    
    def delete_report(self, report_path: str) -> bool:
        """
        Delete a report.
        
        Args:
            report_path: Path to the report file
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            os.remove(report_path)
            logger.info(f"Deleted report {report_path}")
            return True
        except Exception as e:
            logger.error(f"Error deleting report {report_path}: {str(e)}")
            return False
    
    def compare_reports(self, report_path1: str, report_path2: str) -> Optional[str]:
        """
        Compare two reports and return a diff.
        
        Args:
            report_path1: Path to the first report
            report_path2: Path to the second report
            
        Returns:
            String containing the diff output, or None if error
        """
        try:
            # Get content of both reports
            content1 = self.get_report_content(report_path1)
            content2 = self.get_report_content(report_path2)
            
            if content1 is None or content2 is None:
                return None
            
            # Get metadata for report names
            metadata1 = self._get_report_metadata(report_path1)
            metadata2 = self._get_report_metadata(report_path2)
            
            name1 = os.path.basename(report_path1)
            name2 = os.path.basename(report_path2)
            
            # If metadata has timestamps, use those in the labels
            if metadata1.get('timestamp') and metadata2.get('timestamp'):
                ts1 = metadata1.get('timestamp')
                ts2 = metadata2.get('timestamp')
                name1 = f"{name1} ({ts1})"
                name2 = f"{name2} ({ts2})"
            
            # Create diff
            lines1 = content1.splitlines()
            lines2 = content2.splitlines()
            
            diff = difflib.unified_diff(lines1, lines2, fromfile=name1, tofile=name2, lineterm='')
            
            return '\n'.join(diff)
        
        except Exception as e:
            logger.error(f"Error comparing reports: {str(e)}")
            return None
    
    def export_report(self, report_path: str, output_path: Optional[str] = None) -> Optional[str]:
        """
        Export a report to a specific location.
        
        Args:
            report_path: Path to the report file
            output_path: Optional output path, if not provided, creates in current directory
            
        Returns:
            Path to the exported file, or None if error
        """
        try:
            # Get filename
            filename = os.path.basename(report_path)
            
            # Create output path if not provided
            if not output_path:
                output_path = os.path.join(os.getcwd(), filename)
            elif os.path.isdir(output_path):
                output_path = os.path.join(output_path, filename)
            
            # Copy file
            shutil.copy2(report_path, output_path)
            
            logger.info(f"Exported report {report_path} to {output_path}")
            
            return output_path
        
        except Exception as e:
            logger.error(f"Error exporting report {report_path}: {str(e)}")
            return None
    
    def auto_archive_old_reports(self, days: int = 30) -> Tuple[int, List[str]]:
        """
        Automatically archive reports older than a specified number of days.
        
        Args:
            days: Number of days, reports older than this will be archived
            
        Returns:
            Tuple of (number of archives, list of archived paths)
        """
        # Get all reports that are older than the specified days
        cutoff_date = datetime.now() - timedelta(days=days)
        
        # Get all report files in the reports directory
        reports = []
        for client_dir in os.listdir(self.reports_dir):
            client_path = os.path.join(self.reports_dir, client_dir)
            if os.path.isdir(client_path):
                for file in os.listdir(client_path):
                    file_path = os.path.join(client_path, file)
                    if os.path.isfile(file_path):
                        # Check file age
                        modified_time = datetime.fromtimestamp(os.path.getmtime(file_path))
                        if modified_time < cutoff_date:
                            reports.append(file_path)
        
        # Archive each report
        archived_paths = []
        for report_path in reports:
            if self.archive_report(report_path):
                archived_paths.append(report_path)
        
        logger.info(f"Auto-archived {len(archived_paths)} reports older than {days} days")
        
        return len(archived_paths), archived_paths

def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(description='Report History Manager')
    
    # Command selection
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # List reports
    list_parser = subparsers.add_parser('list', help='List reports')
    list_parser.add_argument('--client', help='Filter by client ID')
    list_parser.add_argument('--days', type=int, help='Filter by days back')
    list_parser.add_argument('--start', help='Filter by start date (YYYY-MM-DD)')
    list_parser.add_argument('--end', help='Filter by end date (YYYY-MM-DD)')
    list_parser.add_argument('--format', help='Filter by format type (html, md, pdf, etc.)')
    
    # Search reports
    search_parser = subparsers.add_parser('search', help='Search reports')
    search_parser.add_argument('term', help='Search term')
    search_parser.add_argument('--client', help='Filter by client ID')
    search_parser.add_argument('--days', type=int, help='Filter by days back')
    
    # View report
    view_parser = subparsers.add_parser('view', help='View report content')
    view_parser.add_argument('path', help='Path to report file')
    
    # Archive report
    archive_parser = subparsers.add_parser('archive', help='Archive report')
    archive_parser.add_argument('path', help='Path to report file')
    
    # Restore report
    restore_parser = subparsers.add_parser('restore', help='Restore archived report')
    restore_parser.add_argument('path', help='Path to archived report file')
    
    # Delete report
    delete_parser = subparsers.add_parser('delete', help='Delete report')
    delete_parser.add_argument('path', help='Path to report file')
    delete_parser.add_argument('--force', action='store_true', help='Force deletion without confirmation')
    
    # Compare reports
    compare_parser = subparsers.add_parser('compare', help='Compare two reports')
    compare_parser.add_argument('path1', help='Path to first report file')
    compare_parser.add_argument('path2', help='Path to second report file')
    
    # Export report
    export_parser = subparsers.add_parser('export', help='Export report')
    export_parser.add_argument('path', help='Path to report file')
    export_parser.add_argument('--output', help='Output path')
    
    # Auto-archive old reports
    auto_archive_parser = subparsers.add_parser('auto-archive', help='Auto-archive old reports')
    auto_archive_parser.add_argument('--days', type=int, default=30, help='Age in days (default: 30)')
    
    # Output options
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    args = parser.parse_args()
    
    # Initialize manager
    manager = ReportHistoryManager()
    
    # Execute command
    result = None
    
    if args.command == 'list':
        reports = manager.list_reports(
            client_id=args.client,
            days=args.days,
            start_date=args.start,
            end_date=args.end,
            format_type=args.format
        )
        
        if args.json:
            result = {'reports': reports}
        else:
            print(f"Found {len(reports)} reports:")
            for i, report in enumerate(reports):
                client_name = report.get('client_name', 'Unknown')
                timestamp = report.get('timestamp', 'Unknown')
                format_type = report.get('format', 'Unknown')
                file_path = report.get('file_path')
                
                print(f"{i+1}. {client_name}")
                print(f"   Date: {timestamp}")
                print(f"   Format: {format_type}")
                print(f"   Path: {file_path}")
                print()
    
    elif args.command == 'search':
        reports = manager.search_reports(
            search_term=args.term,
            client_id=args.client,
            days=args.days
        )
        
        if args.json:
            result = {'search_term': args.term, 'reports': reports}
        else:
            print(f"Found {len(reports)} reports matching '{args.term}':")
            for i, report in enumerate(reports):
                client_name = report.get('client_name', 'Unknown')
                timestamp = report.get('timestamp', 'Unknown')
                file_path = report.get('file_path')
                snippets = report.get('search_matches', [])
                
                print(f"{i+1}. {client_name}")
                print(f"   Date: {timestamp}")
                print(f"   Path: {file_path}")
                print("   Matches:")
                for snippet in snippets:
                    print(f"     {snippet}")
                print()
    
    elif args.command == 'view':
        content = manager.get_report_content(args.path)
        if content:
            if args.json:
                result = {'path': args.path, 'content': content}
            else:
                print(f"Content of {args.path}:")
                print("-" * 80)
                print(content)
        else:
            print(f"Error reading report: {args.path}")
            return 1
    
    elif args.command == 'archive':
        success = manager.archive_report(args.path)
        if success:
            if args.json:
                result = {'path': args.path, 'archived': True}
            else:
                print(f"Archived report: {args.path}")
        else:
            print(f"Error archiving report: {args.path}")
            return 1
    
    elif args.command == 'restore':
        success = manager.restore_report(args.path)
        if success:
            if args.json:
                result = {'path': args.path, 'restored': True}
            else:
                print(f"Restored report: {args.path}")
        else:
            print(f"Error restoring report: {args.path}")
            return 1
    
    elif args.command == 'delete':
        # Confirm deletion if not forced
        if not args.force:
            confirm = input(f"Are you sure you want to delete {args.path}? (y/n): ")
            if confirm.lower() != 'y':
                print("Deletion cancelled")
                return 0
        
        success = manager.delete_report(args.path)
        if success:
            if args.json:
                result = {'path': args.path, 'deleted': True}
            else:
                print(f"Deleted report: {args.path}")
        else:
            print(f"Error deleting report: {args.path}")
            return 1
    
    elif args.command == 'compare':
        diff = manager.compare_reports(args.path1, args.path2)
        if diff:
            if args.json:
                result = {'path1': args.path1, 'path2': args.path2, 'diff': diff}
            else:
                print(f"Comparing {args.path1} and {args.path2}:")
                print("-" * 80)
                print(diff)
        else:
            print(f"Error comparing reports")
            return 1
    
    elif args.command == 'export':
        output_path = manager.export_report(args.path, args.output)
        if output_path:
            if args.json:
                result = {'path': args.path, 'output': output_path, 'exported': True}
            else:
                print(f"Exported report to: {output_path}")
        else:
            print(f"Error exporting report: {args.path}")
            return 1
    
    elif args.command == 'auto-archive':
        count, paths = manager.auto_archive_old_reports(args.days)
        if args.json:
            result = {'days': args.days, 'count': count, 'paths': paths}
        else:
            print(f"Auto-archived {count} reports older than {args.days} days")
            if count > 0:
                print("Archived reports:")
                for path in paths:
                    print(f"  {path}")
    
    else:
        parser.print_help()
        return 1
    
    # Output JSON if requested
    if args.json and result:
        print(json.dumps(result, indent=2))
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 