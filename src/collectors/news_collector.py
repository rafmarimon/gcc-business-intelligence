import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
import logging
import re
import urllib3
import time
import csv
from urllib.parse import urljoin

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NewsCollector")

# Suppress SSL verification warnings when necessary
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Import our robust API utilities if available
try:
    from src.utils.api_utils import make_api_request, robust_api_request
    API_UTILS_AVAILABLE = True
except ImportError:
    API_UTILS_AVAILABLE = False
    import requests  # Fallback to regular requests

class GCCBusinessNewsCollector:
    """
    Collects business news from UAE/GCC sources using requests and BeautifulSoup.
    """
    def __init__(self, config_path='config/news_sources.json'):
        """Initialize the news collector with configuration."""
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
        self.data_dir = os.path.join('data', 'news')
        os.makedirs(self.data_dir, exist_ok=True)

        # Initialize cache if API utils is not available
        if not API_UTILS_AVAILABLE:
            self._request_cache = {}

    def _load_sources(self):
        """Load news sources from the configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                sources_dict = {}
                
                # Handle different possible structures
                if isinstance(config, dict) and 'sources' in config:
                    # Convert list to dictionary with name as keys
                    for source in config['sources']:
                        if isinstance(source, dict) and 'name' in source:
                            sources_dict[source['name']] = source
                        else:
                            # If no name, use index
                            sources_dict[f"source_{len(sources_dict)}"] = source
                    return sources_dict
                elif isinstance(config, list):
                    # Convert list to dictionary with indices as keys
                    for idx, source in enumerate(config):
                        if isinstance(source, dict) and 'name' in source:
                            sources_dict[source['name']] = source
                        else:
                            sources_dict[f"source_{idx}"] = source
                    return sources_dict
                else:
                    # Assume the config itself is a dictionary of sources
                    return config
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading sources: {e}")
            return {}

    def collect_news(self, days_back=1, limit_per_source=10, focus_keywords=None):
        """Collect business news from all configured sources.
        
        Args:
            days_back: Number of days to look back for news
            limit_per_source: Maximum articles to collect per source
            focus_keywords: List of keywords to focus on (for client-specific reports)
            
        Returns:
            List of articles with standard fields
        """
        try:
            logger.info(f"Starting news collection (days_back={days_back}, limit_per_source={limit_per_source})")
            if focus_keywords:
                logger.info(f"Focusing on keywords: {', '.join(focus_keywords)}")
            
            # Initialize results
            all_articles = []
            
            # Loop through each source and collect
            for source_name, source_config in self.sources.items():
                try:
                    logger.info(f"Collecting from {source_name}...")
                    
                    # Get source config
                    url = source_config['url']
                    source_type = source_config.get('type', 'rss')
                    country = source_config.get('country', 'UAE')
                    category = source_config.get('category', 'Business')
                    
                    # Skip invalid sources
                    if not url:
                        logger.warning(f"Skipping {source_name} - missing URL")
                        continue
                    
                    # Collect based on source type
                    source_articles = []
                    if source_type == 'rss':
                        source_articles = self._collect_from_rss(url, source_name, country, category, days_back, limit_per_source)
                    elif source_type == 'api':
                        source_articles = self._collect_from_api(url, source_name, country, category, days_back, limit_per_source)
                    elif source_type == 'html':
                        # Pass the entire source_config for HTML sources
                        source_articles = self._collect_from_html(url, source_name, country, category, source_config, days_back, limit_per_source)
                    else:
                        logger.warning(f"Skipping {source_name} - unknown type: {source_type}")
                        continue
                    
                    # Filter articles based on focus keywords if provided
                    if focus_keywords and source_articles:
                        filtered_articles = []
                        for article in source_articles:
                            text_to_search = (article.get('title', '') + ' ' + 
                                             article.get('summary', '') + ' ' + 
                                             article.get('content', '')).lower()
                            
                            # Check if any focus keyword is mentioned
                            if any(keyword.lower() in text_to_search for keyword in focus_keywords):
                                filtered_articles.append(article)
                        
                        # Log filtering results
                        logger.info(f"Filtered {source_name}: {len(filtered_articles)}/{len(source_articles)} articles match keywords")
                        source_articles = filtered_articles
                    
                    # Add articles to the main list
                    all_articles.extend(source_articles)
                    logger.info(f"Collected {len(source_articles)} articles from {source_name}")
                    
                except Exception as e:
                    logger.error(f"Error collecting from {source_name}: {e}")
                    continue
            
            # Log collection summary
            logger.info(f"Collection complete. Total articles: {len(all_articles)}")
            
            # Save to disk for later use
            self._save_articles(all_articles)
            
            return all_articles
            
        except Exception as e:
            logger.error(f"Error in news collection: {e}")
            return []
    
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
    
    def _collect_from_source(self, source):
        """Collect news from a specific source using requests and BeautifulSoup."""
        articles = []
        try:
            url = source['url']
            pattern = source['crawl_pattern']
            
            # Fetch the page using our robust request function
            logger.info(f"Fetching {url}...")
            result = self._make_request(url, verify=False)
            
            # Check for errors
            if 'error' in result:
                logger.error(f"Failed to fetch {url}: {result['error']}")
                return articles
                
            # Get response text
            response_text = result.get('text', '')
            if not response_text:
                logger.error(f"No content received from {url}")
                return articles
                
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response_text, 'html.parser')
            
            # Find all article elements
            article_elements = soup.select(pattern['article_selector'])
            logger.info(f"Found {len(article_elements)} article elements on {url}")
            
            if len(article_elements) == 0:
                # Try alternative selectors if the main one doesn't work
                alternative_selectors = [
                    "div[class*='story']", 
                    "div[class*='article']", 
                    "article", 
                    ".card", 
                    ".news-item",
                    "div[class*='news']"
                ]
                
                for alt_selector in alternative_selectors:
                    article_elements = soup.select(alt_selector)
                    if len(article_elements) > 0:
                        logger.info(f"Found {len(article_elements)} elements with alternate selector: {alt_selector}")
                        break
            
            for i, article_el in enumerate(article_elements):
                try:
                    # Try to extract headline with the configured selector
                    headline_el = article_el.select_one(pattern['headline_selector'])
                    
                    # If not found, try common headline selectors
                    if not headline_el:
                        for selector in ["*[class*='title'] a", "h2 a", "h3 a", "h4 a", ".title a", "a[class*='title']"]:
                            headline_el = article_el.select_one(selector)
                            if headline_el:
                                logger.debug(f"Found headline with alternate selector: {selector}")
                                break
                    
                    # If still not found, look for any text that looks like a headline
                    if not headline_el:
                        # Find all text nodes and look for headline-like content
                        for el in article_el.find_all():
                            if el.name in ['h1', 'h2', 'h3', 'h4', 'h5'] and el.get_text().strip():
                                headline_el = el
                                break
                    
                    headline = headline_el.get_text().strip() if headline_el else ""
                    
                    # Extract link - prioritize links in headlines
                    link = ""
                    if headline_el and headline_el.name == 'a':
                        link = headline_el.get('href', '')
                    elif headline_el:
                        link_in_headline = headline_el.find('a')
                        if link_in_headline:
                            link = link_in_headline.get('href', '')
                    
                    # If link not found in headline, try the configured link selector
                    if not link:
                        link_el = article_el.select_one(pattern['link_selector'])
                        link = link_el.get('href', '') if link_el else ""
                    
                    # If still no link, look for any prominent link
                    if not link:
                        links = article_el.find_all('a')
                        for a_tag in links:
                            # Skip empty links or those that are clearly navigation/category links
                            href = a_tag.get('href', '')
                            text = a_tag.get_text().strip()
                            if href and text and len(text) > 10 and not re.search(r'(more|category|tag|author)', text.lower()):
                                link = href
                                break
                    
                    # Fix relative URLs
                    if link and not (link.startswith('http://') or link.startswith('https://')):
                        base_url = '/'.join(url.split('/')[:3])  # Get domain part
                        link = f"{base_url}{'' if link.startswith('/') else '/'}{link}"
                    
                    # Extract summary - try configured selector first
                    summary_el = article_el.select_one(pattern['summary_selector'])
                    
                    # If not found, try common summary selectors
                    if not summary_el:
                        for selector in ["*[class*='summary']", "*[class*='teaser']", "*[class*='desc']", "p"]:
                            summary_el = article_el.select_one(selector)
                            if summary_el:
                                break
                    
                    # If still not found, use the first paragraph that's not the headline
                    if not summary_el:
                        paragraphs = article_el.find_all('p')
                        for p in paragraphs:
                            p_text = p.get_text().strip()
                            if p_text and p_text != headline and len(p_text) > 20:
                                summary_el = p
                                break
                    
                    summary = summary_el.get_text().strip() if summary_el else ""
                    
                    # Extract date - try configured selector first
                    date_el = article_el.select_one(pattern['date_selector'])
                    
                    # If not found, try common date selectors
                    if not date_el:
                        for selector in ["time", "*[class*='date']", "*[class*='time']", "*[datetime]"]:
                            date_el = article_el.select_one(selector)
                            if date_el:
                                break
                    
                    date_str = date_el.get_text().strip() if date_el else ""
                    
                    # Sometimes the date is in a datetime attribute
                    if date_el and not date_str and date_el.has_attr('datetime'):
                        date_str = date_el['datetime']
                    
                    # Only add articles that have at least a headline and link
                    if headline and link:
                        # Skip duplicates
                        is_duplicate = False
                        for existing in articles:
                            if existing['link'] == link or existing['headline'] == headline:
                                is_duplicate = True
                                break
                        
                        if not is_duplicate:
                            articles.append({
                                'headline': headline,
                                'link': link,
                                'summary': summary,
                                'date': date_str,
                                'url': url
                            })
                            
                            # Limit to 50 articles per source
                            if len(articles) >= 50:
                                logger.info(f"Reached maximum of 50 articles for {url}")
                                break
                    
                except Exception as e:
                    logger.warning(f"Error extracting article data ({i}): {e}")
                    continue
                    
            return articles
            
        except Exception as e:
            logger.error(f"Error in _collect_from_source: {e}")
            return articles
    
    def _collect_from_rss(self, url, source_name, country, category, days_back=1, limit=10):
        """Collect news from an RSS feed.
        
        Args:
            url: RSS feed URL
            source_name: Name of the source
            country: Country of the source
            category: Category of the news
            days_back: Number of days to look back
            limit: Maximum number of articles to collect
            
        Returns:
            List of articles with standard fields
        """
        import feedparser
        from datetime import datetime, timedelta
        import time
        
        articles = []
        try:
            logger.info(f"Fetching RSS feed from {url}...")
            
            # Use feedparser which handles the HTTP request internally
            # We wrap this with our retry mechanism
            feed = None
            retry_count = 0
            max_retries = 3
            
            while retry_count <= max_retries and not feed:
                try:
                    if retry_count > 0:
                        logger.info(f"Retry attempt {retry_count} for RSS feed {url}")
                        time.sleep(retry_count * 2)  # Simple backoff
                    
                    feed = feedparser.parse(url)
                    
                    # Check if feed parsing was successful
                    if not feed or not hasattr(feed, 'entries') or not feed.entries:
                        if retry_count < max_retries:
                            logger.warning(f"Failed to parse RSS feed from {url}, retrying...")
                            retry_count += 1
                            feed = None  # Reset to retry
                            continue
                        else:
                            logger.warning(f"Failed to parse RSS feed from {url} after {max_retries} attempts")
                            return articles
                except Exception as e:
                    if retry_count < max_retries:
                        logger.warning(f"Error parsing RSS feed {url}: {e}, retrying...")
                        retry_count += 1
                        continue
                    else:
                        logger.error(f"Failed to parse RSS feed {url} after {max_retries} attempts: {e}")
                        return articles
            
            # Calculate the cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_back)
            
            # Process each entry
            for i, entry in enumerate(feed.entries):
                if i >= limit:
                    break
                
                try:
                    # Extract basic info
                    title = entry.get('title', '').strip()
                    link = entry.get('link', '').strip()
                    summary = entry.get('summary', '').strip()
                    content = ''
                    
                    # Try to get content if available
                    if 'content' in entry:
                        content = entry.content[0].value if isinstance(entry.content, list) else entry.content
                    elif 'description' in entry and not summary:
                        summary = entry.description
                        
                    # Clean HTML from summary
                    if summary:
                        summary = re.sub(r'<.*?>', '', summary)
                        
                    # Get the publication date
                    pub_date = None
                    date_str = ''
                    
                    if 'published_parsed' in entry and entry.published_parsed:
                        pub_date = datetime.fromtimestamp(time.mktime(entry.published_parsed))
                        date_str = pub_date.strftime('%Y-%m-%d %H:%M:%S')
                    elif 'updated_parsed' in entry and entry.updated_parsed:
                        pub_date = datetime.fromtimestamp(time.mktime(entry.updated_parsed))
                        date_str = pub_date.strftime('%Y-%m-%d %H:%M:%S')
                        
                    # Skip old articles if we have a date
                    if pub_date and pub_date < cutoff_date:
                        continue
                        
                    # Create article object
                    if title and link:
                        article = {
                            'title': title,
                            'url': link,
                            'source': source_name,
                            'country': country,
                            'category': category,
                            'summary': summary,
                            'content': content,
                            'published_date': date_str,
                            'collected_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        articles.append(article)
                        
                except Exception as e:
                    logger.warning(f"Error processing RSS entry: {e}")
                    continue
                    
            logger.info(f"Collected {len(articles)} articles from RSS feed {source_name}")
            return articles
            
        except Exception as e:
            logger.error(f"Error in _collect_from_rss for {source_name}: {e}")
            return articles
            
    def _collect_from_api(self, url, source_name, country, category, days_back=1, limit=10):
        """Collect news from an API endpoint.
        
        Args:
            url: API endpoint URL
            source_name: Name of the source
            country: Country of the source
            category: Category of the news
            days_back: Number of days to look back
            limit: Maximum number of articles to collect
            
        Returns:
            List of articles with standard fields
        """
        from datetime import datetime, timedelta
        
        articles = []
        try:
            logger.info(f"Fetching from API {url}...")
            
            # Calculate the cutoff date
            cutoff_date = datetime.now() - timedelta(days=days_back)
            cutoff_str = cutoff_date.strftime('%Y-%m-%d')
            
            # Some APIs require API keys
            api_key = os.environ.get('NEWS_API_KEY', '')
            
            # Adjust URL if needed (add API key, date range, etc.)
            if 'newsapi.org' in url:
                if '?' in url:
                    url += f"&apiKey={api_key}&from={cutoff_str}&pageSize={limit}"
                else:
                    url += f"?apiKey={api_key}&from={cutoff_str}&pageSize={limit}"
            
            # Use our robust request function
            result = self._make_request(url, verify=False)
            
            # Check for errors
            if 'error' in result:
                logger.error(f"Failed to fetch API {url}: {result['error']}")
                return articles
                
            # Check if we have JSON data
            if not isinstance(result, dict) or ('text' in result and 'status_code' in result):
                # If we got a text response instead of JSON
                if 'status_code' in result and result['status_code'] != 200:
                    logger.warning(f"API request failed: {result['status_code']}")
                    return articles
                    
                # Try to parse the text as JSON
                try:
                    data = json.loads(result.get('text', '{}'))
                except:
                    logger.error(f"Failed to parse API response as JSON")
                    return articles
            else:
                # We already have parsed JSON
                data = result
            
            # Different APIs have different formats, handle common ones
            # NewsAPI format
            if 'articles' in data:
                items = data['articles']
                for item in items[:limit]:
                    title = item.get('title', '').strip()
                    url = item.get('url', '').strip()
                    summary = item.get('description', '').strip()
                    content = item.get('content', '').strip()
                    source = item.get('source', {}).get('name', source_name)
                    pub_date = item.get('publishedAt', '')
                    
                    if title and url:
                        article = {
                            'title': title,
                            'url': url,
                            'source': source,
                            'country': country,
                            'category': category,
                            'summary': summary,
                            'content': content,
                            'published_date': pub_date,
                            'collected_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        articles.append(article)
            
            # Other common API formats can be added here
            
            logger.info(f"Collected {len(articles)} articles from API {source_name}")
            return articles
            
        except Exception as e:
            logger.error(f"Error in _collect_from_api for {source_name}: {e}")
            return articles
            
    def _collect_from_html(self, url, source_name, country, category, selectors, days_back=1, limit=10):
        """Collect news by scraping HTML.
        
        Args:
            url: Website URL to scrape
            source_name: Name of the source
            country: Country of the source
            category: Category of the news
            selectors: CSS selectors for extracting content
            days_back: Number of days to look back
            limit: Maximum number of articles to collect
            
        Returns:
            List of articles with standard fields
        """
        articles = []
        try:
            logger.info(f"Scraping HTML from {url}...")
            
            # Get the selectors - if selectors is a dictionary with crawl_pattern, use that
            if isinstance(selectors, dict) and 'crawl_pattern' in selectors:
                selectors = selectors['crawl_pattern']
            
            # Use the appropriate selectors from crawl_pattern
            article_selector = selectors.get('article_selector', 'article, .article, .news-item, .card')
            title_selector = selectors.get('headline_selector', 'h1, h2, h3, .title, .headline')
            link_selector = selectors.get('link_selector', 'a')
            summary_selector = selectors.get('summary_selector', '.summary, .description, p')
            date_selector = selectors.get('date_selector', '.date, .time, time')
            
            # Fetch the page with our robust request function
            result = self._make_request(url, verify=False)
            
            # Check for errors
            if 'error' in result:
                logger.error(f"Failed to fetch HTML from {url}: {result['error']}")
                return articles
                
            # Get response text
            response_text = result.get('text', '')
            if not response_text:
                logger.error(f"No content received from {url}")
                return articles
                
            # Check status code
            if 'status_code' in result and result['status_code'] != 200:
                logger.warning(f"Failed to fetch HTML: {result['status_code']}")
                return articles
                
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response_text, 'html.parser')
            
            # Find all article elements
            article_elements = soup.select(article_selector)
            logger.info(f"Found {len(article_elements)} article elements on {url}")
            
            # Process each article
            for i, article_el in enumerate(article_elements[:limit]):
                try:
                    # Extract title
                    title_el = article_el.select_one(title_selector)
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
                        link_el = article_el.select_one(link_selector)
                        if link_el:
                            link = link_el.get('href', '')
                    
                    # Fix relative URLs
                    if link and not (link.startswith('http://') or link.startswith('https://')):
                        base_url = '/'.join(url.split('/')[:3])
                        link = f"{base_url}{'' if link.startswith('/') else '/'}{link}"
                    
                    # Extract summary
                    summary_el = article_el.select_one(summary_selector)
                    summary = summary_el.get_text().strip() if summary_el else ""
                    
                    # Extract date
                    date_el = article_el.select_one(date_selector)
                    date_str = date_el.get_text().strip() if date_el else ""
                    
                    # Format date if possible
                    pub_date = date_str
                    if date_str:
                        try:
                            # Try to parse common date formats
                            # This is a simplified approach - real implementation would need more robust date parsing
                            date_obj = None
                            if re.match(r'\d+ \w+ ago', date_str):
                                # Handle relative dates like "2 hours ago"
                                from datetime import datetime, timedelta
                                num = int(re.search(r'\d+', date_str).group())
                                if 'minute' in date_str:
                                    date_obj = datetime.now() - timedelta(minutes=num)
                                elif 'hour' in date_str:
                                    date_obj = datetime.now() - timedelta(hours=num)
                                elif 'day' in date_str:
                                    date_obj = datetime.now() - timedelta(days=num)
                                elif 'week' in date_str:
                                    date_obj = datetime.now() - timedelta(days=num*7)
                                elif 'month' in date_str:
                                    date_obj = datetime.now() - timedelta(days=num*30)
                                
                            if date_obj:
                                pub_date = date_obj.strftime('%Y-%m-%d %H:%M:%S')
                        except:
                            # If date parsing fails, just use the original string
                            pass
                    
                    # Create article object if we have at least title and link
                    if title and link:
                        article = {
                            'title': title,
                            'url': link,
                            'source': source_name,
                            'country': country,
                            'category': category,
                            'summary': summary,
                            'content': '',
                            'published_date': pub_date,
                            'collected_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        }
                        articles.append(article)
                    
                except Exception as e:
                    logger.warning(f"Error extracting article data ({i}): {e}")
                    continue
                    
            logger.info(f"Collected {len(articles)} articles from HTML {source_name}")
            return articles
            
        except Exception as e:
            logger.error(f"Error in _collect_from_html for {source_name}: {e}")
            return articles
    
    def _save_articles(self, articles):
        """Save collected articles to disk for later use."""
        if not articles:
            logger.warning("No articles to save.")
            return
        
        # Create timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
        # Save as JSON
        json_path = f'data/news_data_{timestamp}.json'
        with open(json_path, 'w') as f:
            json.dump(articles, f, indent=2)
        
        # Save as CSV
        try:
            df = pd.DataFrame(articles)
            csv_path = f'data/news_data_{timestamp}.csv'
            df.to_csv(csv_path, index=False)
            logger.info(f"Saved {len(articles)} articles to {csv_path} and {json_path}")
        except Exception as e:
            logger.error(f"Error saving to CSV: {e}")
            logger.info(f"Saved {len(articles)} articles to {json_path}")

if __name__ == "__main__":
    # Test the collector
    collector = GCCBusinessNewsCollector()
    articles = collector.collect_news()
    print(f"Collected {len(articles)} articles in total.") 