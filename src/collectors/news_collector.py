import json
import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
from dotenv import load_dotenv
import logging
import re

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("NewsCollector")

class GCCBusinessNewsCollector:
    """
    Collects business news from UAE/GCC sources using requests and BeautifulSoup.
    """
    def __init__(self, config_path='config/news_sources.json'):
        """Initialize the news collector with configuration."""
        self.config_path = config_path
        self.sources = self._load_sources()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        
    def _load_sources(self):
        """Load news sources from the configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                return config.get('sources', [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Error loading sources: {e}")
            return []

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
                    selectors = source_config.get('selectors', {})
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
                        source_articles = self._collect_from_html(url, source_name, country, category, selectors, days_back, limit_per_source)
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
    
    def _collect_from_source(self, source):
        """Collect news from a specific source using requests and BeautifulSoup."""
        articles = []
        try:
            url = source['url']
            pattern = source['crawl_pattern']
            
            # Fetch the page
            logger.info(f"Fetching {url}...")
            response = requests.get(url, headers=self.headers, timeout=30)
            if response.status_code != 200:
                logger.error(f"Failed to fetch {url}: Status code {response.status_code}")
                return articles
                
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
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
            
            # Parse the RSS feed
            feed = feedparser.parse(url)
            
            # Check if feed parsing was successful
            if not feed or not hasattr(feed, 'entries'):
                logger.warning(f"Failed to parse RSS feed from {url}")
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
            
            # Make the API request
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"API request failed: {response.status_code} - {response.text}")
                return articles
                
            # Parse the response
            data = response.json()
            
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
            
            # Get the selectors
            article_selector = selectors.get('article', 'article, .article, .news-item, .card')
            title_selector = selectors.get('title', 'h1, h2, h3, .title, .headline')
            link_selector = selectors.get('link', 'a')
            summary_selector = selectors.get('summary', '.summary, .description, p')
            date_selector = selectors.get('date', '.date, .time, time')
            
            # Fetch the page
            response = requests.get(url, headers=self.headers, timeout=30)
            
            if response.status_code != 200:
                logger.warning(f"Failed to fetch HTML: {response.status_code}")
                return articles
                
            # Parse with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
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