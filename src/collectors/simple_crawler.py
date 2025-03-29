#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Simple Crawler Module for Market Intelligence Platform.

This module provides functionality to crawl web pages, extract content,
and store it in Redis for later use in reports and analysis.
"""

import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.redis_cache import get_redis_cache

# Optional Playwright import for JavaScript rendering
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

# Load environment variables
load_dotenv()

# Configure logging
logger = logging.getLogger(__name__)

class SimpleCrawler:
    """
    Simple web crawler that extracts content from URLs and stores it in Redis.
    
    Attributes:
        redis_cache: Redis cache instance for storing crawled data
        user_agent: User agent string to use for HTTP requests
        timeout: HTTP request timeout in seconds
        use_playwright: Whether to use Playwright for JavaScript rendering
    """
    
    def __init__(self):
        """Initialize the simple crawler."""
        self.redis_cache = get_redis_cache()
        
        # Load configuration from environment variables
        self.user_agent = os.getenv('USER_AGENT', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
        self.timeout = int(os.getenv('CRAWLER_TIMEOUT', '30'))
        self.use_playwright = os.getenv('USE_PLAYWRIGHT', 'false').lower() == 'true'
        
        # Initialize Playwright if needed
        self.browser = None
        if self.use_playwright:
            try:
                self.playwright = sync_playwright().start()
                self.browser = self.playwright.chromium.launch(headless=True)
                logger.info("Playwright initialized for JavaScript rendering")
            except ImportError:
                logger.warning("Playwright not installed. JavaScript rendering disabled.")
                self.use_playwright = False
            except Exception as e:
                logger.error(f"Error initializing Playwright: {str(e)}")
                self.use_playwright = False
        
        logger.info(f"SimpleCrawler initialized (JavaScript rendering: {'enabled' if self.use_playwright else 'disabled'})")
    
    def __del__(self):
        """Clean up resources when the crawler is destroyed."""
        if self.use_playwright and self.browser:
            try:
                self.browser.close()
                self.playwright.stop()
                logger.info("Playwright resources cleaned up")
            except Exception as e:
                logger.error(f"Error cleaning up Playwright: {str(e)}")
    
    def _generate_article_id(self, url: str) -> str:
        """
        Generate a unique ID for an article based on its URL.
        
        Args:
            url: The URL to generate an ID for
            
        Returns:
            A unique ID string
        """
        # Create a hash of the URL for the ID
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return f"article-{url_hash}"
    
    def _extract_domain(self, url: str) -> str:
        """
        Extract the domain from a URL.
        
        Args:
            url: The URL to extract domain from
            
        Returns:
            The domain string
        """
        parsed_url = urlparse(url)
        domain = parsed_url.netloc
        return domain
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def _fetch_url_with_requests(self, url: str) -> str:
        """
        Fetch a URL using the requests library.
        
        Args:
            url: The URL to fetch
            
        Returns:
            The HTML content as a string
            
        Raises:
            Exception: If the request fails or returns a non-200 status code
        """
        headers = {
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=self.timeout)
            response.raise_for_status()  # Raise exception for non-200 status codes
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching URL {url}: {str(e)}")
            raise
    
    def _fetch_url_with_playwright(self, url: str) -> str:
        """
        Fetch a URL using Playwright for JavaScript rendering.
        
        Args:
            url: The URL to fetch
            
        Returns:
            The HTML content as a string
            
        Raises:
            Exception: If the request fails
        """
        if not self.browser:
            raise ValueError("Playwright browser not initialized")
        
        try:
            page = self.browser.new_page(user_agent=self.user_agent)
            page.goto(url, timeout=self.timeout * 1000)  # Playwright timeout is in ms
            
            # Wait for the page to load (adjust this based on your needs)
            page.wait_for_load_state("networkidle", timeout=self.timeout * 1000)
            
            content = page.content()
            page.close()
            return content
        except Exception as e:
            logger.error(f"Error fetching URL with Playwright {url}: {str(e)}")
            raise
    
    def _extract_content(self, html: str, url: str) -> Dict[str, Any]:
        """
        Extract title, text content, and metadata from HTML.
        
        Args:
            html: The HTML content
            url: The source URL
            
        Returns:
            Dictionary with extracted content
        """
        try:
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract title
            title = ''
            title_tag = soup.find('title')
            if title_tag and title_tag.text:
                title = title_tag.text.strip()
            
            # Try to extract from meta tags if no title found
            if not title:
                meta_title = soup.find('meta', property='og:title')
                if meta_title and meta_title.get('content'):
                    title = meta_title['content'].strip()
            
            # Try to extract from h1 if still no title
            if not title and soup.h1:
                title = soup.h1.text.strip()
            
            # Extract description from meta tags
            description = ''
            meta_desc = soup.find('meta', attrs={'name': 'description'})
            if meta_desc and meta_desc.get('content'):
                description = meta_desc['content'].strip()
            
            if not description:
                meta_desc = soup.find('meta', property='og:description')
                if meta_desc and meta_desc.get('content'):
                    description = meta_desc['content'].strip()
            
            # Extract the main content
            # This is a simple approach - real implementations would need more sophisticated content extraction
            
            # First, remove script, style and nav tags
            for tag in soup(['script', 'style', 'nav', 'header', 'footer', 'aside']):
                tag.decompose()
            
            # Get all paragraphs and headers
            content_tags = soup.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'article', 'section'])
            content = ' '.join([tag.get_text().strip() for tag in content_tags])
            
            # Clean up whitespace
            content = re.sub(r'\s+', ' ', content).strip()
            
            # If content is still empty, get all text
            if not content:
                content = soup.get_text()
                content = re.sub(r'\s+', ' ', content).strip()
            
            # Generate a summary (this could be enhanced with NLP later)
            summary = content[:1000] + '...' if len(content) > 1000 else content
            
            # Extract publication date
            pub_date = None
            meta_date = soup.find('meta', property='article:published_time')
            if meta_date and meta_date.get('content'):
                pub_date = meta_date['content']
            
            # Try other common date meta tags
            if not pub_date:
                for date_attr in ['date', 'pubdate', 'publishdate', 'timestamp', 'article:published_time']:
                    date_tag = soup.find('meta', attrs={'name': date_attr})
                    if date_tag and date_tag.get('content'):
                        pub_date = date_tag['content']
                        break
            
            # Extract keywords/tags
            keywords = []
            meta_keywords = soup.find('meta', attrs={'name': 'keywords'})
            if meta_keywords and meta_keywords.get('content'):
                keywords = [k.strip() for k in meta_keywords['content'].split(',')]
            
            # Return the extracted data
            result = {
                "title": title,
                "description": description,
                "content": content,
                "summary": summary,
                "url": url,
                "domain": self._extract_domain(url),
                "pub_date": pub_date,
                "extracted_at": datetime.now().isoformat(),
                "keywords": keywords
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error extracting content from {url}: {str(e)}")
            return {
                "title": "Error: Content Extraction Failed",
                "description": "",
                "content": "",
                "summary": f"Failed to extract content: {str(e)}",
                "url": url,
                "domain": self._extract_domain(url),
                "extracted_at": datetime.now().isoformat(),
                "error": str(e)
            }
    
    def _process_article_data(self, article_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process and enrich article data before storage.
        
        Args:
            article_data: The raw extracted article data
            
        Returns:
            Processed article data
        """
        # Generate a unique ID
        article_id = self._generate_article_id(article_data['url'])
        
        # Add timestamp for sorting
        article_data['timestamp'] = int(time.time())
        
        # Add article ID
        article_data['id'] = article_id
        
        # Extract potential topics/tags based on content
        if 'content' in article_data and article_data['content']:
            # This is a very simple approach - a real implementation would use NLP
            # to extract topics and entities
            keywords = article_data.get('keywords', [])
            
            # Add keywords from title
            if 'title' in article_data and article_data['title']:
                title_words = re.findall(r'\b[A-Za-z]{4,}\b', article_data['title'])
                for word in title_words:
                    if word.lower() not in [k.lower() for k in keywords]:
                        keywords.append(word)
            
            article_data['keywords'] = keywords[:10]  # Limit to top 10 keywords
            
            # Generate LLM-based summary if not already present
            if 'summary' not in article_data or not article_data['summary']:
                try:
                    summary = self._generate_summary_with_llm(article_data)
                    if summary:
                        article_data['summary'] = summary
                        logger.info(f"Generated LLM summary for article: {article_data.get('title', 'Unknown')}")
                except Exception as e:
                    logger.warning(f"Failed to generate LLM summary: {str(e)}")
        
        return article_data
    
    def _generate_summary_with_llm(self, article_data: Dict[str, Any]) -> Optional[str]:
        """
        Generate a summary for an article using OpenAI.
        
        Args:
            article_data: The article data dictionary
            
        Returns:
            Generated summary or None if failed
        """
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.warning("OpenAI API key not set. Cannot generate summary.")
            return None
            
        try:
            from openai import OpenAI
            
            content = article_data.get('content', '')
            if not content:
                return None
                
            # Truncate content if it's too long
            max_content_length = 4000  # Adjust based on token limits
            if len(content) > max_content_length:
                content = content[:max_content_length] + "..."
            
            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",  # Use a faster, cheaper model for summarization
                messages=[
                    {"role": "system", "content": "You are a helpful assistant that summarizes articles concisely."},
                    {"role": "user", "content": f"Please summarize the following article in 2-3 paragraphs:\n\n{content}"}
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            summary = response.choices[0].message.content.strip()
            return summary
            
        except Exception as e:
            logger.error(f"Error generating summary: {str(e)}")
            return None
    
    def _store_article(self, article_data: Dict[str, Any]) -> bool:
        """
        Store article data in Redis.
        
        Args:
            article_data: The processed article data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            article_id = article_data['id']
            
            # Store the article data
            article_key = f"article:{article_id}"
            self.redis_cache.set(article_key, article_data)
            
            # Add to recent articles list
            recent_articles_key = "recent_articles"
            recent_articles = self.redis_cache.get(recent_articles_key) or []
            
            # Add to front, keep the list at a reasonable size
            if article_id not in recent_articles:
                recent_articles.insert(0, article_id)
                recent_articles = recent_articles[:100]  # Keep only the 100 most recent
                self.redis_cache.set(recent_articles_key, recent_articles)
            
            # Index by domain
            domain = article_data.get('domain', '')
            if domain:
                domain_key = f"domain:{domain}"
                domain_articles = self.redis_cache.get(domain_key) or []
                if article_id not in domain_articles:
                    domain_articles.insert(0, article_id)
                    self.redis_cache.set(domain_key, domain_articles)
            
            # Index by keywords/tags
            keywords = article_data.get('keywords', [])
            for keyword in keywords:
                keyword_key = f"keyword:{keyword.lower()}"
                keyword_articles = self.redis_cache.get(keyword_key) or []
                if article_id not in keyword_articles:
                    keyword_articles.insert(0, article_id)
                    self.redis_cache.set(keyword_key, keyword_articles)
            
            # Index by client tags if present
            client_tags = article_data.get('client_tags', [])
            for tag in client_tags:
                tag_key = f"tag:{tag.lower()}"
                tag_articles = self.redis_cache.get(tag_key) or []
                if article_id not in tag_articles:
                    tag_articles.insert(0, article_id)
                    self.redis_cache.set(tag_key, tag_articles)
                    
                # Also index under articles key for this tag
                articles_key = f"articles:{tag.lower()}"
                tag_article_ids = self.redis_cache.get(articles_key) or []
                if article_id not in tag_article_ids:
                    tag_article_ids.insert(0, article_id)
                    self.redis_cache.set(articles_key, tag_article_ids)
            
            logger.info(f"Article stored successfully: {article_data.get('title', 'Unknown')} (ID: {article_id})")
            return True
            
        except Exception as e:
            logger.error(f"Error storing article: {str(e)}")
            return False
    
    def crawl_url(self, url: str, client_tags: Optional[List[str]] = None, use_playwright: Optional[bool] = None, force_update: bool = False) -> Dict[str, Any]:
        """
        Crawl a single URL and extract content.
        
        Args:
            url: The URL to crawl
            client_tags: Tags to associate with the article for client relevance
            use_playwright: Whether to use Playwright for this specific URL
            force_update: Whether to crawl even if the URL has been crawled recently
            
        Returns:
            The crawled and processed article data
        """
        # Check if we've already crawled this URL recently
        url_hash = hashlib.md5(url.encode()).hexdigest()
        article_id = f"article-{url_hash}"
        
        existing_article = self.redis_cache.get(f"article:{article_id}")
        
        # If we have a recent version and force_update is False, return the cached version
        if existing_article and not force_update:
            # Check if the article was crawled in the last 24 hours
            timestamp = existing_article.get('timestamp', 0)
            current_time = int(time.time())
            if current_time - timestamp < 86400:  # 24 hours in seconds
                logger.info(f"Using cached version of {url}")
                return existing_article
        
        try:
            logger.info(f"Crawling URL: {url}")
            
            # Determine whether to use Playwright for this specific URL
            should_use_playwright = use_playwright if use_playwright is not None else self.use_playwright
            
            # Fetch the HTML content
            if should_use_playwright and PLAYWRIGHT_AVAILABLE:
                html = self._fetch_url_with_playwright(url)
            else:
                html = self._fetch_url_with_requests(url)
            
            # Extract content from the HTML
            article_data = self._extract_content(html, url)
            
            # Process and enrich the article data
            processed_data = self._process_article_data(article_data)
            
            # Add client tags if provided
            if client_tags:
                processed_data['client_tags'] = client_tags
            
            # Store the processed article
            success = self._store_article(processed_data)
            
            if not success:
                logger.warning(f"Failed to store article data for {url}")
            
            # Add success flag
            processed_data['success'] = success
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error crawling URL {url}: {str(e)}")
            # Return a minimal error response
            error_data = {
                "id": article_id,
                "url": url,
                "title": "Error: Crawling Failed",
                "content": "",
                "summary": f"Failed to crawl URL: {str(e)}",
                "timestamp": int(time.time()),
                "error": str(e),
                "success": False
            }
            return error_data
    
    def crawl_urls(self, urls: List[str], force_update: bool = False) -> List[Dict[str, Any]]:
        """
        Crawl multiple URLs.
        
        Args:
            urls: List of URLs to crawl
            force_update: Whether to crawl even if URLs have been crawled recently
            
        Returns:
            List of crawled and processed article data
        """
        results = []
        for url in urls:
            try:
                article_data = self.crawl_url(url, force_update)
                results.append(article_data)
                # Small delay to avoid overloading servers
                time.sleep(1)
            except Exception as e:
                logger.error(f"Error in crawl_urls for {url}: {str(e)}")
        
        return results
    
    def get_article(self, article_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve an article by ID.
        
        Args:
            article_id: The article ID
            
        Returns:
            The article data or None if not found
        """
        article_key = f"article:{article_id}"
        article_data = self.redis_cache.get(article_key)
        return article_data
    
    def get_recent_articles(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recently crawled articles.
        
        Args:
            limit: Maximum number of articles to return
            
        Returns:
            List of article data
        """
        recent_articles_key = "recent_articles"
        recent_article_ids = self.redis_cache.get(recent_articles_key) or []
        
        results = []
        for article_id in recent_article_ids[:limit]:
            article_data = self.get_article(article_id)
            if article_data:
                results.append(article_data)
        
        return results
    
    def get_articles_by_domain(self, domain: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get articles from a specific domain.
        
        Args:
            domain: The domain to retrieve articles for
            limit: Maximum number of articles to return
            
        Returns:
            List of article data
        """
        domain_key = f"domain:{domain}"
        domain_article_ids = self.redis_cache.get(domain_key) or []
        
        results = []
        for article_id in domain_article_ids[:limit]:
            article_data = self.get_article(article_id)
            if article_data:
                results.append(article_data)
        
        return results
    
    def get_articles_by_keyword(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get articles matching a specific keyword.
        
        Args:
            keyword: The keyword to match
            limit: Maximum number of articles to return
            
        Returns:
            List of article data
        """
        keyword_key = f"keyword:{keyword.lower()}"
        keyword_article_ids = self.redis_cache.get(keyword_key) or []
        
        results = []
        for article_id in keyword_article_ids[:limit]:
            article_data = self.get_article(article_id)
            if article_data:
                results.append(article_data)
        
        return results
    
    def search_articles(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search for articles matching a query string.
        
        Args:
            query: The search query
            limit: Maximum number of articles to return
            
        Returns:
            List of matching article data
        """
        # This is a simple implementation - a real search would use more sophisticated techniques
        query = query.lower()
        query_terms = query.split()
        
        # Get all recent articles as a starting point
        recent_articles_key = "recent_articles"
        all_article_ids = self.redis_cache.get(recent_articles_key) or []
        
        # Score articles based on query match
        scored_articles = []
        
        for article_id in all_article_ids:
            article_data = self.get_article(article_id)
            if not article_data:
                continue
            
            score = 0
            
            # Check title
            title = article_data.get('title', '').lower()
            for term in query_terms:
                if term in title:
                    score += 10  # Title matches are weighted more heavily
            
            # Check description
            description = article_data.get('description', '').lower()
            for term in query_terms:
                if term in description:
                    score += 5
            
            # Check content snippet
            content = article_data.get('content', '')[:1000].lower()  # Check just the beginning
            for term in query_terms:
                if term in content:
                    score += 2
            
            # Check keywords
            keywords = [k.lower() for k in article_data.get('keywords', [])]
            for term in query_terms:
                if term in keywords:
                    score += 7
            
            if score > 0:
                scored_articles.append((score, article_data))
        
        # Sort by score (highest first)
        scored_articles.sort(key=lambda x: x[0], reverse=True)
        
        # Return the top results (just the article data, not the scores)
        return [article for _, article in scored_articles[:limit]]
    
    def get_articles_by_tag(self, tag: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get articles associated with a specific client tag.
        
        Args:
            tag: The client tag to retrieve articles for
            limit: Maximum number of articles to return
            
        Returns:
            List of article data
        """
        tag_key = f"tag:{tag.lower()}"
        tag_article_ids = self.redis_cache.get(tag_key) or []
        
        results = []
        for article_id in tag_article_ids[:limit]:
            article_data = self.get_article(article_id)
            if article_data:
                results.append(article_data)
        
        return results

# Create a singleton instance
_crawler = None

def get_crawler() -> SimpleCrawler:
    """
    Get the singleton crawler instance.
    
    Returns:
        The SimpleCrawler instance
    """
    global _crawler
    if _crawler is None:
        _crawler = SimpleCrawler()
    return _crawler 