#!/usr/bin/env python3
"""
FirecrawlSDKCollector - News collection using Firecrawl SDK

This script implements a news collection system using the official Firecrawl SDK
instead of direct API calls. It provides better error handling, type safety with
Pydantic models, and access to advanced Firecrawl features.
"""

import os
import json
import logging
import argparse
import time
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
import csv
from dotenv import load_dotenv

# Import the Firecrawl SDK
try:
    from firecrawl import FirecrawlApp
    from pydantic import BaseModel, Field
except ImportError:
    print("Please install the Firecrawl SDK: pip install firecrawl-py pydantic")
    exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(f"logs/firecrawl_sdk_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger("firecrawl_sdk_collector")

# Ensure logs directory exists
Path("logs").mkdir(exist_ok=True)
# Ensure data directory exists
Path("data/news").mkdir(parents=True, exist_ok=True)

class ArticleSchema(BaseModel):
    """Pydantic schema for news article extraction"""
    title: str = Field(..., description="The title of the article")
    content: Optional[str] = Field(None, description="The main content of the article")
    publication_date: Optional[str] = Field(None, description="When the article was published")
    author: Optional[str] = Field(None, description="Author of the article")
    summary: Optional[str] = Field(None, description="Summary or excerpt of the article")
    url: str = Field(..., description="The URL of the article")
    source: str = Field(..., description="The name of the news source")

class NewsCollection(BaseModel):
    """Schema for a collection of articles"""
    articles: List[ArticleSchema] = Field(..., description="List of news articles")


class FirecrawlSDKNewsCollector:
    """
    News collector using the Firecrawl SDK to scrape and process news articles
    from configured sources, filtering by keywords.
    """
    
    def __init__(self, api_key: str, config_file: str):
        """
        Initialize the news collector with API key and configuration file
        
        Args:
            api_key (str): Firecrawl API key
            config_file (str): Path to the JSON configuration file containing news sources
        """
        self.api_key = api_key
        self.config_file = config_file
        self.sources = []
        
        # Initialize the Firecrawl SDK client
        self.firecrawl = FirecrawlApp(api_key=api_key)
        
        # Setup logger
        self.logger = logging.getLogger("firecrawl_sdk_collector")
        
        # Load configuration
        self._load_sources()
        
        # Collection of articles
        self.articles = []
        
    def _load_sources(self):
        """Load news sources from the configuration file"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.sources = config.get('sources', [])
                self.logger.info(f"Loaded {len(self.sources)} sources from {self.config_file}")
        except Exception as e:
            self.logger.error(f"Failed to load sources from {self.config_file}: {e}")
            self.sources = []
            
    def collect_news(self, keywords: List[str] = None) -> List[Dict[str, Any]]:
        """
        Collect news articles from configured sources, filtering by keywords
        
        Args:
            keywords (List[str], optional): List of keywords to filter articles by
            
        Returns:
            List[Dict[str, Any]]: List of collected articles
        """
        self.articles = []
        start_time = time.time()
        
        self.logger.info(f"Starting news collection for {len(keywords or [])} keywords from {len(self.sources)} sources")
        
        for source in self.sources:
            source_name = source.get('name', 'Unknown')
            source_url = source.get('url', '')
            
            if not source_url:
                self.logger.warning(f"Skipping source {source_name} - no URL provided")
                continue
                
            self.logger.info(f"Processing source: {source_name} ({source_url})")
            
            try:
                # Get article links from main page
                article_links = self._get_article_links(source_url)
                self.logger.info(f"Found {len(article_links)} article links for {source_name}")
                
                # Process each article
                for article_url in article_links:
                    # Check if the article might be relevant based on URL
                    if keywords and not any(keyword.lower() in article_url.lower() for keyword in keywords):
                        continue
                        
                    article_data = self._process_article(article_url, source_name, source)
                    if article_data:
                        # Filter by keywords in title/content if we have keywords
                        if keywords:
                            article_text = f"{article_data.get('title', '')} {article_data.get('content', '')}".lower()
                            if any(keyword.lower() in article_text for keyword in keywords):
                                self.articles.append(article_data)
                        else:
                            self.articles.append(article_data)
            
            except Exception as e:
                self.logger.error(f"Error processing source {source_name}: {e}")
                
        # Save the collected articles
        if self.articles:
            self._save_articles()
            
        elapsed_time = time.time() - start_time
        self.logger.info(f"Collection completed in {elapsed_time:.2f} seconds. Found {len(self.articles)} articles.")
        
        return self.articles
    
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
            # Using SDK to scrape the page
            response = self.firecrawl.scrape_url(url, params={
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
            
            if response and 'data' in response and 'json' in response['data']:
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
    
    def _process_article(self, article_url: str, source_name: str, source_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process an article URL to extract content using Firecrawl SDK
        
        Args:
            article_url (str): URL of the article
            source_name (str): Name of the source
            source_config (Dict[str, Any]): Source configuration
            
        Returns:
            Dict[str, Any]: Extracted article data
        """
        try:
            # Define article schema for extraction
            article_schema = ArticleSchema.model_json_schema()
            
            # Extract article data with updated API format
            response = self.firecrawl.scrape_url(article_url, params={
                'formats': ['json', 'markdown'],
                'jsonOptions': {
                    'schema': article_schema
                }
            })
            
            if response and 'data' in response and 'json' in response['data']:
                article_data = response['data']['json']
                # Ensure we have the source name
                article_data['source'] = source_name
                # Ensure we have the URL
                article_data['url'] = article_url
                return article_data
            
            return None
            
        except Exception as e:
            self.logger.error(f"Error processing article {article_url}: {e}")
            return None
    
    def _save_articles(self):
        """Save collected articles to JSON and CSV files"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Create output file paths
        json_file = f"data/news/firecrawl_sdk_news_{timestamp}.json"
        csv_file = f"data/news/firecrawl_sdk_news_{timestamp}.csv"
        
        # Save as JSON
        try:
            with open(json_file, 'w') as f:
                json.dump({'articles': self.articles}, f, indent=2)
            self.logger.info(f"Saved {len(self.articles)} articles to {json_file}")
        except Exception as e:
            self.logger.error(f"Error saving articles to JSON: {e}")
        
        # Save as CSV
        try:
            if self.articles:
                # Get all possible fields from the articles
                fieldnames = set()
                for article in self.articles:
                    fieldnames.update(article.keys())
                fieldnames = sorted(list(fieldnames))
                
                with open(csv_file, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(self.articles)
                self.logger.info(f"Saved {len(self.articles)} articles to {csv_file}")
        except Exception as e:
            self.logger.error(f"Error saving articles to CSV: {e}")


def main():
    """Main entry point for the script"""
    parser = argparse.ArgumentParser(description='Collect news articles using Firecrawl SDK')
    parser.add_argument('--config', default='config/firecrawl_sources.json', help='Path to configuration file')
    parser.add_argument('--keywords', nargs='+', help='Keywords to filter articles')
    parser.add_argument('--api-key', help='Firecrawl API key (overrides .env)')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    # Get API key
    api_key = args.api_key or os.getenv('FIRECRAWL_API_KEY')
    if not api_key:
        logger.error("No Firecrawl API key provided. Set FIRECRAWL_API_KEY in .env or use --api-key")
        return
    
    # Initialize collector
    collector = FirecrawlSDKNewsCollector(api_key=api_key, config_file=args.config)
    
    # Get keywords to filter articles
    keywords = args.keywords or []
    logger.info(f"Starting collection with keywords: {keywords}")
    
    # Collect news
    articles = collector.collect_news(keywords=keywords)
    
    logger.info(f"Collection complete. Found {len(articles)} articles.")
    
    
if __name__ == "__main__":
    main() 