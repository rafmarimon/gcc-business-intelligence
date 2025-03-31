#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Content Filtering and Search Tool

This script provides capabilities to filter and search through report content
based on keywords, regions, topics, and date ranges.
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime, timedelta
import re
import glob
from typing import Dict, List, Any, Optional, Set, Tuple

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

log_filename = os.path.join(log_dir, f'content_filter_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_filename),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class ContentFilter:
    """Handles content filtering and search functionality."""
    
    # GCC region keywords for classification
    GCC_REGIONS = {
        'saudi arabia': ['saudi', 'ksa', 'riyadh', 'jeddah', 'dammam', 'mecca', 'medina'],
        'uae': ['uae', 'emirates', 'dubai', 'abu dhabi', 'sharjah', 'ajman', 'fujairah', 'ras al khaimah', 'umm al quwain'],
        'qatar': ['qatar', 'doha', 'lusail', 'al wakrah', 'mesaieed'],
        'kuwait': ['kuwait', 'kuwait city', 'al ahmadi'],
        'bahrain': ['bahrain', 'manama', 'muharraq', 'riffa'],
        'oman': ['oman', 'muscat', 'salalah', 'sohar', 'nizwa']
    }
    
    # Common industries to categorize content
    INDUSTRIES = {
        'energy': ['oil', 'gas', 'petroleum', 'energy', 'renewables', 'solar', 'wind', 'hydrocarbon'],
        'finance': ['banking', 'finance', 'investment', 'fintech', 'insurance', 'stocks', 'bonds'],
        'technology': ['technology', 'tech', 'software', 'hardware', 'ai', 'ml', 'cloud', 'digital', 'iot'],
        'healthcare': ['healthcare', 'medical', 'hospital', 'pharma', 'pharmaceutical', 'biotech', 'health'],
        'real estate': ['real estate', 'property', 'construction', 'housing', 'commercial property', 'residential'],
        'retail': ['retail', 'e-commerce', 'shop', 'mall', 'consumer goods', 'merchandise'],
        'tourism': ['tourism', 'hospitality', 'hotel', 'travel', 'leisure', 'vacation', 'resort'],
        'manufacturing': ['manufacturing', 'industrial', 'factory', 'production', 'assembly'],
        'transportation': ['transportation', 'logistics', 'shipping', 'freight', 'aviation']
    }
    
    def __init__(self):
        """Initialize the content filter."""
        # Initialize Redis cache
        self.redis = RedisCache()
        
        # Initialize client model
        self.client_model = ClientModel()
        
        # Set up reports directory
        reports_dir = os.environ.get('REPORTS_DIR', 'reports')
        self.reports_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), reports_dir))
        
        # Set up data directory for content index
        data_dir = os.environ.get('DATA_DIR', 'data')
        self.data_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), data_dir))
        self.index_dir = os.path.join(self.data_dir, 'content_index')
        
        # Create directories if they don't exist
        os.makedirs(self.index_dir, exist_ok=True)
        
        logger.info("Content filter initialized")
    
    def _extract_text_from_report(self, report_path: str) -> Optional[str]:
        """Extract text content from a report file."""
        try:
            _, ext = os.path.splitext(report_path)
            ext = ext.lower()
            
            # Handle different file types
            if ext in ['.html', '.htm']:
                try:
                    from bs4 import BeautifulSoup
                    with open(report_path, 'r', encoding='utf-8') as f:
                        soup = BeautifulSoup(f.read(), 'html.parser')
                        # Remove script and style elements
                        for script in soup(["script", "style"]):
                            script.extract()
                        # Get text
                        text = soup.get_text(separator=' ', strip=True)
                        return text
                except ImportError:
                    # Fallback if BeautifulSoup is not available
                    with open(report_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # Simple regex to remove HTML tags
                        text = re.sub(r'<[^>]+>', ' ', content)
                        return text
            
            elif ext in ['.md', '.txt']:
                with open(report_path, 'r', encoding='utf-8') as f:
                    return f.read()
            
            elif ext == '.json':
                with open(report_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Try to extract text from common JSON structures
                    if isinstance(data, dict):
                        # Extract all string values
                        texts = []
                        for value in data.values():
                            if isinstance(value, str):
                                texts.append(value)
                        return ' '.join(texts)
                    return str(data)
            
            elif ext == '.pdf':
                try:
                    import PyPDF2
                    with open(report_path, 'rb') as f:
                        reader = PyPDF2.PdfReader(f)
                        text = ""
                        for page in reader.pages:
                            text += page.extract_text() + " "
                        return text
                except ImportError:
                    logger.warning(f"PyPDF2 not available, can't extract text from PDF: {report_path}")
                    return None
            
            else:
                logger.warning(f"Unsupported file type for text extraction: {ext}")
                return None
            
        except Exception as e:
            logger.error(f"Error extracting text from {report_path}: {str(e)}")
            return None
    
    def _identify_regions(self, text: str) -> Set[str]:
        """Identify GCC regions mentioned in text."""
        text = text.lower()
        regions = set()
        
        for region, keywords in self.GCC_REGIONS.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    regions.add(region)
                    break
        
        return regions
    
    def _identify_industries(self, text: str) -> Set[str]:
        """Identify industries mentioned in text."""
        text = text.lower()
        industries = set()
        
        for industry, keywords in self.INDUSTRIES.items():
            for keyword in keywords:
                if keyword.lower() in text:
                    industries.add(industry)
                    break
        
        return industries
    
    def _extract_dates_from_text(self, text: str) -> List[str]:
        """Extract dates mentioned in text."""
        # Common date formats: MM/DD/YYYY, DD/MM/YYYY, Month DD YYYY, etc.
        date_patterns = [
            r'\b\d{1,2}/\d{1,2}/\d{2,4}\b',  # MM/DD/YY or MM/DD/YYYY
            r'\b\d{1,2}-\d{1,2}-\d{2,4}\b',  # MM-DD-YY or MM-DD-YYYY
            r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b',  # Month DD, YYYY
            r'\b\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b',  # DD Month YYYY
            r'\b(?:January|February|March|April|May|June|July|August|September|October|November|December) \d{1,2},? \d{4}\b'  # Full month
        ]
        
        dates = []
        for pattern in date_patterns:
            dates.extend(re.findall(pattern, text, re.IGNORECASE))
        
        return dates
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """Extract named entities from text (companies, people, locations)."""
        try:
            import spacy
            try:
                nlp = spacy.load("en_core_web_sm")
            except OSError:
                logger.warning("Spacy model not found. Using blank model.")
                nlp = spacy.blank("en")
                return {"companies": [], "people": [], "locations": []}
            
            doc = nlp(text[:100000])  # Limit to first 100K chars to avoid memory issues
            
            entities = {
                "companies": [],
                "people": [],
                "locations": []
            }
            
            for ent in doc.ents:
                if ent.label_ == "ORG":
                    entities["companies"].append(ent.text)
                elif ent.label_ == "PERSON":
                    entities["people"].append(ent.text)
                elif ent.label_ in ["GPE", "LOC"]:
                    entities["locations"].append(ent.text)
            
            # Deduplicate
            for key in entities:
                entities[key] = list(set(entities[key]))
            
            return entities
            
        except ImportError:
            logger.warning("Spacy not available for entity extraction")
            return {"companies": [], "people": [], "locations": []}
    
    def index_report(self, report_path: str) -> Optional[Dict[str, Any]]:
        """
        Index a report for search and filtering.
        
        Args:
            report_path: Path to the report file
            
        Returns:
            Dictionary with report metadata and extracted content information,
            or None if indexing failed
        """
        try:
            # Get basic file info
            filename = os.path.basename(report_path)
            file_size = os.path.getsize(report_path)
            last_modified = datetime.fromtimestamp(os.path.getmtime(report_path)).isoformat()
            
            # Extract client ID from path
            path_parts = os.path.normpath(report_path).split(os.sep)
            client_id = path_parts[-2] if len(path_parts) >= 2 else "unknown"
            
            # Extract timestamp from filename
            timestamp_match = re.search(r'(\d{8}_\d{6})', filename)
            timestamp = timestamp_match.group(1) if timestamp_match else None
            
            # Extract text content
            text = self._extract_text_from_report(report_path)
            if not text:
                logger.warning(f"Could not extract text from {report_path}")
                return None
            
            # Extract metadata
            regions = self._identify_regions(text)
            industries = self._identify_industries(text)
            dates = self._extract_dates_from_text(text)
            
            # Create simple keyword index (word frequency)
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
            word_freq = {}
            for word in words:
                if word not in word_freq:
                    word_freq[word] = 0
                word_freq[word] += 1
            
            # Get top keywords (most frequent terms)
            keywords = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)[:50]
            
            # Attempt to extract entities if spacy is available
            try:
                entities = self._extract_entities(text)
            except Exception as e:
                logger.warning(f"Entity extraction failed for {report_path}: {str(e)}")
                entities = {"companies": [], "people": [], "locations": []}
            
            # Create index data
            index_data = {
                "file_path": report_path,
                "file_name": filename,
                "file_size": file_size,
                "last_modified": last_modified,
                "client_id": client_id,
                "timestamp": timestamp,
                "regions": list(regions),
                "industries": list(industries),
                "dates_mentioned": dates,
                "keywords": [k for k, v in keywords],
                "keyword_freq": {k: v for k, v in keywords},
                "entities": entities,
                "indexed_at": datetime.now().isoformat()
            }
            
            # Try to get client name
            client = self.client_model.get_client_by_id(client_id)
            if client:
                index_data["client_name"] = client.get('name', 'Unknown')
            
            # Save to index file
            index_id = os.path.splitext(filename)[0]
            index_path = os.path.join(self.index_dir, f"{index_id}_index.json")
            
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(index_data, f, indent=2)
            
            logger.info(f"Indexed report {report_path} to {index_path}")
            
            return index_data
            
        except Exception as e:
            logger.error(f"Error indexing report {report_path}: {str(e)}")
            return None
    
    def index_all_reports(self) -> Tuple[int, int]:
        """
        Index all reports in the reports directory.
        
        Returns:
            Tuple of (success_count, failure_count)
        """
        # Get all report files
        report_files = []
        for root, _, files in os.walk(self.reports_dir):
            for file in files:
                file_path = os.path.join(root, file)
                report_files.append(file_path)
        
        success_count = 0
        failure_count = 0
        
        for report_path in report_files:
            result = self.index_report(report_path)
            if result:
                success_count += 1
            else:
                failure_count += 1
        
        logger.info(f"Indexed {success_count} reports, {failure_count} failures")
        
        return success_count, failure_count
    
    def _load_index(self, report_path: str) -> Optional[Dict[str, Any]]:
        """Load index data for a report."""
        try:
            filename = os.path.basename(report_path)
            index_id = os.path.splitext(filename)[0]
            index_path = os.path.join(self.index_dir, f"{index_id}_index.json")
            
            if not os.path.exists(index_path):
                return None
            
            with open(index_path, 'r', encoding='utf-8') as f:
                return json.load(f)
                
        except Exception as e:
            logger.error(f"Error loading index for {report_path}: {str(e)}")
            return None
    
    def _load_all_indexes(self) -> List[Dict[str, Any]]:
        """Load all index data."""
        indexes = []
        
        index_files = glob.glob(os.path.join(self.index_dir, "*_index.json"))
        for index_path in index_files:
            try:
                with open(index_path, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
                    indexes.append(index_data)
            except Exception as e:
                logger.error(f"Error loading index file {index_path}: {str(e)}")
        
        return indexes
    
    def search(self, query: str, 
               client_id: Optional[str] = None,
               regions: Optional[List[str]] = None,
               industries: Optional[List[str]] = None,
               start_date: Optional[str] = None,
               end_date: Optional[str] = None,
               entities: Optional[Dict[str, List[str]]] = None) -> List[Dict[str, Any]]:
        """
        Search for reports matching criteria.
        
        Args:
            query: Search query (keywords)
            client_id: Optional client ID filter
            regions: Optional list of GCC regions to filter by
            industries: Optional list of industries to filter by
            start_date: Optional start date (YYYY-MM-DD)
            end_date: Optional end date (YYYY-MM-DD)
            entities: Optional dict of entities to filter by (e.g. {'companies': ['ADNOC']})
            
        Returns:
            List of matching report metadata
        """
        # Load all indexes
        indexes = self._load_all_indexes()
        
        # Split query into keywords
        if query:
            keywords = [k.lower() for k in query.split()]
        else:
            keywords = []
        
        # Convert dates to datetime objects if provided
        start_datetime = None
        end_datetime = None
        
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
            except ValueError:
                logger.warning(f"Invalid start_date format: {start_date}")
        
        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                # Set to end of day
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
            except ValueError:
                logger.warning(f"Invalid end_date format: {end_date}")
        
        # Process each index
        results = []
        
        for index in indexes:
            # Apply filters
            
            # Client filter
            if client_id and index.get('client_id') != client_id:
                continue
            
            # Report date filter
            if (start_datetime or end_datetime) and index.get('timestamp'):
                try:
                    report_date = datetime.strptime(index.get('timestamp'), '%Y%m%d_%H%M%S')
                    
                    if start_datetime and report_date < start_datetime:
                        continue
                    
                    if end_datetime and report_date > end_datetime:
                        continue
                except ValueError:
                    # If timestamp format is invalid, don't filter by date
                    pass
            
            # Region filter
            if regions:
                index_regions = set(index.get('regions', []))
                if not any(region.lower() in index_regions for region in regions):
                    continue
            
            # Industry filter
            if industries:
                index_industries = set(index.get('industries', []))
                if not any(industry.lower() in index_industries for industry in industries):
                    continue
            
            # Entity filter
            if entities:
                index_entities = index.get('entities', {})
                match_failed = False
                
                for entity_type, entity_list in entities.items():
                    if entity_type not in index_entities:
                        match_failed = True
                        break
                    
                    index_entity_set = set(e.lower() for e in index_entities[entity_type])
                    if not any(entity.lower() in index_entity_set for entity in entity_list):
                        match_failed = True
                        break
                
                if match_failed:
                    continue
            
            # Keyword search
            if keywords:
                index_keywords = set(k.lower() for k in index.get('keywords', []))
                
                # Check if any keyword matches
                if not any(keyword in index_keywords for keyword in keywords):
                    # Secondary check in case the keyword wasn't in the top 50
                    keyword_freq = index.get('keyword_freq', {})
                    if not any(keyword in keyword_freq for keyword in keywords):
                        continue
            
            # Add to results if it passed all filters
            results.append(index)
        
        # Sort by date (newest first)
        results.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
        
        return results
    
    def filter_by_topic(self, topic: str) -> List[Dict[str, Any]]:
        """
        Filter reports by topic.
        
        Args:
            topic: Topic to filter by
            
        Returns:
            List of matching report metadata
        """
        # For simplicity, we'll use the search function with the topic as a keyword
        return self.search(query=topic)
    
    def filter_by_region(self, region: str) -> List[Dict[str, Any]]:
        """
        Filter reports by GCC region.
        
        Args:
            region: GCC region to filter by
            
        Returns:
            List of matching report metadata
        """
        # Use the search function with the region as a filter
        return self.search(query="", regions=[region])
    
    def filter_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """
        Filter reports by date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of matching report metadata
        """
        # Use the search function with date filters
        return self.search(query="", start_date=start_date, end_date=end_date)
    
    def get_popular_topics(self, limit: int = 10) -> List[Tuple[str, int]]:
        """
        Get most popular topics across all reports.
        
        Args:
            limit: Number of topics to return
            
        Returns:
            List of (topic, count) tuples
        """
        # Load all indexes
        indexes = self._load_all_indexes()
        
        # Count keyword frequencies across all reports
        topic_counts = {}
        
        for index in indexes:
            keyword_freq = index.get('keyword_freq', {})
            
            for keyword, freq in keyword_freq.items():
                if keyword not in topic_counts:
                    topic_counts[keyword] = 0
                topic_counts[keyword] += 1
        
        # Sort by count (descending)
        topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        
        # Return top N
        return topics[:limit]
    
    def get_related_reports(self, report_path: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get reports related to a given report.
        
        Args:
            report_path: Path to the reference report
            limit: Number of related reports to return
            
        Returns:
            List of related report metadata
        """
        # Load index for the reference report
        ref_index = self._load_index(report_path)
        if not ref_index:
            # Try to index it if not already indexed
            ref_index = self.index_report(report_path)
            if not ref_index:
                logger.error(f"Could not index report {report_path}")
                return []
        
        # Get reference report keywords
        ref_keywords = set(ref_index.get('keywords', [])[:20])  # Use top 20 keywords
        
        # Load all indexes
        all_indexes = self._load_all_indexes()
        
        # Calculate similarity scores
        similarity_scores = []
        
        for index in all_indexes:
            # Skip the reference report itself
            if index.get('file_path') == report_path:
                continue
            
            # Get report keywords
            index_keywords = set(index.get('keywords', []))
            
            # Calculate Jaccard similarity (intersection / union)
            intersection = len(ref_keywords.intersection(index_keywords))
            union = len(ref_keywords.union(index_keywords))
            
            if union > 0:
                similarity = intersection / union
            else:
                similarity = 0
                
            similarity_scores.append((index, similarity))
        
        # Sort by similarity (descending)
        similarity_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Return top N related reports
        return [index for index, _ in similarity_scores[:limit]]

def main():
    """Main function to parse arguments and execute commands."""
    parser = argparse.ArgumentParser(description='Content Filtering and Search Tool')
    
    # Command selection
    subparsers = parser.add_subparsers(dest='command', help='Command to execute')
    
    # Index a report
    index_parser = subparsers.add_parser('index', help='Index a report')
    index_parser.add_argument('path', help='Path to report file')
    
    # Index all reports
    index_all_parser = subparsers.add_parser('index-all', help='Index all reports')
    
    # Search reports
    search_parser = subparsers.add_parser('search', help='Search reports')
    search_parser.add_argument('query', nargs='?', default='', help='Search query')
    search_parser.add_argument('--client', help='Filter by client ID')
    search_parser.add_argument('--regions', help='Filter by regions (comma-separated)')
    search_parser.add_argument('--industries', help='Filter by industries (comma-separated)')
    search_parser.add_argument('--start', help='Filter by start date (YYYY-MM-DD)')
    search_parser.add_argument('--end', help='Filter by end date (YYYY-MM-DD)')
    search_parser.add_argument('--company', help='Filter by company name')
    
    # Filter by topic
    topic_parser = subparsers.add_parser('topic', help='Filter by topic')
    topic_parser.add_argument('topic', help='Topic to filter by')
    
    # Filter by region
    region_parser = subparsers.add_parser('region', help='Filter by GCC region')
    region_parser.add_argument('region', help='GCC region to filter by')
    
    # Filter by date range
    date_parser = subparsers.add_parser('dates', help='Filter by date range')
    date_parser.add_argument('start', help='Start date (YYYY-MM-DD)')
    date_parser.add_argument('end', help='End date (YYYY-MM-DD)')
    
    # Get popular topics
    topics_parser = subparsers.add_parser('popular-topics', help='Get popular topics')
    topics_parser.add_argument('--limit', type=int, default=10, help='Number of topics to return')
    
    # Get related reports
    related_parser = subparsers.add_parser('related', help='Get related reports')
    related_parser.add_argument('path', help='Path to reference report')
    related_parser.add_argument('--limit', type=int, default=5, help='Number of related reports to return')
    
    # Output options
    parser.add_argument('--json', action='store_true', help='Output in JSON format')
    
    args = parser.parse_args()
    
    # Initialize content filter
    filter = ContentFilter()
    
    # Execute command
    result = None
    
    if args.command == 'index':
        index_data = filter.index_report(args.path)
        if index_data:
            if args.json:
                result = {'indexed': True, 'path': args.path, 'data': index_data}
            else:
                print(f"Indexed report: {args.path}")
                print(f"Regions identified: {', '.join(index_data.get('regions', []))}")
                print(f"Industries identified: {', '.join(index_data.get('industries', []))}")
                print(f"Top keywords: {', '.join(index_data.get('keywords', [])[:10])}")
        else:
            print(f"Error indexing report: {args.path}")
            return 1
    
    elif args.command == 'index-all':
        success_count, failure_count = filter.index_all_reports()
        if args.json:
            result = {'success_count': success_count, 'failure_count': failure_count}
        else:
            print(f"Indexed {success_count} reports, {failure_count} failures")
    
    elif args.command == 'search':
        # Parse filter arguments
        regions = args.regions.split(',') if args.regions else None
        industries = args.industries.split(',') if args.industries else None
        
        # Set up entity filter if company was specified
        entities = None
        if args.company:
            entities = {'companies': [args.company]}
        
        reports = filter.search(
            query=args.query,
            client_id=args.client,
            regions=regions,
            industries=industries,
            start_date=args.start,
            end_date=args.end,
            entities=entities
        )
        
        if args.json:
            result = {'query': args.query, 'count': len(reports), 'results': reports}
        else:
            print(f"Found {len(reports)} matching reports:")
            for i, report in enumerate(reports):
                client_name = report.get('client_name', 'Unknown')
                timestamp = report.get('timestamp', 'Unknown')
                file_path = report.get('file_path')
                
                print(f"{i+1}. {client_name}")
                print(f"   Date: {timestamp}")
                print(f"   Path: {file_path}")
                print(f"   Regions: {', '.join(report.get('regions', []))}")
                print(f"   Industries: {', '.join(report.get('industries', []))}")
                print(f"   Top keywords: {', '.join(report.get('keywords', [])[:5])}")
                print()
    
    elif args.command == 'topic':
        reports = filter.filter_by_topic(args.topic)
        if args.json:
            result = {'topic': args.topic, 'count': len(reports), 'results': reports}
        else:
            print(f"Found {len(reports)} reports about '{args.topic}':")
            for i, report in enumerate(reports):
                client_name = report.get('client_name', 'Unknown')
                timestamp = report.get('timestamp', 'Unknown')
                file_path = report.get('file_path')
                
                print(f"{i+1}. {client_name}")
                print(f"   Date: {timestamp}")
                print(f"   Path: {file_path}")
                print()
    
    elif args.command == 'region':
        reports = filter.filter_by_region(args.region)
        if args.json:
            result = {'region': args.region, 'count': len(reports), 'results': reports}
        else:
            print(f"Found {len(reports)} reports about '{args.region}':")
            for i, report in enumerate(reports):
                client_name = report.get('client_name', 'Unknown')
                timestamp = report.get('timestamp', 'Unknown')
                file_path = report.get('file_path')
                
                print(f"{i+1}. {client_name}")
                print(f"   Date: {timestamp}")
                print(f"   Path: {file_path}")
                print()
    
    elif args.command == 'dates':
        reports = filter.filter_by_date_range(args.start, args.end)
        if args.json:
            result = {'start_date': args.start, 'end_date': args.end, 'count': len(reports), 'results': reports}
        else:
            print(f"Found {len(reports)} reports between {args.start} and {args.end}:")
            for i, report in enumerate(reports):
                client_name = report.get('client_name', 'Unknown')
                timestamp = report.get('timestamp', 'Unknown')
                file_path = report.get('file_path')
                
                print(f"{i+1}. {client_name}")
                print(f"   Date: {timestamp}")
                print(f"   Path: {file_path}")
                print()
    
    elif args.command == 'popular-topics':
        topics = filter.get_popular_topics(args.limit)
        if args.json:
            result = {'topics': [{'topic': topic, 'count': count} for topic, count in topics]}
        else:
            print(f"Top {len(topics)} popular topics:")
            for i, (topic, count) in enumerate(topics):
                print(f"{i+1}. {topic} ({count} reports)")
    
    elif args.command == 'related':
        reports = filter.get_related_reports(args.path, args.limit)
        if args.json:
            result = {'reference': args.path, 'count': len(reports), 'results': reports}
        else:
            print(f"Found {len(reports)} reports related to {args.path}:")
            for i, report in enumerate(reports):
                client_name = report.get('client_name', 'Unknown')
                timestamp = report.get('timestamp', 'Unknown')
                file_path = report.get('file_path')
                
                print(f"{i+1}. {client_name}")
                print(f"   Date: {timestamp}")
                print(f"   Path: {file_path}")
                print(f"   Common topics: {', '.join(report.get('keywords', [])[:5])}")
                print()
    
    else:
        parser.print_help()
        return 1
    
    # Output JSON if requested
    if args.json and result:
        print(json.dumps(result, indent=2))
    
    return 0

if __name__ == '__main__':
    sys.exit(main()) 