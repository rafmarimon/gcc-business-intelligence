#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import requests
import logging
import re
import pandas as pd
import urllib3
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urllib.parse import urljoin
from dotenv import load_dotenv
import time

# Load environment variables
load_dotenv()

# Suppress SSL verification warnings when necessary
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("GovDataCollector")

# Import our robust API utilities if available
try:
    from src.utils.api_utils import make_api_request, robust_api_request
    API_UTILS_AVAILABLE = True
except ImportError:
    API_UTILS_AVAILABLE = False
    import requests  # Fallback to regular requests

class GovernmentDataCollector:
    """
    Specialized collector for government economic data, reports, and statistics.
    Handles structured data sources from official government websites.
    """
    
    def __init__(self, config_path='config/government_sources.json'):
        """Initialize the government data collector."""
        self.config_path = config_path
        self.sources = self._load_sources()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.131 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Output directory
        self.data_dir = os.path.join('data', 'government')
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Initialize cache if API utils is not available
        if not API_UTILS_AVAILABLE:
            self._request_cache = {}
        
        # If government sources config doesn't exist, use news_sources.json
        if not os.path.exists(self.config_path):
            alternative_path = 'config/news_sources.json'
            if os.path.exists(alternative_path):
                logger.info(f"Using {alternative_path} as fallback for government sources")
                self.config_path = alternative_path
                self.sources = self._load_sources()
            
    def _load_sources(self):
        """Load government data sources from configuration file."""
        try:
            # If the config file exists, load it
            if os.path.exists(self.config_path):
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    # Extract only government sources if using news_sources.json
                    if 'sources' in config:
                        gov_sources = {}
                        for source in config['sources']:
                            if source.get('category') == 'Government':
                                gov_sources[source['name']] = source
                        return gov_sources
                    return config
            else:
                logger.warning(f"Config file not found: {self.config_path}")
                return {}
                
        except Exception as e:
            logger.error(f"Error loading government sources: {e}")
            return {}
    
    def collect_data(self, days_back=30, limit_per_source=20, focus_keywords=None):
        """
        Collect government data, reports, and statistics.
        
        Args:
            days_back: Number of days to look back (government data often has longer relevance)
            limit_per_source: Maximum items to collect per source
            focus_keywords: List of keywords to focus on
            
        Returns:
            List of data items with standard fields
        """
        try:
            logger.info(f"Starting government data collection (days_back={days_back}, limit_per_source={limit_per_source})")
            if focus_keywords:
                logger.info(f"Focusing on keywords: {', '.join(focus_keywords)}")
            
            # Initialize results list
            all_data = []
            
            # Check if we have sources to collect from
            if not self.sources:
                logger.warning("No government sources configured")
                return all_data
            
            # Collect from each source
            for source_name, source_config in self.sources.items():
                try:
                    logger.info(f"Collecting from {source_name}...")
                    
                    # Get source configuration
                    url = source_config['url']
                    source_type = source_config.get('type', 'html')
                    country = source_config.get('country', 'Unknown')
                    category = source_config.get('category', 'Government')
                    
                    # Skip invalid sources
                    if not url:
                        logger.warning(f"Skipping {source_name} - missing URL")
                        continue
                    
                    # Collect data based on source type
                    source_data = []
                    if source_type == 'html':
                        source_data = self._collect_from_html(url, source_name, country, source_config, days_back, limit_per_source)
                    elif source_type == 'api':
                        source_data = self._collect_from_api(url, source_name, country, source_config, days_back, limit_per_source)
                    elif source_type == 'pdf':
                        source_data = self._collect_pdf_reports(url, source_name, country, source_config, days_back, limit_per_source)
                    else:
                        logger.warning(f"Skipping {source_name} - unknown type: {source_type}")
                        continue
                    
                    # Filter by keywords if provided
                    if focus_keywords and source_data:
                        filtered_data = []
                        for item in source_data:
                            text_to_search = (
                                item.get('title', '') + ' ' + 
                                item.get('summary', '') + ' ' + 
                                item.get('content', '') + ' ' +
                                item.get('category', '')
                            ).lower()
                            
                            if any(keyword.lower() in text_to_search for keyword in focus_keywords):
                                filtered_data.append(item)
                        
                        logger.info(f"Filtered {source_name}: {len(filtered_data)}/{len(source_data)} items match keywords")
                        source_data = filtered_data
                    
                    # Add collected data to results
                    all_data.extend(source_data)
                    logger.info(f"Collected {len(source_data)} items from {source_name}")
                    
                except Exception as e:
                    logger.error(f"Error collecting from {source_name}: {e}")
                    continue
            
            # Log collection summary and save results
            logger.info(f"Government data collection complete. Total items: {len(all_data)}")
            self._save_data(all_data)
            
            return all_data
            
        except Exception as e:
            logger.error(f"Error in government data collection: {e}")
            return []
    
    def _collect_from_html(self, url, source_name, country, source_config, days_back=30, limit=20):
        """Collect data from HTML government websites."""
        data_items = []
        try:
            logger.info(f"Scraping government HTML from {url}...")
            
            # Get selectors from crawl pattern
            if isinstance(source_config, dict) and 'crawl_pattern' in source_config:
                selectors = source_config['crawl_pattern']
            else:
                selectors = source_config.get('selectors', {})
            
            # Get specific selectors
            article_selector = selectors.get('article_selector', 'article, .card, div[class*="article"], .news-item')
            title_selector = selectors.get('headline_selector', 'h1, h2, h3, h4, .title')
            summary_selector = selectors.get('summary_selector', 'p, .summary, .desc')
            link_selector = selectors.get('link_selector', 'a')
            date_selector = selectors.get('date_selector', 'time, .date, [class*="date"]')
            
            # Fetch the page using robust request function
            result = self._make_request(url, verify=False)
            
            # Check for errors
            if 'error' in result:
                logger.error(f"Failed to fetch HTML from {url}: {result['error']}")
                return data_items
                
            # Get response text
            response_text = result.get('text', '')
            if not response_text:
                logger.error(f"No content received from {url}")
                return data_items
                
            # Check status code
            if 'status_code' in result and result['status_code'] != 200:
                logger.warning(f"Failed to fetch HTML: {result['status_code']}")
                return data_items
            
            # Parse HTML
            soup = BeautifulSoup(response_text, 'html.parser')
            
            # Find all article/data elements
            elements = soup.select(article_selector)
            logger.info(f"Found {len(elements)} potential data elements on {url}")
            
            # Calculate cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # Process each element
            for i, element in enumerate(elements):
                if i >= limit:
                    break
                    
                try:
                    # Extract title
                    title_el = element.select_one(title_selector)
                    title = title_el.get_text().strip() if title_el else ""
                    
                    # Extract link
                    link = ""
                    if title_el and title_el.name == 'a':
                        link = title_el.get('href', '')
                    elif title_el:
                        link_in_title = title_el.find('a')
                        if link_in_title:
                            link = link_in_title.get('href', '')
                    
                    # If no link found in title, try the dedicated link selector
                    if not link:
                        link_el = element.select_one(link_selector)
                        if link_el:
                            link = link_el.get('href', '')
                    
                    # Fix relative URLs
                    if link and not (link.startswith('http://') or link.startswith('https://')):
                        link = urljoin(url, link)
                    
                    # Extract summary
                    summary_el = element.select_one(summary_selector)
                    summary = summary_el.get_text().strip() if summary_el else ""
                    
                    # Extract date
                    date_el = element.select_one(date_selector)
                    date_str = date_el.get_text().strip() if date_el else ""
                    
                    # Try to parse date
                    pub_date = None
                    if date_str:
                        try:
                            # Common date formats in government sites
                            date_formats = [
                                '%B %d, %Y',
                                '%m/%d/%Y',
                                '%d/%m/%Y',
                                '%Y-%m-%d',
                                '%d-%m-%Y',
                                '%d %B %Y',
                                '%b %d, %Y'
                            ]
                            
                            # Clean up date string
                            date_str = re.sub(r'(Posted on:|Published:|Date:)', '', date_str).strip()
                            
                            # Try each format
                            for date_format in date_formats:
                                try:
                                    pub_date = datetime.strptime(date_str, date_format)
                                    break
                                except ValueError:
                                    continue
                            
                            # Skip old content
                            if pub_date and pub_date < cutoff_date:
                                continue
                                
                        except Exception as e:
                            # If date parsing fails, use current date
                            pub_date = datetime.now()
                    else:
                        # If no date found, use current date
                        pub_date = datetime.now()
                    
                    # Format the date
                    formatted_date = pub_date.strftime('%Y-%m-%d %H:%M:%S') if pub_date else ""
                    
                    # Determine data type based on URL or title
                    data_type = "Article"
                    if any(ext in link.lower() for ext in ['.pdf', '.doc', '.docx', '.xlsx', '.xls', '.ppt', '.pptx']):
                        data_type = "Report" if '.pdf' in link.lower() else "Document"
                    elif any(term in title.lower() for term in ['report', 'study', 'analysis', 'survey']):
                        data_type = "Report"
                    elif any(term in title.lower() for term in ['data', 'statistics', 'figures', 'indicators']):
                        data_type = "Statistics"
                    elif any(term in title.lower() for term in ['press release', 'statement', 'announcement']):
                        data_type = "Press Release"
                    
                    # Create data item if we have at least a title and link
                    if title and link:
                        item = {
                            'title': title,
                            'url': link,
                            'source': source_name,
                            'country': country,
                            'summary': summary,
                            'published_date': formatted_date,
                            'collected_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'data_type': data_type,
                            'category': 'Government',
                            'format': 'PDF' if '.pdf' in link.lower() else 'HTML'
                        }
                        data_items.append(item)
                
                except Exception as e:
                    logger.warning(f"Error processing data element {i}: {e}")
                    continue
            
            logger.info(f"Collected {len(data_items)} government data items from {source_name}")
            return data_items
            
        except Exception as e:
            logger.error(f"Error in _collect_from_html for {source_name}: {e}")
            return data_items
    
    def _collect_from_api(self, url, source_name, country, source_config, days_back=30, limit=20):
        """Collect data from government API endpoints."""
        data_items = []
        try:
            logger.info(f"Fetching from government API {url}...")
            
            # Get API configuration
            api_key = os.environ.get('GOV_API_KEY', '')
            api_params = source_config.get('api_params', {})
            
            # Add API key if available
            if api_key and 'api_key_param' in source_config:
                api_params[source_config['api_key_param']] = api_key
            
            # Adjust date parameters if needed
            cutoff_date = datetime.now() - timedelta(days=days_back)
            if 'date_param' in source_config:
                api_params[source_config['date_param']] = cutoff_date.strftime(source_config.get('date_format', '%Y-%m-%d'))
            
            # Use robust request function
            result = self._make_request(url, verify=False, params=api_params)
            
            # Check for errors
            if 'error' in result:
                logger.error(f"Failed to fetch API {url}: {result['error']}")
                return data_items
                
            # Check if we have JSON data
            if not isinstance(result, dict) or ('text' in result and 'status_code' in result):
                # If we got a text response instead of JSON
                if 'status_code' in result and result['status_code'] != 200:
                    logger.warning(f"API request failed: {result['status_code']}")
                    return data_items
                    
                # Try to parse the text as JSON
                try:
                    data = json.loads(result.get('text', '{}'))
                except:
                    logger.error(f"Failed to parse API response as JSON")
                    return data_items
            else:
                # We already have parsed JSON
                data = result
            
            # Extract data items based on the response structure
            items = []
            if 'results' in data:
                items = data['results']
            elif 'data' in data:
                items = data['data']
            elif 'items' in data:
                items = data['items']
            elif isinstance(data, list):
                items = data
            
            # Process each item
            for i, item in enumerate(items[:limit]):
                try:
                    # Extract fields based on source configuration
                    field_mapping = source_config.get('field_mapping', {})
                    
                    title = self._extract_field(item, field_mapping.get('title', ['title', 'name', 'headline']))
                    url = self._extract_field(item, field_mapping.get('url', ['url', 'link', 'web_url']))
                    summary = self._extract_field(item, field_mapping.get('summary', ['summary', 'description', 'abstract']))
                    date_str = self._extract_field(item, field_mapping.get('date', ['date', 'published_date', 'created_at']))
                    
                    # Skip if no title or URL
                    if not title or not url:
                        continue
                    
                    # Fix relative URLs
                    if url and not (url.startswith('http://') or url.startswith('https://')):
                        url = urljoin(source_config['url'], url)
                    
                    # Parse date if available
                    pub_date = None
                    if date_str:
                        try:
                            date_format = source_config.get('date_format', '%Y-%m-%d')
                            pub_date = datetime.strptime(date_str, date_format)
                        except:
                            # If format unknown, try common formats
                            for fmt in ['%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                                try:
                                    pub_date = datetime.strptime(date_str[:19], fmt)
                                    break
                                except:
                                    continue
                    
                    # Format date for output
                    formatted_date = pub_date.strftime('%Y-%m-%d %H:%M:%S') if pub_date else datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Determine data type
                    data_type = self._extract_field(item, field_mapping.get('type', ['type', 'content_type']))
                    if not data_type:
                        if any(ext in url.lower() for ext in ['.pdf', '.doc', '.xlsx']):
                            data_type = "Report" if '.pdf' in url.lower() else "Document"
                        else:
                            data_type = "Article"
                    
                    # Create data item
                    data_item = {
                        'title': title,
                        'url': url,
                        'source': source_name,
                        'country': country,
                        'summary': summary,
                        'published_date': formatted_date,
                        'collected_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'data_type': data_type,
                        'category': 'Government',
                        'format': 'PDF' if '.pdf' in url.lower() else 'HTML'
                    }
                    data_items.append(data_item)
                    
                except Exception as e:
                    logger.warning(f"Error processing API item {i}: {e}")
                    continue
            
            logger.info(f"Collected {len(data_items)} government data items from API {source_name}")
            return data_items
            
        except Exception as e:
            logger.error(f"Error in _collect_from_api for {source_name}: {e}")
            return data_items
    
    def _collect_pdf_reports(self, url, source_name, country, source_config, days_back=30, limit=20):
        """Collect PDF reports and documents from government websites."""
        data_items = []
        try:
            logger.info(f"Collecting PDF reports from {url}...")
            
            # Get selectors from crawl pattern
            if isinstance(source_config, dict) and 'crawl_pattern' in source_config:
                selectors = source_config['crawl_pattern']
            else:
                selectors = source_config.get('selectors', {})
            
            # Get specific selectors (adjust for PDF links)
            article_selector = selectors.get('article_selector', 'article, .card, div[class*="publication"], .document-item')
            title_selector = selectors.get('headline_selector', 'h1, h2, h3, h4, .title')
            link_selector = selectors.get('link_selector', 'a[href$=".pdf"], a[href*="/download/"], a[href*="/publication/"]')
            date_selector = selectors.get('date_selector', 'time, .date, [class*="date"]')
            
            # Fetch the page using robust request function
            result = self._make_request(url, verify=False)
            
            # Check for errors
            if 'error' in result:
                logger.error(f"Failed to fetch HTML from {url}: {result['error']}")
                return data_items
                
            # Get response text
            response_text = result.get('text', '')
            if not response_text:
                logger.error(f"No content received from {url}")
                return data_items
                
            # Check status code
            if 'status_code' in result and result['status_code'] != 200:
                logger.warning(f"Failed to fetch HTML: {result['status_code']}")
                return data_items
            
            # Parse HTML
            soup = BeautifulSoup(response_text, 'html.parser')
            
            # Find all potential report/document elements
            elements = soup.select(article_selector)
            logger.info(f"Found {len(elements)} potential report elements on {url}")
            
            # If no elements found with article selector, try finding PDF links directly
            if len(elements) == 0:
                pdf_links = soup.select(link_selector)
                logger.info(f"Found {len(pdf_links)} direct PDF links on {url}")
                
                # Process direct PDF links
                for i, link_el in enumerate(pdf_links[:limit]):
                    if i >= limit:
                        break
                        
                    try:
                        # Get link URL
                        link = link_el.get('href', '')
                        if not link or not any(ext in link.lower() for ext in ['.pdf', '.doc', '.docx', '.xlsx']):
                            continue
                            
                        # Fix relative URLs
                        if not (link.startswith('http://') or link.startswith('https://')):
                            link = urljoin(url, link)
                        
                        # Use link text as title, or extract from filename
                        title = link_el.get_text().strip()
                        if not title:
                            # Extract title from filename
                            file_name = os.path.basename(link)
                            title = os.path.splitext(file_name)[0].replace('-', ' ').replace('_', ' ').title()
                        
                        # Create data item
                        data_item = {
                            'title': title,
                            'url': link,
                            'source': source_name,
                            'country': country,
                            'summary': f"PDF document from {source_name}",
                            'published_date': datetime.now().strftime('%Y-%m-%d'),
                            'collected_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'data_type': "Report" if '.pdf' in link.lower() else "Document",
                            'category': 'Government',
                            'format': 'PDF' if '.pdf' in link.lower() else 'Document'
                        }
                        data_items.append(data_item)
                        
                    except Exception as e:
                        logger.warning(f"Error processing PDF link {i}: {e}")
                        continue
            else:
                # Process each element that might contain reports
                for i, element in enumerate(elements):
                    if i >= limit:
                        break
                        
                    try:
                        # Find PDF links within this element
                        pdf_el = element.select_one(link_selector)
                        if not pdf_el:
                            # Try any link that might be a document
                            pdf_el = element.find('a', href=lambda href: href and any(ext in href.lower() for ext in ['.pdf', '.doc', '.docx', '.xlsx']))
                        
                        if not pdf_el:
                            continue
                            
                        # Get link URL
                        link = pdf_el.get('href', '')
                        if not link:
                            continue
                            
                        # Fix relative URLs
                        if not (link.startswith('http://') or link.startswith('https://')):
                            link = urljoin(url, link)
                        
                        # Extract title
                        title_el = element.select_one(title_selector)
                        title = title_el.get_text().strip() if title_el else ""
                        
                        # If no title found, use link text or filename
                        if not title:
                            title = pdf_el.get_text().strip()
                        if not title:
                            file_name = os.path.basename(link)
                            title = os.path.splitext(file_name)[0].replace('-', ' ').replace('_', ' ').title()
                        
                        # Extract date if available
                        date_el = element.select_one(date_selector)
                        date_str = date_el.get_text().strip() if date_el else ""
                        
                        # Format date
                        formatted_date = date_str if date_str else datetime.now().strftime('%Y-%m-%d')
                        
                        # Create data item
                        data_item = {
                            'title': title,
                            'url': link,
                            'source': source_name,
                            'country': country,
                            'summary': f"PDF document from {source_name}",
                            'published_date': formatted_date,
                            'collected_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'data_type': "Report" if '.pdf' in link.lower() else "Document",
                            'category': 'Government',
                            'format': 'PDF' if '.pdf' in link.lower() else 'Document'
                        }
                        data_items.append(data_item)
                        
                    except Exception as e:
                        logger.warning(f"Error processing report element {i}: {e}")
                        continue
            
            logger.info(f"Collected {len(data_items)} PDF reports/documents from {source_name}")
            return data_items
            
        except Exception as e:
            logger.error(f"Error in _collect_pdf_reports for {source_name}: {e}")
            return data_items
    
    def _extract_field(self, item, possible_fields):
        """Helper to extract a field from an item using multiple possible field names."""
        if isinstance(possible_fields, str):
            possible_fields = [possible_fields]
            
        for field in possible_fields:
            if field in item:
                return item[field]
            
            # Handle nested fields with dot notation
            if '.' in field:
                parts = field.split('.')
                nested_item = item
                found = True
                
                for part in parts:
                    if part in nested_item:
                        nested_item = nested_item[part]
                    else:
                        found = False
                        break
                        
                if found:
                    return nested_item
                    
        return ""
    
    def _save_data(self, data_items):
        """Save collected government data to disk."""
        if not data_items:
            logger.warning("No government data items to save.")
            return
        
        # Create timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Ensure data directory exists
        os.makedirs(self.data_dir, exist_ok=True)
        
        # Save as JSON
        json_path = os.path.join(self.data_dir, f'gov_data_{timestamp}.json')
        with open(json_path, 'w') as f:
            json.dump(data_items, f, indent=2)
        
        # Save as CSV
        try:
            df = pd.DataFrame(data_items)
            csv_path = os.path.join(self.data_dir, f'gov_data_{timestamp}.csv')
            df.to_csv(csv_path, index=False)
            logger.info(f"Saved {len(data_items)} government data items to {csv_path} and {json_path}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            logger.info(f"Saved {len(data_items)} government data items to {json_path}")

    # Robust request function using our utility library if available
    def _make_request(self, url, method='get', headers=None, timeout=30, **kwargs):
        """
        Make a robust HTTP request with retries, error handling, and caching
        """
        if headers is None:
            headers = self.headers
            
        if API_UTILS_AVAILABLE:
            # Use our robust API utilities
            return make_api_request(
                url=url, 
                method=method, 
                headers=headers, 
                timeout=timeout, 
                **kwargs
            )
        else:
            # Simple caching implementation
            cache_key = f"{method}:{url}"
            if cache_key in self._request_cache:
                cache_time, cache_data = self._request_cache[cache_key]
                # Cache valid for 1 hour
                if time.time() - cache_time < 3600:
                    logger.debug(f"Using cached response for {url}")
                    return cache_data
            
            # Fallback to regular requests with basic retry
            max_retries = 3
            retry_count = 0
            while retry_count <= max_retries:
                try:
                    if retry_count > 0:
                        logger.info(f"Retry attempt {retry_count} for {url}")
                        time.sleep(retry_count * 2)  # Simple backoff
                    
                    if method.lower() == 'get':
                        response = requests.get(url, headers=headers, timeout=timeout, **kwargs)
                    elif method.lower() == 'post':
                        response = requests.post(url, headers=headers, timeout=timeout, **kwargs)
                    else:
                        raise ValueError(f"Unsupported HTTP method: {method}")
                    
                    response.raise_for_status()
                    
                    # For non-JSON responses, return a dict with text and status
                    try:
                        result = response.json()
                    except:
                        result = {
                            'text': response.text,
                            'status_code': response.status_code
                        }
                    
                    # Cache successful response
                    self._request_cache[cache_key] = (time.time(), result)
                    return result
                    
                except (requests.exceptions.RequestException, requests.exceptions.Timeout, 
                         requests.exceptions.ConnectionError) as e:
                    retry_count += 1
                    if retry_count > max_retries:
                        logger.error(f"Failed to fetch {url} after {max_retries} retries: {e}")
                        return {'error': str(e)}
                    logger.warning(f"Error fetching {url}: {e}. Retrying...")
    
    def _process_date(self, date_str):
        """Helper to process a date string and return a datetime object."""
        if not date_str:
            return None
        
        try:
            # Try to parse the date using multiple formats
            date_formats = [
                '%B %d, %Y',
                '%m/%d/%Y',
                '%d/%m/%Y',
                '%Y-%m-%d',
                '%d-%m-%Y',
                '%d %B %Y',
                '%b %d, %Y'
            ]
            
            for date_format in date_formats:
                try:
                    return datetime.strptime(date_str, date_format)
                except ValueError:
                    continue
            
            # If all formats fail, return None
            return None
        except Exception as e:
            logger.error(f"Error processing date: {e}")
            return None
    
    def _determine_data_type(self, url, title):
        """Helper to determine data type based on URL or title."""
        if any(ext in url.lower() for ext in ['.pdf', '.doc', '.docx', '.xlsx', '.xls', '.ppt', '.pptx']):
            return "Report" if '.pdf' in url.lower() else "Document"
        elif any(term in title.lower() for term in ['report', 'study', 'analysis', 'survey']):
            return "Report"
        elif any(term in title.lower() for term in ['data', 'statistics', 'figures', 'indicators']):
            return "Statistics"
        elif any(term in title.lower() for term in ['press release', 'statement', 'announcement']):
            return "Press Release"
        else:
            return "Article"

if __name__ == "__main__":
    # Simple test
    collector = GovernmentDataCollector()
    data = collector.collect_data()
    print(f"Collected {len(data)} government data items.") 