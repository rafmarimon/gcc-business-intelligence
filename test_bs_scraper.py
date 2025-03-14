import json
import requests
from bs4 import BeautifulSoup
import logging
import os
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("Test_Scraper")

def save_html_for_analysis(url, filename):
    """Save the HTML content of a URL for analysis"""
    try:
        # Headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        
        # Fetch the page
        logger.info(f"Fetching {url}...")
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            logger.error(f"Failed to fetch {url}: Status code {response.status_code}")
            return False
        
        # Save HTML to file
        os.makedirs('test_data', exist_ok=True)
        with open(f'test_data/{filename}', 'w', encoding='utf-8') as f:
            f.write(response.text)
        
        logger.info(f"Saved HTML to test_data/{filename}")
        return True
    except Exception as e:
        logger.error(f"Error saving HTML: {e}")
        return False

def test_scrape(url, selectors):
    """
    Test scraping a URL with the provided selectors
    """
    try:
        # Headers to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        
        # Fetch the page
        logger.info(f"Fetching {url}...")
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            logger.error(f"Failed to fetch {url}: Status code {response.status_code}")
            return
            
        # Parse with BeautifulSoup
        logger.info("Parsing HTML...")
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Find all article elements
        article_elements = soup.select(selectors['article_selector'])
        logger.info(f"Found {len(article_elements)} article elements")
        
        articles = []
        for i, article_el in enumerate(article_elements[:5]): # Process first 5 only for the test
            try:
                # Extract headline
                headline_el = article_el.select_one(selectors['headline_selector'])
                headline = headline_el.get_text().strip() if headline_el else "No headline found"
                
                # Extract link
                link_el = article_el.select_one(selectors['link_selector'])
                link = link_el.get('href') if link_el else "No link found"
                
                # Fix relative URLs
                if link and not (link.startswith('http://') or link.startswith('https://')) and not link.startswith("No link"):
                    base_url = '/'.join(url.split('/')[:3])  # Get domain part
                    link = f"{base_url}{'' if link.startswith('/') else '/'}{link}"
                
                # Extract summary
                summary_el = article_el.select_one(selectors['summary_selector'])
                summary = summary_el.get_text().strip() if summary_el else "No summary found"
                
                # Extract date
                date_el = article_el.select_one(selectors['date_selector'])
                date_str = date_el.get_text().strip() if date_el else "No date found"
                
                articles.append({
                    'headline': headline,
                    'link': link,
                    'summary': summary,
                    'date': date_str
                })
                
                logger.info(f"Article {i+1}:")
                logger.info(f"  Headline: {headline}")
                logger.info(f"  Link: {link}")
                logger.info(f"  Summary: {summary[:50]}..." if len(summary) > 50 else f"  Summary: {summary}")
                logger.info(f"  Date: {date_str}")
                logger.info("-" * 50)
                
            except Exception as e:
                logger.error(f"Error processing article {i+1}: {e}")
        
        return articles
    except Exception as e:
        logger.error(f"Error in test_scrape: {e}")
        return None

def inspect_html_structure(html_file):
    """Inspect the HTML structure to find better selectors"""
    try:
        with open(html_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for common article containers - expanded list
        potential_article_containers = [
            ('div.article', soup.select('div.article')),
            ('div.news-item', soup.select('div.news-item')),
            ('div.story', soup.select('div.story')),
            ('div.card', soup.select('div.card')),
            ('article', soup.select('article')),
            ('.post', soup.select('.post')),
            ('.news', soup.select('.news')),
            ('.content-list-item', soup.select('.content-list-item')),
            ('.entry', soup.select('.entry')),
            ('.item', soup.select('.item')),
            ('.story', soup.select('.story')),
            ('div[class*="article"]', soup.select('div[class*="article"]')),
            ('div[class*="story"]', soup.select('div[class*="story"]')),
            ('div[class*="news"]', soup.select('div[class*="news"]')),
            ('div[class*="post"]', soup.select('div[class*="post"]')),
            ('div[class*="card"]', soup.select('div[class*="card"]')),
            ('li[class*="article"]', soup.select('li[class*="article"]')),
            ('li[class*="story"]', soup.select('li[class*="story"]')),
            ('li[class*="news"]', soup.select('li[class*="news"]')),
        ]
        
        logger.info("Potential article containers:")
        for selector, elements in potential_article_containers:
            if elements:
                logger.info(f"  {selector}: {len(elements)} elements found")
                # Look at first element to find potential headline, link, etc.
                element = elements[0]
                
                # Get class attribute for the first element
                el_class = element.get('class')
                if el_class:
                    logger.info(f"    Class: {' '.join(el_class)}")
                
                # Check for headline elements
                headline_candidates = [
                    ('h1', element.select('h1')),
                    ('h2', element.select('h2')),
                    ('h3', element.select('h3')),
                    ('h4', element.select('h4')),
                    ('.title', element.select('.title')),
                    ('.headline', element.select('.headline')),
                    ('*[class*="title"]', element.select('*[class*="title"]')),
                    ('*[class*="headline"]', element.select('*[class*="headline"]')),
                    ('*[class*="head"]', element.select('*[class*="head"]')),
                ]
                
                for htype, headlines in headline_candidates:
                    if headlines:
                        logger.info(f"    Headline candidate ({htype}): {headlines[0].get_text().strip()[:50]}")
                        # Also check if this contains a link
                        links = headlines[0].select('a')
                        if links:
                            for link in links:
                                href = link.get('href', '')
                                logger.info(f"      Link in headline: {href[:50]}")
                
                # Check for link elements
                links = element.select('a')
                if links:
                    logger.info(f"    Link candidates: {len(links)} found")
                    for link in links[:3]:
                        href = link.get('href', '')
                        text = link.get_text().strip()
                        if text:
                            logger.info(f"      Link: {text[:30]} -> {href[:50]}")
                
                # Check for summary/description elements
                summary_candidates = [
                    ('.summary', element.select('.summary')),
                    ('.description', element.select('.description')),
                    ('.excerpt', element.select('.excerpt')),
                    ('.teaser', element.select('.teaser')),
                    ('p', element.select('p')),
                    ('*[class*="desc"]', element.select('*[class*="desc"]')),
                    ('*[class*="summary"]', element.select('*[class*="summary"]')),
                    ('*[class*="excerpt"]', element.select('*[class*="excerpt"]')),
                    ('*[class*="teaser"]', element.select('*[class*="teaser"]')),
                ]
                
                for stype, summaries in summary_candidates:
                    if summaries:
                        logger.info(f"    Summary candidate ({stype}): {summaries[0].get_text().strip()[:50]}")
                
                # Check for date elements
                date_candidates = [
                    ('.date', element.select('.date')),
                    ('.time', element.select('.time')),
                    ('.timestamp', element.select('.timestamp')),
                    ('time', element.select('time')),
                    ('*[class*="date"]', element.select('*[class*="date"]')),
                    ('*[class*="time"]', element.select('*[class*="time"]')),
                    ('*[datetime]', element.select('*[datetime]')),
                ]
                
                for dtype, dates in date_candidates:
                    if dates:
                        logger.info(f"    Date candidate ({dtype}): {dates[0].get_text().strip()[:30]}")
                
                logger.info("  " + "-" * 40)
        
        # Check for any DOM elements that have typical news article headline text
        all_text_elements = soup.find_all(text=True)
        potential_headlines = []
        
        for text in all_text_elements:
            # Skip if too short or just whitespace
            if len(text.strip()) < 20 or len(text.strip()) > 150:
                continue
                
            # Look for text that may be a headline (contains keywords, starts with capital, etc.)
            if re.search(r'(launch|announce|reveal|introduce|new|today|report)', text.lower()):
                parent = text.parent
                logger.info(f"Potential headline element ({parent.name}): {text.strip()[:50]}")
                logger.info(f"  Parent element: <{parent.name} class='{parent.get('class', '')}'>")
                
                # Look at what's around this element
                if parent.parent:
                    logger.info(f"  Grandparent: <{parent.parent.name} class='{parent.parent.get('class', '')}'>")
        
        return True
    except Exception as e:
        logger.error(f"Error inspecting HTML: {e}")
        return False

if __name__ == "__main__":
    # Save HTML for analysis
    save_html_for_analysis("https://gulfnews.com/business", "gulf_news.html")
    save_html_for_analysis("https://www.khaleejtimes.com/business", "khaleej_times.html")
    
    # Inspect HTML structure
    logger.info("\nInspecting Gulf News HTML structure:")
    inspect_html_structure("test_data/gulf_news.html")
    
    logger.info("\nInspecting Khaleej Times HTML structure:")
    inspect_html_structure("test_data/khaleej_times.html")
    
    # Updated selectors based on inspection
    gulf_news_selectors = {
        'article_selector': "div[class*='story']",
        'headline_selector': "*[class*='title'] a",
        'summary_selector': "*[class*='teaser']",
        'link_selector': "*[class*='title'] a",
        'date_selector': "time"
    }
    
    khaleej_times_selectors = {
        'article_selector': "article",
        'headline_selector': "h4 a",
        'summary_selector': "div.desc",
        'link_selector': "h4 a",
        'date_selector': ".time-elapsed"
    }
    
    # Test with the updated selectors
    logger.info("\nTesting Gulf News scraping with updated selectors:")
    gulf_news_url = "https://gulfnews.com/business"
    gulf_news_articles = test_scrape(gulf_news_url, gulf_news_selectors)
    
    logger.info("\nTesting Khaleej Times scraping with updated selectors:")
    khaleej_times_url = "https://www.khaleejtimes.com/business"
    khaleej_times_articles = test_scrape(khaleej_times_url, khaleej_times_selectors) 