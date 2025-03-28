#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import json
import logging
import csv
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from urllib.parse import urlparse

# Add the project root to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("firecrawl_collector")

# Load environment variables
load_dotenv()

class FirecrawlNewsCollector:
    """
    News collector that uses the Firecrawl API to scrape news articles.
    This is a drop-in replacement for the existing news collection system.
    """
    
    def __init__(self, api_key=None, config_file=None):
        """Initialize the Firecrawl news collector."""
        self.api_key = api_key or os.getenv("FIRECRAWL_API_KEY")
        self.base_url = "https://api.firecrawl.dev/v1"
        
        # Setup logger
        self.logger = logging.getLogger("firecrawl_collector")
        
        if not self.api_key:
            self.logger.warning("No Firecrawl API key provided. Please set it via FIRECRAWL_API_KEY environment variable or pass it to the constructor.")
        
        # Load configuration
        self.config_file = config_file or "config/news_sources.json"
        self.sources = self._load_sources()
        
        # Set up data directories
        self.data_dir = "data/news"
        os.makedirs(self.data_dir, exist_ok=True)
    
    def _load_sources(self):
        """Load news sources from configuration file."""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
                sources = config.get("sources", [])
            self.logger.info(f"Loaded {len(sources)} sources from {self.config_file}")
            return sources
        except Exception as e:
            self.logger.error(f"Error loading sources from {self.config_file}: {str(e)}")
            return []
    
    def _make_api_request(self, endpoint, payload):
        """
        Make a request to the Firecrawl API
        
        Args:
            endpoint (str): API endpoint to call
            payload (dict): Request payload
            
        Returns:
            dict: API response JSON
        """
        try:
            url = f"{self.base_url}/{endpoint}"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API request error for {endpoint}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_json = e.response.json()
                    self.logger.error(f"API error response: {error_json}")
                except:
                    self.logger.error(f"API error status code: {e.response.status_code}")
            return {"error": str(e), "data": {}}
    
    def collect_news(self, keywords=None):
        """
        Collect news articles from configured sources.
        
        Args:
            keywords (list): List of keywords to filter articles by.
            
        Returns:
            list: Collected news articles.
        """
        if not self.api_key:
            self.logger.error("Cannot collect news: No Firecrawl API key provided")
            return []
        
        if not self.sources:
            self.logger.error("Cannot collect news: No sources configured")
            return []
        
        # Default keywords
        if keywords is None:
            keywords = [
                "UAE economy", "Dubai business", "Abu Dhabi investment",
                "GCC trade", "Middle East startups", "UAE technology"
            ]
        
        self.logger.info(f"Collecting news for {len(keywords)} keywords from {len(self.sources)} sources")
        
        all_articles = []
        
        # Process each source
        for source in self.sources:
            source_name = source.get("name", "Unknown")
            base_url = source.get("url")
            
            if not base_url:
                self.logger.warning(f"Skipping source {source_name}: No URL provided")
                continue
            
            self.logger.info(f"Processing source: {source_name} ({base_url})")
            
            # Get selectors for article links and content
            link_selector = source.get("selectors", {}).get("article_links", "a")
            article_selectors = {
                "title": source.get("selectors", {}).get("title", "h1"),
                "content": source.get("selectors", {}).get("content", "article"),
                "date": source.get("selectors", {}).get("date", "time"),
                "author": source.get("selectors", {}).get("author", ".author")
            }
            
            # First, get article links from the main page
            article_links = self._get_article_links(base_url, link_selector)
            self.logger.info(f"Found {len(article_links)} article links from {source_name}")
            
            # Then, process each article
            source_articles = []
            for link in article_links[:5]:  # Limit to 5 articles per source
                article = self._process_article(link, article_selectors, source_name)
                
                if article:
                    # Check if the article contains any of the keywords
                    article_text = (article.get("title", "") + " " + article.get("content", "")).lower()
                    matches = [keyword for keyword in keywords if keyword.lower() in article_text]
                    
                    if matches:
                        article["keywords"] = matches
                        source_articles.append(article)
                        self.logger.info(f"Article matched {len(matches)} keywords: {article.get('title', '')}")
                    else:
                        self.logger.debug(f"Article did not match any keywords: {article.get('title', '')}")
            
            self.logger.info(f"Collected {len(source_articles)} articles from {source_name}")
            all_articles.extend(source_articles)
        
        # Save collected articles
        self._save_articles(all_articles)
        
        self.logger.info(f"Total articles collected: {len(all_articles)}")
        return all_articles
    
    def _get_article_links(self, url, selector='a'):
        """
        Get links to articles from a page
        
        Args:
            url (str): URL to scrape for links
            selector (str): CSS selector for article links
            
        Returns:
            list: List of article URLs
        """
        try:
            response = self._make_api_request('scrape', {
                'url': url,
                'formats': ['json'],
                'jsonOptions': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'links': {
                                'type': 'array',
                                'items': {'type': 'string'},
                                'description': 'Links to articles on the page'
                            }
                        }
                    }
                }
            })
            
            if 'data' in response and 'json' in response['data']:
                data = response['data']['json']
                if 'links' in data and isinstance(data['links'], list):
                    # Basic filtering for likely article links
                    article_links = [
                        link for link in data['links']
                        if any(pattern in link.lower() for pattern in ['/news/', '/article/', '/story/', '/business/'])
                    ]
                    return article_links[:10]  # Limit to 10 links for testing purposes
            
            self.logger.warning(f"No article links found on {url}")
            return []
        except Exception as e:
            self.logger.error(f"Error getting article links from {url}: {e}")
            return []

    def _extract_article_content(self, url):
        """
        Extract content from an article URL
        
        Args:
            url (str): URL of the article to extract content from
            
        Returns:
            dict: Extracted article data including title, content, and metadata
        """
        try:
            # Define the article schema
            article_schema = {
                "type": "object",
                "properties": {
                    "title": {
                        "type": "string",
                        "description": "The title or headline of the article"
                    },
                    "content": {
                        "type": "string",
                        "description": "The main content of the article"
                    },
                    "published_date": {
                        "type": "string",
                        "description": "When the article was published"
                    },
                    "author": {
                        "type": "string",
                        "description": "The author of the article"
                    },
                    "category": {
                        "type": "string",
                        "description": "The category or section of the article"
                    },
                    "summary": {
                        "type": "string",
                        "description": "A brief summary of the article (2-3 sentences)"
                    }
                }
            }
            
            response = self._make_api_request('scrape', {
                'url': url,
                'formats': ['json', 'markdown'],
                'jsonOptions': {
                    'schema': article_schema
                }
            })
            
            if 'data' in response:
                data = {}
                
                # Extract structured data if available
                if 'json' in response['data'] and response['data']['json']:
                    data = response['data']['json']
                    
                # Ensure we have content - if not, use markdown as fallback
                if (not data.get('content') or len(data.get('content', '')) < 100) and 'markdown' in response['data']:
                    data['content'] = response['data']['markdown']
                    
                    # If no title either, try to extract from markdown
                    if not data.get('title'):
                        markdown_lines = response['data']['markdown'].split('\n')
                        for line in markdown_lines[:5]:  # Check first 5 lines
                            if line.startswith('# '):
                                data['title'] = line.replace('# ', '')
                                break
                
                # Set URL and source fields
                data['url'] = url
                data['source'] = self._extract_source_from_url(url)
                
                return data
            
            self.logger.warning(f"No data extracted from {url}")
            return None
        except Exception as e:
            self.logger.error(f"Error extracting content from {url}: {e}")
            return None
    
    def _process_article(self, url, selectors, source_name):
        """
        Process an article using Firecrawl.
        
        Args:
            url (str): URL of the article.
            selectors (dict): CSS selectors for article content.
            source_name (str): Name of the news source.
            
        Returns:
            dict: Processed article data.
        """
        endpoint = f"{self.base_url}/extract"
        
        # Prepare request payload
        payload = {
            "url": url,
            "selectors": selectors,
            "js_rendering": True,
            "headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        }
        
        # Set headers with API key
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        try:
            self.logger.info(f"Processing article: {url}")
            response = requests.post(endpoint, json=payload, headers=headers)
            response.raise_for_status()
            
            result = response.json()
            
            if "data" in result:
                data = result["data"]
                
                # Format the article data
                article = {
                    "url": url,
                    "source_name": source_name,
                    "title": data.get("title", ""),
                    "content": data.get("content", ""),
                    "date": data.get("date", ""),
                    "author": data.get("author", ""),
                    "timestamp": datetime.now().isoformat()
                }
                
                return article
            
            self.logger.warning(f"No data extracted from article: {url}")
            return None
        
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Error processing article {url}: {str(e)}")
            return None
    
    def _save_articles(self, articles):
        """
        Save collected articles to files.
        
        Args:
            articles (list): List of article dictionaries.
        """
        if not articles:
            self.logger.warning("No articles to save")
            return
        
        # Create timestamp for filenames
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Save as JSON
        json_file = os.path.join(self.data_dir, f"articles_{timestamp}.json")
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2)
        
        # Save as CSV
        csv_file = os.path.join(self.data_dir, f"articles_{timestamp}.csv")
        with open(csv_file, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Write header
            writer.writerow([
                "URL", "Source", "Title", "Date", "Author", 
                "Content Length", "Keywords", "Timestamp"
            ])
            # Write data
            for article in articles:
                writer.writerow([
                    article.get("url", ""),
                    article.get("source_name", ""),
                    article.get("title", ""),
                    article.get("date", ""),
                    article.get("author", ""),
                    len(article.get("content", "")),
                    ", ".join(article.get("keywords", [])),
                    article.get("timestamp", "")
                ])
        
        self.logger.info(f"Saved {len(articles)} articles to {json_file} and {csv_file}")

    def _extract_source_from_url(self, url):
        """
        Extract the source name from a URL
        
        Args:
            url (str): URL to extract source from
            
        Returns:
            str: Source name
        """
        try:
            # Parse the URL
            parsed_url = urlparse(url)
            
            # Get the domain
            domain = parsed_url.netloc
            
            # Remove www. if present
            if domain.startswith('www.'):
                domain = domain[4:]
                
            # Extract the main domain (e.g., gulfnews.com from gulfnews.com)
            parts = domain.split('.')
            if len(parts) >= 2:
                main_domain = parts[-2]  # Second-to-last part is usually the main domain
                return main_domain.capitalize()
            
            return domain
        except Exception as e:
            self.logger.error(f"Error extracting source from URL {url}: {e}")
            return "Unknown"

def main():
    """Main function to run the Firecrawl news collector."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Collect news articles using Firecrawl API")
    parser.add_argument("--api-key", help="Your Firecrawl API key")
    parser.add_argument("--config", help="Path to news sources configuration file")
    parser.add_argument("--keywords", help="Comma-separated list of keywords to filter articles by")
    args = parser.parse_args()
    
    # Set API key if provided
    if args.api_key:
        os.environ["FIRECRAWL_API_KEY"] = args.api_key
    
    # Parse keywords if provided
    keywords = None
    if args.keywords:
        keywords = [k.strip() for k in args.keywords.split(",")]
    
    # Initialize collector with optional config file
    collector = FirecrawlNewsCollector(config_file=args.config)
    
    # Collect news
    articles = collector.collect_news(keywords=keywords)
    
    print(f"\n=== Firecrawl News Collection Results ===")
    print(f"Total articles collected: {len(articles)}")
    
    # Display article information
    for i, article in enumerate(articles[:5]):  # Show first 5 articles
        print(f"\n{i+1}. {article.get('title', 'Untitled')}")
        print(f"   Source: {article.get('source_name', 'Unknown')}")
        print(f"   URL: {article.get('url', 'N/A')}")
        print(f"   Date: {article.get('date', 'N/A')}")
        print(f"   Keywords: {', '.join(article.get('keywords', []))}")
    
    if len(articles) > 5:
        print(f"\n... and {len(articles) - 5} more articles")

if __name__ == "__main__":
    main() 