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

    def collect_news(self):
        """Collect news from all configured sources."""
        all_articles = []
        
        for source in self.sources:
            logger.info(f"Collecting news from {source['name']}...")
            
            try:
                articles = self._collect_from_source(source)
                
                for article in articles:
                    article['source_name'] = source['name']
                    article['country'] = source['country']
                    article['language'] = source['language']
                    article['category'] = source['category']
                    article['collected_at'] = datetime.now().isoformat()
                
                all_articles.extend(articles)
                logger.info(f"Collected {len(articles)} articles from {source['name']}")
                
            except Exception as e:
                logger.error(f"Error collecting from {source['name']}: {e}")
        
        # Save collected data
        if all_articles:
            self._save_collected_data(all_articles)
        
        return all_articles
    
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
    
    def _save_collected_data(self, articles):
        """Save collected articles to CSV and JSON."""
        if not articles:
            logger.warning("No articles to save.")
            return
        
        # Create timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Ensure data directory exists
        os.makedirs('data', exist_ok=True)
        
        # Save as CSV
        df = pd.DataFrame(articles)
        csv_path = f'data/news_data_{timestamp}.csv'
        df.to_csv(csv_path, index=False)
        
        # Save as JSON
        json_path = f'data/news_data_{timestamp}.json'
        with open(json_path, 'w') as f:
            json.dump(articles, f, indent=2)
        
        logger.info(f"Saved {len(articles)} articles to {csv_path} and {json_path}")

if __name__ == "__main__":
    # Test the collector
    collector = GCCBusinessNewsCollector()
    articles = collector.collect_news()
    print(f"Collected {len(articles)} articles in total.") 